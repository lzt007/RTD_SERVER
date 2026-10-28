"""Pin real master probability boundaries without flaky statistical assertions."""
import unittest
from rtd.masters.catalog import load_catalog
from rtd.services.battle_generation import generate_enemies
from rtd.common import ProtocolError


class FixedRoll:
    def __init__(self, percent):
        self.percent = percent

    def randint(self, low, high):
        return self.percent if (low,high)==(1,100) else high


class BattleGenerationTest(unittest.TestCase):
    def test_moving_object_preserves_navigation_code_without_loot_master_or_roll(self):
        masters,_=load_catalog();table=next(t for t in masters[21]['data_list'] if t['id']==10000)
        table=dict(table,enemy1_drop_id=102,enemy1_rate=100)
        drops={d['id']:d for d in masters[22]['data_list'] if d['id']!=102}
        types={table['enemy1_set_id']:dict(type=21)}
        result=generate_enemies(table,dict(map_data='01',width=1),drops,FixedRoll(1),enemy_masters=types)
        self.assertEqual((result[0]['drop_data_id'],result[0]['drop_unit_id']),(102,0))
        override={102:dict(no_drop_weight=0,entries=[dict(unit_id=10000,weight=100,level_min=1,level_max=1)])}
        again=generate_enemies(table,dict(map_data='01',width=1),drops,FixedRoll(1),enemy_masters=types,drop_overrides=override)
        self.assertEqual(again,result)

    def test_missing_original_drop_is_controlled_and_explicit_override_can_supply_it(self):
        masters,_=load_catalog();table=next(t for t in masters[21]['data_list'] if t['id']==10000)
        table=dict(table,enemy1_drop_id=999999,enemy1_rate=100)
        drops={d['id']:d for d in masters[22]['data_list']}
        with self.assertRaises(ProtocolError) as error:
            generate_enemies(table,dict(map_data='01',width=1),drops,FixedRoll(1))
        self.assertEqual(error.exception.args[0],8197)
        override={999999:dict(no_drop_weight=0,entries=[dict(unit_id=10000,weight=100,level_min=1,level_max=1)])}
        result=generate_enemies(table,dict(map_data='01',width=1),drops,FixedRoll(1),drop_overrides=override)
        self.assertEqual((result[0]['drop_data_id'],result[0]['drop_unit_id']),(999999,10000))

    def test_drop_bonus_retries_only_empty_roll_without_extra_presence_or_books(self):
        masters,_=load_catalog();table=next(t for t in masters[21]['data_list'] if t['id']==10000)
        drops={d['id']:d for d in masters[22]['data_list']}
        table=dict(table,enemy1_rate=100)
        class Rolls:
            def __init__(self,values):self.values=iter(values);self.calls=[]
            def randint(self,lo,hi):
                self.calls.append((lo,hi));return next(self.values) if (lo,hi)==(1,100) else hi
        # First enemy rolls empty then a book; boss/death each present+book.
        rng=Rolls([1,100,1,1,1,1,1])
        result=generate_enemies(table,dict(map_data='01',width=1),drops,rng,drop_attempts=2)
        self.assertEqual(result[0]['drop_unit_id'],10000)
        self.assertEqual(sum(c==(1,100) for c in rng.calls),7)
        rng=Rolls([1,1,1,1,1,1])
        result=generate_enemies(table,dict(map_data='01',width=1),drops,rng,drop_attempts=2)
        self.assertEqual(result[0]['drop_unit_id'],10000)
        self.assertEqual(sum(c==(1,100) for c in rng.calls),6)

    def test_presence_empty_drop_and_weighted_level_boundaries(self):
        masters, _ = load_catalog()
        table=next(t for t in masters[21]['data_list'] if t['id']==10000)
        drops={d['id']:d for d in masters[22]['data_list']}
        # Select the audited 80%-presence treasure, with a 60%-drop record
        # solely for the boundary fixture; production master stays unchanged.
        table=dict(table,enemy1_rate=80)
        level=dict(map_data='01',width=1)
        for roll,present,book in ((1,True,10000),(60,True,10000),
                                  (61,True,0),(80,True,0),(81,False,0),(100,False,0)):
            with self.subTest(roll=roll):
                result=generate_enemies(table,level,drops,FixedRoll(roll))
                self.assertIs(result[0]['flag'],present)
                self.assertEqual(result[0]['drop_unit_id'],book)
                self.assertEqual(result[0]['drop_unit_level'],3 if book else 0)
                self.assertTrue(all(e['flag'] for e in result[1:]))
        maximum=generate_enemies(table,level,drops,FixedRoll(100))
        self.assertEqual((maximum[1]['drop_unit_id'],maximum[1]['drop_unit_level']),(10034,6))
        self.assertEqual((maximum[2]['drop_unit_id'],maximum[2]['drop_unit_level']),(11030,1))


if __name__ == '__main__':
    unittest.main()
