"""Evidence-scoped naming adaptation; never adds bones or changes transforms."""
import copy


def adapt_ms02_dragon_tail(trees, motion_prefix):
    result=copy.deepcopy(trees);changes=[]
    if motion_prefix!='ms02_dra':return result,changes
    transforms={pid:t for pid,(typ,t) in result.items() if typ=='Transform'}
    def name(tid):return result[transforms[tid]['m_GameObject']['m_PathID']][1]['m_Name']
    for tid,t in transforms.items():
        if name(tid)!='mn_c_tail':continue
        parent=t['m_Father']['m_PathID']
        if parent not in transforms or name(parent)!='mn_c_main':raise ValueError('Unexpected dragon tail parent')
        if any(name(ch['m_PathID'])=='mn_c_tail_01' for ch in transforms[parent]['m_Children']):
            raise ValueError('Ambiguous dragon tail rename')
        gid=t['m_GameObject']['m_PathID'];result[gid][1]['m_Name']='mn_c_tail_01'
        changes.append(dict(game_object_id=gid,transform_id=tid,before='mn_c_tail',after='mn_c_tail_01',inferred=True,reason='Original type7 ms02_dra motions bind mn_c_main/mn_c_tail_01; recovered dragon uses same tail position under mn_c_main with unsuffixed name. Bone IDs, transforms, bindposes and weights unchanged.'))
    if changes:
        for _,(typ,t) in result.items():
            if typ!='AnimationClip':continue
            for key in ('m_RotationCurves','m_CompressedRotationCurves','m_EulerCurves','m_PositionCurves','m_ScaleCurves','m_FloatCurves'):
                for curve in t.get(key,[]):
                    parts=curve['path'].split('/')
                    for i in range(1,len(parts)):
                        if parts[i-1]=='mn_c_main' and parts[i]=='mn_c_tail':parts[i]='mn_c_tail_01'
                    curve['path']='/'.join(parts)
    return result,changes
