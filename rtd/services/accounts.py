import datetime as dt
import unicodedata
from ..common import ProtocolError, compact
from ..config import ROOT, STARTERS
from ..policies.login_rewards import daily
from ..policies.event_points import login_points
from ..policies.helper_rewards import claim as claim_helper


def change_user_name(self,state,req,token,operation):
    name=req.get('user_name')
    if (not isinstance(name,str) or not 1<=len(name)<=32 or not name.strip()
            or any(unicodedata.category(char) in ('Cc','Cs') for char in name)):
        raise ProtocolError(8448,'Invalid local player name')
    if state['player']['user_name']!=name:
        state['player']['user_name']=name
        self.store.save(state)
    return dict(code=4096,session_id=token,result=[])

def login(self, state, req, token, operation):
    player = state['player']
    reward = daily(self,state)
    help_count,received=claim_helper(self,state)
    result = dict(friend_point=player['friend_point'], help_count=help_count,
                  received_friend_point=received, login_days=player['login_days'],
                  login_bonus=reward['calendar'], sequence_login_days=player['sequence_login_days'],
                  sequence_login_bonus=reward['bonus'], review_bonus=False,
                  move_password='', unit_collection=state['unit_collection'],
                  quest_challenge_state=player['quest_challenge_state'],
                  quest_challenge_reward_state=player['quest_challenge_reward_state'],
                  sp_event_point_list=login_points(state,{r['sp_event_id'] for r in self.masters[34]['data_list']}),
                  payment_total=0, bonus_flags=state.get('bonus_flags',[0]*256))
    return dict(code=4096, session_id=token, result=result)


