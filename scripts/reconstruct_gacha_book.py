"""Build inferred map billboards from authentic gacha book sprites (not recovered map art).

Only the quad geometry, scale and binding are inferred. Inputs are never overwritten.
UnityPy is an offline build dependency, not a server dependency.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile

TEMPLATE_SHA256='8ee34859e01f71985f023f255933c838ff30da80848cf0efd0cdc9bda6b5dac8'
ATLAS_MEMBER='assets/bin/Data/sharedassets1.assets'
ATLAS_SHA256='7f7418d4b276136ce878a5d717a13f8da7ada75c4ddef5c8135ba1210a58e267'
POLICY='inferred-gacha-book-billboard-native-activation-v3'

def digest(data):return hashlib.sha256(data).hexdigest()
def ptr(path):return dict(m_FileID=0,m_PathID=path)
def vector(x,y,z):return dict(x=x,y=y,z=z)
def bounds():return dict(m_Center=vector(0,.68,0),m_Extent=vector(.505,.68,.01))

def sprites(raw):
    # Old UIAtlas.Sprite: aligned UTF8 name, outer/inner Rects, rotated/padding.
    result={}
    for color in range(1,7):
        name=f'book_0{color}'
        marker=struct.pack('<i',len(name))+name.encode()+b'\0'
        start=raw.find(marker)
        if start<0 or raw.find(marker,start+1)>=0:raise ValueError('Ambiguous original atlas sprite')
        outer=struct.unpack_from('<4f',raw,start+len(marker))
        if any(int(v)!=v for v in outer) or outer[2:]!=(101.,136.):
            raise ValueError('Unexpected original book sprite rectangle')
        result[color]=tuple(map(int,outer))
    return result

def build_gacha_book(apk,template,output,book_color=5):
    import UnityPy
    if type(book_color) is not int or book_color not in range(1,7):raise ValueError('Book color must be 1 through 6')
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    template=Path(template);source=template.read_bytes()
    if digest(source)!=TEMPLATE_SHA256:raise ValueError('Unaudited serialization template')
    apk=Path(apk)
    with zipfile.ZipFile(apk) as archive:
        atlas_bytes=archive.read(ATLAS_MEMBER)
    if digest(atlas_bytes)!=ATLAS_SHA256:raise ValueError('Original gacha atlas differs from audited bytes')
    atlas=UnityPy.load(atlas_bytes);a={o.path_id:o for o in atlas.objects}
    material=a[2].read_typetree()
    if material['m_SavedProperties']['m_TexEnvs'][0][1]['m_Texture']!=ptr(15):
        raise ValueError('Original atlas material binding changed')
    crop_rect=sprites(a[47].get_raw_data())[book_color]
    x,y,w,h=crop_rect
    original_image=a[15].read().image
    if original_image.size!=(512,512):raise ValueError('Original atlas dimensions changed')
    crop=original_image.crop((x,y,x+w,y+h))
    env=UnityPy.load(source);objects={o.path_id:o for o in env.objects}
    sf=objects[1].assets_file
    keep={1,6,26,42,52,609,1174,603,1160,1184,1214}
    sf.objects={i:o for i,o in sf.objects.items() if i in keep}
    sf.externals=[]
    name=f'ast_ms00_book_el_0{book_color}'
    def save(i,tree):objects[i].save_typetree(tree)
    root=objects[609].read_typetree()
    root.update(m_Name=name,m_IsActive=0,m_Component=[(4,ptr(1174)),(137,ptr(1214))])
    save(609,root)
    transform=objects[1174].read_typetree()
    transform.update(m_LocalRotation=dict(x=0.,y=0.,z=0.,w=1.),m_LocalScale=vector(1.,1.,1.),m_Children=[ptr(1160)])
    save(1174,transform)
    move=objects[603].read_typetree()
    move.update(m_Name='move',m_IsActive=0,m_Component=[(4,ptr(1160)),(111,ptr(1184))])
    save(603,move)
    bone=objects[1160].read_typetree()
    bone.update(m_LocalRotation=dict(x=0.,y=0.,z=0.,w=1.),m_LocalPosition=vector(0.,0.,0.),m_LocalScale=vector(1.,1.,1.),m_Children=[],m_Father=ptr(1174))
    save(1160,bone)
    renderer=objects[1214].read_typetree()
    renderer.update(m_GameObject=ptr(609),m_Materials=[ptr(6)],m_Mesh=ptr(42),m_Bones=[ptr(1160)],m_RootBone=ptr(1160),m_AABB=bounds(),m_UpdateWhenOffscreen=True)
    save(1214,renderer)
    mesh=objects[42].read_typetree()
    mesh.update(m_Name=name+'_quad',m_MeshCompression=0,m_LocalAABB=bounds())
    mesh['m_SubMeshes']=[dict(firstByte=0,indexCount=4,isTriStrip=2,triangleCount=2,firstVertex=0,vertexCount=4,localAABB=bounds())]
    # Match the original Unity 3.5 strip encoding; a six-index triangle
    # list is decoded as overlapping strip faces by the legacy reader.
    mesh['m_IndexBuffer']=list(struct.pack('<4H',0,1,3,2))
    mesh['m_Skin']=[{**{f'weight[{i}]':float(i==0) for i in range(4)},**{f'boneIndex[{i}]':0 for i in range(4)}} for _ in range(4)]
    mesh['m_BindPose']=[{f'e{r}{c}':float(r==c) for r in range(4) for c in range(4)}]
    vertex=mesh['m_VertexData'];vertex.update(m_CurrentChannels=43,m_VertexCount=4)
    vertex['m_Streams[0]']=dict(channelMask=43,offset=0,stride=48,align=16)
    for i in range(1,4):vertex[f'm_Streams[{i}]']=dict(channelMask=0,offset=0,stride=0,align=16)
    # Legacy Unity 3.5 interleaving: position, normal, UV0, tangent.
    vertex['m_DataSize']=b''.join(struct.pack('<12f',px,py,0,0,0,-1,u,v,1,0,0,1) for px,py,u,v in [(-.505,0,0,0),(.505,0,1,0),(.505,1.36,1,1),(-.505,1.36,0,1)])
    # Clear compressed payload so only the new four vertices are authoritative.
    for field,value in mesh['m_CompressedMesh'].items():
        if isinstance(value,dict):
            for key,val in value.items():
                if isinstance(val,list):value[key]=[]
                elif isinstance(val,bytes):value[key]=b''
                elif isinstance(val,(int,float)):value[key]=type(val)(0)
    save(42,mesh)
    tex=objects[26].read();tex.m_Name=name;tex.set_image(crop,target_format=4,mipmap_count=1);tex.save()
    mat=objects[6].read_typetree();mat['m_Name']=name
    mat['m_SavedProperties']=dict(m_TexEnvs=[({'name':'_MainTex'},dict(m_Texture=ptr(26),m_Scale=dict(x=1.,y=1.),m_Offset=dict(x=0.,y=0.)))],m_Floats=[({'name':'_Cutoff'},.1)],m_Colors=[({'name':'_Color'},dict(r=1.,g=1.,b=1.,a=1.))])
    save(6,mat)
    bundle=objects[1].read_typetree()
    dependencies=[ptr(i) for i in sorted(keep-{1})]
    bundle.update(m_Name=f'inferred-gacha-map-book-{book_color}',m_PreloadTable=dependencies,m_Container=[(name,dict(preloadIndex=0,preloadSize=len(dependencies),asset=ptr(609)))],m_MainAsset=dict(preloadIndex=0,preloadSize=0,asset=ptr(0)),m_ScriptCompatibility=[])
    save(1,bundle)
    original_names=list(env.file.files)
    for old in original_names:
        f=env.file.files.pop(old);unique='CustomAssetBundle-'+hashlib.md5(f'{POLICY}:{book_color}:{old}'.encode()).hexdigest();f.name=unique;env.file.files[unique]=f
    payload=env.file.save();output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(payload)
    validation=validate_book(output,book_color)
    rebuilt=UnityPy.load(payload)
    rebuilt_texture=next(o.read().image for o in rebuilt.objects if o.type.name=='Texture2D')
    if rebuilt_texture.tobytes()!=crop.tobytes():raise ValueError('Cropped original pixels changed during serialization')
    return dict(policy=POLICY,inferred=True,source_apk=apk.name,source_apk_sha256=digest(apk.read_bytes()),source_member=ATLAS_MEMBER,source_member_sha256=digest(atlas_bytes),source_atlas_path_id=47,source_texture_path_id=15,source_sprite=f'book_0{book_color}',source_rect_xywh=list(crop_rect),source_pixels_sha256=digest(crop.tobytes()),serialization_template=template.name,serialization_template_sha256=TEMPLATE_SHA256,prefab=name,generated_bundle=output.name,generated_sha256=digest(payload),original_internal_files=original_names,generated_internal_files=list(env.file.files),validation=validation,limitations=['Original gacha artwork; inferred flat quad and scale, not recovered original map model.','No live Unity client validation; visual scale, orientation and animation require device check.'])

def validate_book(path,color):
    import UnityPy
    env=UnityPy.load(str(path));a={o.path_id:o for o in env.objects}
    allowed={'AssetBundle','GameObject','Transform','Animation','SkinnedMeshRenderer','Mesh','Material','Texture2D','Shader'}
    if len(a)!=11 or any(o.type.name not in allowed for o in a.values()):raise ValueError('Unexpected retained objects')
    externals=0
    def check(tree):
        nonlocal externals
        if isinstance(tree,dict):
            if 'm_FileID' in tree and 'm_PathID' in tree:
                if tree['m_FileID']:externals+=1
                elif tree['m_PathID'] and tree['m_PathID'] not in a:raise ValueError('Dangling internal reference')
            for value in tree.values():check(value)
        elif isinstance(tree,(list,tuple)):
            for value in tree:check(value)
    for o in a.values():
        tree=o.read_typetree()
        check(tree)
        if o.type.name=='GameObject' and tree['m_IsActive']!=0:
            raise ValueError('Invalid Unity 3.5 native activation flag')
    if externals:raise ValueError('External dependencies remain')
    b=a[1].read_typetree();name=f'ast_ms00_book_el_0{color}'
    if [n for n,_ in b['m_Container']]!=[name] or a[609].read_typetree()['m_Name']!=name:raise ValueError('Wrong loader export')
    mesh=a[42].read_typetree()
    from UnityPy.helpers.MeshHelper import MeshHandler
    decoded=MeshHandler(a[42].read());decoded.process()
    if decoded.m_UV0!=[(0.,0.),(1.,0.),(1.,1.),(0.,1.)]:raise ValueError('Invalid decoded quad UVs')
    if len(decoded.m_Vertices)!=4 or any(abs(v[2])>1e-6 for v in decoded.m_Vertices):raise ValueError('Invalid decoded planar geometry')
    if len(mesh['m_Skin'])!=4 or len(mesh['m_BindPose'])!=1:raise ValueError('Invalid single-bone skin')
    if a[603].read_typetree()['m_Name']!='move' or a[1184].read_typetree()['m_GameObject']!=ptr(603):raise ValueError('Missing AnimationController attachment contract')
    shader=a[52].read_typetree()['m_Script']
    if 'Cull Off' not in shader or 'discard' not in shader:raise ValueError('Shader transparency or double-sided support missing')
    faces=decoded.get_triangles()
    if (len(faces)!=1 or len(faces[0])!=2
            or {frozenset(face) for face in faces[0]}!={frozenset((0,1,3)),frozenset((1,2,3))}
            or mesh['m_SubMeshes'][0]['isTriStrip']!=2
            or mesh['m_SubMeshes'][0]['triangleCount']!=len(faces[0])):
        raise ValueError('Invalid legacy triangle strip')
    if mesh['m_VertexData']['m_VertexCount']!=4 or len(mesh['m_IndexBuffer'])!=8:raise ValueError('Invalid quad')
    if a[26].read().image.size!=(101,136):raise ValueError('Wrong cropped texture')
    return dict(objects=len(a),external_references=externals,vertex_count=4,triangles=2,has_camera=False,has_particles=False,has_ui_scripts=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apk',type=Path,required=True);p.add_argument('--template',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    reports=[build_gacha_book(args.apk,args.template,args.output/f'ms00_book_el_0{color}.unity3d',color) for color in range(1,7)]
    (args.output/'resource-provenance.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
    print('Generated and structurally verified six inferred gacha book billboards')
