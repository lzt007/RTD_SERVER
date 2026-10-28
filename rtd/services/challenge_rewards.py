"""Earned category medal rewards are delivered through the owned inbox."""
import copy
import re

from ..common import ProtocolError
from .presents import issue


def post_quest_challenge_reward(self,state,req,token,operation):
    reward_id=req.get('reward_id')
    # CreateRequest_PostQuestChallengeReward uses Dictionary<string,string>,
    # despite the unused integer DTO shipped alongside it.
    if isinstance(reward_id,str) and re.fullmatch(r'[1-9][0-9]{0,9}',reward_id):
        reward_id=int(reward_id)
    if type(reward_id) is not int or reward_id<=0:
        raise ProtocolError(8194,'Expected positive challenge reward id')
    master=next((m for m in self.masters[33]['data_list'] if m['id']==reward_id),None)
    if master is None:raise ProtocolError(8197,'Unknown challenge reward')
    player=state['player']
    result={k:master[k] for k in ('present_type','present_param_0','present_param_1')}
    result['reward_id']=reward_id
    if any(r['reward_id']==reward_id and r['state']==1 for r in player['quest_challenge_reward_state']):
        result=copy.deepcopy(state.get('challenge_reward_receipts',{}).get(str(reward_id),result))
    else:
        valid={(q['id'],q[k]) for q in self.masters[30]['data_list'] if q['category']==master['category']
               for k in ('challenge_id_0','challenge_id_1','challenge_id_2') if q[k]!=0}
        cleared={(r['quest_id'],r['challenge_id']) for r in player['quest_challenge_state'] if r['state']==1}
        if len(valid&cleared)<master['point']:
            raise ProtocolError(8197,'Challenge reward threshold not earned')
        if master['present_type'] not in (1,2,3,4):
            raise ProtocolError(8197,'Unsupported challenge gift kind')
        issue(state,master['present_type'],master['present_param_0'],master['present_param_1'],
              'エリア目標達成報酬')
        player['quest_challenge_reward_state']=[r for r in player['quest_challenge_reward_state']
                                                if r['reward_id']!=reward_id]
        player['quest_challenge_reward_state'].append(dict(reward_id=reward_id,state=1))
        state.setdefault('challenge_reward_receipts',{})[str(reward_id)]=copy.deepcopy(result)
        self.store.save(state)
    return dict(code=4096,session_id=token,result=result)
