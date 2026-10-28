"""Cumulative experience for dropped units follows shipped level thresholds."""
import unittest
from rtd.services import battle_rewards


class UnitAcquisitionTest(unittest.TestCase):
    def test_drop_level_has_consistent_cumulative_experience(self):
        master=dict(category=1,grow=20)
        self.assertEqual(battle_rewards.unit_acquisition_exp(master,1),0)
        self.assertEqual(battle_rewards.unit_acquisition_exp(master,2),20)
        self.assertEqual(battle_rewards.unit_acquisition_exp(master,3),104)
        self.assertEqual(battle_rewards.unit_acquisition_exp(dict(category=2,grow=22),2),22)


if __name__ == '__main__':
    unittest.main()
