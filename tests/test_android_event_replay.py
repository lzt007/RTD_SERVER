"""Device replay must retain observed coordinates on high resolution phones."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from android_event_unlock_replay import input_point, reference_point, window_point


class DeviceCoordinatesTest(unittest.TestCase):
    def test_observed_phone_coordinate_is_not_clamped_to_emulator_width(self):
        self.assertEqual(input_point([1300.4, 2900.2], (1440, 3200)), [1300, 2900])

    def test_outside_or_invalid_observations_stop_instead_of_tapping(self):
        for point in ([1440, 20], [-1, 20], [20, float('nan')]):
            with self.subTest(point=point), self.assertRaises(ValueError):
                input_point(point, (1440, 3200))

    def test_reference_screen_actions_scale_to_phone(self):
        self.assertEqual(reference_point([540, 888], (1440, 3200)), [720, 1480])
        self.assertEqual(reference_point([540, 888], (1080, 1920)), [540, 888])

    def test_miui_compatibility_window_origin_is_added(self):
        self.assertEqual(window_point([1276, 353], (0, 138, 1440, 2678), (1440, 3200)), [1276, 491])
        self.assertEqual(window_point([638, 176], (0, 69, 720, 1339), (720, 1600)), [638, 245])

    def test_visible_edge_anchored_menu_button_uses_last_window_pixel(self):
        self.assertEqual(window_point([720, 347], (0, 69, 720, 1339), (720, 1600)), [719, 416])
        with self.assertRaises(ValueError):
            window_point([721, 347], (0, 69, 720, 1339), (720, 1600))

class WirelessCureTimingTest(unittest.TestCase):
    def test_delayed_wireless_acknowledgement_confirms_once(self):
        from android_event_unlock_play import CureController
        driver = CureController(True)
        state = dict(controlsUnlocked=True, gameState='GameStateBattle', fieldState=dict(
            partyLife=5000, partyMaxLife=17000, partySoul=20, skillDialog=dict(active=False),
            combatSkills=[dict(id=11000, type=2, available=True, partyIndex=1, point=[300, 700])]))
        self.assertEqual(driver.step(state, 0)['kind'], 'cure-open')
        state['fieldState']['skillDialog'] = dict(active=True, status='OPEN', id=11000,
            type=2, cost=2, partyIndex=1, buttons=[dict(action='ExecSkill', point=[250, 750])])
        self.assertEqual(driver.step(state, 20)['kind'], 'cure-confirm')
        self.assertEqual(driver.step(state, 21)['kind'], 'wait')
        state['fieldState'].update(partyLife=7500, partySoul=18, skillDialog=dict(active=False))
        self.assertEqual(driver.step(state, 22)['kind'], 'cure-completed')

    def test_unknown_skill_is_not_confirmed(self):
        from android_event_unlock_play import CureController
        driver = CureController(True)
        driver.pending = dict(phase='opening', party_index=1, life_before=5000, deadline=60)
        with self.assertRaises(RuntimeError):
            driver.step(dict(fieldState=dict(skillDialog=dict(active=True, id=99999))), 1)

class NativeBattleBoardTest(unittest.TestCase):
    def test_unused_class_board_is_cycled_by_normal_touch(self):
        from android_event_unlock_play import battle_choice
        state = dict(panelDetails=[dict(point=[x, y], way=0, **{'class': 1})
                                   for y in (100, 200) for x in (100, 200, 300, 400)],
                     fieldState=dict(attackEstimates=[[0]*8 for _ in range(6)],
                                     enemyLife=4476, partyLife=13044, partyMaxLife=17263))
        points, action = battle_choice(state)
        self.assertEqual(len(points), 8)
        self.assertEqual(action['kind'], 'battle-cycle')
        self.assertEqual(action['estimated_damage'], 0)

class AllPanelsStrategyTest(unittest.TestCase):
    def test_mixed_board_uses_one_adjacent_snake_without_class_filtering(self):
        from android_event_unlock_play import all_panel_chain
        panels = [dict(point=[x,y], **{'class': i % 5}) for i,(x,y) in enumerate(
            [(x,y) for y in (100,200) for x in (100,200,300,400)])]
        points = all_panel_chain(panels)
        self.assertEqual(len(set(map(tuple, points))), 8)
        for a,b in zip(points, points[1:]):
            self.assertEqual(abs(a[0]-b[0])+abs(a[1]-b[1]), 100)
