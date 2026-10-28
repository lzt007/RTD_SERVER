"""Explicit local pools, independent of unavailable historical gacha tables."""
import hashlib
import json
import secrets
from pathlib import Path
from ..config import path_for
from ..common import compact


def load_pools(masters,path=None):
    data=json.loads(Path(path or path_for('gacha_pools')).read_text(encoding='utf-8-sig'))
    if (not isinstance(data,dict) or set(data)!={'version','normal','rare'}
            or type(data['version']) is not int or data['version']!=1):
        raise ValueError('Expected local gacha pool configuration version 1')
    units={u['id']:u for u in masters[10]['data_list']}
    for name in ('normal','rare'):
        rows=data[name]
        if not isinstance(rows,list) or not 1<=len(rows)<=256:
            raise ValueError('Expected 1-256 local pool entries')
        seen=set()
        for row in rows:
            if (not isinstance(row,dict) or set(row)!={'unit_id','level','weight'}
                    or any(type(n) is not int for n in row.values())
                    or row['unit_id'] not in units or row['unit_id'] in seen
                    or not 1<=row['level']<=units[row['unit_id']]['lv_max']
                    or not 1<=row['weight']<=1000000):
                raise ValueError('Invalid local gacha entry')
            seen.add(row['unit_id'])
    digest=hashlib.sha256(compact(data).encode()).hexdigest()
    return {name:data[name] for name in ('normal','rare')},digest


def draw(pool,count,rng=None):
    rng=rng or secrets.SystemRandom();total=sum(row['weight'] for row in pool)
    result=[]
    for _ in range(count):
        roll=rng.randint(1,total);cumulative=0
        for row in pool:
            cumulative+=row['weight']
            if roll<=cumulative:
                result.append(dict(row));break
    return result
