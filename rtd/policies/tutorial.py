from ..common import ProtocolError, compact


def tutorial_credit(self, state):
    # Explicit reconstruction policy: fund the client's mandatory five-crystal
    # first summon once. Original server grant timing/pool is unavailable.
    player=state['player']
    if player['quest_clear_flags'][0] & 2 and not state.get('tutorial_credit'):
        player['free_paid_point'] += 5
        player['total_paid_point'] += 5
        state['tutorial_credit'] = True
        return True
    return False

