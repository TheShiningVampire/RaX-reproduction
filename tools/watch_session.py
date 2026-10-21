"""Spend watcher + recorder for one RaX session.

Every INTERVAL seconds:
  - sums token usage from Claude Code transcripts (claude-home/projects/**/*.jsonl, deduped by message id)
    and prices it (Opus 5.5 list prices; cache writes priced by TTL);
  - appends a timeline row (cost, tokens, lifecycle stage, episodes used, bundles, submission) to
    <out>/timeline.jsonl;
  - on first sight of agent-workspace/, copies the text files the agent was given to <out>/deployed_workspace/;
  - if cost >= cap, runs the harness's own stop script once and records it.
Usage: python -I watch_session.py <session_dir> <out_dir> <cap_usd> <project_root>
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

INTERVAL = 60
# $/MTok: input, output, cache read, cache write 5m, cache write 1h.
PRICES = {
    'opus': (4.0, 20.0, 0.20, 5.0, 8.0),
    'sonnet': (2.0, 10.0, 0.20, 2.5, 4.0),
    'haiku-5': (0.10, 0.50, 0.01, 0.125, 0.20),
    'haiku-4': (1.0, 5.0, 0.10, 1.25, 2.0),
}


def price_for(model):
    m = (model or '').lower()
    if 'opus' in m:
        return PRICES['opus']
    if 'sonnet' in m:
        return PRICES['sonnet']
    if 'haiku' in m and '4' in m:
        return PRICES['haiku-4']
    if 'haiku' in m:
        return PRICES['haiku-5']
    return PRICES['opus']  # unknown: assume the expensive one


def usage(session):
    messages = {}
    for path in (session/'claude-home/projects').rglob('*.jsonl') if (session/'claude-home/projects').exists() else []:
        try:
            lines = path.read_text(errors='replace').splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            msg = record.get('message') if isinstance(record, dict) else None
            if not isinstance(msg, dict) or not isinstance(msg.get('usage'), dict):
                continue
            key = msg.get('id') or record.get('uuid')
            messages[key] = (msg.get('model'), msg['usage'])
    totals = {'input': 0, 'output': 0, 'cache_read': 0, 'cache_write_5m': 0, 'cache_write_1h': 0, 'calls': 0}
    cost = 0.0
    by_model = {}
    for model, u in messages.values():
        cw = u.get('cache_creation') or {}
        w5 = cw.get('ephemeral_5m_input_tokens')
        w1 = cw.get('ephemeral_1h_input_tokens')
        if w5 is None and w1 is None:  # no breakdown: harness enables 1h caching, so price as 1h
            w5, w1 = 0, u.get('cache_creation_input_tokens', 0) or 0
        row = (u.get('input_tokens', 0) or 0, u.get('output_tokens', 0) or 0,
               u.get('cache_read_input_tokens', 0) or 0, w5 or 0, w1 or 0)
        p = price_for(model)
        c = sum(a*b for a, b in zip(row, p))/1e6
        cost += c
        for k, v in zip(('input', 'output', 'cache_read', 'cache_write_5m', 'cache_write_1h'), row):
            totals[k] += v
        totals['calls'] += 1
        by_model[model] = round(by_model.get(model, 0.0) + c, 4)
    return round(cost, 4), totals, by_model


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def progress(session):
    state = read_json(session/'state.json') or {}
    lifecycle = read_json(session/'agent-lifecycle.json') or {}
    bundles = state.get('bundles') or {}
    return {
        'stage': lifecycle.get('stage') or lifecycle.get('status'),
        'episodes_started': state.get('exploration_started'),
        'bundles': len(bundles) if hasattr(bundles, '__len__') else None,
        'submission': bool(state.get('submission')),
        'formal_scores': (session/'formal-scores.json').exists(),
    }


def snapshot_workspace(session, out):
    src = session/'agent-workspace'
    dst = out/'deployed_workspace'
    if dst.exists() or not (src/'AGENTS.md').exists():
        return False
    for path in src.rglob('*'):
        rel = path.relative_to(src)
        if rel.parts and rel.parts[0] in ('code', 'memory', 'output', 'runtime'):
            continue
        if path.is_file() and path.suffix in ('.md', '.json', '.py', '.txt') and path.stat().st_size < 2_000_000:
            (dst/rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst/rel)
    demo = src/'runtime/demonstrations'
    if demo.exists():
        shutil.copytree(demo, dst/'runtime/demonstrations', dirs_exist_ok=True)
    return True


def main():
    session, out, cap, project = Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3]), Path(sys.argv[4])
    out.mkdir(parents=True, exist_ok=True)
    stopped = False
    while True:
        cost, totals, by_model = usage(session)
        row = {'t': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'cost_usd': cost, 'tokens': totals,
               'by_model': by_model, **progress(session)}
        if snapshot_workspace(session, out):
            row['event'] = 'workspace_snapshot'
        if cost >= cap and not stopped:
            result = subprocess.run(['bash', str(project/'scripts/stop_auto_research_agent.sh'), '--config',
                                     str(session/'operator-input.json')], capture_output=True, text=True)
            row['event'] = f'CAP_REACHED stop rc={result.returncode}'
            (out/'stop.log').write_text(result.stdout + result.stderr)
            stopped = True
        with open(out/'timeline.jsonl', 'a') as handle:
            handle.write(json.dumps(row) + '\n')
        if row['formal_scores'] or (stopped and row['stage'] in ('exited', 'stopped', 'failed')):
            break
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
