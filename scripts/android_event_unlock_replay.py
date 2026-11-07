"""Replay RTD event navigation through observed ADB input, without game-state writes.

Requires the existing passive RTD_FLOW observation component on the test device.
Each action checks the current UI, records its selector and coordinates, captures a
screenshot, and waits for a verified transition. Unknown states stop the run.
Logs/screenshots belong under ignored logs/, never in Git.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import struct
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import subprocess
import time


def input_point(point, viewport):
    if len(point) != 2 or any(not isinstance(v, (int, float)) or not math.isfinite(v)
                              or not 0 <= v < bound for v, bound in zip(point, viewport)):
        raise ValueError('Observed point is outside the current screenshot')
    rounded = [round(v) for v in point]
    if any(v >= bound for v, bound in zip(rounded, viewport)):
        raise ValueError('Rounded point is outside the current screenshot')
    return rounded


def reference_point(point, viewport):
    return input_point([point[0] * viewport[0] / 1080, point[1] * viewport[1] / 1920], viewport)


def window_point(point, frame, viewport):
    # Edge-anchored menu transforms can equal the window width exactly.
    # Use its last visible pixel; values beyond that still fail validation.
    local = input_point([v - 1 if v == bound else v for v, bound in zip(point, frame[2:])], frame[2:])
    return input_point([local[0] + frame[0], local[1] + frame[1]], viewport)


def window_frame(command):
    command('shell', 'uiautomator', 'dump', '/data/local/tmp/rtd-window.xml')
    xml = command('shell', 'cat', '/data/local/tmp/rtd-window.xml')
    roots = list(ET.fromstring(xml))
    if not roots or roots[0].get('package') != 'jp.co.acquire.RTD':
        raise RuntimeError('RTD must be the foreground app')
    bounds = list(map(int, re.findall(r'\d+', roots[0].get('bounds', ''))))
    if len(bounds) != 4 or bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
        raise RuntimeError('Unknown RTD window bounds')
    return (bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1])


def log_snapshot(command, pid, count=3500):
    if not pid.isdecimal():
        raise RuntimeError('Expected numeric RTD PID')
    # Drain into a local file first. Streaming directly over a slow tunnel can
    # keep chasing new frames indefinitely and return stale observations.
    return command('shell', 'logcat -d --pid=' + pid + ' -t ' + str(count) +
                   ' -v raw -s Unity:I > /data/local/tmp/rtd-flow-snapshot.txt; '
                   'tail -n 800 /data/local/tmp/rtd-flow-snapshot.txt; '
                   'grep RTD_POINT_PROBE /data/local/tmp/rtd-flow-snapshot.txt | tail -n 1').decode('utf-8', errors='replace')


def observations(text):
    groups, states = {}, []
    for line in text.splitlines():
        try:
            if 'RTD_FLOW_CHUNK ' in line:
                item = json.loads(line.split('RTD_FLOW_CHUNK ', 1)[1])
                group = groups.setdefault(item['seq'], {})
                group[item['index']] = item['data']
                if len(group) == item['total']:
                    states.append(json.loads(''.join(group[i] for i in range(item['total']))))
            elif 'RTD_FLOW {' in line:
                states.append(json.loads(line.split('RTD_FLOW ', 1)[1]))
        except (ValueError, KeyError):
            continue  # Incomplete first/last Android log chunks are not states.
    if not states:
        raise RuntimeError('No complete passive RTD_FLOW observations; do not inject input')
    latest = states[-1]
    mains = [s for s in states[-20:] if s.get('scene') == 'MainMenu']
    if mains and (latest.get('scene', '').startswith('MM') or latest.get('scene') == 'MainMenu'):
        latest = dict(mains[-1])
        if latest.get('menu') == 'SELECT_HELPER':
            helpers = [s for s in states[-20:] if s.get('scene') == 'MMHelper']
            if helpers:
                latest['helperRows'] = helpers[-1].get('helperRows', [])
    return latest


def summary(state):
    keys = ('scene', 'mode', 'menu', 'dialog', 'choice', 'ok', 'buttons',
            'selectedQuestId', 'gameState', 'controlsUnlocked', 'turn', 'progress',
            'panels', 'panelDetails', 'fieldState')
    result = {key: state.get(key) for key in keys}
    result['areaRows'] = [r for r in state.get('areaRows', []) if r.get('category') == 1640]
    result['questRows'] = [r for r in state.get('questRows', []) if r.get('questId', r.get('id')) in (20710, 20711, 20712)]
    # Helper/player identities and account fields stay out of the replay trace.
    result['helperPoints'] = [r.get('point') for r in state.get('helperRows', [])]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--serial', required=True)
    parser.add_argument('--output', type=Path, default=Path('logs/android-event-unlock'))
    parser.add_argument('--action', choices=('inspect', 'close-notice', 'title-start', 'events', 'history', 'quest', 'helper', 'confirm', 'field-forward', 'gameover-open', 'decline-continue', 'cancel-cure', 'stage-clear', 'enter-history', 'button', 'dialog-ok'), default='inspect')
    parser.add_argument('--stop-at-list', action='store_true', help='Stop entry flow at history quest list without spending stamina')
    parser.add_argument('--helper-index', type=int, default=0, help='Index among currently visible helpers')
    parser.add_argument('--quest', type=int, choices=(20710, 20711, 20712), default=20710)
    parser.add_argument('--expect-text', help='Required substring for a known onboarding dialog')
    parser.add_argument('--expect-dialog', type=int)
    parser.add_argument('--button', help='Exact observed action name; no arbitrary coordinates')
    parser.add_argument('--timeout', type=float, default=25)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    adb = [args.adb, '-s', args.serial]

    def command(*parts):
        return subprocess.check_output(adb + list(map(str, parts)), timeout=180)

    pid = command('shell', 'pidof', 'jp.co.acquire.RTD').decode().strip()
    if not pid.isdecimal():
        raise RuntimeError('Expected one running game process')

    def state():
        return observations(log_snapshot(command, pid))

    if args.action == 'enter-history':
        import sys
        until = time.monotonic() + 150
        while time.monotonic() < until:
            try:
                current = state()
            except RuntimeError as error:
                if 'No complete passive' not in str(error):
                    raise
                time.sleep(1)
                continue
            scene, mode, menu = (current.get(k) for k in ('scene', 'mode', 'menu'))
            if current.get('dialog', -1) not in (-1, None):
                raise RuntimeError('Unknown dialog during entry; inspect before continuing')
            if args.stop_at_list and scene == 'MainMenu' and mode == 100 and menu == 'SELECT_QUEST' and current.get('questRows'):
                print(json.dumps(dict(event='verified-history-list', state=summary(current)), ensure_ascii=True), flush=True)
                return
            if scene == 'GameManager' and current.get('controlsUnlocked'):
                print('Verified target quest field controls are available', flush=True)
                return
            action = None
            if scene == 'TitleMenu' and mode == 2001: action = 'close-notice'
            elif scene == 'TitleMenu' and mode == 203: action = 'title-start'
            elif scene == 'MainMenu' and mode == 100:
                action = {'SELECT_AREA': 'events', 'SELECT_AREA_EVENT': 'history', 'SELECT_QUEST': 'quest', 'SELECT_HELPER': 'helper', 'QUEST_CONFIRM': 'confirm'}.get(menu)
                if action == 'quest' and not current.get('questRows'): action = None
                if action == 'helper' and not current.get('helperRows'): action = None
            if action:
                subprocess.run([sys.executable, str(Path(__file__).resolve()), '--adb', args.adb, '--serial', args.serial, '--output', str(args.output), '--quest', str(args.quest), '--helper-index', str(args.helper_index), '--action', action], check=True)
            time.sleep(1)
        raise RuntimeError('Entry flow did not reach playable field; inspect trace')

    before = state()
    screenshot = command('exec-out', 'screencap', '-p')
    if screenshot[:8] != b'\x89PNG\r\n\x1a\n':
        raise RuntimeError('Expected PNG screenshot')
    viewport = struct.unpack('>II', screenshot[16:24])
    frame = window_frame(command)
    scale_y = frame[3] / 1920
    print(json.dumps(summary(before), ensure_ascii=True), flush=True)
    if args.action == 'inspect':
        return
    if args.action != 'dialog-ok' and before.get('dialog', -1) not in (-1, None):
        raise RuntimeError('Unexpected dialog; inspect and diagnose before continuing')
    point = None
    selector = dict(action=args.action)
    if args.action == 'dialog-ok':
        if not args.expect_text or args.expect_text not in before.get('text', '') or before.get('dialog') != args.expect_dialog:
            raise RuntimeError('Known onboarding dialog does not match')
        matches = [b for b in before.get('buttons', []) if b['action'] == 'ClickOK']
        if len(matches) != 1:
            raise RuntimeError('Expected one observed OK button')
        point = matches[0]['point']
        selector['text_sha256'] = hashlib.sha256(before['text'].encode()).hexdigest()
    elif args.action in ('close-notice', 'title-start', 'events', 'button'):
        action = {'close-notice': 'ClickViewClose', 'title-start': 'PushButton', 'events': 'ChangeAreaKind'}.get(args.action, args.button)
        if args.action == 'close-notice' and not (before['scene'] == 'TitleMenu' and before['mode'] == 2001):
            raise RuntimeError('Notification page is not current')
        if args.action == 'title-start' and not (before['scene'] == 'TitleMenu' and before['mode'] == 203):
            raise RuntimeError('Title ready state is not current')
        if args.action == 'events' and before.get('menu') != 'SELECT_AREA':
            raise RuntimeError('Normal area list is not current')
        matches = [b for b in before.get('buttons', []) if b['action'] == action]
        if len(matches) != 1:
            raise RuntimeError('Expected exactly one observed action: ' + str(action))
        point = matches[0]['point']; selector['button'] = action
    elif args.action == 'history':
        if before.get('menu') != 'SELECT_AREA_EVENT':
            raise RuntimeError('Event area list is not current')
        matches = [r for r in before.get('areaRows', []) if r.get('category') == 1640]
        if len(matches) != 1:
            raise RuntimeError('History category is not present')
        row = matches[0]; selector['category'] = 1640
        if row.get('point') and 450 * scale_y <= row['point'][1] <= 1550 * scale_y:
            point = row['point']
        else:
            y = row['scrollPoint'][1]
            ends = ([540, 1450], [540, 550]) if y > 1550 * scale_y else ([540, 550], [540, 1450])
            swipe = window_point(reference_point(ends[0], frame[2:]), frame, viewport) + window_point(reference_point(ends[1], frame[2:]), frame, viewport) + [350]
            command('shell', 'input', 'swipe', *swipe)
            print('Scrolled toward observed category 1640; inspect before next action', flush=True)
            record = dict(at=dt.datetime.now(dt.timezone.utc).isoformat(), selector=selector, before=summary(before), swipe=swipe)
            with (args.output / 'steps.jsonl').open('a', encoding='utf-8') as f: f.write(json.dumps(record) + '\n')
            return
    elif args.action == 'quest':
        matches = [r for r in before.get('questRows', []) if r.get('questId', r.get('id')) == args.quest]
        if len(matches) != 1:
            raise RuntimeError('Requested quest is not present in observed UI')
        point = matches[0].get('point'); selector['quest'] = args.quest
    elif args.action == 'stage-clear':
        if before.get('gameState') != 'GameStateGameClear':
            raise RuntimeError('Original game-clear state is required')
        point = reference_point([540, 888], frame[2:]); selector['source'] = 'GameStatus.Update clear-state input'
    elif args.action == 'cancel-cure':
        dialog = (before.get('fieldState') or {}).get('skillDialog') or {}
        matches = [b for b in dialog.get('buttons', []) if b.get('action') == 'ExitDialog']
        if not dialog.get('active') or dialog.get('status') != 'OPEN' or dialog.get('id') != 11000 or len(matches) != 1:
            raise RuntimeError('Expected one open original Cure I cancel button')
        point = matches[0]['point']; selector['button'] = 'ExitDialog'
    elif args.action == 'gameover-open':
        if before.get('gameState') != 'GameStateGameOver' or before.get('continuePanelOpen'):
            raise RuntimeError('Game-over screen without continue dialog is required')
        point = reference_point([540, 888], frame[2:]); selector['source'] = 'GameStatus.Update Input.GetMouseButton(0)'
    elif args.action == 'decline-continue':
        matches = [b for b in before.get('continueButtons', []) if b.get('action') == 'ContinueNo']
        if before.get('gameState') != 'GameStateGameOver' or len(matches) != 1:
            raise RuntimeError('No observed ContinueNo button on game-over dialog')
        point = matches[0]['point']; selector['button'] = 'ContinueNo'
    elif args.action == 'field-forward':
        if before.get('gameState') != 'GameStateField' or not before.get('controlsUnlocked'):
            raise RuntimeError('Field controls are not ready')
        matches = [p for p in before.get('panelDetails', []) if (p['way'] >> 8) == 8]
        if not matches:
            raise RuntimeError('No observed straight single-step panel')
        point = matches[0]['point']; selector['way'] = matches[0]['way']
    elif args.action == 'confirm':
        if before.get('menu') != 'QUEST_CONFIRM' or before.get('selectedQuestId') != args.quest:
            raise RuntimeError('Requested quest confirmation is not current')
        matches = [b for b in before.get('buttons', []) if b.get('point') and b['point'][1] > 1100 * scale_y]
        if len(matches) != 1:
            raise RuntimeError('Expected exactly one visible departure button')
        point = matches[0]['point']; selector['quest'] = args.quest
    elif args.action == 'helper':
        matches = [r for r in before.get('helperRows', []) if r.get('point') and 450 * scale_y <= r['point'][1] <= 1600 * scale_y]
        if not 0 <= args.helper_index < len(matches):
            raise RuntimeError('Requested visible helper selection is unavailable')
        point = matches[args.helper_index]['point']; selector['helper_index'] = args.helper_index
    if not point:
        raise RuntimeError('Selector has no visible point; stop instead of guessing')
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    (args.output / (stamp + '.png')).write_bytes(screenshot)
    point = window_point(point, frame, viewport)
    command('shell', 'input', 'tap', *point)
    record = dict(at=stamp, selector=selector, before=summary(before), tap=point, screenshot_sha256=hashlib.sha256(screenshot).hexdigest())
    with (args.output / 'steps.jsonl').open('a', encoding='utf-8') as f: f.write(json.dumps(record) + '\n')
    old_key = tuple(before.get(k) for k in ('scene', 'mode', 'menu', 'selectedQuestId', 'dialog', 'gameState', 'turn', 'continuePanelOpen', 'controlsUnlocked', 'text'))
    until = time.monotonic() + args.timeout
    while time.monotonic() < until:
        time.sleep(0.5)
        after = state()
        key = tuple(after.get(k) for k in ('scene', 'mode', 'menu', 'selectedQuestId', 'dialog', 'gameState', 'turn', 'continuePanelOpen', 'controlsUnlocked', 'text'))
        if key != old_key:
            print(json.dumps(summary(after), ensure_ascii=True), flush=True)
            with (args.output / 'steps.jsonl').open('a', encoding='utf-8') as f: f.write(json.dumps(dict(at=stamp, verified_transition=summary(after))) + '\n')
            return
    raise RuntimeError('No verified UI transition before timeout; inspect logs, do not retry blindly')


if __name__ == '__main__':
    main()
