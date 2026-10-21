"""Tabulate the Hanoi controller's own log lines per rehearsal/formal run.
Usage: python -I runs_table.py <session_dir> [--json out.json]"""
import json
import re
import sys
from pathlib import Path

NUM = r'[-+]?\d*\.?\d+(?:e[-+]?\d+)?'


def vec(text):
    return [float(x) for x in re.findall(NUM, text)]


def parse(log):
    row = {}
    for line in log.splitlines():
        m = re.match(r'scene: (yellow|red|blue) ctr=\[([^\]]*)\] top=(\S+) yaw=(\S+) size=\[([^\]]*)\]', line)
        if m:
            c, ctr, top, yaw, size = m.groups()
            row[f'{c}_ctr'] = vec(ctr); row[f'{c}_top'] = float(top); row[f'{c}_yaw'] = float(yaw)
            row[f'{c}_size'] = vec(size)
        m = re.match(r'scene: board top b=(\S+) peg_top=(\S+)', line)
        if m:
            row['board_top'], row['peg_top'] = float(m.group(1)), float(m.group(2))
        m = re.match(r'lift check (r|l) (\w+): hand \+(\S+) disk \((\S+), .*?\) -> \((\S+), .*?\) ok=(\w+)', line)
        if m:
            arm, disk, dh, z0, z1, ok = m.groups()
            row.setdefault(f'lift_{arm}', []).append({'disk': disk, 'hand_dz': float(dh), 'disk_dz': (round(float(z1)-float(z0), 4) if 'None' not in (z0, z1) else None),
                                                     'ok': ok == 'True'})
        m = re.match(r'grasp (r|l): ok=(\w+)', line)
        if m:
            row.setdefault(f'grasp_ok_{m.group(1)}', []).append(m.group(2) == 'True')
        m = re.match(r'== stage (\w+): (\d+) steps \(total (\d+)', line)
        if m:
            row.setdefault('stages', []).append((m.group(1), int(m.group(3))))
        m = re.match(r'done: steps=(\d+) task_complete=(\w+)', line)
        if m:
            row['end_step'] = int(m.group(1)); row['task_complete'] = m.group(2) == 'True'
    return row


def main():
    session = Path(sys.argv[1])
    rows = []
    for run in sorted((session/'published/runs').glob('*')):
        log = run/'stdout.log'
        if not log.exists():
            continue
        result = {}
        for name in ('result.json',):
            try:
                result = json.loads((run/name).read_text())
            except (OSError, ValueError):
                pass
        row = {'run': run.name, 'mtime': log.stat().st_mtime, **parse(log.read_text(errors='replace'))}
        row['bundle'] = result.get('bundle')
        rows.append(row)
    rows.sort(key=lambda r: r['mtime'])
    if '--json' in sys.argv:
        Path(sys.argv[sys.argv.index('--json')+1]).write_text(json.dumps(rows, indent=1))
    for r in rows:
        last = r['stages'][-1] if r.get('stages') else None
        lr = r.get('lift_r', [{}])[-1] if r.get('lift_r') else {}
        ll = r.get('lift_l', [{}])[-1] if r.get('lift_l') else {}
        print(f"{r['run'][:22]:22} ok={str(r.get('task_complete')):5} end={r.get('end_step')!s:5} last={last} "
              f"board={r.get('board_top')} red={r.get('red_ctr')} redtop={r.get('red_top')} "
              f"liftR={lr.get('ok')}/{lr.get('disk_dz')} liftL={ll.get('ok')}/{ll.get('disk_dz')} grR={r.get('grasp_ok_r')} grL={r.get('grasp_ok_l')}")


if __name__ == '__main__':
    main()
