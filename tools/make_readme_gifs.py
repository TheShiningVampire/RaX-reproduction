"""Build the README GIFs from episode videos (sensors.mp4: ego | wrist_left | wrist_right, 30 fps, frame k = step k).
Usage: python -I make_readme_gifs.py <ffmpeg> <out_dir> <clips_dir> <pert_root>
clips_dir holds the report's feed_*.mp4 (1200x400); pert_root holds the perturbation batch dirs."""
import subprocess
import sys
import tempfile
from pathlib import Path

FF, OUT, CLIPS, PERT = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
TMP = Path(tempfile.mkdtemp())
PALETTE = "split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4"
ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: L,DejaVu Sans,{fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,3,4,0,7,8,8,6,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,9:00:00.00,L,,0,0,0,,{text}
"""


def ass(name, text, w, h, fs):
    path = TMP/f"{name}.ass"
    path.write_text(ASS_HEAD.format(w=w, h=h, fs=fs, text=text))
    return path


def run(args):
    subprocess.run([FF, "-y", "-loglevel", "error", *args], check=True)


def clip_gif(name, src, start, dur, speed, label, width=720):
    h = width // 3
    lab = ass(name, label, width, h, 15)
    vf = f"trim={start}:{start+dur},setpts=(PTS-STARTPTS)/{speed},fps=12,scale={width}:{h}:flags=lanczos,ass={lab},{PALETTE}"
    run(["-i", str(src), "-vf", vf, "-loop", "0", str(OUT/f"{name}.gif")])


def ego_panel(name, src, label, length, speed):
    """Third-person camera (left third), sped up, frozen on its last frame to `length` seconds."""
    lab = ass(name, label, 320, 320, 15)
    out = TMP/f"{name}.mp4"
    if src.suffix == ".png":
        # A run that stopped at step 0 has no episode video: show the one image the program saw.
        vf = f"fps=12,scale=320:320:flags=lanczos,ass={lab}"
        run(["-loop", "1", "-t", str(length), "-i", str(src), "-vf", vf, "-c:v", "libx264", "-crf", "18",
             "-pix_fmt", "yuv420p", str(out)])
        return out
    vf = (f"crop=iw/3:ih:0:0,setpts=PTS/{speed},fps=12,scale=320:320:flags=lanczos,"
          f"tpad=stop_mode=clone:stop_duration={length},trim=0:{length},ass={lab}")
    run(["-i", str(src), "-vf", vf, "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(out)])
    return out


def main():
    clip_gif("1_hook_grasp_works", CLIPS/"feed_s1_explore_e2.mp4", 23, 10, 1,
             "Session 1, practice ep. 2 · the hook grasp holds the red disk")
    clip_gif("2_agent_spots_the_cause", CLIPS/"feed_s2_explore_n3.mp4", 3, 11, 1,
             "Session 2, ep. N3 · the agent sees the hands' fingers collide")
    clip_gif("3_first_full_tower", CLIPS/"feed_s2_explore_n4.mp4", 33, 12.1, 1,
             "Session 2, ep. N4 · right hand first, then left: tower complete")
    clip_gif("4_unseen_layout_program_alone", CLIPS/"feed_s2_formal_108.mp4", 0, 41.4, 3,
             "Unseen test layout 108 · the program alone, no agent (3x speed)")

    layout = "layout-003"
    def video(batch):
        return next((PERT/batch/layout).rglob("sensors.mp4"))

    def first_view(batch):
        return sorted((PERT/batch/layout).rglob("calls/*/image_01.png"))[0]
    length, speed = 11, 4
    panels = [
        ego_panel("mass", video("pert_mass_r2"), "Heavier/lighter disks · 72/75 ✓", length, speed),
        ego_panel("texture", video("pert_texture_v2"), "New table texture · 66/75 ✓", length, speed),
        ego_panel("camera", first_view("pert_camera_v2"), "Moved camera · 29/75 · does not start", length, speed),
        # The colour run stopped at step 0 (no video); use its perturbation's rendered verification video.
        ego_panel("colors", next((PERT.parent/"diagnostics"/"verify_colors_new").rglob("sensors.mp4")),
                  "New disk colours · 0/75 · does not start", length, speed),
    ]
    inputs = sum((["-i", str(p)] for p in panels), [])
    # A 128-colour palette from moving pixels only turns the static purple/green disks blue/grey; use 256 colours from all pixels.
    graph = ("[0:v][1:v]hstack[top];[2:v][3:v]hstack[bot];[top][bot]vstack,split[a][b];"
             "[a]palettegen=max_colors=256:stats_mode=full[p];[b][p]paletteuse=dither=bayer:bayer_scale=4")
    run([*inputs, "-filter_complex", graph, "-loop", "0", str(OUT/"5_robustness_grid.gif")])
    for gif in sorted(OUT.glob("*.gif")):
        print(gif.name, gif.stat().st_size)


if __name__ == "__main__":
    main()
