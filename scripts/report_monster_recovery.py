"""Generate an honest static mesh/texture inspection sheet (not a Unity screenshot)."""
import html
import json
import struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageChops
import UnityPy
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/resource-audit/monster-recovery'

def preview(env,texture_name):
    mesh=next(o for o in env.objects if o.type.name=='Mesh').read_typetree()
    vd=mesh['m_VertexData'];stride=vd['m_Streams[0]']['stride'];raw=bytes(vd['m_DataSize'])
    if (vd['m_CurrentChannels'],stride) not in ((9,20),(43,48)):raise ValueError('Unsupported preview layout')
    uv_offset=12 if stride==20 else 24
    vertices=[struct.unpack_from('<3f',raw,i*stride)+struct.unpack_from('<2f',raw,i*stride+uv_offset) for i in range(vd['m_VertexCount'])]
    tex=env.container[texture_name].read().image.convert('RGBA')
    lowx=min(v[0] for v in vertices);highx=max(v[0] for v in vertices)
    lowy=min(v[1] for v in vertices);highy=max(v[1] for v in vertices)
    scale=min(280/(highx-lowx),280/(highy-lowy))
    points=[(160+(v[0]-(lowx+highx)/2)*scale,160-(v[1]-(lowy+highy)/2)*scale) for v in vertices]
    buf=bytes(mesh['m_IndexBuffer']);triangles=[]
    for sub in mesh['m_SubMeshes']:
        inds=struct.unpack_from('<'+'H'*sub['indexCount'],buf,sub['firstByte'])
        if sub['isTriStrip']==2:
            triangles += [tuple(inds[i:i+3]) for i in range(len(inds)-2) if len(set(inds[i:i+3]))==3]
        elif sub['isTriStrip']==0:triangles += [tuple(inds[i:i+3]) for i in range(0,len(inds),3)]
        else:raise ValueError('Unsupported topology')
    image=Image.new('RGBA',(320,320),(240,242,245,255))
    for tri in sorted(triangles,key=lambda tri:sum(vertices[i][2] for i in tri)):
        p=[points[i] for i in tri];uv=[(vertices[i][3]*tex.width,(1-vertices[i][4])*tex.height) for i in tri]
        x0,y0=p[0];x1,y1=p[1];x2,y2=p[2];det=(x1-x0)*(y2-y0)-(x2-x0)*(y1-y0)
        if abs(det)<1e-6:continue
        def coeff(vals):
            a=((vals[1]-vals[0])*(y2-y0)-(vals[2]-vals[0])*(y1-y0))/det
            b=((x1-x0)*(vals[2]-vals[0])-(x2-x0)*(vals[1]-vals[0]))/det
            return a,b,vals[0]-a*x0-b*y0
        warped=tex.transform((320,320),Image.Transform.AFFINE,coeff([v[0] for v in uv])+coeff([v[1] for v in uv]),Image.Resampling.BILINEAR)
        mask=Image.new('L',(320,320));ImageDraw.Draw(mask).polygon(p,fill=255)
        image.paste(warped,(0,0),ImageChops.multiply(mask,warped.getchannel('A')))
    return image.convert('RGB')

def main():
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'images').mkdir(exist_ok=True)
    manifest=json.loads((ROOT/'config/monster-recovery.json').read_text())
    rows=[]
    for row in manifest['bundles']:
        env=UnityPy.load(str(ROOT/'resources/reconstructed/monsters/bundles'/row['bundle']))
        images=[]
        for name in row['textures']:
            path=OUT/'images'/(name+'.png');preview(env,name).save(path)
            images.append(f'<figure><img src="images/{path.name}" width="180"><figcaption>{html.escape(name)}</figcaption></figure>')
        if 'wolf' in row['model']:reason='新备份真实狼模型与配色；旧 Lv/特殊型对应关系为推测复用。'
        elif row['model'].endswith('_silver'):reason='原金史莱姆几何与蒙皮，灰银配色为推测重着色；未找回原银史莱姆画稿。'
        else:reason='原客户端同族素材复用；原等级/特殊型外形尚未找回。'
        rows.append('<tr><td><code>'+row['model']+'</code></td><td>'+reason+'<p><code>'+html.escape(row['source'])+'</code></p></td><td>'+''.join(images)+'</td></tr>')
    (OUT/'兼容修复预览.html').write_text('<!doctype html><meta charset="utf-8"><title>狼与史莱姆兼容修复</title><style>body{font:15px sans-serif;margin:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:10px;vertical-align:top}td:last-child{display:flex;flex-wrap:wrap}figure{margin:5px}figcaption{max-width:180px;overflow-wrap:anywhere;font-size:12px}code{overflow-wrap:anywhere}</style><h1>狼与史莱姆兼容修复预览</h1><p>以下为实际输出包中的网格和贴图所生成的离线静态预览，未运行 Unity：不含骨骼姿势、Billboard、阴影及游戏内尺寸，仅供外形与配色核对。原件存在的普通 Lv1、金 Lv1/Lv4 未替换。</p><p>测试关卡：11012 暴赫龙吼（暴赫の竜咆）；补充：11010 尖炎断崖。</p><table><tr><th>原引用／输出包模型名</th><th>来源与推测说明</th><th>实际贴图的静态网格预览</th></tr>'+''.join(rows)+'</table>',encoding='utf-8')

if __name__=='__main__':main()
