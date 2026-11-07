"""Record installation, launches and screenshot-based onboarding on a test phone.

No device address, credentials or account data is embedded. Keep output in ignored
logs/. Gameplay scripts handle navigation and battle once tutorial is complete.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from android_event_unlock_replay import observations, log_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--serial', required=True)
    parser.add_argument('--output', type=Path, default=Path('logs/event-unlock-phone'))
    parser.add_argument('--action', choices=('install', 'launch', 'relogin', 'inspect', 'tap', 'system-button', 'display-test', 'display-restore', 'record-points'), required=True)
    parser.add_argument('--apk', type=Path)
    parser.add_argument('--no-screenshot', action='store_true', help='Read-only inspect only')
    parser.add_argument('--text', help='Exact visible Android system button text')
    parser.add_argument('--point', type=int, nargs=2)
    parser.add_argument('--expect-scene', help='Required for observed onboarding taps')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    adb = [args.adb, '-s', args.serial]

    def command(*parts):
        return subprocess.check_output(adb + list(map(str, parts)), timeout=180)

    record = dict(at=dt.datetime.now(dt.timezone.utc).isoformat(), action=args.action)
    if args.action == 'record-points':
        with (args.output / 'points-live.jsonl').open('ab') as out:
            process = subprocess.Popen(adb + ['shell', 'logcat -v raw -s Unity:I | grep RTD_POINT_PROBE'], stdout=out)
            try:
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
                process.wait(timeout=10)
        return
    if args.action == 'display-test':
        original = command('shell', 'wm', 'size').decode()
        saved = args.output / 'original-display.txt'
        with saved.open('x', encoding='utf-8') as out:
            out.write(original)
        command('shell', 'wm', 'size', '720x1600')
        record['test_size'] = [720, 1600]
    elif args.action == 'display-restore':
        import re
        original = (args.output / 'original-display.txt').read_text()
        override = re.search(r'Override size: (\d+x\d+)', original)
        command('shell', 'wm', 'size', override.group(1) if override else 'reset')
        record['restored'] = True
    elif args.action == 'install':
        if not args.apk:
            parser.error('--apk is required')
        record['apk_sha256'] = hashlib.sha256(args.apk.read_bytes()).hexdigest()
        command('install', '-r', '--bypass-low-target-sdk-block', args.apk)
    elif args.action in ('launch', 'relogin'):
        if args.action == 'relogin':
            command('shell', 'am', 'force-stop', 'jp.co.acquire.RTD')
        component = command('shell', 'cmd', 'package', 'resolve-activity', '--brief',
                            'jp.co.acquire.RTD').decode().strip().splitlines()[-1]
        if not component.startswith('jp.co.acquire.RTD/'):
            raise RuntimeError('Expected the RTD launcher')
        result = command('shell', 'am', 'start', '-W', '-n', component).decode()
        if 'Error:' in result or 'Status: ok' not in result:
            raise RuntimeError('RTD launch failed')
    elif args.action == 'system-button':
        import re
        import xml.etree.ElementTree as ET
        if not args.text:
            parser.error('--text is required')
        command('shell', 'uiautomator', 'dump', '/data/local/tmp/rtd-ui.xml')
        xml = command('shell', 'cat', '/data/local/tmp/rtd-ui.xml')
        matches = [n for n in ET.fromstring(xml).iter('node')
                   if n.get('text') == args.text and n.get('clickable') == 'true'
                   and n.get('package') in ('com.lbe.security.miui', 'com.google.android.permissioncontroller', 'com.android.permissioncontroller')]
        if len(matches) != 1:
            raise RuntimeError('Expected one observed Android permission/review button')
        bounds = list(map(int, re.findall(r'\d+', matches[0].get('bounds', ''))))
        if len(bounds) != 4:
            raise RuntimeError('Expected system button bounds')
        point = [(bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2]
        record.update(text=args.text, point=point, hierarchy_sha256=hashlib.sha256(xml).hexdigest())
        command('shell', 'input', 'tap', *point)
    else:
        pid = command('shell', 'pidof', 'jp.co.acquire.RTD').decode().strip()
        if not pid.isdecimal():
            raise RuntimeError('Expected one running RTD process')
        log = log_snapshot(command, pid)
        state = observations(log)
        # Full private observations remain local; do not print account fields.
        (args.output / 'latest-state.json').write_text(json.dumps(state), encoding='utf-8')
        if args.no_screenshot:
            if args.action != 'inspect':
                parser.error('--no-screenshot is inspect only')
            print(json.dumps({k:state.get(k) for k in ('scene','mode','menu','dialog','text','buttons','ok','questRows','helperRows','gachaResultOk')}))
            return
        png = command('exec-out', 'screencap', '-p')
        name = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.png'
        (args.output / name).write_bytes(png)
        record.update(scene=state.get('scene'), mode=state.get('mode'),
                      screenshot=name, screenshot_sha256=hashlib.sha256(png).hexdigest())
        if args.action == 'tap':
            if not args.expect_scene or state.get('scene') != args.expect_scene or not args.point:
                raise RuntimeError('A matching observed scene and point are required')
            from android_event_unlock_replay import input_point
            import struct
            point = input_point(args.point, struct.unpack('>II', png[16:24]))
            record['point'] = point
            command('shell', 'input', 'tap', *point)
        else:
            from android_event_unlock_replay import summary
            print(json.dumps(summary(state), ensure_ascii=False))
    with (args.output / 'device-steps.jsonl').open('a', encoding='utf-8') as out:
        out.write(json.dumps(record) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
