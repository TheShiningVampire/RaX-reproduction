# Task file: bimanual_hanoi (RaX + privileged object state)

Read `COMMON.md` (same folder) first. This file gives the task parameters and the sections COMMON 1b asks
for. Task facts here win over COMMON; protocol in COMMON wins over this file. Citations: `UP:` is the
upstream worktree `~/my_things/codes/rax/.worktrees/dexjoco-v2` (bcd748c); `DEV:` is the development
worktree `~/my_things/codes/rax/.worktrees/add-state-info` (line numbers as of a42f98b; re-check at
CODE_COMMIT in P1); `REPRO:` is `~/my_things/codes/rax-reproduction`; `GL:` is `DEV:services/dexjoco/goals.py`
at 223f1a8 (re-check line numbers at CODE_COMMIT).

## A. Parameters

```
TASK          = bimanual_hanoi
ARM           = A   # A (default): object state + success info (exp/add-state-info/object), no lookahead; B: + dexjoco_lookahead (COMMON 1c)
ROOT          = /data/user_data/vawale/rax_state/bimanual_hanoi_A
CODE_COMMIT   = 943da37cb1c1fb4d71f62585b66beaf0d9fe144d   # 223f1a8 (Arm A, GPU smoke passed: job 10880424) + my auth opt-in
CODE_WORKTREE = ~/my_things/codes/rax/.worktrees/add-state-info   # existing worktree, frozen for this run (P1.1)
REUSE_ENVS    = /data/user_data/vawale/rax_repro_v2/runtime/envs
GPU_JOB       = <optional: running katef GPU job id; empty = submit new jobs (COMMON P1.4, P2.5)>
```

For `ARM = B` (COMMON section 1c), three settings change (keep the values above for the A
run): `ROOT = /data/user_data/vawale/rax_state/bimanual_hanoi_B`,
`CODE_WORKTREE = ~/my_things/codes/rax/.worktrees/state-run-bimanual_hanoi-B` (a new detached worktree,
not `add-state-info`), and `CODE_COMMIT` from `exp/add-state-info/lookahead` ("<fill in after GPU
acceptance passes>"). Job scripts also export `RAX_LOOKAHEAD=on RAX_LOOKAHEAD_ROWS_FACTOR=3`. Add gates
G1c and G6, and the extra P5 lookahead fields. The row budget is 3 x 1500 = 4500 rows per episode. The
summary line gets the lookahead use and formal wall time vs Arm A (`bimanual_hanoi_A`), plus the 1c report
wording. Hanoi only: a lookahead that makes an illegal move stops with `stop_reason: "illegal_move"`. The
real episode is not affected. Count these stops per episode. Everything else in this file is unchanged.

## B. Task facts

- **Goal, as the agent sees it** (UP:services/dexjoco/task_rules/bimanual_hanoi.md:1): finish the
  three-disk Tower of Hanoi in its last two moves. The right hand moves the medium disk from the middle
  peg to the right peg. Then the left hand moves the small disk from the left peg onto it.
- **Success** (task_rules:3-4): all three disks on the right peg, large at the bottom, small on top,
  each centred on the peg and at its stacking height, all disks still, held for some consecutive steps.
- **Fail** (task_rules:6-7): a larger disk on a smaller one, or a disk on the table off the pegs, held
  for some consecutive steps while the disks are still.
- **Scene variation** (task_rules:9): only the base position along the table changes. The start
  arrangement (small on left, medium in the middle, large on right) never changes. Camera, light and disk
  colours do not change either (rand_obj).
- **Robot and step cap:** dual arm, 1500 control steps at 30 Hz (UP:services/dexjoco/tasks.py:35, :44).
- **Peg names:** A = left, B = middle, C = right (UP:services/dexjoco/analysis.py:46). Disk colours in
  v1: large blue, medium red, small yellow (REPRO:notes/session1_program.md:52, :79).
- **What `dexjoco_object_states` reports for this task:**
  - `tower base`: `body:hanoi_base` (UP:services/dexjoco/objects.py:32). The official tail holds only
    its 3-value reset position; the live tool reads the body, so it returns position + quaternion.
  - `large disk`, `medium disk`, `small disk`: the free joints `hanoi_disk_{large,medium,small}_joint`.
    These are new; the review code only had the tail (DEV:services/dexjoco/objects.py:62-66, `STATE_EXTRA`).
  - `peg A`, `peg B`, `peg C`: sites `hanoi_post_{a,b,c}_site` (DEV:objects.py:62-66). The env uses these sites for
    its success check (UP:DexJoCo/dexjoco/dexjoco/sim/envs/panda_bimanual_hanoi_env.py:215-217); this is a success
    reference point; record it in DECISIONS.md and tell me at P1.
  - `arm_joint_positions_rad`: `right` and `left`, 7 values each (`joint1_right..joint7_right`, etc.;
    DEV:objects.py:74). Hand joints are not in this tool; they stay in the official state vector.
  - No POINTS entry for Hanoi; no hinge.
  - At `full`: `tower base` and the three disks also carry `linear_velocity_mps`,
    `angular_velocity_radps` and `size`; the reply has `contacts` (disk-disk, disk-peg/base and hand-disk
    rows) and `goal`.
- **What `goal` reports** (`GL:243-315`, `bimanual_hanoi()`). It uses the env's side-effect-free helpers
  `_reconstruct_tower_state()` and `_tower_geometry_errors()` (`GL:244-253`) and reads the counters as
  attributes, because `_compute_success_metrics` itself updates them.
  - `description`: all three disks on peg C, large/medium/small from the bottom, centred and seated, all
    static, for the required consecutive steps; a bigger disk on a smaller one, or a disk on the table,
    for the illegal threshold's consecutive steps fails (`GL:305-308`).
  - `conditions` (`GL:272-284`): `tower_C_order` (measured: disks on C from the bottom; threshold
    [large, medium, small]; A and B must be empty); `xy_centred_on_peg_C` (largest horizontal error,
    threshold `env._post_assignment_tol`); `stack_height_on_peg_C` (largest height error, threshold
    `env._placement_height_tol`); `all_disks_static` (each disk's 6-D qvel norm, threshold
    `env._static_qvel_tol`); `no_illegal_state` (current illegal-state count, must stay below
    `env._illegal_trigger_target`). The target stack and the 0.06 m table margin are local literals of
    the official code (`GL:49-52`), guarded by `test_copied_literals_match_the_official_source`.
  - `failure_conditions` (`GL:285-294`): `illegal_stack` (a bigger disk on a smaller one, seated and
    static: the official candidate recomputed at `GL:260-268`) and `disk_on_table` (all disks static and
    one off the pegs within 0.06 m above the base top, `GL:269-270`); measured = the illegal counter for
    that reason, threshold = `_illegal_trigger_target`.
  - `targets` (`GL:295-300`): each disk's stacked position on peg C (from `_disk_half_height`) and
    `peg C`. Extra keys: `tower_state` (disks per peg), `disk_assignment` (peg, table or floating per
    disk) (`GL:310`).
  - `holding` (`GL:311`): `_success_trigger_count` of `_success_trigger_target`; `failure_holding`
    (`GL:312-313`): `reason`, `steps_satisfied` (`_illegal_trigger_count`), `steps_required`.
    `satisfied_now` = order, both geometry errors within tolerance, all static, and no illegal state (`GL:301`, `GL:314`).
- **Demos (G4):** `python scripts/setup_dexjoco_demos.py --gpu $G --task bimanual_hanoi`.
- **Official tolerances (the agent reads them through `goal`; never paste them into the workspace
  yourself):** 0.040 m peg-axis distance, 0.012 m height error, disk qvel norm <= 0.35
  (panda_bimanual_hanoi_env.py:68-70). The smoke's `goal` thresholds must equal these.

## C. Paper reference (vision only) and our earlier runs

From REPRO:notes/paper_claims_vs_evidence.md:92-99 (Table 5, one session per cell):

| Budget | 2 | 4 | 8 | 16 | 32 | Best ME-Dex† |
|---|---|---|---|---|---|---|
| Hanoi success % | 0.0 | 100 | **100** | 98.7 | 100 | 32.0 |

Paper Table 17 agent time at budget 8: median 1.34 h, range 0.59-3.02 h (notes:116-122).

Our earlier vision-only runs (REPRO:README.md:27, :55-57; label them "our earlier runs", not the paper):
- v1 session 1, budget 8, paper protocol: **82/150 (54.7%)**, seeds 56/54/54%. Most misses at the right
  hand's first grasp (46 of 68 failures end in `grasp`; REPRO:notes/session1_results.md:19-27).
- v1 session 2, after 6 more practice episodes (continuation, beyond the protocol): **145/150 (96.7%)**.
The fair comparison for this run is the paper's 100% @8 and our 54.7% fresh session 1, both vision only.

## D. Object-state smoke checklist (G5)

Call once after reset and once after ~10 no-op steps on one exploration layout. Expect all of these:
- `frame` == `"world"`; no entry has an `error` key.
- `tower base`, 3 disks: finite `position_m`, `quaternion_wxyz` with norm 1 +/- 1e-3.
- Disks at reset: small within 0.04 m (xy) of `peg A`, medium of `peg B`, large of `peg C`. Each disk z
  above `tower base` z and below it + 0.25 m. One disk per peg at reset.
- Disk quaternions near upright (tilt < 10 deg). After no-op steps disk positions change < 5 mm.
- `peg A/B/C`: `position_m` only; the three pegs roughly on a line, spacing a few cm to ~0.2 m, same z
  within 1 cm. Order along the line: A, B, C (left to right as seen in the third-person camera).
- Two layouts (seeds 1000, 1001): tower base and pegs shift together along one table axis; disks follow.
- `arm_joint_positions_rad`: `right` and `left`, 7 finite floats each, within Panda limits (|q| < 3.1).
- `privileged_level == "full"`; no `velocity_error`; no key named `success`, `reward`, `terminated` or
  `native_*` anywhere in the output.
- Disk and base velocities finite and about 0 at step 0; each `size` 3 non-negative half extents,
  disks flat (z half extent smallest), identical at both calls.
- `contacts`: well-formed rows, <= 64, sorted by force; at step 0 each disk resting on the base or its
  peg, no hand rows; record what is there.
- `goal` at step 0: `tower_C_order` False (C holds only the large disk; measured [large disk]);
  `all_disks_static` True; `no_illegal_state` True; `satisfied_now` False; both `failure_conditions`
  False; `holding` 0 of 20 (`success_trigger_target`); `failure_holding.reason` null, required 10
  (`illegal_trigger_target`); thresholds 0.040 / 0.012 / 0.35 (env defaults, `panda_bimanual_hanoi_env.py:68-72`);
  `disk_assignment` small A, medium B, large C; `targets` large/medium/small disk stacked above `peg C`.
Save to `ROOT/results/smoke_object_states.json`.

## E. What to watch

- **Grasp of the medium disk by the right hand** was v1's main failure (colour masks plus wrist-camera
  offsets). With the tool, the program can read disk poses directly. Check whether it does.
- **Placement height and centring:** success needs each disk on the peg axis and at its stacking height,
  then still. Watch for disks dropped from too high (bounce, still moving) or released off-axis.
- **Hand clearance:** v1 success usually registered only after the left hand cleared the stack. A hand
  left touching the stack can keep a disk moving.
- **Illegal states:** medium placed on the small disk, or the small disk knocked off peg A while the
  right arm transports. A disk on the table ends the episode as a failure. The agent sees these as
  `failure_conditions` and `failure_holding`; watch whether it reacts to them.
- **Two-arm timing and collisions:** both arms work near the middle peg; v1 staged the left arm early.
- **Step budget:** 1500 steps. v1 failures from grasp ended around steps 250-520; a slow program can run
  out of steps during the second move.
- **Signs the privileged state helped:** the program calls `ctx.call("dexjoco_object_states", {})` and
  uses disk or peg poses, `goal.targets` stacking positions, `contacts` (grasp checks) or the
  `goal.conditions` rows (centring, height, static) for approach, grasp check or placement instead of
  colour thresholds and hard-coded offsets (v1 had `HALF`, `BOTTOM_DZ`, RGB/HSV boxes; notes/session1_program.md:52-79);
  fewer exploration episodes to first full tower; grasp failures fall well below v1's 46/150.
- **Signs it did not:** the program keeps camera masks and never calls the tool; or it reads poses but
  fails at the same stage. Count tool calls per formal episode from logs.

## F. Breakthrough candidates (clips)

1. First exploration episode with a full tower on peg C (simulator `task_complete`).
2. The first episode where the agent uses `dexjoco_object_states` to verify a grasp or a placement
   (e.g. it reads the medium disk's z after lifting).
3. A formal success, and if useful one formal failure at the main failure stage, side by side.

## Time and usage at budget 8

- Agent session: paper median 1.34 h (0.59-3.02 h). v1 Hanoi: 2.6 h; 8th episode reached at minute 156;
  0.65 M output, 57 M cache-read, 1.2 M cache-write tokens, about $34 API-equivalent
  (REPRO:notes/session1_results.md:84). Use the v1 figures when asking the user before launch.
- Formal eval: 150 episodes x up to 1500 steps, 4 workers. v1 took about 2.3 h. Plan 2-3 h, no usage.
- GPU job: about 1 h gates + up to 3 h session + 3 h formal + clips; the 1-12:00:00 limit covers waits.

## Acceptance line for the summary

"bimanual_hanoi @8 with full privileged state: X/150 (Y%), seeds a/b/c. Paper @8 vision only: 100%. Our earlier
vision-only session @8: 54.7%. The program [does / does not] call dexjoco_object_states (N calls per
episode); main failure stage: S." All numbers from `ROOT/results/bimanual_hanoi.json`, re-read just before
writing; the comparison is one session each, so a gap may be session-to-session spread.
