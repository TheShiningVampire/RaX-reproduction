"""Cut report clips from the session's sensors.mp4 files, with burned-in captions written in
ASD-STE100 style (short sentences, present tense, active voice, one instruction or fact per sentence).
Stage captions are timed from the controller's own stage log (step / 30 Hz).
Usage: python -I make_clips.py <ffmpeg> <report_dir> <runs_table.json>"""
import json
import subprocess
import sys
from pathlib import Path

FPS = 30.0
STAGE_TEXT = {
    'approach': 'The hands move to the disks.',
    'grasp': 'The hands close on the red disk and the yellow disk.',
    'lift': 'The hands lift the disks.',
    'transport_r': 'The right hand moves the red disk to the right peg.',
    'place_r': 'The right hand lowers the red disk onto the blue disk.',
    'release_r': 'The right hand opens.',
    'handover': 'The right hand moves away. The left hand moves the yellow disk.',
    'place_l': 'The left hand lowers the yellow disk onto the red disk.',
    'release_l': 'The left hand opens.',
    'check': 'The program examines the result.',
}
OUTCOME = {
    'success': 'Result: the task is complete.',
    'grasp_right': 'Result: failure. The right hand does not hold the red disk.',
    'grasp_both': 'Result: failure. The hands do not hold the disks.',
    'lift': 'Result: failure. A disk falls during the lift.',
    'check': 'Result: failure. The disks are not in the correct position.',
}


def ts(seconds):
    seconds = max(0.0, seconds)
    h = int(seconds // 3600); m = int(seconds % 3600 // 60); s = seconds % 60
    return f'{h}:{m:02d}:{s:05.2f}'


def ass(label, events, duration):
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1200
PlayResY: 400

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,22,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,0,0,0,0,100,100,0,0,3,6,0,2,20,20,14,1
Style: Lab,DejaVu Sans,17,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,1,0,0,0,100,100,0,0,3,5,0,7,14,14,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [f'Dialogue: 0,{ts(0)},{ts(duration)},Lab,,0,0,0,,{label}']
    for start, end, text in events:
        lines.append(f'Dialogue: 0,{ts(start)},{ts(end)},Cap,,0,0,0,,{text}')
    return head + '\n'.join(lines) + '\n'


def stage_events(stages, duration, outcome, speed):
    events, prev = [], 0
    for name, total in stages:
        text = STAGE_TEXT.get(name)
        start, end = prev / FPS / speed, total / FPS / speed
        prev = total
        if text and end - start > 0.6:
            events.append((start, min(end, duration - 2.5), text))
    events = [e for e in events if e[1] > e[0]]
    events.append((max(0.0, duration - 2.5), duration, OUTCOME[outcome]))
    return events


def probe_duration(ffmpeg, path):
    out = subprocess.run([ffmpeg, '-i', str(path)], capture_output=True, text=True).stderr
    for token in out.split('Duration: ')[1:2]:
        h, m, s = token.split(',')[0].split(':')
        return int(h)*3600 + int(m)*60 + float(s)
    return 0.0


def encode(ffmpeg, src, dst, ass_path, speed):
    vf = f"setpts=PTS/{speed},scale=1200:400,ass={ass_path}"
    cmd = [ffmpeg, '-y', '-loglevel', 'error', '-i', str(src), '-an', '-vf', vf, '-r', '30', '-c:v', 'libx264',
           '-preset', 'slow', '-crf', '30', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(dst)]
    subprocess.run(cmd, check=True)


def main():
    ffmpeg, report, table = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    results = json.loads((report/'results.json').read_text())
    runs = {r['run']: r for r in json.loads(table.read_text())}
    rep = results['representative_formal_episodes']
    expl = results['exploration_episodes']
    clips = []
    # Exploration episode 1: the agent drives the robot itself.
    clips.append(dict(id='e1_manual', src=expl['E1']['video']['path'], speed=2.0,
                      label='Our run · practice episode 1 · the agent controls the robot · 2× speed',
                      events=[(0, 9, 'The agent sends motions one at a time and examines the cameras.'),
                              (9, 18, 'The agent tries different grasps on the red disk.'),
                              (18, 25, 'The red disk does not stay in the hand. The agent records the problem.')]))
    # Rehearsal E8: the frozen program alone.
    reh = runs.get('rehearsal-52fb2c2829ee430787bc7a534d51fd5e', {})
    clips.append(dict(id='e8_rehearsal', src=expl['E8']['video']['path'], speed=1.0, stages=reh.get('stages', []),
                      outcome='success', label='Our run · practice episode 8 · the program operates alone (rehearsal)'))
    pick = [('formal_success', rep['success'][0], 'success'),
            ('formal_grasp_right', rep['grasp_failure'][0], 'grasp_right'),
            ('formal_grasp_both', rep['grasp_failure'][1], 'grasp_both'),
            ('formal_lift', rep['lift_failure'][0] if isinstance(rep['lift_failure'], list) else rep['lift_failure'], 'lift'),
            ('formal_check', rep['check_failure'][0] if isinstance(rep['check_failure'], list) else rep['check_failure'], 'check')]
    for cid, e, outcome in pick:
        run = runs.get(e['run_id'], {})
        clips.append(dict(id=cid, src=e['video']['path'], speed=1.0, stages=run.get('stages', []), outcome=outcome,
                          label=f"Our run · test layout {e['layout_id']} · the program operates alone"))
    out = report/'clips'
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for clip in clips:
        duration = probe_duration(ffmpeg, clip['src']) / clip['speed']
        events = clip.get('events') or stage_events(clip['stages'], duration, clip['outcome'], clip['speed'])
        ass_path = out/f"{clip['id']}.ass"
        ass_path.write_text(ass(clip['label'], events, duration))
        dst = out/f"{clip['id']}.mp4"
        encode(ffmpeg, clip['src'], dst, ass_path, clip['speed'])
        manifest.append({'id': clip['id'], 'file': dst.name, 'source': clip['src'], 'speed': clip['speed'],
                         'seconds': round(duration, 1), 'bytes': dst.stat().st_size, 'label': clip['label'],
                         'captions': [e[2] for e in events]})
        print(clip['id'], round(duration, 1), dst.stat().st_size)
    # Montage of all clips in order.
    listing = out/'montage.txt'
    listing.write_text(''.join(f"file '{m['file']}'\n" for m in manifest))
    subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy',
                    str(out/'montage.mp4')], check=True)
    (out/'clips.json').write_text(json.dumps(manifest, indent=1))
    print('montage', (out/'montage.mp4').stat().st_size)


if __name__ == '__main__':
    main()
