"""Export original NGUI role icons without changing APK/cache source files.

UnitMaster uses I{g_id}; UIAtlas stores top-left pixel rectangles. Unity 3.5
Android format 2 stores little-endian RGBA4444, unlike UnityPy's modern mapping.
Requires Pillow and UnityPy only at generation time.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rtd.config import path_for
from PIL import Image


def decode_icon_texture(data,width,height,format):
    if format!=2 or width<=0 or height<=0 or len(data)<width*height*2:
        raise ValueError('Expected original Android RGBA4444 icon atlas')
    pixels=struct.unpack('<'+str(width*height)+'H',data[:width*height*2])
    rgba=bytes(((pixel>>shift)&15)*17 for pixel in pixels for shift in (12,8,4,0))
    return Image.frombytes('RGBA',(width,height),rgba).transpose(Image.Transpose.FLIP_TOP_BOTTOM)


def read_atlas_sprites(raw):
    # Empty MonoBehaviour name: 8-byte game ptr, 4-byte enabled/alignment,
    # 8-byte script ptr, 4-byte name. Then material ptr and sprite count.
    try:
        if struct.unpack_from('<i',raw,20)[0]!=0:raise ValueError('Unexpected atlas header')
        count=struct.unpack_from('<i',raw,32)[0]
        if not 0<count<=1024:raise ValueError('Unexpected sprite count')
        pos=36;result={}
        for _ in range(count):
            size=struct.unpack_from('<i',raw,pos)[0];pos+=4
            if not 0<size<=128 or pos+size>len(raw):raise ValueError('Invalid sprite name')
            name=raw[pos:pos+size].decode('utf-8');pos=(pos+size+3)//4*4
            fields=struct.unpack_from('<12f',raw,pos);pos+=48
            rect=fields[:4]
            if name in result or any(not x.is_integer() or x<0 for x in rect) or min(rect[2:])<=0:
                raise ValueError('Invalid or duplicate sprite rectangle')
            result[name]=tuple(map(int,rect))
        coordinates,pixel_size,replacement_file,replacement_id=struct.unpack_from('<ifii',raw,pos)
        if pos+16!=len(raw) or coordinates!=0 or pixel_size!=1 or replacement_file or replacement_id:
            raise ValueError('Unsupported atlas coordinates/replacement')
        return result
    except (struct.error,UnicodeDecodeError) as exc:
        raise ValueError('Truncated or invalid original atlas') from exc


def main():
    import UnityPy
    base=path_for('icon_sources');output=path_for('unit_icons')
    output.mkdir(parents=True,exist_ok=True)
    files={};sources={}
    def load(name):
        if name not in files:
            path=base/name
            files[name]=next(iter(UnityPy.load(str(path)).files.values()))
            sources[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        return files[name]
    def resolve(file,ptr):
        if ptr['m_FileID']:
            name=file.externals[ptr['m_FileID']-1].path.replace('\\','/').rsplit('/',1)[-1]
            file=load(name)
        return file.objects[ptr['m_PathID']]
    main=load('mainData')
    resources=dict(next(o for o in main.objects.values() if o.type.name=='ResourceManager').read_typetree()['m_Container'])
    icons={}
    for n in range(1,7):
        key=f'graphics/iconatlas/icon_atlas_{n:03}'
        go=resolve(main,resources[key]);fields=go.read_typetree()
        mono=next(resolve(go.assets_file,p) for kind,p in fields['m_Component'] if kind==114)
        raw=mono.get_raw_data();rects=read_atlas_sprites(raw)
        mat=resolve(mono.assets_file,dict(zip(('m_FileID','m_PathID'),struct.unpack_from('<ii',raw,24))))
        textures=mat.read_typetree()['m_SavedProperties']['m_TexEnvs']
        tex_ptr=next(value['m_Texture'] for name,value in textures if name['name']=='_MainTex')
        texture=resolve(mat.assets_file,tex_ptr);data=texture.read()
        image=decode_icon_texture(data.image_data,data.m_Width,data.m_Height,data.m_TextureFormat)
        for name,(x,y,w,h) in rects.items():
            if not name.startswith('I') or not name[1:].isdigit():continue
            id=int(name[1:])
            if id in icons or x+w>image.width or y+h>image.height:raise ValueError('Invalid atlas mapping')
            path=output/f'{id}.png';image.crop((x,y,x+w,y+h)).save(path,optimize=True)
            icons[id]=dict(atlas=key,rect=[x,y,w,h],sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    units=json.loads((path_for('master_data')/'UNIT_MASTER.json').read_text(encoding='utf-8-sig'))['result'][0]['data_list']
    mapping={str(u['id']):u['g_id'] for u in units}
    missing=[id for id,g_id in mapping.items() if g_id not in icons]
    manifest=dict(sources=sources,unit_icons=mapping,icons=icons,missing_units=missing)
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Exported {len(icons)} original icons; mapped {len(mapping)-len(missing)}/{len(mapping)} units; missing={missing}')


if __name__=='__main__':main()
