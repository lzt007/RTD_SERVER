import copy
from ..common import ProtocolError, compact
from ..config import ROOT, STARTERS
from ..policies.instance_ids import allocate_instance_ids
from ..policies.gacha_pools import draw

def buy_gacha(self, state, req, token, operation):
    player = state['player']
    if str(req.get('gacha_id')) != '20000' or str(req.get('tutorial_flag')).lower() != 'true':
        raise ProtocolError(8197, 'Only the first tutorial summon is supported')
    if state.get('tutorial_summon_receipt'):
        result=state['tutorial_summon_receipt']
    else:
        if not player['quest_clear_flags'][0] & 2 or player['free_paid_point'] < 5:
            raise ProtocolError(8197, 'Tutorial summon is not ready')
        # New tutorial draws obey the same exclusions as the rare pool.
        pool,_=self.operations.gacha(20000)
        unit_id=draw(pool['entries'],1)[0]['unit_id']
        unit=dict(instance_id=allocate_instance_ids(state,1)[0],
            user_id=player['user_id'],unit_id=unit_id,member_id=0,leader=0,
            level=1,exp=0,bonus_life=0,bonus_attack=0,bonus_heal=0,bonus_limit=0,attribute_exp=0,favorite=0)
        state['units'].append(unit)
        player['free_paid_point']-=5
        player['total_paid_point']-=5
        player['tutorial_flags'][0] |= 1
        fields=('user_id','user_name','action_point','max_action_point','action_point_recover',
            'game_money','total_paid_point','paid_point','free_paid_point','friend_point',
            'rank','exp','max_unit','max_cost','max_friend','login_days','sequence_login_days')
        result={k:player[k] for k in fields}
        result['unit']={k:v for k,v in unit.items() if k!='leader'}
        state['tutorial_summon_receipt']=copy.deepcopy(result)
        self.store.save(state)
    return dict(code=4096, session_id=token, result=result)


