"""Make a lock-free copy of a finished RaX session for parallel_batch, pointed at another GPU.
Copies the top-level JSON files and bundles/, rewriting sim_gpu and root.
Usage: python -I make_source_copy.py <source_session> <dest_dir> <gpu_uuid>"""
import json
import shutil
import sys
from pathlib import Path

src, dst, gpu = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
dst.mkdir(parents=True, exist_ok=False)
shutil.copytree(src/'bundles', dst/'bundles')
for path in src.glob('*.json'):
    shutil.copy2(path, dst/path.name)
(dst/'owner.lock').touch()


def retarget(config):
    config['sim_gpu'] = gpu
    if 'formal_sim_gpus' in config:
        config['formal_sim_gpus'] = []
    config['root'] = str(dst)
    return config


for name in ('configuration.json', 'operator-input.json'):
    path = dst/name
    if path.exists():
        path.write_text(json.dumps(retarget(json.loads(path.read_text())), indent=2))
state = json.loads((dst/'state.json').read_text())
state['configuration'] = retarget(state['configuration'])
(dst/'state.json').write_text(json.dumps(state))
print(dst, gpu)
