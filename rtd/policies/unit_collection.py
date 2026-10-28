"""Monotonic acquired-unit library, independent of the current inventory."""


def sync_collection(state):
    previous = state.get('unit_collection')
    collection = {row['unit_id']:dict(row) for row in previous or []}
    for unit in state['units']:
        unit_id = unit['unit_id']
        old = collection.get(unit_id)
        collection[unit_id] = dict(unit_id=unit_id,status=100,
                                  level=max(unit['level'],old['level'] if old else 0))
    result = [collection[k] for k in sorted(collection)]
    if result == previous:
        return False
    state['unit_collection'] = result
    return True
