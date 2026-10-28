"""Monotonic per-account instances survive removal of the highest owned ID."""


def remember_instance_ids(state):
    high = max([state['player']['user_id']*1000,
                state.get('unit_instance_high_water',0)]
               +[u['instance_id'] for u in state['units']])
    state['unit_instance_high_water'] = high
    return high


def allocate_instance_ids(state, count):
    if type(count) is not int or count < 1:
        raise ValueError('Expected positive instance count')
    high = remember_instance_ids(state)
    state['unit_instance_high_water'] = high+count
    return list(range(high+1,high+count+1))
