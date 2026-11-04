"""Conservative render-state gate for mapping backup shaders to the native shader.
No shader name alone establishes compatibility. Unknown states block conversion.
"""
import re


def render_signature(tree):
    script=tree.get('m_Script','')
    # Compiled programs carry implementation text, not ShaderLab render states.
    header=script.split('Program "',1)[0]
    directives={}
    for key in ('Cull','Blend','BlendOp','ZWrite','ZTest','ColorMask','Offset','AlphaTest','Fog','Lighting','Stencil'):
        directives[key]=[' '.join(s.split()) for s in re.findall(r'(?im)^\s*'+key+r'\s+([^\n{}]+)',header)]
    tags=[(k.lower(),v.lower()) for k,v in re.findall(r'"(QUEUE|RenderType|IgnoreProjector)"\s*=\s*"([^"]+)"',header,re.I)]
    props=re.search(r'Properties\s*\{(.*?)\n\}',header,re.S)
    properties=re.sub(r'\s+','',props.group(1)) if props else ''
    shader=re.search(r'Shader\s+"([^"]+)"',script)
    return dict(shader=shader.group(1) if shader else tree.get('m_Name'),directives=directives,tags=tags,properties=properties,passes=len(re.findall(r'\bPass\s*\{',script)))


def validate_shader_mapping(source_tree,target_tree):
    source=render_signature(source_tree);target=render_signature(target_tree)
    if source['passes']!=1 or re.search(r'\b(Stencil|UsePass|GrabPass)\b',source_tree.get('m_Script','')):
        raise ValueError('Complex/multipass shader requires explicit native mapping')
    if source!=target:
        mismatch=[k for k in source if source[k]!=target[k]]
        raise ValueError('Unverified shader mapping '+str(source['shader'])+': '+','.join(mismatch))
    return dict(render_state_compatible=True,signature=source,
                scope='ShaderLab render state/properties only; GPU program equivalence requires separate evidence')


def validate_material_overrides(material):
    """Do not discard modern per-material state unsupported by the native schema."""
    for key,allowed in (('m_CustomRenderQueue',(-1,None)),('m_ShaderKeywords',('',None)),('stringTagMap',([],{},None)),('disabledShaderPasses',([],None))):
        if material.get(key) not in allowed:
            raise ValueError('Unsupported material rendering override '+key+': '+str(material.get(key)))
    return dict(material_render_overrides_compatible=True)


def native_shader_for(source_tree,target_tree):
    """Return native GPU program with an explicitly verified ShaderLab state map."""
    import copy
    result=copy.deepcopy(target_tree)
    source=render_signature(source_tree)
    if source['shader']=='Character/brightnessCullBack':
        signature=render_signature(target_tree)
        comparable=dict(source);comparable['shader']=signature['shader']
        comparable['directives']=dict(source['directives']);comparable['directives']['Cull']=signature['directives']['Cull']
        if comparable!=signature or source['directives']['Cull'] not in ([],['Back']):
            raise ValueError('brightnessCullBack differs beyond supported cull state')
        result['m_Name']=source_tree['m_Name']
        result['m_Script']=result['m_Script'].replace('Shader "Character/brightness"','Shader "Character/brightnessCullBack"',1)
        # Omitted Cull is the source's native Back default; retain the exact syntax.
        replacement='  Cull Back' if source['directives']['Cull'] else ''
        result['m_Script']=re.sub(r'(?m)^\s*Cull Off\s*$',replacement,result['m_Script'],count=1)
    proof=validate_shader_mapping(source_tree,result)
    proof['native_mapping']='brightness-cull-back' if source['shader']=='Character/brightnessCullBack' else 'brightness-native'
    return result,proof
