import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import select_backup_skeleton as m

class SelectionTests(unittest.TestCase):
    def test_prefers_complete_binding_over_first_candidate(self):
        choices=[dict(source=0,name='ast_first'),dict(source=1,name='ast_complete')]
        scores=[dict(missing=['tail'],required_count=2,skeleton_count=1),dict(missing=[],required_count=2,skeleton_count=1)]
        with patch.object(m,'hierarchy_score',side_effect=scores):
            winner,proof=m.select_source(choices,[dict(path='a'),dict(path='b')],'/tmp','ms02_four')
        self.assertEqual('ast_complete',winner['name']);self.assertEqual([],proof['score']['missing'])
