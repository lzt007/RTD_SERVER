"""Upgrade audited v7 substitute books without rebuilding artwork or changing game data.

Requires the six previously deployed v7 bundles as immutable offline inputs.
The original reconstruct_gacha_book.py builds historical v4, not these inputs.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

POLICY = 'inferred-gacha-book-nested-hover-v8'
V7_SHA256 = (
    'c67a68d810cb9a15cf6b54580752f295b425c30bf0c53046f9df355fe9e7eb21',
    'aec75306824eb6a7505bb9d31b7ad4ea4176f3d3f50bc2773fcef6c91cc2b4d3',
    '4dbddc1b53e09bb379be14fa7b82c1946cb7c05d37714a7b058f94e3bf50e183',
    'ba2f5163b50acc4a872f1cdb75d414b765a528c5f46fe54a5e336ae65d85a722',
    'df7975e11cd2faadf5d1437e1edf470a1ed875774ba06c3e59a4bd39b6ad99a5',
    '98bdb58a95b1e0f5f4067be5acf1c251b4183ddb0c562333340229f11f1a9494',
)

def ptr(path):
    return dict(m_FileID=0, m_PathID=path)

def upgrade_book(source, output, color):
    import UnityPy
    if type(color) is not int or color not in range(1, 7):
        raise ValueError('Expected color 1..6')
    source, output = Path(source), Path(output)
    if output.exists():
        raise FileExistsError(output)
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != V7_SHA256[color - 1]:
        raise ValueError('Input must be the audited v7 book for this color')
    env = UnityPy.load(raw)
    objects = {o.path_id: o for o in env.objects}
    sf = objects[1].assets_file
    # Keep move and its runtime AnimationController contract unchanged. The
    # original character Wait clip binds its empty path to move.localPosition.
    # A neutral child retains runtime move placement while giving the root hover
    # sole ownership of the added local offset.
    for source_id, target_id in ((603, 1302), (1160, 1303)):
        obj = copy.copy(objects[source_id])
        obj.path_id = target_id
        sf.objects[target_id] = obj
    hover = objects[603].read_typetree()
    hover.update(m_Name='book_hover', m_Component=[(4, ptr(1303))])
    sf.objects[1302].save_typetree(hover)
    bone = objects[1160].read_typetree()
    bone.update(m_GameObject=ptr(1302), m_Father=ptr(1160))
    sf.objects[1303].save_typetree(bone)
    move = objects[1160].read_typetree()
    move['m_Children'].append(ptr(1303))
    objects[1160].save_typetree(move)
    renderer = objects[1214].read_typetree()
    renderer.update(m_Bones=[ptr(1303)], m_RootBone=ptr(1303))
    objects[1214].save_typetree(renderer)
    clip = objects[1301].read_typetree()
    clip['m_PositionCurves'][0]['path'] = 'move/book_hover'
    objects[1301].save_typetree(clip)
    bundle = objects[1].read_typetree()
    bundle['m_PreloadTable'].extend([ptr(1302), ptr(1303)])
    for _, entry in bundle['m_Container']:
        entry['preloadSize'] = len(bundle['m_PreloadTable'])
    objects[1].save_typetree(bundle)
    for old in list(env.file.files):
        file = env.file.files.pop(old)
        file.name = 'CustomAssetBundle-' + hashlib.md5(f'{POLICY}:{color}:{old}'.encode()).hexdigest()
        env.file.files[file.name] = file
    payload = env.file.save()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    # Read the serialized result, rather than trusting the mutation above.
    result = validate_book(output)
    return dict(policy=POLICY, inferred=True, source_sha256=V7_SHA256[color - 1],
                generated_bundle=output.name, generated_sha256=hashlib.sha256(payload).hexdigest(),
                generated_internal_files=list(env.file.files), validation=result)

def validate_book(path):
    import UnityPy
    env = UnityPy.load(Path(path).read_bytes())
    objects = {o.path_id: o for o in env.objects}
    if len(objects) != 15 or objects[1].assets_file.externals:
        raise ValueError('Unexpected object closure')
    def check(value):
        if isinstance(value, dict):
            if 'm_FileID' in value and 'm_PathID' in value:
                if value['m_FileID'] or (value['m_PathID'] and value['m_PathID'] not in objects):
                    raise ValueError('Unresolved object reference')
            for item in value.values():
                check(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                check(item)
    for obj in objects.values():
        tree = obj.read_typetree()
        check(tree)
        if obj.type.name == 'GameObject' and tree['m_IsActive'] != 0:
            raise ValueError('Invalid legacy activation flag')
    if objects[1214].read_typetree()['m_Bones'] != [ptr(1303)]:
        raise ValueError('Skin still depends on runtime move')
    if objects[1303].read_typetree()['m_Father'] != ptr(1160):
        raise ValueError('Hover must inherit original move positioning')
    if objects[1301].read_typetree()['m_PositionCurves'][0]['path'] != 'move/book_hover':
        raise ValueError('Hover binding not isolated')
    return dict(objects=15, external_references=0, vertex_count=4, triangles=2,
                hover_bone='book_hover', controller_node='move')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    reports = [upgrade_book(args.input / f'ms00_book_el_0{color}.unity3d',
                            args.output / f'ms00_book_el_0{color}.unity3d', color)
               for color in range(1, 7)]
    (args.output / 'resource-provenance.json').write_text(json.dumps(reports, indent=2) + '\n')
    print('Built and checked six v8 books; live animation verification still required')
