"""One-crystal local continuation for an existing supported single-floor run."""
from ..common import ProtocolError
from .shop import number
from .presents import USER_FIELDS
from ..policies.quest_content import layer_quests
from ..policies.event_content import single_quests


def continue_quest(api,state,req,token,operation):
    floor=number(req.get('floor'));count=number(req.get('quest_continue'),True)
    retry=number(req.get('retry',0));battle=state.get('battle');player=state['player']
    run=api.store.active_run(player['user_id'])
    supported=(single_quests(api)-{10001})|layer_quests(api)
    if not battle or battle['quest_id'] not in supported or battle['quest_status']!=1 or floor!=len(state.get('battle_history',[])) or not run:
        raise ProtocolError(9472,'No supported active single-floor battle')
    current=battle['quest_continue'];receipt=state.get('battle_continue_receipt',{})
    def response():return dict(code=4096,session_id=token,result={k:player[k] for k in USER_FIELDS})
    expected=dict(run_id=run,count=count)
    if 'battle_history' in state:expected['floor']=floor
    if count==current and receipt==expected:return response()
    if count!=current+1:raise ProtocolError(9472,'Continue count does not match active battle')
    # The wire has no run ID. Without a receipt in this run, retry>0 could
    # belong to a previous run. Reject instead of charging a different run.
    if retry:raise ProtocolError(8197,'No continuation receipt in the current run')
    funds=[player[k] for k in ('free_paid_point','paid_point','total_paid_point')]
    if any(type(n) is not int or n<0 for n in funds) or funds[0]+funds[1]!=funds[2]:
        raise ProtocolError(8197,'Invalid local currency balance')
    if funds[2]<1:raise ProtocolError(8961,'Not enough local crystals')
    player['free_paid_point' if funds[0] else 'paid_point']-=1
    player['total_paid_point']-=1
    battle['quest_continue']=count
    state['battle_continue_receipt']=expected
    api.store.save(state)
    return response()
