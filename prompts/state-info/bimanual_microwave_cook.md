# Task file: bimanual_microwave_cook (read COMMON.md first)

Citations: `UP` = upstream worktree `~/my_things/codes/rax/.worktrees/dexjoco-v2` (bcd748c).
`DJ` = `/data/user_data/vawale/rax_repro_v2/DexJoCo/dexjoco/dexjoco/sim/envs` (official env, read-only).
`NOTES` = `~/my_things/codes/rax-reproduction/notes/paper_claims_vs_evidence.md`.
`GL` = `services/dexjoco/goals.py` at 223f1a8 in the dev worktree `~/my_things/codes/rax/.worktrees/add-state-info` (re-check line numbers at CODE_COMMIT).

## A. Parameters

```
TASK          = bimanual_microwave_cook
ARM           = A   # A (default): object state only, exp/add-state-info/object; B: + dexjoco_lookahead (COMMON 1c)
ROOT          = /data/user_data/vawale/rax_state/bimanual_microwave_cook_A
CODE_COMMIT   = <fill in after GPU smoke passes>
CODE_WORKTREE = ~/my_things/codes/rax/.worktrees/state-run-bimanual_microwave_cook
REUSE_ENVS    = /data/user_data/vawale/rax_repro_v2/runtime/envs
GPU_JOB       = <optional; empty = submit new jobs (COMMON P1.4, P2.5)>
```

For `ARM = B` (COMMON section 1c): `ROOT = /data/user_data/vawale/rax_state/bimanual_microwave_cook_B`,
`CODE_WORKTREE = ~/my_things/codes/rax/.worktrees/state-run-bimanual_microwave_cook-B`, and `CODE_COMMIT` from
`exp/add-state-info/lookahead` ("<fill in after GPU acceptance passes>"). Job scripts also export
`RAX_LOOKAHEAD=on RAX_LOOKAHEAD_ROWS_FACTOR=3`. Add gates G1c and G6, and the extra P5 lookahead fields.
The lookahead row budget here is 3 x the step cap (section B). The summary line gets the lookahead
use and formal wall time vs Arm A, plus the 1c report wording. Everything else in this file is unchanged.

## B. Task facts

- **What the agent sees** (`--task-rules public`), `UP/services/dexjoco/task_rules/bimanual_microwave_cook.md:1-8`:
  goal "Open the microwave door, put the food inside, close the door and press the start button."
  Success needs, **at the same step**: food inside the cavity, door closed, something touching the
  start button. Scene variation: food position and heading, and table height; the microwave stays put.
- **Robot:** dual arm (two Pandas + two Allegro hands, 44-dim actions), cap **1100 steps**
  (`UP/services/dexjoco/tasks.py:37`; the env sets `terminated` at `env_step >= 1100`, `DJ/panda_bimanual_microwave_cook_env.py:572-573`).
- **No early failure condition:** the episode ends only on success or at the cap (`DJ/...env.py:571-590`).
- **Official success check** (the agent reads these numbers through `goal`, `DJ/...env.py:592-607`, `706-723`):
  door hinge `|microjoint| < 0.01 rad`; food centre (`sensor:hot_dog_pos`) inside the cavity box
  (sites `int_p0/px/py/pz` in the microwave frame) with 1 cm margin; any contact on geom `start_button`.
  Next to it sits a smaller `stop_button` (`DJ/xmls/robocasa_microwave.xml:54-55`). Touching it does nothing.
- **Layout ranges** (`DJ/...env.py:20-21, 324, 345-366`): table offset `delta_h` U(0, 0.05) m; food x in
  [-0.35, -0.25], y in [-0.40, -0.30] m, yaw +-20 deg about its base pose; food z = 0.965 + delta_h
  (`DJ/xmls/hot_dog.xml:8`); microwave at (-0.05, 0.12, 1.10 + delta_h), fixed quat (0.7071, 0, 0, -0.7071)
  (`DJ/xmls/robocasa_microwave.xml:24`). Door hinge range [-1.6, 0] rad, 0 = closed (`robocasa_microwave.xml:59-68`).
- **What `dexjoco_object_states` reports for this task** (re-check at CODE_COMMIT): `state_sources()`
  = `TAIL` + `POINTS` (+ no `STATE_EXTRA` for this task): `food` (pose, free joint `hot_dog_free`),
  `microwave` (pose, body `microwave_object`), `food centre` (position, `sensor:hot_dog_pos`, the point the
  success check uses), `door hinge` (`angle_rad`, `microjoint`), plus `arm_joint_positions_rad` `right` and
  `left` (7 each). At `full`, `food` and `microwave` also carry velocities and `size`, and the reply has
  `contacts` (e.g. a hand on the start button or the door) and `goal`. The button and cavity positions are
  now in `goal.targets`.
- **What `goal` reports** (`GL:156-205`, `bimanual_microwave_cook()`):
  - `description`: put the food inside the cavity, close the door (|hinge| < 0.01 rad) and touch the start
    button, all at the same step (`GL:193-194`).
  - `conditions` (`GL:181-190`): `door_closed` (measured: `microjoint` angle; threshold 0.01 on |angle|,
    open is negative); `food_inside_cavity` (satisfied = the env's own `hot_dog_inside_microwave(margin=0.01)`;
    measured: food centre in the microwave body frame; threshold: the cavity box from sites
    `int_p0/px/py/pz` widened by 0.01 m); `start_button_touched` (satisfied = the env's
    `_geom_in_contact("start_button")`; measured: number of contacts with dist <= 0; the note names the
    touching bodies). 0.01 rad and 0.01 m are local literals of the official check (`GL:45-48`), guarded by
    `test_copied_literals_match_the_official_source`.
  - `failure_conditions`: none (`GL:195`). No `holding`: success counts on the first step all hold.
  - `targets` (`GL:196-203`): `microwave cavity` (world centre, `half_extents_m` in the microwave body
    axes, point = food centre), `start button` (position, half extents), `door handle` (position),
    `door hinge` (angle 0, tolerance 0.01). `satisfied_now` = all three (`GL:204`).
- **Demos:** `runtime/envs/host/bin/python scripts/setup_dexjoco_demos.py --gpu $G --task bimanual_microwave_cook`
  (`UP/scripts/setup_dexjoco_demos.py:11,73-74`); gate G4.

## C. Paper reference (vision only), `NOTES:92-99` (Table 5, one session per budget)

| Budget | 2 | 4 | 8 | 16 | 32 | Best ME-Dex |
|---|---|---|---|---|---|---|
| Microwave (%) | 0.0 | 0.0 | **84.0** | 93.3 | 99.3 | 88.0 |

Our comparison cell is budget 8: **84.0% (126/150)**. ME-Dex beats RaX@8 here, so say so. Not monotonic
elsewhere in the table (`NOTES:106-110`): one session per cell. We have no earlier microwave run of our own.

## D. Object-state smoke checklist (G5)

After reset (step 0) and after ~10 `hold` steps, on exploration layout 0 (env seed 1000), and layout 1
(seed 1001) where a second layout is needed:

| Label | Field | Sane range |
|---|---|---|
| `food` | `position_m`, `quaternion_wxyz` | x in [-0.36, -0.24], y in [-0.41, -0.29], z in [0.94, 1.03] (allow ~3 cm settling); unit quat (+-1e-6) |
| `food centre` | `position_m` | within ~10 cm of `food` position; z above 0.9 |
| `microwave` | `position_m`, `quaternion_wxyz` | about (-0.05, 0.12, 1.10..1.15); quat = +-(0.7071, 0, 0, -0.7071); unchanged between the two calls |
| `door hinge` | `angle_rad` | about 0 (closed) at reset; inside [-1.6, 0] |
| `arm_joint_positions_rad` | `right`, `left` | 7 floats each; at reset about (0, -0.785, 0, -2.35, 0, 1.57, 0.785) (`DJ/...env.py:17`) |
| `food`, `microwave` velocities | `linear_velocity_mps`, `angular_velocity_radps` | finite; about 0 at step 0; the microwave body 0 |
| `food`, `microwave` `size` | `half_extents_m`, `center_offset_m` | 3 non-negative values each, plausible (record them); identical at both calls |
| `contacts` | list | well-formed rows, <= 64, sorted by force; at step 0 the food on the table, no hand rows; record what is there |
| `goal.conditions` at step 0 | `satisfied` | `door_closed` **True** (door starts closed, measured ~0); `food_inside_cavity` False; `start_button_touched` False; `satisfied_now` False |
| `goal.targets` | | `microwave cavity` centre inside the microwave's footprint; `start button` near the microwave front; both unchanged between calls |

Also: `privileged_level` == `full`; no `error` or `velocity_error` entries; no key named `success`,
`reward`, `terminated` or `native_*`; `frame == "world"`; `goal` has no `holding` and an empty
`failure_conditions`; the reset-tail `food` pose (operator `state.json`) matches the first call within
1e-6. If the hot-dog xy sits outside the box above, check whether `hot_dog` has a parent frame before
failing the gate. Record in DECISIONS.md at P1 that the agent reads the door tolerance, the cavity box and
the start-button position through `goal`.

## E. What to watch

- **Order and two arms:** open door, grasp food, place inside, close door, press start. All must hold
  at one step, so a door that springs back open, or food pushed out while closing, fails.
- **Door closing precision:** success needs |hinge| < 0.01 rad. A door left 1-2 deg ajar fails. The
  agent reads `door hinge` and the `door_closed` row and can close the loop.
- **Door has friction and damping** (`robocasa_microwave.xml:59-68`): pushes may stall partway.
- **Start vs stop button:** they sit 5 cm apart. Pressing `stop_button` does nothing. `goal.targets`
  gives the start button's position and `start_button_touched` names what touches it; watch whether the
  agent uses them.
- **Food grasp:** small hot dog, random yaw; drops on transfer; the arm or hand knocking it off the tray.
- **Collisions:** the hand hitting the door or the microwave body on the way in.
- **Time:** 1100 steps for five sub-tasks; a slow program reaches the cap.
- **Signs the privileged state helped:** the program reads `food`/`food centre` poses instead of colour
  masks or depth blobs; it checks `door hinge` before pressing start; it retries on a dropped grasp
  detected from `food` z or `contacts`; it checks `goal.satisfied_now` or the three rows before
  stopping. Count `ctx.call("dexjoco_object_states"` in `controller.py` and per formal episode.
- **Signs it did not:** the program never calls the tool, or calls it once and then runs open loop.

## F. Breakthrough candidates (clips)

- First episode where the food ends inside the cavity.
- First time the door closes fully (hinge near 0) with the food inside.
- First full success (simulator `task_complete`), ideally with the hinge reading and the button press visible.
- A recovery: a dropped food or stalled door that the agent or program notices from the tool and fixes.

## Time and usage (budget 8)

- Agent time: paper Table 17 median 1.34 h (range 0.59-3.02 h) at budget 8 (`NOTES:116-122`); our v1
  Hanoi session took 2.6 h, about 0.65 M output and 57 M cache-read tokens. Expect similar; five
  sub-tasks may push it toward the upper end.
- Formal eval: v1 Hanoi (1500-step cap) took about 2.3 h for 150 episodes on 4 workers, about 220 s per
  episode per worker. Scaled to 1100 steps: about 1.5-2 h. This is a rough estimate.

## Acceptance line for `report/summary.md`

"bimanual_microwave_cook @8: paper 84.0% (126/150, vision only) vs ours X/150 (Y%, with full privileged state);
seeds a/b/c; the program called dexjoco_object_states N times per episode (or never); main failure stage: S."
All numbers from `R/results/bimanual_microwave_cook.json`, regenerated just before writing.
