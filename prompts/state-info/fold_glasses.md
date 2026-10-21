# Task file: fold_glasses (RaX + privileged object state)

Read `COMMON.md` (same folder) first. This file gives the task parameters and sections A-F that
COMMON section 1b asks for. Citations `file:line` are in the upstream worktree
`~/my_things/codes/rax/.worktrees/dexjoco-v2` unless marked otherwise. `GL` = `services/dexjoco/goals.py`
at 223f1a8 in the dev worktree `~/my_things/codes/rax/.worktrees/add-state-info` (re-check line numbers
at CODE_COMMIT). Official-source details reach the agent only through the tool's `goal`; never paste
them into the agent's workspace yourself.

## A. Parameters

```
TASK          = fold_glasses
ARM           = A   # A (default): object state only, exp/add-state-info/object; B: + dexjoco_lookahead (COMMON 1c)
ROOT          = /data/user_data/vawale/rax_state/fold_glasses_A
CODE_COMMIT   = <fill in after GPU smoke passes>
CODE_WORKTREE = ~/my_things/codes/rax/.worktrees/state-run-fold_glasses
REUSE_ENVS    = /data/user_data/vawale/rax_repro_v2/runtime/envs
GPU_JOB       =             # empty = submit new jobs (COMMON P1.4, P2.5)
```

For `ARM = B` (COMMON section 1c): `ROOT = /data/user_data/vawale/rax_state/fold_glasses_B`,
`CODE_WORKTREE = ~/my_things/codes/rax/.worktrees/state-run-fold_glasses-B`, and `CODE_COMMIT` from
`exp/add-state-info/lookahead` ("<fill in after GPU acceptance passes>"). Job scripts also export
`RAX_LOOKAHEAD=on RAX_LOOKAHEAD_ROWS_FACTOR=3`. Add gates G1c and G6, and the extra P5 lookahead fields.
The lookahead row budget here is 3 x the step cap (section B). The summary line gets the lookahead
use and formal wall time vs Arm A, plus the 1c report wording. Everything else in this file is unchanged.

## B. Task facts

- **Goal (as the agent sees it):** "Fold both temples of the glasses and place the glasses in the case."
  (`services/dexjoco/task_rules/fold_glasses.md:1`)
- **Success, held for a number of consecutive steps:** both temple hinges folded past a set angle, and
  the glasses' centre inside the open case, within its footprint and between its floor and rim height
  (`task_rules/fold_glasses.md:3-5`). There is no failure condition that ends the episode early.
- **Scene variation:** glasses' and case's positions and headings, and the table height
  (`task_rules/fold_glasses.md:7`).
- **Robot:** single arm, one Panda with a 16-DoF Allegro hand (`services/dexjoco/tasks.py:32`,
  `docs/DEXJOCO_BACKEND.md:57`). Action is 22-dim per step.
- **Step cap:** 1200 control steps, 20 ms each (`tasks.py:32`, `tasks.py:44-45`). No pre-roll.
- **Official check details (the agent reads the thresholds through `goal`; layout ranges are not in
  the tool):** in
  `/data/user_data/vawale/rax_repro_v2/DexJoCo/dexjoco/dexjoco/sim/envs/panda_fold_glasses_env.py`:
  both hinges must exceed 1.1 rad (`:545-553`), for 50 consecutive steps (`:193`, `:564`); the case
  check is axis-aligned in world x/y (half-width 0.145 m), ignoring the case's yaw (`:522-536`); the
  centre must sit between 0.045 m below and 0.0275 m above the case origin (`:533-537`). Hinge ranges are
  0.2-1.38 rad and 0.2-1.29 rad (`xmls/glass.xml:36,41`). Layout: glasses x in [-0.40,-0.35],
  y in [-0.225,-0.175]; case x in [-0.275,-0.225], y in [0.25,0.30]; yaw +-10 deg each; table
  height offset 0-0.05 m (`:20-22`, `:354`, `:375-403`).
- **What `dexjoco_object_states` reports for this task** (labels from `services/dexjoco/objects.py`):
  - `glasses`: free-joint pose `joint:glass_root` -> `position_m`, `quaternion_wxyz` (`objects.py:29`).
  - `glasses case`: body pose `body:open_box` -> `position_m`, `quaternion_wxyz` (`objects.py:29`).
    The case is a fixed body: its pose changes per layout, not during an episode.
  - `glasses centre`: `sensor:glass_pos`, a 3-value world position (`objects.py:45`).
  - `first temple hinge`, `second temple hinge`: since dcbf92f these come from `STATE_EXTRA` as
    `hinge:glass_joint_{0,1}` and are returned as `{"angle_rad": angle}` (the hinge angle in rad);
    re-check the shape at CODE_COMMIT and record it.
  - `arm_joint_positions_rad`: `{"arm": [7 values]}` (Panda joint1..7). Hand joints are not in this
    tool; they stay in the official state vector (`add-state-info/services/dexjoco/tools.py`, tool
    description). Success reference points: `glasses case` and `glasses centre`; record them in
    DECISIONS.md at P1.
  - At `full`: `glasses` and `glasses case` also carry `linear_velocity_mps`, `angular_velocity_radps`
    and `size`; the reply has `contacts` and `goal`.
- **What `goal` reports** (`GL:120-153`, `fold_glasses()`):
  - `description`: fold both temples past 1.1 rad and put the glasses centre inside the case (within
    0.145 m of its origin in x and y, -0.045..0.0275 m in z), all at once for the required consecutive
    steps (`GL:143-145`).
  - `conditions` (`GL:132-139`): `first_temple_folded`, `second_temple_folded` (measured: hinge angle from
    `sensor:glass_joint_{0,1}_pos`; threshold 1.1, strict `>`); `glasses_inside_case_x`, `_y`, `_z`
    (measured: glasses centre minus case origin in **world** axes, not rotated into the case yaw, as the
    official check does; thresholds [-0.145, 0.145] for x and y, [-0.045, 0.0275] for z). The constants
    are local literals of the official check, copied at `GL:38-44` (`TEMPLE_FOLDED_RAD`,
    `CASE_HALF_XY_M`, `CASE_Z_MIN_M`, `CASE_Z_MAX_M` 0.0475 minus `CASE_Z_TOP_ALLOWANCE_M` 0.02), guarded by
    `test_copied_literals_match_the_official_source`.
  - `failure_conditions`: none (`GL:146`).
  - `targets` (`GL:147-150`): `glasses case` (position, `accepted_offset_m` box, point = glasses centre),
    `glasses centre` (position).
  - `holding` (`GL:151`): `steps_satisfied` = `env._success_trigger_count`, `steps_required` =
    `env._success_trigger_target` (50). `satisfied_now` = both folded and all three axes inside (`GL:152`).
- **Demos:** G4 runs `scripts/setup_dexjoco_demos.py --gpu $G --task fold_glasses`
  (`scripts/setup_dexjoco_demos.py:9,73-74`; `docs/DEXJOCO_BACKEND.md:87`). The agent sees their
  terminal-state images (`--demonstration-context terminal_state`, `docs/USAGE.md:65`).

## C. Paper reference (vision only, one session per cell)

From `~/my_things/codes/rax-reproduction/notes/paper_claims_vs_evidence.md`, section 2, Table 5:

| Budget | 2 | 4 | 8 | 16 | 32 | Best ME-Dex |
|---|---|---|---|---|---|---|
| Glasses (%) | 0.7 | 0.0 | **100** | 55.3 | 93.3 | 56.0 |

- The @8 number is already 100%. Object state cannot raise it; it can only match it or fall short.
- The row is not monotonic (100 -> 55.3 -> 93.3), which shows large session-to-session spread.
- We have no earlier runs of our own on this task.

## D. Object-state smoke checklist (G5)

Call once right after reset and once after ~10 no-op (hold) steps, on exploration layout 0. Save to
`R/results/smoke_object_states.json`. Pass if all hold:

| Label | Sane range |
|---|---|
| `glasses` position | x in [-0.42,-0.33], y in [-0.25,-0.15], z in [0.93,1.06]; unit quaternion (|q|-1 < 1e-4) |
| `glasses case` position | x in [-0.28,-0.22], y in [0.25,0.30], z in [0.97,1.02]; unit quaternion; identical at both calls |
| `glasses centre` | 3 finite values, within 0.1 m of the `glasses` position, z above the table top (0.92 + offset) |
| `first temple hinge` | `angle_rad` in [0.2,1.39] rad, below 1.1 at reset (temples open) |
| `second temple hinge` | `angle_rad` in [0.2,1.30] rad, below 1.1 at reset |
| `glasses`, `glasses case` velocities | 3 finite values each; about 0 at step 0; the case exactly 0 (fixed body) |
| `glasses`, `glasses case` `size` | 3 non-negative half extents each, plausible (record them); identical at both calls |
| `contacts` | well-formed rows, <= 64, sorted by force; at step 0 the glasses resting on the table, no hand rows; record what is there |
| `goal.conditions` at step 0 | both `*_temple_folded` False (measured = the hinge angles above); `glasses_inside_case_y` False (the glasses start ~0.45 m away in y; x may already be within 0.145 m, so `_x` can be True); `satisfied_now` False |
| `goal.failure_conditions` | empty list |
| `goal.holding` at step 0 | `steps_satisfied` 0, `steps_required` 50 |
| `arm_joint_positions_rad.arm` | 7 finite values inside Panda limits; unchanged (< 0.01 rad) across the no-op steps |

Also: `privileged_level` == `full`; no entry has an `error` or `velocity_error` key; no key named
`success`, `reward`, `terminated` or `native_*`; `goal` thresholds equal 1.1, 0.145, -0.045 and 0.0275.
The glasses may settle a few mm between calls; that is fine. Record in DECISIONS.md at P1 that the
agent reads the fold angle, the case box (world axes), and the 50-step hold through `goal`.

## E. What to watch

- **Folding a thin temple with an Allegro hand.** Likely stuck stages: cannot hook the temple, folds
  one temple but knocks the other open, or folds only past ~1.0 rad. Hinges have no spring, so a fold
  stays unless pushed.
- **Order of fold and place.** Folding on the table then lifting can unfold a temple or drop the
  glasses. Folding inside the case is possible but the 0.095 m walls block the fingers.
- **Placement.** The centre must sit low in the case (resting on the floor). A pair balanced on a
  wall or held above the rim fails. Releasing too early can bounce it out.
- **Holding 50 steps** (the agent sees `goal.holding`). A hand still touching the glasses can keep a hinge from settling; a successful
  episode needs a clean release before the step cap.
- **Signs the privileged state helped:** the program reads hinge angles or `goal.conditions` to decide
  when a fold is done (closed loop) instead of fixed motions; it checks the `glasses_inside_case_*` rows
  and `goal.holding` before letting go or ending; it uses `contacts` to confirm a clean release; it reads the case pose and glasses yaw instead of segmenting
  colours or depth; exploration needs fewer episodes before the first success; failure handling
  (retry a fold) is triggered by state, not by images.
- **Signs it did not:** the program never calls `dexjoco_object_states`, or only hard-codes constants
  that the tool read during exploration.

## F. Breakthrough candidates (clips)

1. First episode where one temple hinge passes 1.1 rad (find the step from `mcp.jsonl` state calls).
2. First episode with both temples folded.
3. First exploration episode with simulator `task_complete` true (glasses in the case).
4. If the program uses the tool: a formal episode where a state read triggers a retry that succeeds.

## Expected time and usage at budget 8

- Agent time: paper Table 17 median 1.34 h at budget 8 (range 0.59-3.02 h). Our v1 Hanoi budget-8
  session: 2.6 h, about 0.65 M output and 57 M cache-read tokens. Use the v1 numbers when asking me.
- Formal eval: 150 episodes x at most 1200 steps (24 s simulated; about 40 s wall at the 30 Hz pacing). v1 Hanoi
  (1500 steps) took about 2.3 h with 4 workers; expect at most about 1.8 h here, less if episodes
  succeed early. Report only "n/150 done" until it finishes.

## Acceptance line for the summary

"fold_glasses @8 with full privileged state: X/150 (Y%) vs the paper's 100% vision only (one session each).
The agent called `dexjoco_object_states` N times in exploration; the submitted program calls it
[yes/no]." Every number comes from `R/results/fold_glasses.json`. If X < 150, name the main failure
stage (fold, lift, place, hold) from the formal logs.
