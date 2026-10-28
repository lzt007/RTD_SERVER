"""Single-floor random choices sampled once into the durable order snapshot."""
import secrets
from ..common import ProtocolError


def generate_enemies(table, level, drops, rng=None, drop_attempts=1, drop_overrides=None, enemy_masters=None):
    rng = rng or secrets.SystemRandom()
    enemies = []

    def add(prefix, x=0, y=0):
        field_object=(enemy_masters or {}).get(table[prefix+'_set_id'],{}).get('type') in (20,21)
        drop_id=table[prefix+'_drop_id']
        override=(drop_overrides or {}).get(drop_id)
        drop = dict(id=drop_id) if field_object or override is not None else drops.get(drop_id)
        if drop is None:raise ProtocolError(8197,'Missing recovered drop master: '+str(drop_id))
        present = rng.randint(1,100) <= table[prefix+'_rate']
        unit_id = unit_level = 0
        for attempt in range(drop_attempts if present and not field_object else 0):
            if override is not None:
                roll = rng.randint(1,override['no_drop_weight']+sum(r['weight'] for r in override['entries']))
                cumulative = 0
                for row in override['entries']:
                    cumulative += row['weight']
                    if roll <= cumulative:
                        unit_id=row['unit_id'];unit_level=rng.randint(row['level_min'],row['level_max'])
                        break
                if unit_id:break
                continue
            roll = rng.randint(1,100)
            cumulative = 0
            for index in range(1,5):
                cumulative += drop[f'unit{index}_rate']
                if roll <= cumulative:
                    unit_id = drop[f'unit{index}_id']
                    if unit_id:
                        unit_level = rng.randint(drop[f'unit{index}_lv_min'],drop[f'unit{index}_lv_max'])
                    break
            if unit_id:break
        enemies.append(dict(enemy_id=table[prefix+'_id'],enemy_set_id=table[prefix+'_set_id'],
            x=x,y=y,flag=present,drop_data_id=drop['id'],drop_unit_id=unit_id,
            drop_unit_level=unit_level,sp_event_point=(override.get('sp_event_point',0) if override is not None else drop.get('sp_event_point',0))
                if present and not field_object else 0,
            add_attribute_exp=(override.get('attribute_exp',0) if override is not None else drop.get('add_attribute_exp',0))
                if present and not field_object else 0))

    for index, cell in enumerate(bytes.fromhex(level['map_data'])):
        slot = cell & 31
        if 1 <= slot <= 18:
            add(f'enemy{slot}', index%level['width'], index//level['width'])
    add('boss')
    add('death')
    return enemies
