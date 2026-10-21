# The submitted program (code-as-policy): bimanual_hanoi

Paths below are relative to the session dir
`$ROOT/runtime/auto-research/20261020T031742Z_f1e2aa9d11/` unless absolute.
`B/` = `bundles/7bc56ae7250d439d93baa365d5c58c08/` (the submitted bundle).

## 1. Files

The bundle is byte-identical to the live copy `agent-workspace/code/hanoi/`, and to the code
copied into each formal run (checked with `cmp` against `published/runs/formal-f4edd89c.../code/`).

| File | Lines | Role |
|---|---|---|
| `B/controller.py` | 256 | `main(ctx)` → `run()`: 11 stages, logging to `output/hanoi_log.txt` |
| `B/skills.py` | 395 | Scene class, grasp geometry, hand postures, grasp, lift check, lift, place. About 120 lines (`place`, `place_fast`, `pick`, `lift_check`, `release_and_back`, `lift`, `lower_to`) are left over from earlier versions and never called |
| `B/robot.py` | 204 | `Robot`: action-row planning (cosine-eased interpolation plus slerp), `goto`/`goto_multi` with integral correction of the steady-state error of the operational-space controller (OSC), `settle_still`. `descend_until_contact` is never called |
| `B/perception.py` | 157 | Decodes observations (RGB, depth, intrinsics, camera poses), back-projects depth to points, fits a minimum-area rectangle, colour masks, peg finder |
| `B/motion.py` | 52 | Rotation and state-vector helpers |
| **Total** | **1064** | |

## 2. Control flow of `main(ctx)`

`main` (controller.py:243) opens the log and calls `run` (controller.py:203). `run` seeds a 2 mm z bias for each arm
(skills.py:37-47) and runs the stages in a fixed order (controller.py:208). The loop stops when the episode ends,
or when a stage raises an exception (controller.py:235). The episode limit is 1500 steps
(`session1/deployed_workspace/TASK.md:9`). "Observed" step counts are medians over the 150 formal runs,
taken from the `== stage` lines in `published/runs/formal-*/stdout.log`.

| # | Stage | What it does | Step budget in the code | Observed (median, range) |
|---|---|---|---|---|
| 1 | perceive (c:30) | One ego RGB-D observation → `Scene`: each disk's top face, centre and yaw; the peg axes; board top `b`; `peg_top`. Then plans each arm's grasp: G (the grasp pose), G_out (the same pose with the thumb 2.2 cm further out), pre = G_out + 4 cm z, and the hand rotation | 0 (observations only) | 0 |
| 2 | approach (c:50) | Both arms move to `pre` with the hand open and the wrist rotated front-facing, settle, then go straight down to G_out | 60+6 move, ≤20 settle, 15+4 move | 105 (fixed) |
| 3 | grasp (c:83) | Both arms slide to G at the same time (`goto_multi`, tolerance 2 mm, ≤3 correction passes), then close the hook postures (25+8 steps), then run the 2.5 cm lift check on both. An arm that fails gets up to 3 regrasps, and only while `steps_used < 540`. Finally sets the default held offset (peg xy − flange xy) | ~150; each regrasp adds ~70–110 | 152 (142–422) |
| 4 | lift (c:105) | Raises both disks together to flange z = `peg_top + 0.06 + BOTTOM_DZ`, in segments of ≤5 cm over 25+3 steps each (~2 mm/step). Then settles and makes one height correction if the error is above 6 mm | ≤12×28, plus settles | 188 (28–193) |
| 5 | transport_r (c:131) | The right arm carries red over the blue peg (`goto_multi`, n=45). At the same time, the left arm stages yellow 6 cm +y of the middle peg. Then the wrist camera measures the held offset | 45+4, plus 1 correction | 123 (123–148) |
| 6 | place_r (c:147 → `place_staged` s:306) | goto to disk bottom 1.5 cm above the peg top, with the xy error removed. Then one eased descent over 40 steps to 1.2 cm below the landing height `b + 1·DISK_H`. Counts as landed if it ends within 3.5 cm; otherwise rises and retries with a ±5 mm search shift (≤3 tries) | ~141 per try | 141 (136–141) |
| 7 | release_r (c:156) | Opens the right hand, backs off 6 cm in −x | 12+4+15+2 = 33 | 33 |
| 8 | handover (c:173) | The right arm rises 8 cm and returns to its home pose (`HOME_POS`). The left arm carries yellow over the blue peg (70+6 steps, plus a goto). Then the left held offset is measured | ~165 | 165 (165–248) |
| 9 | place_l | As in stage 6, with landing height `b + 2·DISK_H` | ~141 | 141 |
| 10 | release_l | Opens the left hand and rises 7 cm. Success is usually registered here, once the hand clears the stack (73 of the 82 successes end in this stage) | 38 | 38 |
| 11 | check (c:190) | Holds 10 steps, logs each disk's top height and stack level (diagnostics only, no action) | 10 | 10 |

Successful runs end at a median of step 1081 (limit 1500). Failed runs end at a median of step 314.

## 3. Hard-coded constants: geometry, scene and grasp

c = controller.py, s = skills.py, p = perception.py, r = robot.py

| Name | Value | Meaning | Where |
|---|---|---|---|
| `DISK_H` | 0.0485 m | Disk thickness. Gives board top (median disk top − DISK_H) and both landing heights | s:26; used at s:66, c:149 |
| `HALF` | yellow 0.0275, red 0.0375, blue 0.05 m | Disk half-widths. Set grasp standoff, thumb offset and held-offset estimate; the measured `size` is only logged | s:27 |
| `GRASP_DZ` | 0.07 m | Flange height above the board top at grasp | s:28 |
| `BOTTOM_DZ` | 0.0698 m | Flange minus held-disk bottom (measured once in exploration E2). Sets lift, transport and landing heights | s:29 |
| `PALM_GAP_U` | 0.0635 m | Flange stands half-width + this in front of the disk centre (palm about 2.3 cm from the face) | s:30 |
| `THUMB_IN` | 0.0128 m | Flange offset inward from the thumb-side face | s:31 |
| `THUMB_CLEAR` | 0.022 m | Extra thumb-side offset at G_out during the approach | s:32 |
| `R_RIGHT` / `R_LEFT` | fixed matrices | Front-facing hand frames: palm +x, fingers ±y, index down | s:11-12 |
| `H_OPEN`, `H_HOOK`, `H_HOOK_L` | 16-joint postures | Open hand; right hook (index j0–3 plus thumb); left deep hook (j8–11 plus thumb) | s:13, 19, 22 |
| `HOOK_J1` | r 1, l 9 | Hooking finger's proximal joint, used by the fallback stall test | s:24 |
| `LIFT_RATIO` | r 0.6, l 0.5 | Lift check passes if disk rise / hand rise exceeds this | s:25 |
| stall threshold | 0.15 rad | Fallback lift check: target − actual angle of the hooking joint | s:202 |
| lift check dz | 0.025 m, hand rise > 0.004 | Test lift height and the minimum hand rise that counts | s:183, 199 |
| `SEED` bias | +0.002 m z | Initial guess for the OSC position bias | s:37-38 |
| peg-top fallback | b + 0.177 m | Used only if no peg is detected | s:68 |
| disk-centre fallback | +0.01 m x | Disk centre if the peg is not found (the ego centre is biased toward the camera) | s:77 |
| peg radius | 0.006 m | Shifts the visible peg surface back to the peg axis | p:136 |
| peg search | radius 0.06 m, z from disk top + 0.01 to +0.25 | Region searched for brown peg pixels | p:122-129, s:61 |
| `CLEAR` | 0.06 m | Held-disk bottom above the peg tops while carrying | c:26 |
| pre-grasp | G_out + 0.04 m z | Overrides the `pre` returned by `grasp_poses` | c:45 |
| `STAGE_DY` | 0.06 m | Left staging point, +y of the middle peg | c:128 |
| `REGRASP_BEFORE` / tries | 540 steps / 3 | Regrasp cut-off and the maximum regrasps per arm | c:27, 91 |
| regrasp G tolerance | 0.0025 m | Runs a goto if the flange is further than this from G after the plain moves | c:75 |
| offset agreement | 0.012 m | Wrist estimate is averaged with the default if within this; otherwise the default is used | c:118 |
| release moves | right −0.06 m x; left +0.07 m z | Move away after opening | c:163, 165 |
| `HOME_POS` / `HOME_ROT` | (−0.443, −0.40, 1.45), start orientation | Right-arm park pose during handover | c:169-170 |
| handover rise | 0.08 m | Right arm rises before parking | c:178 |
| place | above peg top +0.015, descend to land −0.012, success if within 0.035 m, search 0.005 m, ≤3 tries; measured bottom clipped to [BOTTOM_DZ, 0.085] | Placement geometry | s:306-334 |
| colour thresholds | RGB/HSV boxes | Yellow, red and blue disk masks; brown peg mask | p:146-157, p:117-119 |
| min point counts | 600 (wrist z), 300 / 200 (offset), 40 (ego disk), 15 (peg) | Minimum point counts for a valid estimate | s:119, 133, 144, 154; p:101, 131 |
| motion | goto gain 0.8, settle 1.2 mm / 0.4° per 5 steps, max rotation correction 15°, 150-row step chunks | Controller tuning | r:102, 164, 80 |

**Measured at runtime instead:**

- From ego depth: each disk's centre, taken as the peg axis (`Scene.center`, s:71).
- The disk yaw, from the minimum-area rectangle; it rotates the whole grasp (s:94).
- The board top, from the median disk top − `DISK_H`.
- `peg_top`, the 99th-percentile z of the peg points.
- The OSC bias, re-learnt on every `goto` (r:157-161).
- The held-disk xy offset, from the wrist camera; it is averaged with the default offset, and the default (taken at grasp time) is used if the two disagree by ≥12 mm (c:111-125).
- The held-disk bottom, from the wrist camera; used in `place_staged` after clipping.
- The disk rise during the lift check.
- The final stack heights, which are only logged.

**Not measured:** the top of the placed red disk. The yellow landing height is the nominal `b + 2·DISK_H`.
The disk sizes are also not measured, even though `size` is computed.

## 4. Perception

- **Cameras:** `ego`, `wrist_right` and `wrist_left` (TASK.md:8). Every observation is RGB plus depth
  (16-bit mm → m, p:30), with intrinsics and camera poses. Points are back-projected in the OpenGL
  convention (p:46-69).
- **Scene, from one ego frame (s:50-69):** each disk is segmented with an RGB/HSV threshold mask (p:146),
  turned into a world point cloud, and its top slab kept (points within 6 mm of the 97th percentile z).
  A minimum-area rectangle on the slab gives the centre and yaw (p:82-114). The pegs are found from the
  brown mask (p:117) in a cylinder around each disk, above the disk top; the median xy is shifted 6 mm
  away from the camera to reach the axis, and the 99th-percentile z gives the peg top (p:122-137).
- **Held disk, from the wrist camera of the holding arm:**
  - xy offset: the thumb-side face edge (the extreme 3 % in y) plus the near-x edge, each shifted by
    the half-width (s:128-147).
  - bottom height: the 2nd-percentile z of the colour cloud (s:150-157).
  - lift check height: the median z (s:109-125). It falls back to the ego top face if the wrist camera
    sees fewer than 600 points. A comment notes that the left fingers carry thin yellow stripes that
    contaminate the yellow mask (s:117, c:119).
- No learned model, no reference images and no Gemini calls are used.

## 5. Failure handling

- **Lift check** (`lift_check_multi`, s:183): both arms rise 2.5 cm, settle, and are re-observed.
  An arm passes if the hand rose more than 4 mm and the disk rose more than 0.6× (right) or 0.5× (left)
  of the hand's rise. If the disk was not seen by the same camera before and after, it falls back to
  "the hooking joint stalled more than 0.15 rad short of its target".
- **Regrasp** (c:62): with the hand still closed, lower back to G so a tilted disk reseats; open; back
  out to G_out; slide in to G; goto if more than 2.5 mm off; close again; re-check. At most 3 regrasps
  per arm, and only before step 540.
- **If the grasp still fails:** `run()` ignores `grasp()`'s return value (c:222). The program keeps
  going with lift, transport and place regardless. The only use of `grasp_ok` is to skip staging the
  left arm (c:138). There is no abort and no re-plan.
- **Placement:** if the disk stays high (sitting on the peg tip), it rises and retries with a ±5 mm
  shift (≤3 tries). If all tries fail it logs "could not engage", and the following stages continue
  anyway.
- **Exceptions:** an exception in any stage stops the loop and logs a traceback (c:235). This
  never happened in the formal runs (0/150 logs contain "raised").
- **Formal outcome by failure mode** (`published/runs/formal-*/{result.json,stdout.log}`, 150 runs, 82 successes):

  | Group | Runs | Successes | What happened |
  |---|---|---|---|
  | Right lift check passed first time | 92 [corrected] | 71 | |
  | Right lift check failed first time, episode ended before any regrasp | 10 [corrected] | 0 | Both arms' first lift checks failed in these runs |
  | Right needed 1 regrasp | 45 | 11 | |
  | Right needed 2 regrasps | 3 | 0 | |
  | Episode ended during grasp | 46 | 0 | Right grasp never confirmed. In 36 of the 46 logs the episode ends during a regrasp (the last lift check reads hand +0.0000), so the simulator's failure condition fires first. The other 10 end right after the first lift check, with no regrasp [corrected] |
  | Episode ended during lift | 15 | 0 | |
  | Ran every stage but did not succeed | 7 | 0 | |

  The left lift check passed on the first try in 137/150 runs [corrected]. 147/150 runs had no left regrasp, but
  10 of those are the runs that ended during grasp after a failed first check. The other 3 needed one left regrasp.
- `session1/runs_table.json` has `task_complete=false` for every formal run, so its outcome field is
  wrong. Use `formal.json` or `formal-scores.json` for outcomes.

## 6. Tools

Through `ctx.call`, the program only calls `dexjoco_observe` (r:24, r:38) and `dexjoco_step` (r:84).

- **Imports:** os, sys, time, traceback, json, base64, io, numpy, scipy and PIL. There is no network,
  subprocess or Gemini use (grep over `B/*.py`).
- **Files:** the only file it writes is `output/hanoi_log.txt`.
- **Timing:** every formal `result.json` records `gemini_api_seconds: 0.0`.

## 7. Ours vs theirs (authors' published Hanoi program)

Source: `RAX.simcases.hanoi` in
`$SCRATCH/projjs/simcases.js`
(`.code.lines`, `.program`, `.chapters`).

**Same overall approach.** Both programs:

- Read the scene once from ego depth (disk top faces, pegs from the depth points above the disks).
- Grasp both disks at the same time.
- Run a lift check ("did the disk rise at least half the lift?"), and on failure open, back off and grasp again.
- Carry red over the blue peg, lower it and release; then carry yellow over and lower it.
- Run without Gemini, as plain numpy over depth.
- Overlap the arms' motions to save steps. Theirs lifts yellow while the right arm parks (about 100 steps saved). Ours stages yellow next to the middle peg while red is carried, and parks the right arm before the left carry.

**Different grasp idea.** In their exploration log (chapter "Measuring its fingertips"), the agent segmented
the white fingertip caps in the wrist camera and measured the tips in 3D:

| | Offset from the flange |
|---|---|
| Thumb tip (`TH_TIP`) | (−0.024, 0.038, −0.163) |
| Index tip (`IX_TIP`) | (0.083, 0.036, −0.133) |

It then built a **rolled vertical palm-down pinch** on that geometry: roll 0.44 rad, thumb tip 6 mm outside
the near face, index at the far face, and the pinch line through the disk's centre so the disk stays level.

Ours uses a **front-facing hook grasp**:

- The palm faces +x, the fingers lie horizontal along ±y with the index down, and the hand stays
  `HALF + 6.35 cm` in front of the disk centre.
- One finger chain curls around the far face as a hook while the thumb presses the side face.
- The grasp is set by flange offsets found by trial in exploration (`agent-workspace/memory/TIPS.md`, row 1:
  "flange (meas) = (cx-0.101, cy-0.0247, b+0.07)" [corrected: exact wording]). It is not derived from measured fingertip positions.
- The squeeze comes from commanding joint angles past the disk, so the servo stalls against it
  (s:14-22). This grasp is the weak point: right grasp failures account for 46 of our 68 formal failures.

**Other differences**

| | Theirs | Ours |
|---|---|---|
| Alignment before lowering | Settles, then models the arm's lag (decays ×0.78 every 5 steps) and aligns on the predicted final position, to a 4 mm tolerance, from three cameras | Integral-bias `goto` plus `settle_still`, and a single wrist-camera offset estimate averaged with the grasp-time default |
| Yellow landing height | Re-measures the top of the placed red disk and uses it as the support | Uses the nominal `b + 2·DISK_H` |
| Lowering | Stops just below the peg tip and checks whether the disk caught there, then lowers onto the stack | One staged descent with a landing-height test and ±5 mm search retries |
| Testing during exploration | 47 exploration episodes; it injected its own errors (8 and 15 mm misalignments, pinches 4.5 cm too high); 41/41 autonomous runs and 3/3 rehearsals passed before submitting | 8-episode budget: 6 interactive episodes and 2 rehearsals (`published/runs/`); no fault-injection runs. The program as submitted ran in exactly one rehearsal, which passed at step 1081 (`rehearsal-52fb2c28.../result.json`). The earlier bundle `2966a2af...` failed its rehearsal |
| Formal result | 150/150 | 82/150 (54.7 %) |

In short, the architecture is the same (perceive, simultaneous grasp, lift check with regrasp, carry,
staged place). The grasp differs: theirs is a pinch designed from measured fingertip geometry, ours is an
empirically tuned hook. Theirs also uses lag-predictive alignment and re-measures the support it places onto.
Ours does neither, and its right-hand hook is unreliable.

## Verification

Each claim was checked against the cited source. Run statistics were re-parsed from all 150
`published/runs/formal-*/{result.json,stdout.log}` with a script kept outside the session dir.

1. **CONFIRMED.** Bundle line counts are 256/395/204/157/52 = 1064. The 5 files are byte-identical (`cmp`) to
   `agent-workspace/code/hanoi/` and to `code/` in all 150 formal runs.
2. **CONFIRMED.** The episode limit is 1500 steps (`session1/deployed_workspace/TASK.md:9`). The cameras are ego,
   wrist_left and wrist_right (TASK.md:8).
3. **CONFIRMED.** `run()` calls `grasp(rb, st, log)` without using its return value (controller.py:222). `grasp_ok`
   is read only at c:138, to decide left staging. `REGRASP_BEFORE = 540` (c:27). The exception handler is at c:235.
4. **CONFIRMED.** The constants match: `DISK_H` 0.0485 (s:26), `HALF` (s:27), `GRASP_DZ` 0.07, `BOTTOM_DZ` 0.0698 (E2),
   `PALM_GAP_U` 0.0635, `THUMB_IN` 0.0128, `THUMB_CLEAR` 0.022 (s:28-32), `LIFT_RATIO` 0.6/0.5 (s:25). `place`,
   `place_fast`, `pick`, `lift_check`, `release_and_back`, `lift` and `lower_to` are never reached from `main`
   (127 lines). `ctx.call` is used only for `dexjoco_observe` and `dexjoco_step` (robot.py:24, 38, 84).
5. **WRONG (corrected).** The failure table said "right lift check passed first time: 102 runs". In fact 92 runs
   passed first time (71 succeeded). 102 is the number of runs with no right regrasp, and it includes 10 runs that
   ended after a failed first check. The claim that the 46 grasp-stage runs all end "during the regrasp" holds for
   only 36 of them.
6. **WRONG (corrected).** "The left grasp passed first try in 147/150" is wrong. 137/150 passed first try; 147 is
   the number of runs with no left regrasp.
7. **CONFIRMED.** There are 82/150 successes. The episode ended in each stage as follows: grasp 46, lift 15,
   check 7 failed and 9 succeeded, release_l 73 succeeded. The median end step is 1081 for successes and 314 for
   failures. Per-stage step medians and ranges match §2. No log contains "raised" (0/150), and
   `gemini_api_seconds` is 0.0 in all 150 runs.
8. **CONFIRMED.** The runs are 6 interactive and 2 rehearsals. Rehearsal 52fb2c28 ran bundle 7bc56ae7 and succeeded at
   step 1081. Rehearsal c967110e ran bundle 2966a2af and failed (reason "exit", step 1213). `runs_table.json` has
   `task_complete=false` for all 152 rows.
9. **CONFIRMED, with a wording fix.** TIPS.md row 1 (line 5) reads "flange (meas) = (cx-0.101, cy-0.0247, b+0.07)".
   The quote was tightened to this exact text.
10. **CONFIRMED.** Checked in `simcases.js`: `TH_TIP` (−0.024, 0.038, −0.163) and `IX_TIP` (0.083, 0.036, −0.133),
    `ROLL = 0.44`, the thumb 6 mm outside the face, lag decay ×0.78 every 5 steps, `tol = 0.004`, three-camera
    alignment, 47 exploration episodes, "41 of 41 autonomous runs", rehearsal "3/3", the 8 and 15 mm injected
    errors with a pinch 4.5 cm too high, "about 100 steps" saved, and "all 150 formal episodes".
