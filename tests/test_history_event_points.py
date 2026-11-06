import unittest
from rtd.services.battle_generation import generate_enemies
from test_battle_generation import FixedRoll

class HistoryPointsTest(unittest.TestCase):
    def test_missing_points_are_scoped_and_preserve_explicit_zero(self):
        table={}
        for prefix in ('enemy1','boss','death'):
            table.update({prefix+'_id':1,prefix+'_set_id':41028,prefix+'_drop_id':0,prefix+'_rate':100})
        args=(table,dict(map_data='01',width=1),{0:dict(id=0,**{f'unit{i}_{k}':0 for i in range(1,5) for k in ('rate','id','lv_min','lv_max')})})
        def points(**kw):
            return [e['sp_event_point'] for e in generate_enemies(*args,rng=FixedRoll(1),enemy_masters={41028:dict(type=24)},**kw)]
        self.assertEqual(points(event_id=100001),[1,1,1])
        self.assertEqual(points(event_id=100002),[0,0,0])
        self.assertEqual(points(event_id=100001,drop_overrides={0:dict(entries=[],no_drop_weight=1,sp_event_point=0)}),[0,0,0])
        self.assertEqual(points(event_id=100001,drop_overrides={0:dict(entries=[],no_drop_weight=1)}),[1,1,1])

    def test_target_points_reach_original_gate(self):
        from rtd.policies.event_points import freeze, apply, require_points
        for event, target in ((100000,40103),(100001,41028),(100003,41040)):
            table={}
            for prefix in ('enemy1','boss','death'):
                table.update({prefix+'_id':1,prefix+'_set_id':target,prefix+'_drop_id':0,prefix+'_rate':100})
            drop=dict(id=0,**{f'unit{i}_{k}':0 for i in range(1,5) for k in ('rate','id','lv_min','lv_max')})
            enemies=generate_enemies(table,dict(map_data='0101010101',width=5),{0:drop},rng=FixedRoll(1),event_id=event)
            snapshot=freeze(dict(sp_event_id=event),enemies,{event})
            state={}
            apply(state,5,snapshot,{event})
            require_points(state,dict(open_sp_event_id=event,open_sp_event_point=5),{event})
            self.assertEqual(state['sp_event_points'][str(event)],5)

    def test_recovered_targets_only_and_explicit_values(self):
        from rtd.policies.event_point_recovery import missing_point
        for event, target in ((100000,40103),(100001,41028),(100003,41040)):
            self.assertEqual(missing_point(event,target),1)
            self.assertEqual(missing_point(event,31030),0)
            self.assertEqual(missing_point(event,22000),0)
        self.assertEqual(missing_point(100002,41040),0)
