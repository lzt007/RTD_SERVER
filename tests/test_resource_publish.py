import hashlib
import tempfile
import unittest
from pathlib import Path
from rtd import resource_catalog as catalog

class ResourcePublishTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a = self.root/'a.unity3d'; self.a.write_bytes(b'old')
        self.b = self.root/'b.unity3d'; self.b.write_bytes(b'dep')
        self.output = self.root/'published'

    def publish(self, dependencies=None):
        return catalog.publish_resources({'Android/a.unity3d': self.a, 'Android/b.unity3d': self.b}, dependencies or {'Android/a.unity3d':['Android/b.unity3d']}, self.output)

    def test_same_length_replacement_keeps_old_blob_and_allocates_version(self):
        first = self.publish(); old = catalog.load_snapshot(self.output)
        self.a.write_bytes(b'new'); second = self.publish(); new = catalog.load_snapshot(self.output)
        self.assertNotEqual(first, second)
        a, b = old['resources']['Android/a.unity3d'], new['resources']['Android/a.unity3d']
        self.assertNotEqual(a['cacheVersion'], b['cacheVersion'])
        self.assertEqual((self.output/a['downloadPath'].removeprefix('/resources/v1/')).read_bytes(), b'old')
        self.assertEqual(b['sha256'], hashlib.sha256(b'new').hexdigest())

    def test_unchanged_publish_preserves_snapshot_and_versions(self):
        self.assertEqual(self.publish(), self.publish())

    def test_resolve_returns_full_transitive_closure(self):
        self.publish()
        result = catalog.resolve_snapshot(catalog.load_snapshot(self.output), ['Android/a.unity3d'])
        self.assertEqual([x['id'] for x in result['resources']], ['Android/a.unity3d','Android/b.unity3d'])
        self.assertEqual(len(result['closureDigest']), 64)

    def test_invalid_dependency_does_not_activate(self):
        self.publish(); active = (self.output/'active.json').read_bytes()
        for dependencies in [{'Android/a.unity3d':['missing']}, {'Android/a.unity3d':['Android/b.unity3d'],'Android/b.unity3d':['Android/a.unity3d']}]:
            with self.assertRaises(ValueError): self.publish(dependencies)
            self.assertEqual((self.output/'active.json').read_bytes(), active)

    def test_same_basename_has_distinct_cache_versions(self):
        catalog.publish_resources({'one/x.unity3d':self.a,'two/x.unity3d':self.b}, {}, self.output)
        entries = list(catalog.load_snapshot(self.output)['resources'].values())
        self.assertNotEqual(entries[0]['cacheVersion'], entries[1]['cacheVersion'])

    def test_unknown_root_is_rejected(self):
        self.publish()
        with self.assertRaises(ValueError):catalog.resolve_snapshot(catalog.load_snapshot(self.output), ['unknown'])

    def test_activation_failure_retains_previous_snapshot_and_never_reuses_versions(self):
        from unittest.mock import patch
        self.publish(); active=(self.output/'active.json').read_bytes()
        self.a.write_bytes(b'new')
        original=catalog._atomic
        def interrupt(path,data):
            if path.name=='active.json':raise OSError('simulated interruption')
            return original(path,data)
        with patch.object(catalog,'_atomic',side_effect=interrupt):
            with self.assertRaises(OSError):self.publish()
        self.assertEqual((self.output/'active.json').read_bytes(),active)
        reserved=__import__('json').loads((self.output/'versions.json').read_bytes())['next']
        self.a.write_bytes(b'alt');self.publish()
        version=catalog.load_snapshot(self.output)['resources']['Android/a.unity3d']['cacheVersion']
        self.assertGreaterEqual(version,reserved)

    def test_empty_resource_and_unsafe_identifier_rejected(self):
        self.a.write_bytes(b'')
        with self.assertRaises(ValueError):self.publish()
        self.a.write_bytes(b'ok')
        for identifier in ['../x.unity3d','/x.unity3d','a//x.unity3d','a\\x.unity3d',
                           'a/./x.unity3d','a/../x.unity3d','é.unity3d',
                           'a\n.unity3d','a .unity3d','a?.unity3d', 'a'*249+'.unity3d']:
            with self.assertRaises(ValueError):catalog.publish_resources({identifier:self.a},{},self.output)

    def test_ascii_identifier_boundaries(self):
        for identifier in ['.unity3d','Android/V1016/A_b-9.unity3d','a'*248+'.unity3d']:
            catalog._validate_id(identifier)

    def test_new_cache_versions_do_not_collide_with_legacy_versions(self):
        self.publish()
        for entry in catalog.load_snapshot(self.output)['resources'].values():
            self.assertGreaterEqual(entry['cacheVersion'], 1000000000)

    def test_export_contract_is_included_and_invalid_names_rejected(self):
        catalog.publish_resources({'a.unity3d':self.a},{'a.unity3d':[]},self.output,
                                  required_prefabs={'a.unity3d':['ast_probe']})
        entry=catalog.resolve_snapshot(catalog.load_snapshot(self.output),['a.unity3d'])['resources'][0]
        self.assertEqual(entry['requiredPrefabs'],['ast_probe'])
        with self.assertRaises(ValueError):
            catalog.publish_resources({'a.unity3d':self.a},{'a.unity3d':[]},self.output,
                                      required_prefabs={'a.unity3d':['bad\nname']})
