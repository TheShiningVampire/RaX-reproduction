"""Write results/summary.json from the report's data.js and draw media/scores.svg from it.
Usage: python -I make_results_and_chart.py <data.js> <repo_root>"""
import json
import sys
from pathlib import Path

data_js, root = Path(sys.argv[1]), Path(sys.argv[2])
text = data_js.read_text()
data = json.loads(text[text.index('{'):text.rindex('}') + 1])
S, P, B = data['scores'], data['paired'], data['base_on_subset']


def rate(s):
    return round(100 * s['success'] / s['done'], 1) if s.get('done') else None


rows = [
    ('paper', 'Paper (authors), budget 8', 100.0, None, 'reported'),
    ('s1', 'Ours · session 1 (paper protocol, 8 episodes)', rate(S['s1']), f"{S['s1']['success']}/{S['s1']['done']}", 'baseline'),
    ('s2', 'Ours · session 2 (same agent, +6 episodes)', rate(S['s2']), f"{S['s2']['success']}/{S['s2']['done']}", 'improved'),
]
pert_names = [('mass', 'Heavier/lighter disks (±25%)', 'physics'), ('texture', 'New table texture', 'appearance'),
              ('lighting', 'New lighting', 'appearance'), ('camera', 'Moved camera', 'viewpoint'),
              ('rand_full', 'Camera + lighting + texture', 'appearance'), ('colors_new', 'New disk colours', 'task understanding')]
summary = {
    'task': 'DexJoCo bimanual_hanoi',
    'formal': {k: {'success': S[k]['success'], 'episodes': S[k]['done'], 'percent': rate(S[k]),
                   'per_seed_percent': S[k].get('per_seed')} for k in ('s1', 's2')},
    'perturbations_layouts_0_74': {
        k: {'label': label, 'kind': kind, 'success': S[k]['success'], 'episodes': S[k]['done'], 'percent': rate(S[k]),
            'unperturbed_same_layouts': f"{B[k]['success']}/{B[k]['n']}", 'twins_lost': P[k]['lost'],
            'twins_gained': P[k]['gained'], 'final': S[k].get('final')}
        for k, label, kind in pert_names if k in S},
    'api_cost_usd': data.get('cost'),
}
(root/'results').mkdir(exist_ok=True)
(root/'results/summary.json').write_text(json.dumps(summary, indent=2) + '\n')
for k, label, kind in pert_names:
    if k in S:
        rows.append((k, f'+ {label}', rate(S[k]), f"{S[k]['success']}/{S[k]['done']}", kind))

COL = {'reported': '#8a96a3', 'baseline': '#c2554b', 'improved': '#2e8b57', 'physics': '#2e8b57',
       'appearance': '#d9962b', 'viewpoint': '#d9962b', 'task understanding': '#c2554b'}
W, L, R, top, rh = 900, 330, 110, 56, 34
H = top + rh * len(rows) + 40
x = lambda v: L + (W - L - R) * v / 100
out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">',
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
       '<text x="16" y="28" font-size="18" font-weight="700" fill="#15212b">Success on DexJoCo Tower of Hanoi (official test layouts)</text>',
       '<text x="16" y="46" font-size="12" fill="#566573">Program runs alone, no agent, no retries. Rows 1–3: 150 layouts. Perturbation rows: layouts 0–74 (unperturbed: 73/75).</text>']
for v in (0, 25, 50, 75, 100):
    out.append(f'<line x1="{x(v):.1f}" y1="{top-6}" x2="{x(v):.1f}" y2="{H-34}" stroke="#e3e8ec"/>')
    out.append(f'<text x="{x(v):.1f}" y="{H-18}" font-size="11" fill="#566573" text-anchor="middle">{v}%</text>')
for i, (k, label, v, frac, kind) in enumerate(rows):
    y = top + i * rh
    if i == 3:
        out.append(f'<line x1="16" y1="{y-4}" x2="{W-16}" y2="{y-4}" stroke="#15212b" stroke-dasharray="3 3"/>')
    out.append(f'<text x="{L-10}" y="{y+17}" font-size="13" fill="#15212b" text-anchor="end">{label}</text>')
    out.append(f'<rect x="{L}" y="{y+4}" width="{max(x(v or 0)-L, 1.5):.1f}" height="20" rx="2" fill="{COL[kind]}"/>')
    lab = f'{v:g}%' + (f'  ({frac})' if frac else '')
    out.append(f'<text x="{x(v or 0)+6:.1f}" y="{y+19}" font-size="12" fill="#15212b">{lab}</text>')
out.append('</svg>')
(root/'media').mkdir(exist_ok=True)
(root/'media/scores.svg').write_text('\n'.join(out) + '\n')
print(json.dumps(summary['formal']), {k: v['percent'] for k, v in summary['perturbations_layouts_0_74'].items()})
