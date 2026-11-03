import copy
import hashlib
import json
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
        reconstruction=os.environ.get('RTD_SHINGETSU_RECONSTRUCTION','0')
        if reconstruction not in ('0','1'):
            raise RuntimeError('RTD_SHINGETSU_RECONSTRUCTION must be 0 or 1')
        self.shingetsu_reconstruction=None
        if reconstruction=='1':
            from ..masters.shingetsu import build_candidate,apply_missing
            self.shingetsu_reconstruction=build_candidate(self.masters,self.levels)
            self.masters,self.levels=apply_missing(self.masters,self.levels,self.shingetsu_reconstruction)
        self.delivery=Delivery(self.store,self.masters)
        content=os.environ.get('RTD_CONTENT_EXPERIMENTAL','1' if SETTINGS['features']['experimental_content'] else '0')
        if content not in ('0','1'):raise RuntimeError('RTD_CONTENT_EXPERIMENTAL must be 0 or 1')
        self.experimental_content=content=='1'
        visual = os.environ.get('RTD_VISUAL_RECOVERY', '1' if SETTINGS['features']['visual_recovery'] else '0')
        if visual not in ('0', '1'):
            raise RuntimeError('RTD_VISUAL_RECOVERY must be 0 or 1')
        self.visual_recovery = apply_visual_recovery(self.masters) if visual == '1' else None
        from ..policies.event_visuals import apply_event_visuals
        self.event_visual_substitutions=apply_event_visuals(self.masters,self.levels) if visual=='1' else []
        if self.event_visual_substitutions:
            self.visual_recovery['substitutions'] += self.event_visual_substitutions
            self.visual_recovery['quest_ids']=sorted(set(self.visual_recovery['quest_ids']) |
                {q for row in self.event_visual_substitutions for q in row['quest_ids']})
            self.visual_recovery['derived_hash']=self.masters[20]['hash']
            payload=json.dumps(self.masters[20]['data_list'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
            self.visual_recovery['payload_sha256']=hashlib.sha256(payload).hexdigest()
        from ..policies.event_content import audit_events, single_quests, recovered_asset_names
        self.event_quests,self.event_rejections=audit_events(self.masters,self.levels,recovered_asset_names())
        batch=os.environ.get('RTD_EVENT_RECONSTRUCTION','0')
        if batch not in ('0','1'):raise RuntimeError('RTD_EVENT_RECONSTRUCTION must be 0 or 1')
        self.event_reconstruction=None
        self.reconstructed_quests=set()
        if batch=='1':
            from ..masters.event_reconstruction import prepare_runtime
            baseline=set(self.event_quests)
            self.masters,self.levels,self.event_reconstruction=prepare_runtime(self.masters,self.levels,baseline)
            self.reconstructed_quests=set(self.event_reconstruction['ready_quests'])
            self.event_quests=baseline|self.reconstructed_quests
            self.event_rejections.update({int(k):v for k,v in self.event_reconstruction['blocked'].items()})
        configurable=(single_quests(self)|layer_quests(self))-{10001}
        self.operations=Operations(self.store,self.masters,lambda:load_pools(self.masters)[0],
            event_quests=configurable-self.blocked_quests,reconstructed_quests=self.reconstructed_quests,reconstructed_levels=self.levels,
            configurable_quests=configurable,playable_quests=(single_quests(self)|layer_quests(self)|{10000})-self.blocked_quests)

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


