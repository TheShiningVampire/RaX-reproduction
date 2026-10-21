# Task file: water_plant (RaX + privileged object state)

Read `COMMON.md` (same folder) first. This file sets the parameters and the task-specific sections
(COMMON section 1b). Task facts here win over COMMON; COMMON wins for protocol.
Citations: `UP` = upstream worktree `~/my_things/codes/rax/.worktrees/dexjoco-v2` (bcd748c).
`OFF` = official env `/data/user_data/vawale/rax_repro_v2/DexJoCo/dexjoco/dexjoco/sim/envs/panda_water_plant_env.py`.
`PC` = `~/my_things/codes/rax-reproduction/notes/paper_claims_vs_evidence.md`.
`GL` = `services/dexjoco/goals.py` at 223f1a8 in the dev worktree `~/my_things/codes/rax/.worktrees/add-state-info` (re-check line numbers at CODE_COMMIT).

## A. Parameters

```
TASK          = water_plant
ARM           = A   # A (default): object state only, exp/add-state-info/object; B: + dexjoco_lookahead (COMMON 1c)
ROOT          = /data/user_data/vawale/rax_state/water_plant_A
CODE_COMMIT   = <fill in after GPU smoke passes>
CODE_WORKTREE = ~/my_things/codes/rax/.worktrees/state-run-water_plant
REUSE_ENVS    = /data/user_data/vawale/rax_repro_v2/runtime/envs
GPU_JOB       = <optional: running katef GPU job id; empty = submit new jobs (COMMON P1.4, P2.5)>
```

For `ARM = B` (COMMON section 1c): `ROOT = /data/user_data/vawale/rax_state/water_plant_B`,
`CODE_WORKTREE = ~/my_things/codes/rax/.worktrees/state-run-water_plant-B`, and `CODE_COMMIT` from
`exp/add-state-info/lookahead` ("<fill in after GPU acceptance passes>"). Job scripts also export
`RAX_LOOKAHEAD=on RAX_LOOKAHEAD_ROWS_FACTOR=3`. Add gates G1c and G6, and the extra P5 lookahead fields.
The lookahead row budget here is 3 x the step cap (section B). The summary line gets the lookahead
use and formal wall time vs Arm A, plus the 1c report wording. Everything else in this file is unchanged.

If CODE_COMMIT is still a placeholder, stop at P1 and ask me.

## B. Task facts

- **Instruction the agent sees:** "Pick up the watering can and water the plant." (UP `services/dexjoco/task_rules/water_plant.md:1`).
- **Success (agent's wording):** the can's nozzle is within a set distance of the plant, horizontally
  and vertically, while the trigger is pulled, for a number of consecutive steps. The trigger counts as
  pulled past a set travel and released below a lower one (`task_rules/water_plant.md:3-4`).
- **Fail (agent's wording):** the episode ends as a failure if the trigger is pulled at any step while
  the nozzle is outside that region (`task_rules/water_plant.md:6-7`).
- **Scene variation:** can position, plant position and table height change per layout (`task_rules/water_plant.md:9`).
- **Robot:** single arm, one Franka Panda + 16-DoF Allegro hand; 22-dim action (`UP services/dexjoco/tasks.py:33`, `tasks.py:97-98`).
- **Step cap:** 1000 control steps, no pre-roll (`tasks.py:33`, `tasks.py:91-94`). Exploration episode
  wall limit = 600 + 1000 x 5 = **5600 s** (`tasks.py:128-136`), not Hanoi's 8100 s.
- **Official check** (the agent reads all of it through `goal`; do not paste it into the workspace
  yourself, the tool is the only channel): a cylinder around the plant body origin, radius 0.2 m, height
  +-0.2 m; trigger joint `spray_joint_0_pos` pulled > 0.34, released < 0.25; 30 consecutive steps inside
  while pulled (`OFF:29-31`, `OFF:555-575`). Layout ranges (not in the tool): can xy sampled in
  x [-0.35,-0.30], y [-0.25,-0.20]; plant xy in x [-0.10,-0.05], y [0.15,0.20]; table height offset
  0-0.05 m (`OFF:23-26`, `OFF:400`). Use these to classify failure stages.
- **What `goal` reports** (`GL:78-117`, `water_plant()`):
  - `description`: hold the nozzle within 0.2 m horizontally and 0.2 m vertically of the plant origin with
    the trigger pulled (above the pull threshold) for the required consecutive steps; pulling outside
    fails (`GL:106-108`).
  - `conditions` (`GL:91-99`): `nozzle_within_radius_of_plant` (measured: horizontal nozzle-plant distance;
    threshold `WATER_RADIUS_M` 0.2), `nozzle_within_height_band_of_plant` (measured: nozzle z minus plant z;
    threshold [-0.2, 0.2], `WATER_HALF_HEIGHT_M`), `trigger_pulled` (satisfied = the env's latch
    `_trigger_pulled`; measured: `spray_joint_0_pos` angle; threshold [release, pull] from the module
    constants `_TRIGGER_RELEASE_THRESHOLD`, `_TRIGGER_PULL_THRESHOLD`). 0.2/0.2 are local literals of the
    official check, copied at `GL:35-37` and guarded by `test_copied_literals_match_the_official_source`.
  - `failure_conditions` (`GL:100-103`): `trigger_pulled_outside_region` = latch on while the nozzle is
    outside the cylinder; measured [horizontal distance, height offset], threshold [0.2, 0.2].
  - `targets` (`GL:110-114`): `plant` (position, `radius_m`, `half_height_m`, point = nozzle), `nozzle`
    (position), `trigger` (`angle_rad`, `pull_above_rad`, `release_below_rad`).
  - `holding` (`GL:115`): `steps_satisfied` = `env._success_counter`, `steps_required` =
    `_SUCCESS_STEPS_REQUIRED` (30). `satisfied_now` = inside and latched (`GL:116`).
- **Demos (G4):** `python scripts/setup_dexjoco_demos.py --gpu $G --task water_plant`.

## C. Paper reference (vision only, one session per cell)

Table 5, Water column (PC lines 92-99; paper P:1099-1180):

| Budget | 2 | 4 | 8 | 16 | 32 | Best ME-Dex |
|---|---|---|---|---|---|---|
| Water (%) | 0.0 | 0.0 | **91.3** | 98.7 | 99.3 | 72.0 |

Compare at budget 8: paper 91.3% (137/150). We have no earlier vision-only water_plant run of our own.
Paper Table 17 agent time at budget 8: median 1.34 h, range 0.59-3.02 h (PC lines 116-124).

## D. Object-state smoke checklist (G5)

Labels come from `objects.py` TAIL/POINTS plus `STATE_EXTRA` (`"trigger": "hinge:joint_0"`, added in
dcbf92f) via `state_sources()` in the dev worktree. Re-check the labels against CODE_COMMIT; if they
differ, record it and ask me before G5 counts as passed.

| Label (source) | Expected at reset | Sane range |
|---|---|---|
| `watering can` (`joint:spray_root`) | `position_m` + `quaternion_wxyz` | x in [-0.36,-0.29], y in [-0.26,-0.19], z ~0.955-1.005; quat unit-norm, near (0.683, 0.183, 0.683, -0.183) up to sign (`spray.xml:60`) |
| `plant` (`body:plant`) | `position_m` + `quaternion_wxyz` | x in [-0.11,-0.04], y in [0.14,0.21], z ~1.06-1.11; quat unit-norm; must not move after no-op steps |
| `nozzle` (`site:ref_point`) | `position_m` | within ~0.15 m of the can origin (site offset 0, 0.095, 0.09 in the can frame); horizontal distance to plant > 0.2 m at reset (outside the region) |
| `trigger` (`hinge:joint_0`) | `angle_rad` | near its rest angle, below 0.25 (released) at reset |
| `watering can`, `plant` velocities | `linear_velocity_mps`, `angular_velocity_radps` | 3 finite values each; about 0 at step 0 (the smoke's at-rest limit) |
| `watering can`, `plant` `size` | `half_extents_m`, `center_offset_m` | 3 non-negative values each, plausible for the object (record them); identical at both calls (cached at reset) |
| `contacts` | list | well-formed rows, <= 64, sorted by force; at step 0 expect the can (and plant) resting on fixtures (table body name), no hand rows; record what is there |
| `goal.conditions` at step 0 | `satisfied` | `nozzle_within_radius_of_plant` False (measured > 0.2), `trigger_pulled` False; `satisfied_now` False |
| `goal.failure_conditions` at step 0 | `satisfied` | `trigger_pulled_outside_region` False |
| `goal.holding` at step 0 | | `steps_satisfied` 0, `steps_required` 30 |
| `arm_joint_positions_rad.arm` | 7 floats `joint1..7` | finite, within Panda limits; match the official state vector |

Also: `privileged_level` == `full`; `frame` == `world`; no `error` or `velocity_error` entries; no key
named `success`, `reward`, `terminated` or `native_*` (the reply filter would drop them); `goal.targets`
radius and half height equal the official 0.2 / 0.2; values unchanged (to 1e-3) after a few no-op steps,
except small settling. Record in DECISIONS.md at P1: the agent reads the full success check (cylinder
size, trigger thresholds, 30-step hold, latch state and counter) through `goal`.

## E. What to watch

Likely failure stages (use them as the formal-run classes). The agent now knows the region and the
trigger thresholds exactly, so failures should be control failures, not ignorance of the check:
1. **Grasp:** the can is not lifted or slips (light can; spray dynamics randomisation exists in `OFF:327-335`, check if rand_obj enables it).
2. **Early trigger:** a power grasp squeezes the trigger before the nozzle is over the plant. One step
   pulled outside the region ends the episode as a failure. Expect this to be the main killer.
3. **Aim:** nozzle carried to the plant but outside the region (too high, or plant leaves block it).
4. **Hold:** trigger pulled inside, but released or dropped below 0.25 travel before 30 steps.
5. **Timeout:** 1000 steps used up (slow approach, long settling holds).
Signs the privileged state helped (report each with evidence from `mcp.jsonl` and `controller.py`):
- the program reads `nozzle` and `plant` from `ctx.call("dexjoco_object_states", {})` instead of
  colour masks or depth; it aims with the nozzle point, not the can origin;
- it re-reads the state after the grasp to check the can is in hand before pulling the trigger;
- it reads `goal.conditions` / `goal.failure_conditions` before pulling, so it never pulls outside the
  region, and watches `goal.holding.steps_satisfied` until 30;
- it reads `contacts` to check the hand holds the can, and the `trigger` angle to control trigger travel;
Signs it did not: hard-coded layout constants, camera-only aiming, or calls only in exploration.

## F. Breakthrough candidates (clips)

- First stable lift of the can without pulling the trigger.
- First episode where the nozzle reaches the plant region and the spray cone shows (rising trigger edge, `OFF:518-519`).
- First simulator success (`task_complete`), and if present, the episode where an early-trigger
  failure was diagnosed and fixed.

## Expected time and usage (budget 8)

- Agent time: paper median 1.34 h (0.59-3.02 h); our v1 Hanoi session 2.6 h. Usage reference: about
  0.65 M output and 57 M cache-read tokens (v1 Hanoi, budget 8). Water should be at or below this.
- Formal eval: 150 x up to 1000 steps, 4 workers. v1 Hanoi (1500 steps) took ~2.3 h; scaled by step
  cap, about 1.5 h or less (successes and trigger failures end early). This is an estimate, not a number
  for the report.

## Acceptance line for the summary

"water_plant @8: paper 91.3% (vision only) vs ours X/150 = Y% (with full privileged state); agent time A h,
usage_wait W h; the program [does / does not] call dexjoco_object_states (N calls per episode)."
Done only when `R/results/water_plant.json` is complete (150/150), the session note passed its fact
check, 2-3 clips exist, and the GPU job is released.
