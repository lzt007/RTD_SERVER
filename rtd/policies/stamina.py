"""Local stamina clock policy: one AP per 600 seconds, no banking at full."""
from ..common import ProtocolError

INTERVAL = 600


def recover(player, now):
    now = int(now)
    current = player['action_point']
    maximum = player['max_action_point']
    anchor = player['action_point_recover']
    if current >= maximum or now <= anchor:
        return False
    points = (now - anchor) // INTERVAL
    if not points:
        return False
    player['action_point'] = min(maximum, current + points)
    player['action_point_recover'] = (now if player['action_point'] == maximum
                                      else anchor + points * INTERVAL)
    return True


def spend(player, cost, now):
    # Keep this helper atomic even outside the API's enclosing transaction.
    candidate = player.copy()
    recover(candidate, now)
    if type(cost) is not int or cost <= 0 or candidate['action_point'] < cost:
        raise ProtocolError(9472, 'Not enough stamina or invalid cost')
    if candidate['action_point'] >= candidate['max_action_point']:
        candidate['action_point_recover'] = max(int(now), candidate['action_point_recover'])
    candidate['action_point'] -= cost
    player.update(candidate)
