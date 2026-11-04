import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from backup_skeleton_compat import adapt_ms02_dragon_tail

class TailRenameTests(unittest.TestCase):
    def test_names_only_and_embedded_paths_follow(self):
        trees={1:('GameObject',{'m_Name':'mn_c_main'}),2:('Transform',{'m_GameObject':{'m_PathID':1},'m_Children':[{'m_PathID':4}]}),3:('GameObject',{'m_Name':'mn_c_tail'}),4:('Transform',{'m_GameObject':{'m_PathID':3},'m_Father':{'m_PathID':2},'m_Children':[],'m_LocalPosition':{'x':1}}),5:('AnimationClip',{'m_PositionCurves':[{'path':'mn_c_main/mn_c_tail/en_c_tail'}]})}
        actual,changes=adapt_ms02_dragon_tail(trees,'ms02_dra')
        self.assertEqual(trees[4],actual[4]);self.assertEqual('mn_c_tail',trees[3][1]['m_Name'])
        self.assertEqual('mn_c_tail_01',actual[3][1]['m_Name'])
        self.assertEqual('mn_c_main/mn_c_tail_01/en_c_tail',actual[5][1]['m_PositionCurves'][0]['path'])
        self.assertEqual(1,len(changes))
        self.assertEqual(trees,adapt_ms02_dragon_tail(trees,'ms03_dra')[0])
