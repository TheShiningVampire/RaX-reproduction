# Task file: bimanual_photograph

Read `COMMON.md` (same folder) first. This file sets the parameters and the task sections it asks for.
Citations: `U:` = upstream worktree `~/my_things/codes/rax/.worktrees/dexjoco-v2`; `S:` = the
development worktree `~/my_things/codes/rax/.worktrees/add-state-info` (line numbers as of a42f98b;
re-check them at CODE_COMMIT); `D:` = the official env
`/data/user_data/vawale/rax_repro_v2/DexJoCo/dexjoco/dexjoco/sim/envs/panda_bimanual_photograph_env.py`;
`GL:` = `S:services/dexjoco/goals.py` at 223f1a8 (re-check line numbers at CODE_COMMIT).

## A. Parameters

```
TASK          = bimanual_photograph
ROOT          = /data/user_data/vawale/rax_state/bimanual_photograph
CODE_COMMIT   = <fill in after GPU smoke passes>   # stop and ask if still a placeholder
CODE_WORKTREE = ~/my_things/codes/rax/.worktrees/state-run-bimanual_photograph
REUSE_ENVS    = /data/user_data/vawale/rax_repro_v2/runtime/envs
GPU_JOB       = <optional: id of a running katef GPU job; empty = submit new jobs (COMMON P1.4, P2.5)>
```

## B. Task facts

- **Goal the agent sees:** "Pick up the camera with the left hand, aim it at the logo and press the
  shutter button with the right hand." (U:services/dexjoco/task_rules/bimanual_photograph.md:1)
- **Success, at the same step** (task_rules:3-6): the lens is inside a target region in front of the
  logo; the camera points at the logo within a set angle; something other than the camera itself
  presses the shutter button.
- **Scene variation** (task_rules:8): the logo's position on the wall and the camera's position change.
- **Robot:** dual arm (two Pandas with Allegro hands), **step cap 1000** (U:services/dexjoco/tasks.py:38).
  The env also ends the episode at the first successful step (D:861).
- **Official check details (the agent reads region, angle and shutter rules through `goal`; the
  layout ranges are not in the tool; never paste any of this into the workspace yourself):** region = a cylinder 0.40 m in front
  of the logo, radius 0.16 m, half height 0.10 m (D:25-27, D:882-889); aim = camera axis within 10 deg
  of world +x (D:28-29, D:891-900); shutter = any contact of geom `camera_body_top_cap` with a geom
  that is not part of the camera (D:902-913). So a press by either hand, or by the table, counts.
  Logo y,z sampled in [-0.10,0.10] x [1.22,1.38] in the wall frame (D:23, D:729); camera x in
  [-0.30,-0.20], y in [0.10,0.20], z = table + offset (D:24, D:743-748); table height +0..0.05 m (D:22).
- **Ground-truth diagnostics** per episode: `region_pass`, `angle_pass`, `shutter_pressed`,
  `radial_dist`, `region_height_dist`, `view_angle_deg` (D:916-923; U:services/dexjoco/analysis.py:369-386
  turns them into "met at the end / met earlier / never met" lines). Use these for failure stages.
- **Demos:** `runtime/envs/host/bin/python scripts/setup_dexjoco_demos.py --gpu $G --task bimanual_photograph`
  (U:scripts/setup_dexjoco_demos.py:11). Terminal-state images land under
  `R/runtime/reference-demos/dexjoco/bimanual_photograph/`.

### What `dexjoco_object_states` reports for this task (check at CODE_COMMIT)

`state_sources('bimanual_photograph')` = the live tail sources + `STATE_EXTRA` (dcbf92f), plus arm joints:
- `camera`: `position_m` + `quaternion_wxyz` from free joint `camera_root`; at `full` also
  `linear_velocity_mps`, `angular_velocity_radps` and `size`.
- `logo`: `position_m` + `quaternion_wxyz` of geom `photograph_logo_disk` (`geompose:`, added in dcbf92f;
  it labels no body, so it has no velocity or size and contacts never resolve to it).
- `arm_joint_positions_rad`: `right` and `left`, 7 values each. Hand joints stay in the official state vector.
- At `full`: `contacts` (a hand on the camera or on its shutter cap shows as rows with `a` = `camera`)
  and `goal`, below. If `logo` is missing at CODE_COMMIT, stop and ask me before P2.
- **What `goal` reports** (`GL:208-240`, `bimanual_photograph()`). It calls the official, side-effect
  free `env._compute_success_metrics()` (`GL:209-210`) and maps its metrics:
  - `description`: lens point inside the target cylinder in front of the logo (radius 0.16 m, half height
    0.10 m), camera aimed within 10 deg of world +x, shutter pressed by something other than the camera,
    all at the same step (`GL:229-231`).
  - `conditions` (`GL:216-225`): `lens_in_target_region` (satisfied = `region_pass`; measured
    [`radial_dist`, `region_height_dist`]; threshold [`_TARGET_REGION_RADIUS`, `_TARGET_REGION_HALF_HEIGHT`]);
    `camera_aimed_along_x` (satisfied = `angle_pass`; measured `view_angle_deg`; threshold
    `_TARGET_ANGLE_DEG` about `_WORLD_POS_X`); `shutter_pressed` (satisfied = `shutter_pressed`;
    measured `shutter_contact_count`; threshold ">= 1 contact"). All constants are the env module's
    (`GL:211-214`), nothing copied.
  - `failure_conditions`: none (`GL:232`). No `holding`: the env ends the episode at the first
    successful step.
  - `targets` (`GL:233-238`): `target region` (world centre, `axis_world`, `radius_m`, `half_height_m`,
    point = lens point), `lens point` (position of `view_direction_site`), `shutter button` (position of
    the top cap geom), `aim direction` (`direction_world`, `max_angle_deg`). `satisfied_now` = the
    official `complete` flag (`GL:239`).
- So the region centre, which the earlier prompt kept hidden, is now given to the agent in
  `goal.targets`. Record this in DECISIONS.md at P1.

## C. Paper reference (vision only; Table 5, one session per cell)

From `~/my_things/codes/rax-reproduction/notes/paper_claims_vs_evidence.md`, section 2 ("Photo" column):

| Budget | 2 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|
| RaX (paper) | 0.0 | 0.0 | **86.7** | 68.7 | 100 |

Best ME-Dex baseline: 48.0. Our comparison cell is @8 = 86.7% (130/150). The paper's own sequence is
not monotonic (86.7 -> 68.7 -> 100), so one-session spread for this task is large. We have no earlier
runs of our own on this task.

## D. Object-state smoke checklist (gate G5)

Call the tool after reset and after ~10 no-op steps on exploration layout 0 (env seed 1000), and
layout 1 (seed 1001) where a second layout is needed (here: to see the camera move). Pass if:
- `privileged_level == "full"`; `frame == "world"`; no entry has an `error` or `velocity_error` key;
  no key named `success`, `reward`, `terminated` or `native_*`.
- `camera.position_m`: x in [-0.32, -0.18], y in [0.08, 0.22], z a few cm above the table top (compare
  with the RGB frame and `table_delta_height` in [0, 0.05]); nearly unchanged between the two calls
  (it rests on the table). `quaternion_wxyz` has norm 1 +- 1e-6.
- Camera pose differs between the two layouts (scene variation is real).
- `arm_joint_positions_rad.right` and `.left`: 7 finite values each, near the Panda home
  (0, -0.785, 0, -2.35, 0, 1.57, 0.785) at reset (D:18).
- `logo` (see B): position near the wall, its height and lateral offset varying between seeds, and
  consistent with where the logo is in an RGB frame. If absent: record it and stop (see B).
- `camera` velocities finite and about 0 at step 0; `camera.size` 3 non-negative half extents
  (record them), identical at both calls.
- `contacts`: well-formed rows, <= 64, sorted by force; at step 0 the camera on the table, no hand rows.
- `goal` at step 0: `conditions` named `lens_in_target_region`, `camera_aimed_along_x`, `shutter_pressed`;
  `lens_in_target_region` False and `shutter_pressed` False (measured 0); `satisfied_now` False; no
  `holding`; `failure_conditions` empty; `targets.target region` about 0.40 m in front of `logo`
  (along the wall normal), radius 0.16, half height 0.10; `aim direction` = world +x, 10 deg.
- Save to `R/results/smoke_object_states.json`.

## E. What to watch

- **Handover of roles:** the rule names left hand holds, right hand presses. The simulator does not
  check which hand. Note if the agent swaps roles; it is allowed.
- **Grasp stage:** lifting the camera with the left Allegro hand without covering the shutter or
  knocking the camera over. A camera grasped near its top cap can press the shutter with the holding
  hand (allowed, any non-camera geom counts), maybe too early.
- **Aim stage:** the 10 deg cone around world +x is tight. With the camera quaternion and the
  `camera_aimed_along_x` row (measured angle), aiming can be closed-loop. Watch for `angle_pass` "met earlier" but not at the press step.
- **Region stage:** the lens must sit about 0.40 m in front of the logo, at the logo's height; the logo
  height varies by 16 cm. `goal.targets` gives the region centre and the lens point directly.
- **Press stage:** pressing moves the camera; `region_pass` and `angle_pass` must still hold at the
  contact step. Typical failure: "shutter pressed earlier; angle not met at the end".
- **Timing:** 1000 steps for grasp, lift, aim and press with two arms. Watch for timeouts.
- **Signs the privileged state helped:** the program calls `dexjoco_object_states` (static grep and
  per-episode count in formal logs); it aims by the camera quaternion instead of image heuristics;
  it moves the `lens point` onto `target region` and checks the three rows (or `satisfied_now`) at the
  press; it uses `contacts` to see the shutter press; it re-reads the pose after the press to retry. Signs it did not: logo found by colour thresholds and
  camera located by depth, the tool used only once in exploration.

## F. Breakthrough candidates (clips)

1. First episode with a stable lift of the camera in the left hand.
2. First step with `region_pass` and `angle_pass` both true (the camera held still, aimed at the logo).
3. First success: the right hand presses the shutter while aim holds (the flash frame, D:554-556).
Optionally the moment the agent first uses the camera quaternion from the tool to correct its aim.

## Time and usage (budget 8)

- Agent time: paper Table 17 median 1.34 h (0.59-3.02 h); v1 Hanoi took 2.6 h. Expect 1.5-3 h.
- Usage reference (v1, budget 8): about 0.65 M output and 57 M cache-read tokens. State it at P2.
- Formal eval: v1 Hanoi (1500-step cap) took about 2.3 h for 150 episodes with 4 workers. With a
  1000-step cap and early stop on success, expect about 1-1.6 h. Measure; do not quote this estimate.

## Acceptance line for the summary

"bimanual_photograph @8: paper (vision only) 86.7% (130/150); ours (with full privileged state) X% (n/150),
seeds 0/1/2 = a/b/c. The program [does / does not] call dexjoco_object_states (k calls per episode).
The tool reported camera, logo and the goal targets [confirm at P1]. Main failure stage: [region / angle / shutter / timeout]."
