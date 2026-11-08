import unittest
from rtd.resource_dependencies import build_dependency_graph

class ResourceDependenciesTest(unittest.TestCase):
    def test_external_serialized_files_resolve_to_bundle_dependencies(self):
        graph=build_dependency_graph({'a.unity3d':{'files':['CAB-a'],'externals':['archive:/CAB-b/CAB-b','Resources/unity_builtin_extra']},'b.unity3d':{'files':['CAB-b'],'externals':[]}})
        self.assertEqual(graph,{'a.unity3d':['b.unity3d'],'b.unity3d':[]})
    def test_unknown_external_is_not_treated_as_leaf(self):
        with self.assertRaises(ValueError):build_dependency_graph({'a.unity3d':{'files':['CAB-a'],'externals':['CAB-absent']}})
    def test_ambiguous_internal_identity_is_rejected(self):
        with self.assertRaises(ValueError):build_dependency_graph({'a.unity3d':{'files':['CAB-same'],'externals':[]},'b.unity3d':{'files':['CAB-same'],'externals':[]}})
    def test_self_reference_is_not_a_dependency_cycle(self):
        self.assertEqual(build_dependency_graph({'a.unity3d':{'files':['CAB-a'],'externals':['CAB-a']}}),{'a.unity3d':[]})
