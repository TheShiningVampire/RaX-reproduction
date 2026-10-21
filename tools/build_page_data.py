"""Build data.js for the RaX Hanoi report page from verified report material and run outputs.
Usage: python -I build_page_data.py <out_data_js>"""
import json
import os
import sys
from pathlib import Path

R = Path(os.environ['RAX_REPRO_ROOT'])  # e.g. /data/user_data/<you>/rax_repro
S1 = R/'runtime/auto-research/20261020T031742Z_f1e2aa9d11'
S2 = R/'runtime/auto-research/20261020T180046Z_b52a07ed8c'
PERT = {k: [R/'runtime/auto-research'/v] for k, v in {'rand_full': 'pert_rand_full_r2', 'mass': 'pert_mass_r2', 'colors_new': 'pert_colors_new_v2', 'lighting': 'pert_lighting_v2', 'camera': 'pert_camera_v2', 'texture': 'pert_texture_v2'}.items()}


def load(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def formal_rows(state):
    return [r for r in (state or {}).get('results', []) if r.get('mode') == 'formal']


def score(session_dir):
    scores = load(session_dir/'formal-scores.json')
    state = load(session_dir/'state.json')
    rows = formal_rows(state)
    done = len(rows)
    ok = sum(1 for r in rows if r.get('task_complete') is True)
    out = {'done': done, 'success': ok, 'total': 150, 'final': bool(scores)}
    if scores:
        out.update(percent=round(scores['average_score_percent'], 1),
                   per_seed=[round(scores['official_seeds']['per_seed'][k]['average_score']*100) for k in ('0', '1', '2')])
    out['by_layout'] = {str(r.get('layout_id')): bool(r.get('task_complete')) for r in rows}
    return out


def batch_score(directories):
    """parallel_batch outputs (possibly split by layout range): formal-report.json 'episodes' rows."""
    by_layout, outcomes, final = {}, {}, True
    for directory in directories:
        rep = load(directory/'formal-report.json')
        if not rep:
            final = False
            continue
        final = final and rep.get('status') == 'completed'
        for row in rep.get('episodes', []):
            if row.get('layout_id') is None:
                continue
            ok = row.get('task_complete') is True
            by_layout[str(row['layout_id'])] = ok
            outcomes[str(row['layout_id'])] = row.get('formal_outcome')
    done = len(by_layout)
    total = 75*len(directories)
    out = {'done': done, 'success': sum(by_layout.values()), 'total': total, 'by_layout': by_layout,
           'final': final and done == total, 'outcomes': dict(__import__('collections').Counter(outcomes.values()))}
    if out['final']:
        out['percent'] = round(100*out['success']/total, 1)
    return out


def paired(base, other):
    both = [k for k in other['by_layout'] if k in base['by_layout']]
    lost = [k for k in both if base['by_layout'][k] and not other['by_layout'][k]]
    gained = [k for k in both if not base['by_layout'][k] and other['by_layout'][k]]
    return {'compared': len(both), 'lost': len(lost), 'gained': len(gained), 'lost_layouts': sorted(lost, key=int)[:40]}


def base_subset(base, other):
    keys = [k for k in other['by_layout'] if k in base['by_layout']]
    return {'n': len(keys), 'success': sum(base['by_layout'][k] for k in keys)}


def main():
    feeds = load(R/'report/v2/feeds.json', {})
    for fid, f in feeds.items():
        f['clip'] = f'clips/feed_{fid}.mp4'
        f['lines'] = [{'t': round(l.get('t_spread', l['t']), 2), 'wall': l.get('wall', ''), 'kind': l['kind'], 'text': l['text'],
                       'approx': bool(l.get('approx'))} for l in f['lines']]
        f.pop('video_path', None)
    s1 = score(S1)
    s2 = score(S2)
    pert = {k: batch_score(v) for k, v in PERT.items()}
    data = {
        'feeds': feeds,
        'chapters_s1': load(R/'report/chapters.json', []),
        'chapters_s2': load(R/'report/v2/chapters2.json', []),
        'scores': {'s1': s1, 's2': s2, **pert},
        'paired': {k: paired(s2, v) for k, v in pert.items()},
        'base_on_subset': {k: base_subset(s2, v) for k, v in pert.items()},
        'cost': {'s1': 34.08, 's2_new': 20.59, 'total': 54.66},
    }
    for v in data['scores'].values():
        v.pop('by_layout', None)
    Path(sys.argv[1]).write_text('window.REPRO = ' + json.dumps(data) + ';\n')
    print(json.dumps(data['scores']), json.dumps(data['paired']))


if __name__ == '__main__':
    main()
