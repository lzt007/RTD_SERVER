"""Reconcile every original gap against actual generated and installed outputs."""
import csv
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def report():
    base=ROOT/'docs/resource-audit/new-backup'
    gaps=list(csv.DictReader((base/'复用决策表.csv').open(encoding='utf-8-sig')))
    candidates=json.loads((ROOT/'resources/reconstructed/backup-recovery/validation.json').read_text())
    installed=json.loads((ROOT/'config/monster-recovery.json').read_text())
    by_model={r['model']:r for r in candidates}
    hashes={r['bundle']:r['sha256'] for r in installed['bundles']}
    result=[]
    for gap in gaps:
        name=gap['原引用']
        matches=[by_model[name[4:]]] if gap['类别']=='模型' and name[4:] in by_model else [r for r in candidates if name in r.get('textures',{})]
        success=[r for r in matches if r.get('status')=='validated_candidate']
        ready=[r for r in success if hashes.get(r['bundle'])==r['sha256']]
        canonical=gap['类别']=='模型' and (ROOT/'resources/bundles'/(name[4:]+'.unity3d')).is_file()
        status='已有原优先资源，保留' if canonical else '已安装兼容资源，待实机验收' if ready else '已生成校验候选，未安装' if success else '转换待解决' if matches else '无同族来源，保留原处理' if not gap['已有同族候选'] else '尚未生成，保留原处理'
        result.append(dict(category=gap['类别'],original=name,material_match=gap['新备份是否命中'],inferred_material=gap['新备份是否命中']!='找到',status=status,models=[r['model'] for r in matches],errors=[r['error'] for r in matches if r.get('error')]))
    from collections import Counter
    summary=dict(total=len(result),status=dict(Counter(r['status'] for r in result)))
    (base/'本次逐项修复结果.json').write_text(json.dumps(dict(summary=summary,items=result),ensure_ascii=False,indent=2)+'\n')
    lines=['# 本次缺口修复结果','',f'原缺口共 {len(result)} 项。','']
    lines.extend(f"- {status}：{count} 项" for status,count in summary['status'].items())
    lines.extend(['','明细见 `本次逐项修复结果.json`。','', '以上是本地构建和安装结果，未代表远端部署或实机验收；显示、释放和通关结算分别验收，既有通关闪退仍未解决。'])
    (base/'本次缺口修复结果.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':report()
