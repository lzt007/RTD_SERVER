"""Load recovered master tables without importing historical account envelopes."""
import json
from ..config import path_for


def load_catalog():
    levels = {int(path.stem):json.loads(path.read_text(encoding='utf-8'))
              for path in (path_for('level_data')).glob('[0-9]*.json')}
    masters = {}
    for path in sorted((path_for('master_data')).glob('*_MASTER.json')):
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        for table in data['result']:
            kind = table['type']
            if kind in masters:
                raise RuntimeError('Ambiguous master type: '+str(kind))
            masters[kind] = {key:table[key] for key in ('type','hash','data_list')}
    return masters, levels
