"""Choose same-family artwork by actual legacy motion hierarchy coverage."""
from functools import lru_cache
from pathlib import Path
import UnityPy
from prepare_monster_recovery import hierarchy_paths, motion_paths, pointers
from backup_skeleton_compat import adapt_ms02_dragon_tail

@lru_cache(maxsize=None)
def hierarchy_score(path, source_model, motion_prefix):
    env=UnityPy.load(str(path));raw={o.path_id:(o.type.name,o.read_typetree()) for o in env.objects}
    root=next(i for i,(typ,t) in raw.items() if typ=='GameObject' and t.get('m_Name')=='ast_'+source_model)
    reached=set();todo=[root]
    while todo:
        pid=todo.pop()
        if pid in reached:continue
        reached.add(pid)
        for p in pointers(raw[pid][1]):
            if p['m_PathID']:
                if p['m_FileID']:raise ValueError('External skeleton dependency')
                todo.append(p['m_PathID'])
    trees={i:raw[i] for i in reached};trees,_=adapt_ms02_dragon_tail(trees,motion_prefix)
    paths=hierarchy_paths(trees);required=motion_paths(motion_prefix)
    missing=sorted(set().union(*(required-p for p in paths))) if paths else sorted(required)
    return dict(missing=missing,required_count=len(required),skeleton_count=len(paths))


def select_source(choices,sources,base,motion_prefix):
    """Preserve choice order as tie breaker, prefer complete actual motion binding."""
    ranked=[]
    for order,asset in enumerate(choices):
        path=Path(base)/sources[asset['source']]['path']
        try:
            score=hierarchy_score(str(path),asset['name'].removeprefix('ast_'),motion_prefix)
        except Exception as exc:
            score=dict(missing=['unscored: '+str(exc)],required_count=0,skeleton_count=0)
        ranked.append((len(score['missing']) if score['required_count'] else 1000000,order,asset,score))
        if score['required_count'] and not score['missing']:break
    ranked.sort(key=lambda r:(r[0],r[1]))
    _,_,winner,score=ranked[0]
    return winner,dict(motion_prefix=motion_prefix,selected=winner['name'],score=score,candidates=[dict(name=a['name'],**s) for _,_,a,s in ranked])
