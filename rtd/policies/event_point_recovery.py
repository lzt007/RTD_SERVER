"""Inferred missing point quantities, scoped to production-open event targets.

2026-11-06: production runtime_config revision 40. Original event/quest
masters supply target identities and gates, but drop masters lack quantities.
One point per listed target is local recovery, not recovered official data.
Original masters remain untouched; explicit values, including zero, win.
"""
TARGETS = {
    100000: frozenset(range(40103, 40115)) | frozenset(range(40119, 40123)),
    100001: frozenset({41028}),
    100003: frozenset({41040, 41045, 41049, 41053, 41058, 41064, 41069}),
}


def missing_point(event_id, enemy_id):
    return int(enemy_id in TARGETS.get(event_id, ()))
