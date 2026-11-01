import copy
import os
import time

from ..config import ROOT, STARTERS, SETTINGS
from ..common import ProtocolError, compact
from ..storage.store import Store
from .routes import ROUTES
from .quests import settle_tutorial
from ..policies.tutorial import tutorial_credit
from ..masters.catalog import load_catalog
from ..policies.visual_recovery import apply_visual_recovery
from ..policies.stamina import recover
from ..policies.unit_collection import sync_collection
from ..policies.gacha_pools import load_pools
from ..diagnostics.logging import summary, account_label
from ..operations.configuration import Operations
from ..operations.presents import Delivery
from ..policies.quest_content import VERIFIED_QUESTS,SINGLE_QUESTS,layer_quests

class API:
    def __init__(self, database):
        self.blocked_quests = set(SETTINGS.get('features', {}).get('blocked_quests', []))
        self.store = Store(database)
        self.masters, self.levels = load_catalog()
        self.delivery=Delivery(self.store,self.masters)
        content=os.environ.get('RTD_CONTENT_EXPERIMENTAL','1' if SETTINGS['features']['experimental_content'] else '0')
        if content not in ('0','1'):raise RuntimeError('RTD_CONTENT_EXPERIMENTAL must be 0 or 1')
        self.experimental_content=content=='1'
        visual = os.environ.get('RTD_VISUAL_RECOVERY', '1' if SETTINGS['features']['visual_recovery'] else '0')
        if visual not in ('0', '1'):
            raise RuntimeError('RTD_VISUAL_RECOVERY must be 0 or 1')
        self.visual_recovery = apply_visual_recovery(self.masters) if visual == '1' else None
        configurable=(SINGLE_QUESTS|layer_quests(self))-{10001}
        self.operations=Operations(self.store,self.masters,lambda:load_pools(self.masters)[0],
            event_quests=configurable-self.blocked_quests,
            configurable_quests=configurable,playable_quests=(SINGLE_QUESTS|layer_quests(self)|{10000})-self.blocked_quests)

    def master_table(self,kind):
        return self.operations.quest_table() if kind==30 else self.masters.get(kind)

    tutorial_credit = tutorial_credit
    settle_tutorial = settle_tutorial

    def call(self, operation, req, token='', user_id=None):
        self.store.local.trace = {}
        if req.get('ver') != '2.4.0':
            raise ProtocolError(8193, 'Client version must be 2.4.0')
        with self.store.transaction():
            if operation == 'create_user':
                state = self.store.create(req)
                if sync_collection(state):
                    self.store.save(state)
                self.store.local.trace = dict(account=account_label(state['player']['user_id']), after=summary(state))
                result = copy.deepcopy(state['player'])
                # The shipped LitJson mapper rejects unknown members, even between
                # superficially similar player/unit response types.
                for field in ('system_flag', 'payment_total'):
                    result.pop(field)
                result.update(get_units=[{k:v for k,v in unit.items() if k != 'favorite'}
                                         for unit in state['units']], party=state['party'])
                return dict(code=4096, session_id='', result=result)
            if operation == 'auth_user':
                state, token = self.store.authenticate(req.get('uuid'))
                self.store.local.trace = dict(account=account_label(state['player']['user_id']), before=summary(state))
                recovered = recover(state['player'], time.time())
                collection_changed = sync_collection(state)
                if self.tutorial_credit(state) or recovered or collection_changed:
                    self.store.save(state)
                self.store.local.trace['after'] = summary(state)
                return dict(code=4096, session_id=token, result=state['player'])
            state = self.store.session(token, user_id)
            player = state['player']
            self.store.local.trace = dict(account=account_label(player['user_id']), before=summary(state))
            handler = ROUTES.get(operation)
            if handler is None:
                raise ProtocolError(8197, 'Not implemented: '+operation)
            recovered = recover(player, time.time())
            collection_changed = sync_collection(state)
            if recovered or collection_changed:
                self.store.save(state)
            result = handler(self, state, req, token, operation)
            if sync_collection(state):
                self.store.save(state)
            self.store.local.trace['after'] = summary(state)
            return result


