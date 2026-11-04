"""Reproducible offline legacy wolf animation/CPU skin audit. numpy, Pillow, UnityPy."""
import copy,json,struct,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageChops
import UnityPy
import prepare_monster_recovery as legacy
from prepare_wolf_strip_candidate import decode_strip

OUT=legacy.ROOT/'resources/reconstructed/wolf-strip-v2-candidate'

def matrix(t):
    x,y,z,w=[t['m_LocalRotation'][k] for k in 'xyzw'];q=np.array([x,y,z,w]);q/=np.linalg.norm(q);x,y,z,w=q
    r=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),0],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),0],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),0],[0,0,0,1.]])
    r[:3,:3]@=np.diag([t['m_LocalScale'][k] for k in 'xyz']);r[:3,3]=[t['m_LocalPosition'][k] for k in 'xyz'];return r

def sample(keys,time):
    if time<=keys[0]['time']:return keys[0]['value']
    if time>=keys[-1]['time']:return keys[-1]['value']
    a,b=next((a,b) for a,b in zip(keys,keys[1:]) if a['time']<=time<=b['time']);dt=b['time']-a['time'];u=(time-a['time'])/dt
    # Unity legacy curves use cubic Hermite component interpolation.
    return {k:(2*u**3-3*u*u+1)*a['value'][k]+(u**3-2*u*u+u)*dt*a['outSlope'][k]+(-2*u**3+3*u*u)*b['value'][k]+(u**3-u*u)*dt*b['inSlope'][k] for k in a['value']}

def clips():
    cat=json.loads((legacy.ROOT/'docs/resource-audit/loading-chain/catalog.json').read_text());out={}
    with zipfile.ZipFile(legacy.APK) as z:
        for obj in cat['objects'].values():
            if obj['type']!='AnimationClip' or obj['name'] not in ['ms01_wolf_wait_01','ms01_wolf_atk_01']:continue
            src=cat['sources'][cat['files'][obj['file']]['source']];entry=next(x['path'].split(':',1)[1] for x in src['origins'] if 'inputs/original/game.apk:' in x['path'])
            out[obj['name']]=next(x for x in UnityPy.load(z.read(entry)).objects if x.path_id==obj['path_id']).read_typetree()
    return out

def run():
    report=[];motions=clips()
    for model in ['ms01_wolf_lv1','ms01_wolf_lv3']:
        env=UnityPy.load(str(OUT/(model+'.unity3d')));objects={o.path_id:(o.type.name,o.read_typetree()) for o in env.objects};trans={i:t for i,(typ,t) in objects.items() if typ=='Transform'}
        def name(i):return objects[trans[i]['m_GameObject']['m_PathID']][1]['m_Name']
        def walk(i,path=''):
            yield path,i
            for c in trans[i]['m_Children']:
                j=c['m_PathID'];yield from walk(j,path+'/'+name(j) if path else name(j))
        moves=[dict(walk(i)) for i in trans if name(i)=='move'];rows=[]
        for rid,(typ,renderer) in objects.items():
            if typ!='SkinnedMeshRenderer':continue
            mesh=objects[renderer['m_Mesh']['m_PathID']][1];vd=mesh['m_VertexData'];vertices=np.array(struct.unpack('<'+'f'*(len(vd['m_DataSize'])//4),bytes(vd['m_DataSize']))).reshape(-1,5);v=np.column_stack((vertices[:,:3],np.ones(len(vertices))))
            assert vd['m_CurrentChannels']==9 and vd['m_Streams[0]']['stride']==20
            assert all(not x.get('m_NumItems',0) for x in mesh['m_CompressedMesh'].values())
            binds=[np.array([[b[f'e{r}{c}'] for c in range(4)] for r in range(4)]) for b in mesh['m_BindPose']]
            indices=struct.unpack('<'+'H'*(len(mesh['m_IndexBuffer'])//2),bytes(mesh['m_IndexBuffer']));triangles=decode_strip(indices)
            own=next(p for p in moves if renderer['m_Bones'][0]['m_PathID'] in p.values());stats=[];panels=[]
            for motion,clip in [('rest',None)]+list(motions.items()):
                duration=0 if clip is None else max(k['time'] for field in ['m_PositionCurves','m_RotationCurves','m_ScaleCurves'] for c in clip[field] for k in c['curve']['m_Curve'])
                for fraction in [0,.25,.5,.75,1]:
                    ts=copy.deepcopy(trans)
                    for field,prop in [('m_PositionCurves','m_LocalPosition'),('m_RotationCurves','m_LocalRotation'),('m_ScaleCurves','m_LocalScale')]:
                        for cv in ([] if clip is None else clip[field]):
                            if cv['curve']['m_Curve']:ts[own[cv['path']]][prop]=sample(cv['curve']['m_Curve'],duration*fraction)
                    cache={}
                    def world(i):
                        if not i:return np.eye(4)
                        if i not in cache:cache[i]=world(ts[i]['m_Father']['m_PathID'])@matrix(ts[i])
                        return cache[i]
                    # Explicit renderer-local output: inverse(rendererWorld) * boneWorld * bindpose.
                    rt=next(i for i,t in ts.items() if t['m_GameObject']==renderer['m_GameObject']);inverse=np.linalg.inv(world(rt));skin=[inverse@world(b['m_PathID'])@bp for b,bp in zip(renderer['m_Bones'],binds)]
                    result=np.zeros((len(v),4))
                    for j,weights in enumerate(mesh['m_Skin']):
                        for k in range(4):result[j]+=weights[f'weight[{k}]']*(skin[weights[f'boneIndex[{k}]']]@v[j])
                    assert np.isfinite(result).all();edge=max(float(np.linalg.norm(result[a,:3]-result[b,:3])) for tri in triangles for a,b in zip(tri,tri[1:]+tri[:1]));stats.append(dict(motion=motion,fraction=fraction,bounds_min=result[:,:3].min(0).tolist(),bounds_max=result[:,:3].max(0).tolist(),max_triangle_edge=edge,rest_vertex_error=float(np.max(np.linalg.norm(result[:,:3]-v[:,:3],axis=1))) if motion=='rest' else None))
                    panels.append((motion,fraction,result))
            tex=env.container[model+'_fire'].read().image.convert('RGBA')
            canvas=Image.new('RGB',(1600,960),'white');draw=ImageDraw.Draw(canvas)
            for n,(motion,fraction,points) in enumerate(panels):
                col=n%5;row=n//5
                # Fixed view across all samples; renderer-local axes, no per-frame rescale.
                xy=[(160+float(p[0])*230,230-float(p[1])*230) for p in points]
                panel=Image.new('RGBA',(320,320),(240,242,245,255))
                for tri in sorted(triangles,key=lambda tri:sum(points[i][2] for i in tri)):
                    p=[xy[i] for i in tri];uv=[(vertices[i][3]*tex.width,(1-vertices[i][4])*tex.height) for i in tri]
                    x0,y0=p[0];x1,y1=p[1];x2,y2=p[2];det=(x1-x0)*(y2-y0)-(x2-x0)*(y1-y0)
                    if abs(det)<1e-6:continue
                    def coeff(vals):
                        aa=((vals[1]-vals[0])*(y2-y0)-(vals[2]-vals[0])*(y1-y0))/det
                        bb=((x1-x0)*(vals[2]-vals[0])-(x2-x0)*(vals[1]-vals[0]))/det
                        return aa,bb,vals[0]-aa*x0-bb*y0
                    warped=tex.transform((320,320),Image.Transform.AFFINE,coeff([u[0] for u in uv])+coeff([u[1] for u in uv]),Image.Resampling.BILINEAR)
                    mask=Image.new('L',(320,320));ImageDraw.Draw(mask).polygon(p,fill=255)
                    panel.paste(warped,(0,0),ImageChops.multiply(mask,warped.getchannel('A')))
                ImageDraw.Draw(panel).text((5,5),motion+' '+str(fraction),fill='black')
                canvas.paste(panel.convert('RGB'),(col*320,row*320))
            canvas.save(OUT/(model+f'-renderer-{rid}-cpu.png'))
            rows.append(dict(renderer=rid,samples=stats,compressed_mesh_empty=True,native_vertex_stream=True))
        report.append(dict(model=model,renderers=rows))
    (OUT/'cpu-skin-validation.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':run()
