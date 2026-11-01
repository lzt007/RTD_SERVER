"""Local offline companion policy; this is not a recovered original roster."""
import datetime as dt

# Same shipped companions used by Installer/TitleMenu for the first tutorial.
FIRST_COMPANIONS = (14021, 14022, 14013, 14012)


def local_helper(starter):
    # This non-account companion is already available; never invite user ID 0.
    return dict(user_id=0, user_name='LOCAL_HELPER', rank=1,
                last_play_date=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                friend=True, friend_point=True,
                unit_id=FIRST_COMPANIONS[starter], unit_level=20,
                unit_bonus_life=0, unit_bonus_attack=0, unit_bonus_heal=0)
