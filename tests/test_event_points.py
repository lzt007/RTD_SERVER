"""Pure original-event accounting boundaries; synthetic inputs are not game victories."""
import copy
import unittest
from rtd.common import ProtocolError
from rtd.policies import event_points as points


REGISTERED={100001,100002,100003}


class EventPointTests(unittest.TestCase):
    def test_snapshot_counts_present_enemies_and_original_per_run_cap(self):
        quest=dict(sp_event_id=100002)
        enemies=[dict(flag=True,sp_event_point=700),dict(flag=True,sp_event_point=600),
                 dict(flag=False,sp_event_point=999)]
        self.assertEqual(points.freeze(quest,enemies,{100002}),dict(event_id=100002,maximum=999))
        self.assertEqual(points.freeze(dict(sp_event_id=0),[],{100002}),dict(event_id=0,maximum=0))
        for quest,enemies,registered in [(quest,enemies,set()),(dict(sp_event_id=True),[],{1}),
                (dict(sp_event_id=0),[dict(flag=True,sp_event_point=1)],{100002}),
                (dict(sp_event_id=100002),[dict(flag=True,sp_event_point=True)],{100002})]:
            with self.assertRaises(ProtocolError):points.freeze(quest,enemies,registered)

    def test_apply_retains_other_events_and_caps_persistent_points(self):
        state=dict(sp_event_points={'100001':7,'100002':99990},player={'unrelated':1})
        points.apply(state,20,dict(event_id=100002,maximum=25), REGISTERED)
        self.assertEqual(state,dict(sp_event_points={'100001':7,'100002':99999},player={'unrelated':1}))
        points.apply(state,1,dict(event_id=100003,maximum=1), REGISTERED)
        self.assertEqual(points.login_points(state, REGISTERED),[
            dict(sp_event_id=100001,point=7),dict(sp_event_id=100002,point=99999),dict(sp_event_id=100003,point=1)])

    def test_old_state_and_old_battle_accept_zero_without_creating_progress(self):
        state={'player':{'unchanged':1}};before=copy.deepcopy(state)
        self.assertEqual(points.login_points(state, REGISTERED),[])
        points.apply(state,0,None, REGISTERED);self.assertEqual(state,before)
        with self.assertRaises(ProtocolError):points.apply(state,1,None, REGISTERED)
        self.assertEqual(state,before)

    def test_invalid_results_and_snapshots_never_mutate(self):
        snapshot=dict(event_id=100002,maximum=4)
        for value in (True,-1,5,1000,'1',1.0,None):
            state={};before=copy.deepcopy(state)
            with self.assertRaises(ProtocolError):points.apply(state,value,snapshot, REGISTERED)
            self.assertEqual(state,before)
        for invalid in ({},dict(event_id=0,maximum=1),dict(event_id=100002,maximum=True),
                        dict(event_id=-1,maximum=0),dict(event_id=1,maximum=0),dict(event_id=100002,maximum=1000)):
            with self.assertRaises(ProtocolError):points.apply({},0,invalid, REGISTERED)

    def test_bad_old_storage_is_rejected_without_silent_reset(self):
        for invalid in (None,[],{'1':7},{'0100002':1},{100002:1},{'100002':True},{'100002':-1},{'100002':100000}):
            state=dict(sp_event_points=invalid);before=copy.deepcopy(state)
            with self.assertRaises(ProtocolError):points.login_points(state, REGISTERED)
            with self.assertRaises(ProtocolError):points.apply(state,1,dict(event_id=100002,maximum=1), REGISTERED)
            self.assertEqual(state,before)

    def test_original_point_gate_requires_enough_points_and_does_not_spend(self):
        quest=dict(open_sp_event_id=100002,open_sp_event_point=5,flag_no=9)
        state=dict(player={'quest_clear_flags':[0,0]},sp_event_points={'100002':4})
        before=copy.deepcopy(state)
        with self.assertRaises(ProtocolError):points.require_points(state,quest, REGISTERED)
        self.assertEqual(state,before)
        state['sp_event_points']['100002']=5;before=copy.deepcopy(state)
        points.require_points(state,quest, REGISTERED);self.assertEqual(state,before)

    def test_cleared_area_decoration_does_not_bypass_quest_entry_point_gate(self):
        state=dict(player={'quest_clear_flags':[0,2]})
        with self.assertRaises(ProtocolError):
            points.require_points(state,dict(open_sp_event_id=100002,open_sp_event_point=5,flag_no=9), REGISTERED)
        points.require_points(state,dict(open_sp_event_id=0,open_sp_event_point=0,flag_no=10), REGISTERED)
        self.assertNotIn('sp_event_points',state)


if __name__=='__main__':unittest.main()
