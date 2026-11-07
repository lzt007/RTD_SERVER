"""Play a verified history-event run using real ADB input and passive observations.

The script never directly edits game fields, accounts, databases or protocol data;
normal gameplay may save its earned progress. The inferred missing map must match the observed client map hash before movement.
Visited cells are route observations/inferences, never an assertion of kills.
Actual points come exclusively from RTD_POINT_PROBE. Stops before result handling,
unknown dialogs, death, process replacement, or 45 seconds without progress.
Run with Python UTF-8 mode (python -X utf8) for reconstruction source loading.
"""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

from android_event_unlock_replay import observations, summary, log_snapshot, window_frame, window_point

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def map_for(quest_id):
    from rtd.masters.catalog import load_catalog
    from rtd.masters.event_reconstruction import build_candidate, apply_missing
    masters, levels = load_catalog()
    masters, levels = apply_missing(masters, levels, build_candidate(masters, levels))
    quest = next(q for q in masters[30]['data_list'] if q['id'] == quest_id)
    table = next(t for t in masters[21]['data_list'] if t['id'] == quest['enemy_table_id'])
    level = levels[quest_id]
    cells = bytes.fromhex(level['map_data'])
    targets = {(i % level['width'], i // level['width']) for i, cell in enumerate(cells)
               if 1 <= (cell & 31) <= 18 and table.get('enemy%d_set_id' % (cell & 31)) == 41028}
    boss_rows = [i // level['width'] for i, cell in enumerate(cells) if cell & 224 == 160]
    if not boss_rows:
        raise RuntimeError('No boss boundary established by the map')
    return level, targets, min(boss_rows)


def trajectory(way, x, y, width, height):
    route = []
    for i in range(4):
        direction = (int(way) >> (8 + 4 * i)) & 15
        if direction == 0:
            break
        # Original field axes, distinct from panel-screen axes.
        if direction == 2: x -= 1
        elif direction == 4: x += 1
        elif direction == 8: y += 1
        else: return None  # Do not guess unsupported/backward directions.
        if not (0 <= x < width and 0 <= y < height):
            return None
        route.append((x, y))
    return route or None


def field_choice(state, level, targets, boss_y, visited, attempts):
    field = state['fieldState']
    x, y = field['cellX'], field['cellY']
    pending = sorted((t for t in targets - visited if t[1] >= y), key=lambda p: (p[1], abs(p[0] - x)))
    destination = pending[0] if pending else (x, boss_y)
    choices = []
    for panel in state.get('panelDetails', []):
        route = trajectory(panel['way'], x, y, level['width'], level['height'])
        if not route or route[-1] == (x, y):
            continue
        hits = len(set(route) & (targets - visited))
        end = route[-1]
        distance = abs(end[0] - destination[0]) + abs(end[1] - destination[1])
        overshoot = max(0, end[1] - destination[1])
        repeated = sum(cell in visited for cell in route)
        # Collect reachable original targets, then seek the next row and boss.
        score = hits * 100 - distance * 7 - overshoot * 18 + (end[1] - y) * 2 - repeated * 3
        score -= attempts[((x, y), int(panel['way']))] * 60
        choices.append((score, panel, route))
    if not choices:
        raise RuntimeError('No observed panel has a supported in-bounds route')
    _, panel, route = max(choices, key=lambda choice: choice[0])
    return [panel['point']], dict(kind='field', way=panel['way'], predicted_route=route,
                                 next_target=destination, visited_target_cells=len(targets & visited))


def longest_chains(panels):
    # Grid membership comes from observed screen centers; only four-neighbor links.
    points = [p['point'] for p in panels]
    xs = sorted({round(p[0]) for p in points})
    ys = sorted({round(p[1]) for p in points})
    positions = [(xs.index(round(p[0])), ys.index(round(p[1]))) for p in points]
    graph = {i: [j for j in range(len(panels)) if i != j
                 and panels[i]['class'] == panels[j]['class']
                 and abs(positions[i][0] - positions[j][0]) + abs(positions[i][1] - positions[j][1]) == 1]
             for i in range(len(panels))}
    best = {}
    def walk(path):
        kind = panels[path[0]]['class']
        if len(path) > len(best.get(kind, [])):
            best[kind] = list(path)
        for next_node in graph[path[-1]]:
            if next_node not in path:
                walk(path + [next_node])
    for i in range(len(panels)):
        walk([i])
    return {kind: [panels[i]['point'] for i in path] for kind, path in best.items()}


def all_panel_chain(panels):
    if len(panels) != 8:
        raise RuntimeError('Expected eight observed battle panels')
    rows = {}
    for panel in panels:
        point = panel['point']
        rows.setdefault(round(point[1]), []).append(point)
    if len(rows) != 2 or any(len(row) != 4 for row in rows.values()):
        raise RuntimeError('Expected a stable two by four panel grid')
    points = []
    for index, y in enumerate(sorted(rows)):
        points.extend(sorted(rows[y], key=lambda p:p[0], reverse=bool(index % 2)))
    return points


def battle_choice(state):
    field = state['fieldState']
    panels = state.get('panelDetails', [])
    if not panels:
        raise RuntimeError('No observed battle panels')
    chains = longest_chains(panels)
    estimates = field.get('attackEstimates', [])
    if len(estimates) != 6 or any(len(row) != 8 for row in estimates):
        raise RuntimeError('No complete passive damage estimates; stop instead of guessing')
    enemy_life = field.get('enemyLife', -1)
    if enemy_life <= 0:
        return None, None
    attacks = [(int(estimates[kind][min(len(chain), 8) - 1]), kind, chain)
               for kind, chain in chains.items() if kind in (0, 1, 2, 3, 5)]
    attacks = [row for row in attacks if row[0] > 0]
    lethal = [row for row in attacks if row[0] >= enemy_life]
    if lethal:
        damage, kind, chain = max(lethal, key=lambda row: (row[0], len(row[2])))
    elif field.get('partyLife', 0) < field.get('partyMaxLife', 1) * .55 and 4 in chains:
        return chains[4], dict(kind='battle-heal', panel_class=4, chain_length=len(chains[4]))
    elif attacks:
        damage, kind, chain = max(attacks, key=lambda row: (row[0], len(row[2])))
    elif 4 in chains:
        return chains[4], dict(kind='battle-heal', panel_class=4, chain_length=len(chains[4]))
    elif chains and all(kind in (0, 1, 2, 3, 5) for kind in chains):
        kind, chain = max(chains.items(), key=lambda item: len(item[1]))
        return chain, dict(kind='battle-cycle', panel_class=kind, chain_length=len(chain),
                           estimated_damage=0, enemy_life=enemy_life)
    else:
        raise RuntimeError('No damaging or healing observed chain')
    return chain, dict(kind='battle-attack', panel_class=kind, chain_length=len(chain),
                       estimated_damage=damage, enemy_life=enemy_life)


class CureController:
    """Observe/open/confirm one original Cure I dialog, never repeat a click."""
    def __init__(self, enabled=False):
        self.enabled = enabled
        self.pending = None

    def step(self, state, now):
        field = state.get('fieldState') or {}
        dialog = field.get('skillDialog') or {}
        active = dialog.get('active') is True
        if self.pending is not None:
            pending = self.pending
            if now > pending['deadline']:
                raise RuntimeError('Cure I dialog/heal transition timed out; no repeated input')
            if active:
                if (dialog.get('id'), dialog.get('type'), dialog.get('cost'), dialog.get('partyIndex')) != (11000, 2, 2, pending['party_index']):
                    raise RuntimeError('Unexpected skill dialog while waiting for Cure I')
                if pending['phase'] == 'opening':
                    if dialog.get('status') != 'OPEN':
                        return dict(kind='wait')
                    buttons = [b for b in dialog.get('buttons', []) if b.get('action') == 'ExecSkill' and b.get('point')]
                    if len(buttons) != 1:
                        return dict(kind='wait')
                    pending['phase'] = 'confirmed'
                    pending['deadline'] = now + 60
                    return dict(kind='cure-confirm', point=buttons[0]['point'], skill_id=11000, cost=2)
                return dict(kind='wait')
            if pending['phase'] == 'confirmed' and field.get('partyLife', 0) > pending['life_before']:
                self.pending = None
                return dict(kind='cure-completed', life_before=pending['life_before'], life_after=field['partyLife'])
            return dict(kind='wait')
        if active:
            raise RuntimeError('Skill dialog was not opened by this driver; stop for inspection')
        if not self.enabled or not state.get('controlsUnlocked') or state.get('gameState') not in ('GameStateField', 'GameStateBattle'):
            return None
        life, maximum, soul = (field.get(k, 0) for k in ('partyLife', 'partyMaxLife', 'partySoul'))
        if not (life > 0 and life < maximum * .75 and maximum - life >= 2500 and soul >= 2):
            return None
        skills = [skill for skill in field.get('combatSkills', [])
                  if skill.get('id') == 11000 and skill.get('type') == 2
                  and skill.get('available') is True and skill.get('point')]
        if not skills:
            return None
        skill = skills[0]
        self.pending = dict(phase='opening', party_index=skill['partyIndex'], life_before=life, deadline=now + 60)
        return dict(kind='cure-open', point=skill['point'], skill_id=11000, party_index=skill['partyIndex'])


def compact_state(state, point):
    # Reuse the navigation summarizer, but omit bulky and account-related UI data.
    safe = summary(state)
    field = safe.get('fieldState') or {}
    return dict(scene=safe.get('scene'), state=safe.get('gameState'),
                quest=safe.get('selectedQuestId'), map_hash=state.get('mapHash'),
                turn=safe.get('turn'), controls=safe.get('controlsUnlocked'),
                x=field.get('cellX'), y=field.get('cellY'), soul=field.get('partySoul'),
                life=field.get('partyLife'), max_life=field.get('partyMaxLife'),
                enemy=field.get('enemyMasterId'), enemy_life=field.get('enemyLife'),
                run_points=(point or {}).get('run_points'),
                event_balance=(point or {}).get('event_100001_balance'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--serial', required=True)
    parser.add_argument('--quest', type=int, choices=(20710, 20711, 20712), default=20710)
    parser.add_argument('--screenshot-every', type=int, default=1, help='Screenshot every N inputs; 0 disables images, all input states still recorded')
    parser.add_argument('--battle-strategy', choices=('estimated', 'all-panels'), default='estimated')
    parser.add_argument('--input-mode', choices=('dex', 'native'), default='dex')
    parser.add_argument('--input-dex', default='/data/local/tmp/rtd-input.dex')
    parser.add_argument('--output', type=Path, default=ROOT / 'logs/android-event-unlock-play')
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--use-cure', action='store_true', help='Use original Cure I through observed UI only')
    parser.add_argument('--minimum-points', type=int, default=0, help='After this observed run-point target, move toward boss (0 pursues all targets)')
    args = parser.parse_args()
    if args.screenshot_every < 0:
        parser.error('--screenshot-every must be nonnegative')
    if args.minimum_points < 0:
        parser.error('--minimum-points must be nonnegative')
    args.output.mkdir(parents=True, exist_ok=True)
    adb = [args.adb, '-s', args.serial]
    def command(*parts):
        return subprocess.check_output(adb + list(map(str, parts)), timeout=180)
    pid = command('shell', 'pidof', 'jp.co.acquire.RTD').decode().strip()
    if not pid.isdecimal():
        raise RuntimeError('Expected one running game process')
    # Check the requested Android-side injector before any play input.
    if not args.input_dex.startswith('/data/local/tmp/') or any(c in args.input_dex for c in " ;'\"$`\\\n\r"):
        raise RuntimeError('Input dex must be a simple /data/local/tmp/ path')
    if args.input_mode == 'dex':
        command('shell', 'test', '-f', args.input_dex)
    level, targets, boss_y = map_for(args.quest)
    visited, attempts, inferred_route = set(), Counter(), []
    last_cell = None
    last_action_key = None
    frame = window_frame(command)
    viewport = (frame[0] + frame[2], frame[1] + frame[3])
    last_action_at = 0
    previous_progress = None
    progress_at = time.monotonic()
    last_point = None
    point_seen = set()
    trace = args.output / 'play-steps.jsonl'
    started = time.monotonic()
    verified_map = False
    cure = CureController(args.use_cure)

    def record(value):
        with trace.open('a', encoding='utf-8') as out:
            out.write(json.dumps(value, ensure_ascii=True) + '\n')

    input_index = 0
    def capture(stamp):
        nonlocal input_index
        input_index += 1
        if not args.screenshot_every or (input_index - 1) % args.screenshot_every:
            return dict(screenshot_captured=False)
        screenshot = command('exec-out', 'screencap', '-p')
        (args.output / (stamp + '.png')).write_bytes(screenshot)
        return dict(screenshot_captured=True, screenshot_sha256=hashlib.sha256(screenshot).hexdigest())

    def cure_tap(action, compact):
        point = window_point(action['point'], frame, viewport)
        if len(point) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in point):
            raise RuntimeError('Invalid observed Cure I button coordinates')
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        evidence = capture(stamp)
        record(dict(event='input', at=stamp, selector=action, coords=[point], state=compact,
                    **evidence))
        print(json.dumps(dict(event='input', selector=action, coords=[point])), flush=True)
        command('shell', 'input', 'tap', *map(round, point))

    while time.monotonic() - started < args.timeout:
        if command('shell', 'pidof', 'jp.co.acquire.RTD').decode().strip() != pid:
            raise RuntimeError('Game process changed or exited; no further input')
        log = log_snapshot(command, pid)
        for line in log.splitlines():
            if 'RTD_POINT_PROBE ' not in line:
                continue
            try:
                point = json.loads(line.split('RTD_POINT_PROBE ', 1)[1])
            except ValueError:
                continue
            encoded = json.dumps(point, sort_keys=True)
            last_point = point
            if encoded not in point_seen:
                point_seen.add(encoded)
                with (args.output / 'point-probe.jsonl').open('a', encoding='utf-8') as out:
                    out.write(json.dumps(point, ensure_ascii=True) + '\n')
        state = observations(log)
        compact = compact_state(state, last_point)
        field = state.get('fieldState') or {}
        if state.get('dialog', -1) not in (-1, None):
            raise RuntimeError('Unknown dialog; no revival, payment, or discard input is allowed')
        if field.get('discoverButtons'):
            raise RuntimeError('Unknown discovery dialog; stop for operator inspection')
        if state.get('gameState') == 'GameStateGameClear' or state.get('menu') == 'QUEST_RESULT':
            record(dict(event='stopped-at-game-clear', state=compact))
            print(json.dumps(dict(event='stopped-at-game-clear', state=compact)), flush=True)
            return
        if state.get('selectedQuestId') != args.quest:
            raise RuntimeError('Current selected quest differs from requested run')
        observed_hash = state.get('mapHash')
        if observed_hash and str(observed_hash) != str(level['hash']):
            raise RuntimeError('Observed map hash does not match the reconstructed map')
        if not verified_map:
            if not observed_hash:
                raise RuntimeError('No observed map hash; refuse route planning')
            verified_map = True
            record(dict(event='map-verified', quest=args.quest, hash=str(level['hash']), target_cells=len(targets), boss_row=boss_y))
        if field.get('partyInitialized') == 'True' and field.get('partyLife', 0) <= 0:
            raise RuntimeError('Party is dead; no revival or payment input is allowed')
        cell = (field.get('cellX'), field.get('cellY'))
        if None not in cell:
            if cell in inferred_route:
                visited.update(inferred_route[:inferred_route.index(cell) + 1])
            visited.add(cell)
            last_cell = cell
        progress = (compact['state'], compact['turn'], cell, compact['life'], compact['enemy_life'], compact['run_points'])
        if progress != previous_progress:
            progress_at = time.monotonic()
            previous_progress = progress
            print(json.dumps(dict(event='progress', **compact)), flush=True)
        elif time.monotonic() - progress_at > 45:
            raise RuntimeError('No observed progress for 45 seconds; stop instead of retrying')
        cure_action = cure.step(state, time.monotonic())
        if cure_action is not None:
            if cure_action['kind'] in ('cure-open', 'cure-confirm'):
                cure_tap(cure_action, compact)
                last_action_at = time.monotonic()
            elif cure_action['kind'] == 'cure-completed':
                record(dict(event='cure-verified', selector=cure_action, state=compact))
                print(json.dumps(dict(event='cure-verified', **cure_action)), flush=True)
                last_action_key = None
                progress_at = time.monotonic()
            time.sleep(.5)
            continue
        if not state.get('controlsUnlocked'):
            time.sleep(.5)
            continue
        mode = state.get('gameState')
        if mode == 'GameStateField':
            active_targets = set() if args.minimum_points > 0 and (last_point or {}).get('run_points', 0) >= args.minimum_points else targets
            points, selector = field_choice(state, level, active_targets, boss_y, visited, attempts)
        elif mode == 'GameStateBattle':
            if args.battle_strategy == 'all-panels':
                points = all_panel_chain(state.get('panelDetails', []))
                selector = dict(kind='battle-all-panels', chain_length=8)
            else:
                points, selector = battle_choice(state)
            if points is None:
                time.sleep(.5)
                continue
        else:
            raise RuntimeError('Controls unlocked in unsupported game state: ' + str(mode))
        action_key = (mode, state.get('turn'), cell, field.get('enemyLife'),
                      tuple((p['class'], p['way'], tuple(p['point'])) for p in state.get('panelDetails', [])))
        # The latest passive frame may predate the just-completed input.
        if action_key == last_action_key or time.monotonic() - last_action_at < 1:
            time.sleep(.5)
            continue
        try:
            points = [window_point(p, frame, viewport) for p in points]
        except ValueError:
            # CanSelect may become true before panel arrival animation ends.
            # Never inject an off-window observation; wait for visible panels.
            time.sleep(.5)
            continue
        if any(len(p) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in p) for p in points):
            raise RuntimeError('Invalid observed input coordinates')
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        evidence = capture(stamp)
        record(dict(event='input', at=stamp, selector=selector, coords=points,
                    state=compact, **evidence))
        print(json.dumps(dict(event='input', selector=selector, coords=points)), flush=True)
        if len(points) == 1:
            command('shell', 'input', 'tap', *map(round, points[0]))
        elif args.input_mode == 'native':
            if len(points) == 2:
                command('shell', 'input', 'swipe', *(round(v) for p in points for v in p), 400)
            else:
                # Stock Android shell input preserves one real finger gesture.
                # Every move visits an observed adjacent panel; no game fields.
                parts = ['input motionevent DOWN %d %d' % tuple(points[0])]
                parts += ['input motionevent MOVE %d %d' % tuple(p) for p in points[1:]]
                parts += ['input motionevent UP %d %d' % tuple(points[-1])]
                command('shell', '; '.join(parts))
        else:
            command('shell', 'CLASSPATH=' + args.input_dex, 'app_process', '/system/bin', 'RTDInput',
                    *(round(v) for p in points for v in p))
        last_action_key, last_action_at = action_key, time.monotonic()
        if mode == 'GameStateField':
            attempts[(cell, int(selector['way']))] += 1
            inferred_route = [tuple(p) for p in selector['predicted_route']]
        time.sleep(.5)
    raise RuntimeError('Play timeout reached; no further input')


if __name__ == '__main__':
    main()
