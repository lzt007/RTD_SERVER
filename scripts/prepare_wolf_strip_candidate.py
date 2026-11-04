"""Offline wolf v2: native Unity 3.5 strip topology; never deploys resources."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import UnityPy
import prepare_monster_recovery as legacy


def decode_strip(indices):
    result=[]
    for i in range(len(indices)-2):
        a,b,c=indices[i:i+3]
        if len({a,b,c})<3:continue
        result.append((b,a,c) if i%2 else (a,b,c))
    return result


def canonical(t):
    return min(tuple(t),tuple(t[1:]+t[:1]),tuple(t[2:]+t[:2]))


def stripify(triangles):
    out=[]
    for a,b,c in triangles:
        if not out:out.extend((a,b,c));continue
        n=len(out)
        out.extend((out[-1],a))
        if n%2:out.append(a)
        out.extend((a,b,c))
    assert [canonical(t) for t in decode_strip(out)]==[canonical(t) for t in triangles]
    return out


def build(output):
    output.mkdir(parents=True,exist_ok=True)
    reports=[]
    configured=[r for r in json.loads((legacy.ROOT/'config/monster-recovery.json').read_text())['bundles'] if 'wolf' in r['model']]
    for previous in configured:
        model=previous['model'];source=legacy.WS/previous['source']
        textures={name:legacy.WS/value['source'] for name,value in previous['textures'].items()}
        path=output/(model+'.unity3d')
        report=legacy.convert_model(source,path,model,textures)
        env=UnityPy.load(str(path));proof=[]
        for obj in env.objects:
            if obj.type.name!='Mesh':continue
            tree=obj.read_typetree();original=struct.unpack('<'+'H'*(len(tree['m_IndexBuffer'])//2),bytes(tree['m_IndexBuffer']));packed=[]
            for sub in tree['m_SubMeshes']:
                start=sub['firstByte']//2;indices=original[start:start+sub['indexCount']]
                triangles=[tuple(indices[i:i+3]) for i in range(0,len(indices),3)]
                strip=stripify(triangles)
                assert max(strip)<tree['m_VertexData']['m_VertexCount']
                sub.update(firstByte=len(packed)*2,indexCount=len(strip),isTriStrip=2,triangleCount=len(triangles))
                packed.extend(strip)
                proof.append(dict(triangles=len(triangles),strip_indices=len(strip),decoded_triangles=len(decode_strip(strip)),oriented_triangle_equality=True,max_index=max(strip),vertices=tree['m_VertexData']['m_VertexCount']))
            tree['m_IndexBuffer']=list(struct.pack('<'+'H'*len(packed),*packed));obj.save_typetree(tree)
        unique='CustomAssetBundle-'+hashlib.md5(('wolf-strip-v2-candidate:'+model).encode()).hexdigest()
        sf=next(iter(env.objects)).assets_file
        sf.name=unique
        env.file.files={unique:sf}
        report['internal_file']=unique
        path.write_bytes(env.file.save())
        check=UnityPy.load(str(path))
        for obj in check.objects:
            if obj.type.name=='Mesh':
                tree=obj.read_typetree();assert all(s['isTriStrip']==2 for s in tree['m_SubMeshes'])
                assert len(tree['m_IndexBuffer'])==len(packed)*2
        report.update(policy='wolf-strip-v2-candidate',sha256=hashlib.sha256(path.read_bytes()).hexdigest(),strip_validation=proof,runtime_verified=False)
        exports=set(check.container)
        expected={'ast_'+model,*textures}
        assert expected<=exports
        report['reference_coverage']={'expected':sorted(expected),'missing':sorted(expected-exports)}
        reports.append(report)
    (output/'validation.json').write_text(json.dumps(reports,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    build(parser.parse_args().output)
