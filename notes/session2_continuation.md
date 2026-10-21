# Session 2 (continuation): what it did and why it helped

Run: `runtime/auto-research/20261020T180046Z_b52a07ed8c`. All times are local (EDT), 2026-10-20.
The agent was resumed with its memory files, its code (`code/hanoi` = the session-1 v2 controller) and a compacted
summary of session 1. It got 6 new practice layouts (exploration seeds 8-13; the agent calls them N1-N6).

**Headline.** Session 1's controller (bundle `7bc56ae7`) scored 82/150 (54.7%). Its 68 failures were mostly grasp
failures: 46 episodes ended with a failed right-hand grasp of the red disk (36 right only, 10 both hands). In session 2
the agent found the cause: both hands closed at the same time, and the left hand's straight fingers blocked the
right index finger. It rewrote the controller so the hands grasp **one at a time** (bundle `c8712bc7`). The formal batch
is still running. At 19:05 EDT it stands at **109/113 successes** [corrected: the draft said 101/105, an earlier snapshot; `state.json` and the run logs now show 109/113]. The right hand's lift check passed on the
first try in **all 113** of those episodes [corrected]. Session 2 cost **$20.59** in new API spend.

Sources: `agent-workspace/memory/PROGRESS.md`, `memory/TIPS.md`, `mcp.jsonl`, `state.json`, the transcript
(`claude-home/projects/**/37931746-....jsonl`), `session2b/timeline.jsonl`, `published/runs/formal-*/stdout.log`.
The diff and the helper scripts are in this directory: `session1_to_session2.diff` and `scripts/s2_*.py`.

## 1. Chapters (episodes and rehearsals)

"New $" is the timeline cost minus session 1's $34.0769, taken at the chapter boundaries (minute samples).

| # | Wall clock | New $ (cum.) | Episode | What it tried | What it learned | Outcome |
|---|---|---|---|---|---|---|
| 0 | 14:01-14:06 | 1.02 (1.02) | none | Re-read memory and ADAPTATION.md. Rebuilt its dev tools (`experiments/ctl.py` stage runner, `mock_run.py`), which were not carried over. | Plan: N1 test v2 stage by stage, N2 rehearse, N3-N5 fixes, N6 final rehearsal. | Ready. |
| 1 | 14:06-14:24 | 2.65 (3.67) | N1, seed 8, interactive | Ran the session-1 v2 controller stage by stage on a new layout. | The left grasp of yellow worked (ratio .82). The right grasp of red failed its 2.5 cm lift check. The v2 regrasp lowered the closed hand, and the episode ended when the hand opened, with the red lying off its peg. | Fail, step 277. |
| 2 | 14:24-14:43 | 3.18 (6.85) | N2, seed 9, interactive | Studied the right grasp using ego-camera frames during the close. | The red was pushed about 4 cm and tilted **during the close**, before any lift. First hypothesis: the hand is too narrow for the 7.5 cm red, a geometry problem (later superseded). | Fail, step 268. |
| 3 | 14:43-16:00 | 10.23 (17.08) | N3, seed 10, interactive, plus 11 robot-only previews | 1) Mapped finger geometry in the previewer. 2) Closed the hands as before and checked the depth clouds. 3) Tried a "staged" right close (curl the fingers first, then swing the index). 4) Built a camera-based re-locator for regrasps (`face_pose`). 5) Wrote v3. | **Root cause:** in a simultaneous close, the left hand's straight middle and ring fingers reach y of about 0.007 and block the right index (stuck 4-6 cm outside the red). The right thumb then pushes alone and shoves the red 8.5 mm and yaws it -9 deg. This explains N1, N2, E5 and E7. The staged close was refuted: the red pitched 30 deg in transport. Episodes end when a disk is off its peg and no hand touches it. | Fail (step 1191, deliberate). v3 written 15:48-16:00 and mock-tested. |
| 4 | 16:00-16:37 | 2.00 (19.08) | N4, seed 11, interactive dev run of v3 | Ran v3 stage by stage: sequential grasps, tucked right fingers, the left moving in the background. | Both grasps worked first try (right ratio .98). The tuck keeps the fingers at least 2.5 cm from the peg. Stage step costs measured. A `goto` in to_blue cost 143 steps and could be dropped. | **Success**, step 1353. Registered v3a, then v3b. |
| 5 | 16:37-16:54 | 1.15 (20.23) | N5, seed 12, **rehearsal** of v3b `20f41499` | The controller ran unattended in the container. | The flow is repeatable on a low board (b=0.958), with both grasps working first try. It used 1237 steps (about 250 to spare, enough for one regrasp), 778 s. | **Success**, step 1237. Wrote v3c (failure fallbacks only). |
| 6 | 16:55-17:09 | 0.22 (20.45) | N6, seed 13, **rehearsal** of v3c `c8712bc7` | Final rehearsal of the submit candidate. | Same stage costs as N5 on the far-peg extreme (x -0.247). Right grasp ratio .94, left .84. 861 s. | **Success**, step 1243. Submitted v3c at 17:09:37. |
| 7 | 17:09-17:10 | 0.14 (20.59) | none | Wrote final notes. The harness saved the agent checkpoint `c1669ce7`. | Remaining risks noted: two regrasps would exceed the 1500-step limit, and the regrasp path was only tested in N3. | Formal batch started 17:10:08. |

For comparison, session 1 used 8 episodes (E1-E8), and only its last rehearsal (E8) succeeded.

## 2. Code diff: session-1 bundle `7bc56ae7` vs final session-2 bundle `c8712bc7`

`diff -ru` (excluding `__pycache__`) is saved as `session1_to_session2.diff` (627 lines). Only `controller.py`,
`robot.py` and `skills.py` changed. `perception.py` and `motion.py` are identical. Line numbers are in the new bundle
unless they are marked "old".

### 2.1 Grasp order: simultaneous -> sequential (the main fix)
The old stages were `approach` (both arms) and `grasp` (both hooks close, then a joint lift check). The new stages are
`grasp_r -> lift_r -> to_blue -> grasp_l -> place_r -> ...`.

Before (old controller.py:83-95):
```python
def grasp(rb, st, log, todo=("r", "l")):
    gm = grasp_multi(rb, {k: st["plans"][k] for k in todo}, log, from_out=False)
    ok = lift_check_multi(rb, {k: COLOR[k] for k in todo}, log)
    for k in todo:
        while not ok[k] and tries < 3 and rb.steps_used < REGRASP_BEFORE and not rb.ended:
```
After (controller.py:153-163, 303-304; the left staying at home is stated in the `grasp_r` docstring, not in an inline comment as the draft showed [corrected]):
```python
def grasp_r(rb, st, log):
    P = st["plans"]["r"]
    rb.move(55, r={"pos": P["pre"] + rb.r.bias, "rot": P["rot"], "hand": H_OPEN}, hold=6, observe=False)
    rb.settle_still(["r"], max_steps=20)
    ok = grasp_arm(rb, st, "r", log)
    if not rb.ended:
        rb.move(12, r={"hand": H_HOOK_TUCK}, hold=2, observe=False)
ORDER = ["perceive", "grasp_r", "lift_r", "to_blue", "grasp_l", "place_r", "release_r", "handover", "place_l", ...
```

### 2.2 Right-hand hook: unchanged; spare fingers now tucked
`H_HOOK` (skills.py:19) is byte-identical: `[0,1.5,1.6,1.4, 0..0, 1.396,0,.6,.3]`. The agent tried a lighter
staged close in N3, refuted it, and kept this hook. The new part is a "tuck" (skills.py:23-25). After the right
grasp, its middle and ring fingers curl into a C, so they do not hit the left fingertips while the red is placed and
the left lifts the yellow:
```python
TUCK = [0, 0.8, 0.8, 0.6]
H_HOOK_TUCK = H_HOOK[:4] + TUCK + TUCK + H_HOOK[12:]
H_OPEN_TUCK = H_OPEN[:4] + TUCK + TUCK + H_OPEN[12:]
```
`release` opens the right hand to `H_OPEN_TUCK` instead of `H_OPEN` (controller.py:253 onward).
The close itself moved into `close_hands` (skills.py:250-256), with the post-close hold cut from 8 to 6 steps.

### 2.3 Lift check: unchanged
`lift_check_multi` is identical in both bundles (a commanded 2.5 cm raise; the measured hand must rise more than 4 mm and the disk by more than LIFT_RATIO x the hand's
rise). [corrected: in the formal logs the measured hand rise is about 1.8 cm, not 2.5 cm.] If the disk is not visible, the check falls back to "hook joint stalled > 0.15 below its command". It now runs
per arm (`lift_check_multi(rb, {k: COLOR[k]})` in `grasp_arm`, controller.py:135-150) instead of on both arms at once.

### 2.4 Regrasp: reseat-then-open -> open, rise, re-locate, come in again
Before (old controller.py:62-81 [corrected: was 62-71]; the quoted lines are 70-73). The closed hand is lowered back to G, then opened:
```python
    rb.move(15, **{k: {"pos": P["G"] + a.bias}}, hold=4, observe=False)
    rb.move(10, **{k: {"hand": H_OPEN}}, hold=4, observe=False)
    rb.move(12, **{k: {"pos": P["G_out"] + a.bias}}, observe=False)
    rb.move(12, **{k: {"pos": P["G"] + a.bias}}, hold=4, observe=False)
```
After (controller.py:97-132):
```python
def regrasp(rb, st, k, log):
    open_rise(rb, k, log)                      # open in place, rise 3 cm
    if rb.ended or not replan(rb, st, k, log): # ego top face, or wrist-cam side faces (skills.face_pose)
        return False                           # disk moved > 4 cm: give up
    come_in(rb, st, k, log)                    # above G_out -> G_out -> tight goto G -> close
```
`replan` (controller.py:64-94) moves G to the disk's measured centre and yaw. `face_pose` (skills.py:155-194)
uses RANSAC to fit lines to the disk's side faces in the wrist camera, because the hovering hand hides the top face
from the ego camera. The agent's reasons: in N1, lowering a closed hand onto a displaced red ended the episode; in N2
and N3, a disk that is off its peg and untouched ends it.

### 2.5 Constants
| constant | old | new | where |
|---|---|---|---|
| `REGRASP_BEFORE` | `540` (both arms) | `{"r": 430, "l": 820}` | controller.py:33 |
| max regrasps | 3 (loop `tries < 3`) | `MAX_REGRASPS = 2` | controller.py:34 |
| pre-grasp height above G_out | `+0.04` | `+0.05` | controller.py:59 |
| close hold | `hold=8` | `hold=6` | skills.py:254 |
| `STAGE_DY` (left staging beside middle peg) | `0.06` | removed | old controller.py:128 |
| `CLEAR` | 0.06 | 0.06 (now via `zt_carry`, :37) | controller.py:30 |

### 2.6 Concurrency: background motion queue (robot.py)
New `Robot.bg_plan / bg_drain / _apply_bg / _arm_steps` (robot.py:46-98; `plan`/`hold_rows` at :99-140 now merge the queue) queue one arm's motion to run inside the
other arm's foreground moves. These calls use it:
- `to_blue` (controller.py:188-201): the left travels to its pre-grasp while the right carries the red.
- `place_r` (controller.py:233-243, `lift_bg` :208): the left lifts the yellow while the right places the red.

This wins back some of the steps that sequential grasping costs.

### 2.7 Step-saving: two gotos removed
`to_blue` now does a plain 45-step move instead of `goto_multi` (N4: the goto cost 143 steps).
`handover` (controller.py:270-289) does a 70-step move plus `settle_still` instead of `rb.goto("l", ...)`
(N4: 83 steps). `place_staged`'s goto above the peg removes the remaining error.

### 2.8 Failure fallbacks (v3c only)
Before (v3b): `if not grasp_r(...): log("...stopping"); break`. The same applied to the left grasp in `handover`.
After (controller.py:320-340): the controller logs "lift check never passed; continuing anyway" and carries on. If the
left check failed, `handover(..., lift_l=True)` lifts the yellow only after the right is home (:282-283). The tuck
is applied whenever the episode is still running, not only after a passed check (:160). The success path is
unchanged; the agent confirmed its mock logs were identical.

## 3. Which change fixed the 46/68 grasp failures

The fix was **sequential grasping** (§2.1), together with the tuck (§2.2) that makes it safe to bring the left hand
in after the right has grasped. The hook shape and the lift check did not change. The agent's own notes:

- PROGRESS.md:71-76: *"Simultaneous close: the LEFT hand's straight mf/rf (pointing -y from y~0.157) reach y~0.007 at
  the same x/z as the right's fingers and block the right index curl (right index stuck 4-6 cm outside the red ...).
  Unopposed right thumb pushed the red +8.5 mm y and yawed it -9 deg ... => explains N1/N2/E5/E7 red failures (all
  simultaneous). Single-hand red grasps (E2, E4) and E8 worked. DECISION: SEQUENTIAL grasps."*
- PROGRESS.md:70: *"N2 'ROOT CAUSE (geometry)' above is SUPERSEDED by N3: the real cause is HAND-HAND INTERFERENCE."*
- TIPS.md row 19: *"close both together -> left mf/rf (pointing -y) block the right index curl; unopposed right
  thumb shoves/yaws the red | refuted (N3; explains N1, N2, E5, E7)"*.
- Final message (transcript 21:10Z): *"Grasps one at a time. In earlier runs, closing both hands at once let the
  left hand's fingers block the right hand's grip, which shoved the red off its peg."*

**Evidence it worked.** In the session-2 formal logs (113 finished episodes at 19:05 [corrected: was 105]; `scripts/fc_formal.py`),
`lift check r red ... ok=True` appears exactly once per episode in all 113, and no right regrasp was ever needed. In
session 1, 46 of 150 episodes ended with a failed right grasp. The 2/2 rehearsals and N4 also passed the right grasp
first try. The new regrasp (§2.4) never ran for the right hand in the formal batch, so it did not cause the
improvement.

**What it costs and what it breaks.** Sequential grasping makes a successful run longer. Successful formal episodes
now take a median of 1241 steps; the session-1 E8 rehearsal took 1081. That leaves about 250 of the 1500 steps: one
regrasp fits, two do not. All 4 session-2 formal failures so far happened in `grasp_l`, at steps 702-880. In each one,
the left hand reached its grasp pose G 1.5-2.5 cm off in y with 10.6-11.4 deg of rotation error, even after `come_in`'s
two-iteration goto (the first goto after the background approach still had 2.2-3.0 cm y error and 18-21 deg)
[corrected: the draft attributed the residual to the end of the background approach]. In three of the four the left
hook joint ended at about 0 (command 1.2); in `formal-02fb629e...` it reached 0.82 [corrected: draft said all barely curled]. In two of them (`formal-93ac88d5...`, `formal-3a76d6b2...`), the lift check reported `ok=True`
although the hand rose 0 mm and the disk was not visible. This is a false positive from the joint-stall fallback in
`lift_check_multi`. The new weak point is the left approach after a background move, not the right grasp.

## 4. Intermediate bundles

| bundle | registered | what it is | used for |
|---|---|---|---|
| `c3e641949dd94b4b88a0f0a0a065d3c2` | 16:34:18 | **v3a**: the exact code that succeeded in N4 (snapshot `output/dev/v3a_snapshot`). `to_blue` uses `goto_multi`; `handover` ends with `rb.goto("l", ...)`. | Not rehearsed (fallback only). |
| `20f41499ab2b4898bd27e6e22fe456b2` | 16:37:06 | **v3b**: v3a minus the two gotos (§2.7), about 110 fewer steps. Stops if a grasp check never passes. | N5 rehearsal: success at step 1237. |
| `c8712bc7f03f4abf8d6a6fab4c00aae5` | 16:54:37 | **v3c**: v3b plus the failure fallbacks (§2.8). The success path is identical. | N6 rehearsal: success at step 1243. **Submitted** (sha 3095559c...). |
| `c1669ce7a39e45c588f50a10fcaec2df` | 17:10:08 | `agent_checkpoint` made by the harness, not a controller: the session transcript, settings, `transfer/code/hanoi` (same as v3c) and `transfer/memory/*`. | For a possible later continuation. |

## 5. Token and cost totals (session 2 only)

From `session2b/timeline.jsonl`: the last sample minus the first post-resume sample, which equals session 1's totals.

| | session 2 new | cumulative (S1+S2) |
|---|---|---|
| cost (USD) | **20.59** | 54.66 |
| API calls | 271 | 732 |
| output tokens | 374,639 | 1,022,229 |
| cache-read tokens | 33,391,284 | 90,433,175 |
| cache-write (1h) tokens | 801,684 | 2,015,810 |
| uncached input tokens | 542 | 1,464 |

Model: claude-opus-5-5, effort xhigh. Wall clock: 14:01-17:10 exploration (3 h 09 m), then the formal batch from 17:10.
N3 (diagnosis plus the v3 rewrite) took half of session 2's spend ($10.23). Each of the two rehearsals cost about
$1 or less. Simulator calls in session 2 (`mcp.jsonl`): 448 `dexjoco_step`, 98 `dexjoco_observe`, 11 `preview_run`,
1 `preview_describe`, 1 `status`. These counts are agent interactive calls only. Rehearsals ran in the
container instead (98 and 99 `dexjoco_step` calls).

## Verification

Checked 2026-10-20 19:05 EDT against the session-2 run dir, the two bundles and `session2b/timeline.jsonl`.
Helper scripts: `scripts/fc_formal.py`, `scripts/fc_state.py`, `scripts/s2_costs.py`, `scripts/s2_transcript.py`.

1. **Session 1: 82/150, 68 failures, 46 failed right grasps (36 right only, 10 both); E8 1081 steps.** CONFIRMED. `report/results.json` (`by_grasp_failure_arm`, `failure_last_stage.grasp` 46) and the session-1 verification of E8.
2. **Formal result "101/105", right lift check first try "in all 105".** WRONG (corrected; stale snapshot). At 19:05, `state.json` shows 113 formal results with 109 successes. Every one of the 113 `stdout.log` files has exactly one `lift check r red` line, and it is `ok=True`. There are no right regrasps. The success median is still 1241 steps (range 1195-1262).
3. **The 4 failures are all in `grasp_l` at steps 702-880. Two are false positives (`93ac88d5`, `3a76d6b2`): `ok=True`, hand +0.0000, disk not visible.** CONFIRMED. Mechanism text WRONG (corrected): the logged 1.5-2.5 cm y error and about 11 deg are the residual at G after `come_in`'s goto, not the end of the background approach. One of the four hooks curled to 0.82.
4. **Diff: 627 lines; only controller/robot/skills changed; perception/motion identical.** CONFIRMED. A fresh `diff -ru -x __pycache__` is byte-identical to `session1_to_session2.diff`, and `cmp` gives the per-file results.
5. **`H_HOOK` unchanged, TUCK at skills.py:23-25, `lift_check_multi` identical, close hold 8 -> 6.** CONFIRMED. The `lift_check_multi` bodies (old :183-207, new :259-283) diff clean. The "2.5 cm raise" is the commanded value; clarified [corrected].
6. **Code excerpts and line refs (grasp old :83-95, grasp_r :153-163, constants :30/:33/:34/:59, old STAGE_DY :128, fallbacks :320-340).** CONFIRMED, with two exceptions. WRONG (corrected): the old regrasp spans :62-81, not :62-71. The `# left arm still at home` comment in the grasp_r excerpt is not in the code, so it was removed.
7. **Fix = sequential grasping; agent's root cause (PROGRESS.md:70-76, TIPS row 19, final message 21:10Z).** CONFIRMED verbatim (with elisions) in `agent-workspace/memory/PROGRESS.md` lines 70-76, `TIPS.md` line 21 (row 19) and the transcript at 2026-10-20T21:10:01Z.
8. **Session 2 new spend $20.59, tokens (271 calls, 374,639 out, 33,391,284 cache-read, 801,684 cache-write 1h, 542 input), cumulative $54.66.** CONFIRMED. Last timeline sample (19:03:42) minus the 14:02:03 sample ($34.0769). The chapter cumulative costs 1.02/3.67/6.85/17.08/19.08/20.23/20.45/20.59 match the timeline samples at the episode-start transitions.
9. **Rehearsals: N5 v3b success at step 1237 in 778 s; N6 v3c success at step 1243 in 861 s; submitted at 17:09:37; formal started at 17:10:08; N1/N2/N3/N4 end steps 277/268/1191/1353.** CONFIRMED (`state.json` results and submission, formal_batch.started). The N6 right/left lift ratios .94/.84 match the rehearsal log.
10. **MCP counts (448 step, 98 observe, 11 preview_run, 1 preview_describe, 1 status).** CONFIRMED (`mcp_request` events in `mcp.jsonl`). One `mcp_error` (14:31:41) is not mentioned in the report.
UNVERIFIABLE: the bundle registration times (16:34:18, 16:37:06, 16:54:37, 17:10:08) are not stored in `state.json`. They are consistent with the timeline's bundle-count transitions (16:34:56, 16:37:59, 16:55:22, 17:10:57 samples).
