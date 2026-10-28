import importlib.util
import hashlib
import json
import pathlib
import struct
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('export_admin_unit_icons',ROOT/'scripts/export_admin_unit_icons.py')
exporter=importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class UnitIconExportTest(unittest.TestCase):
    def test_old_android_rgba4444_channels_and_vertical_origin(self):
        # Bottom row red/green, top row blue/transparent white.
        data=struct.pack('<4H',0xf00f,0x0f0f,0x00ff,0xfff0)
        image=exporter.decode_icon_texture(data,2,2,2)
        self.assertEqual(image.tobytes(),bytes([0,0,255,255,255,255,255,0,255,0,0,255,0,255,0,255]))
        with self.assertRaises(ValueError):exporter.decode_icon_texture(data,2,2,33)

    def test_sprite_rectangles_use_pixel_coordinates_and_reject_truncation(self):
        raw=bytes(24)+struct.pack('<3i',0,11,1)+struct.pack('<i',3)+b'I13\0'
        raw+=struct.pack('<12f',2,3,80,84,*([0]*8))+struct.pack('<ifii',0,1,0,0)
        self.assertEqual(exporter.read_atlas_sprites(raw),{'I13':(2,3,80,84)})
        with self.assertRaises(ValueError):exporter.read_atlas_sprites(raw[:-1])

    def test_generated_original_icons_match_provenance_and_all_nonzero_master_ids(self):
        folder=ROOT/'resources/unit-icons'
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        for filename,sha in manifest['sources'].items():
            self.assertEqual(hashlib.sha256((ROOT/'resources/icon-sources'/filename).read_bytes()).hexdigest(),sha)
        for id,meta in manifest['icons'].items():
            self.assertEqual(hashlib.sha256((folder/f'{id}.png').read_bytes()).hexdigest(),meta['sha256'])
        for id,g_id in manifest['unit_icons'].items():
            self.assertEqual(str(g_id) in manifest['icons'],g_id!=0,id)
        self.assertEqual(manifest['unit_icons']['10000'],13)


if __name__=='__main__':unittest.main()
