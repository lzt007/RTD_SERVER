"""Allowlisted state summaries and recursive credential removal."""
import hashlib
from ..common import compact

SECRET_FIELDS = {'uuid', 'session_id', 'token', 'password', 'move_password',
                 'receipt', 'purchase_token', 'signature', 'authorization', 'cookie'}


def redact(value):
    if isinstance(value, dict):
        return {key: ('<redacted>' if key.lower() in SECRET_FIELDS else redact(item))
                for key,item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def summary(state):
    player = state['player']
    result = {key:player[key] for key in ('action_point', 'game_money', 'exp', 'rank',
        'free_paid_point', 'paid_point', 'max_unit', 'max_friend')}
    result.update(units=len(state['units']), quest_id=(state.get('battle') or {}).get('quest_id'))
    return result


def account_label(user_id):
    return hashlib.sha256(('local-player:'+str(user_id)).encode()).hexdigest()[:12]
