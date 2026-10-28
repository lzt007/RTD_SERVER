from ..common import ProtocolError, compact
from ..config import ROOT, STARTERS

def get_level_master(self, state, req, token, operation):
    player = state['player']
    result = []
    for entry in req.get('get_level_list', []):
        try:
            level = self.levels[int(entry['level_data_id'])]
        except (KeyError, ValueError, TypeError):
            raise ProtocolError(8197, 'Level data not recovered')
        if str(entry.get('hash')) != str(level['hash']):
            result.append(level)
    return dict(code=4096, session_id=token, result=result)



def get_master(self, state, req, token, operation):
    player = state['player']
    result = []
    for entry in req.get('get_data_list', []):
        table = self.master_table(entry['type'])
        if table is None:
            raise ProtocolError(8197, 'Master table not recovered: '+str(entry['type']))
        changed = str(entry.get('hash')) != str(table['hash'])
        item = dict(type=table['type'], hash=str(table['hash']), changed=changed)
        if not req.get('compare_hash_only'):
            item['data_list'] = table['data_list'] if changed else []
        result.append(item)
    return dict(code=4096, session_id=token, result=result,
                **{k:player[k] for k in ('quest_clear_flags', 'quest_new_flags',
                   'quest_challenge_state', 'quest_challenge_reward_state')})
    return dict(code=4096, session_id=token, result=result)


