# Lookahead: wrapper, session and MuJoCo state (everything outside the task env classes)

Scope: what `dexjoco_lookahead(actions)` must snapshot and restore outside the per-task
`Panda*GymEnv` classes so that a later real step is bit-identical to never having looked ahead.
Research only; experiment scripts are in the session scratchpad
(`/tmp/claude-6011310/.../scratchpad/{survey,det,det2,det3}.py`), not in the repo.

Environment checked: `/data/user_data/vawale/rax_repro_v2/runtime/envs/dexjoco/bin/python`,
**mujoco 3.4.0**, numpy 1.26.4. The installed `dexjoco_openpi_client` resolves to
`/data/user_data/vawale/rax_repro/DexJoCo/dexjoco/dexjoco_openpi_client/` (identical, per `diff -rq`,
to `.worktrees/dexjoco-v2/DexJoCo/dexjoco/dexjoco_openpi_client`).

## 1. `DexJoCoOpenPIEnv` (dexjoco_openpi_env.py), mutable attributes

| attribute | written by | notes |
|---|---|---|
| `self.obs` (dict: resized 224x224 images, `state` slice, `prompt`) | `reset()`, `step()` (and so `stay()`) | rebuilt from scratch every step (new dict); `state` is a slice view of the env's obs array |
| `self._raw_obs` (dict camera -> raw frame) | `_update_raw_obs` in `reset()`/`step()` | new dict each step; `get_raw_images()` returns it **by reference** (no copy) |
| `self._done` / `self._success` (`is_done`, `is_success`) | `reset()`, `step()` | from `terminated`, `info["succeed"]` |
| `self.last_stay_state` | `stay(continue_stay=False)` only | created lazily (no attribute before first stay); `stay(True)` reads it. It aliases `self.obs["state"]` of that moment |
| `self.env` | `start()`/`close()` | the raw env; the session replaces it with `_Tap` |

No step counter, no action-chunk buffer and no RNG in the wrapper (the chunk queue/interpolation lives
only in `eval_dexjoco_openpi.py`'s threaded loop, not used by the harness). `step()` returns
`info.get("pressed_digits")`. `_process_action` uses scipy `Rotation` (deterministic, no RNG).

Snapshot for lookahead: `obs` (shallow dict copy is enough since step builds a new dict, but deep copy
is safer because `obs["state"]` is a view into env memory), `_raw_obs` (same), `_done`, `_success`,
and `last_stay_state` **including its absence** (`hasattr`; restore with `delattr` if it did not
exist). Restoring `obs`/`_raw_obs` by object reassignment keeps `get_raw_images()` consistent.

## 2. `services/dexjoco/session.py`

`_Tap` (wraps `env.env`, forwards everything else via `__getattr__`):
- `last_obs`, `last_info` (replaced each step; `last_obs["state"]` holds the privileged tail),
- `ever_true` (set, grows), `sequences` (dict of lists, `extend`ed in place up to 200 entries).
  Lookahead must deep-copy `ever_true`/`sequences` (in-place mutation), or better: bypass the Tap
  bookkeeping entirely by stepping `tap._env` (the raw env) directly during lookahead, and still
  snapshot `last_obs`/`last_info` defensively.

`DexjocoSession` state touched by a real step path (`chunk_step`/`hold` -> `_execute` -> `_after_step`):
- `step_id` (+1 per row), `terminated`, `success`, `in_stay`, `obs` (agent observation cache returned by
  `observe`), `video` (imageio writer: `_write_video_frame` appends a frame per row - **irreversible**),
  operator files written at the end of `_execute`: `operator_state.json`, `<episode>/live.npz`;
  on termination `_write_summary` writes `evaluation_outcome.json`, `summary.json`,
  `private_goal_report.json` (**irreversible, and ends the episode**).
- Untouched by steps: `initial_state`, `initial_info`, `initial_live`, `scene`, `layout*`, `metadata`.

Implication: lookahead must NOT go through `_execute`/`_after_step`/`chunk_step`/`hold`. Call
`self.env.step(row)` (or the raw env's `step(self.env._process_action(row))`) in a private loop and
never touch `step_id`, `video`, operator files or `_write_summary`. Keep `step_id` unchanged also
because `action_execution_scope` (services/simulator/io.py) treats a `step_id` delta as "rows
executed" and converts a later rejection into `PartialExecutionError`. Termination/success seen during
lookahead must be reported in the tool result only, never stored in `self.terminated/self.success`.
A lookahead "hold" (stay semantics) needs `in_stay`/`last_stay_state` restored.

Cost note: every raw-env `step()` renders all cameras (`_compute_observation`) and sleeps
`max(0, 1/hz - dt)` with hz=30, so lookahead of K rows costs >= K/30 s wall clock unless the sleep
is patched out during lookahead (e.g. temporarily `env.hz = float('inf')` -> `1/inf = 0`; restore after).

## 3. MuJoCo 3.4.0 state API

`mjtState` bits: TIME 1, QPOS 2, QVEL 4, ACT 8, WARMSTART 16, CTRL 32, QFRC_APPLIED 64,
XFRC_APPLIED 128, EQ_ACTIVE 256, MOCAP_POS 512, MOCAP_QUAT 1024, USERDATA 2048, PLUGIN 4096.
- `mjSTATE_PHYSICS` = 14 (qpos|qvel|act)
- `mjSTATE_FULLPHYSICS` = 4111 = time|qpos|qvel|act|plugin - **no warmstart, no mocap, no ctrl**
- `mjSTATE_USER` = 4064 (ctrl, applied forces, eq_active, mocap, userdata)
- `mjSTATE_INTEGRATION` = 8191 = everything incl. warmstart. **Use this.**

Python bindings: `mj_stateSize(m, sig)`, `mj_getState(m, d, out, sig)`, `mj_setState(m, d, state, sig)`,
`mj_copyState(m, src, dst, sig)`, `mj_extractState`. There is **no `mj_copyData` binding**; full copies
are `copy.copy(d)` / `copy.deepcopy(d)` (new MjData objects).

All 10 DexJoCo XMLs (CPU load only): `na=0`, `nuserdata=0`, `nplugin=0`, `neq=0`, `nflex=0`,
`nmocap` 1 (single-arm) or 2 (bimanual), Euler integrator, Newton solver, noslip_iterations=5,
warmstart **enabled**, `enableflags=0` (sleep off). INTEGRATION state size 407-858 doubles.
Mocap matters: the envs write `mocap_pos/quat` from the action and opspace tracks it; the zero-action
branch keeps the previous mocap. `time` matters for `time_limit_exceeded`. Warmstart matters: see below.

### Determinism experiment (CPU, no rendering)

Models: a toy (3 free bodies stacked on a plane + slide actuator, 9-12 contacts) and the real
`arena_arm_hand_monitor_mouse.xml` (5 contacts). 10 substeps per control row, seeded random ctrl.
Reference: pre N=30 rows then real M=40 rows, never looking ahead. Test: pre 30 rows, snapshot,
lookahead 25 different rows, restore, real 40 rows; compare time|qpos|qvel|qacc_warmstart|sensordata
per row with `np.array_equal`, plus every ndarray field of MjData at the end.

| restore method | toy | click_mouse xml |
|---|---|---|
| `mj_setState(INTEGRATION)` | bit-identical | bit-identical |
| `mj_setState(FULLPHYSICS)` | **differs (max 1.08e-12)** - missing warmstart | identical here (luck) |
| `FULLPHYSICS\|WARMSTART` | bit-identical | bit-identical |
| `mj_copyState(snap -> d, INTEGRATION)` | bit-identical | bit-identical |
| `INTEGRATION` + `mj_forward` | bit-identical | bit-identical |
| lookahead on `copy.copy(d)` (live untouched) | prediction == real; live identical | same |

Caveat on derived fields: right after `mj_setState`, ~78-82 derived fields (xpos/xquat, sensordata,
contact, efc_*, actuator_*, cam_xpos/xmat, M, ...) still hold the **lookahead's** values until the next
`mj_step`. The next `mj_step` recomputes them, so physics is unaffected, but anything that reads
`_data` between restore and the next real step (the `object_states` op, `collect_depth_frames`/
rendering, `_compute_success`-style helpers) would see stale lookahead data. `mj_forward` does not fix
this exactly either (after a real `mj_step`, derived fields correspond to the pre-integration state,
whereas `mj_forward` computes them at the post-integration state).

Exact full restore that works in place (det3.py, both models, including when `ncon` changed 9 -> 12
during lookahead): snapshot `snap = copy.deepcopy(d)`; restore with
1. `mujoco.mj_copyState(m, snap, d, mjSTATE_INTEGRATION)`,
2. `setattr(d, name, value)` for every int/float scalar attribute of `snap` (ncon, nefc, ne, nf, nl,
   nJ, nA, time, ...; only `signature` is read-only - skip it). Do scalars **before** arrays so the
   `contact`/`efc_*` views take the right shape,
3. `np.copyto(getattr(d, n), getattr(snap, n))` for every ndarray attribute.
Result: zero non-garbage array diffs, zero scalar diffs, next trajectory bit-identical.

Noise to ignore in comparisons: `efc_AR_colind`, `efc_AR_rowadr`, `efc_AR_rownnz`, `iefc_J_colind`,
`iefc_J_rowadr`, `iefc_J_rowsuper` differ between two fresh identical runs and even change on the
live data when an unrelated copy is made/stepped: unused arena memory for the dense Newton path,
not state.

Why not swap `raw._data` for a scratch copy: the envs build `MujocoRenderer(self.model, self.data)`
at init (`_viewer`, water_plant `_mj_viewer`), so the renderer keeps the original MjData; the
lookahead's images would show the live state. Restoring in place on the same MjData object is
the safer design. **Model mutation is out of scope here but must be checked per task env** (e.g.
click_mouse `_set_display_blue` on click, randomized dynamics touch `MjModel`); any `MjModel` field
a step can write must be snapshotted too (MjModel also supports `copy.deepcopy`).

## 4. Global RNG

- `_set_seed(seed)` (eval_dexjoco_openpi.py) does `np.random.seed` + `random.seed`; torch lines are
  commented out. No `import torch` anywhere in `dexjoco` or `dexjoco_openpi_client`.
- AST scan of all `sim/envs/*.py` and `sim/mujoco_gym_env.py`: functions using `np.random.*`,
  `random.*` or `self._random` are only `__init__`, `reset`, `randomize_{camera,lighting,desktop_texture}`,
  `_sample_reset_tower_state` (hanoi), `_randomize_dynamics` (fold_glasses),
  `_randomize_spray_dynamics`/`_mul` (water_plant, called from reset). **No `step()` path draws
  random numbers**; `self._random = np.random.RandomState(seed)` in `MujocoGymEnv` is unused by steps.
- MuJoCo itself draws no random numbers in `mj_step` (sensor noise is not applied).
- Still cheap insurance: `np.random.get_state()`/`set_state()`, `random.getstate()`/`setstate()`, and
  `raw._random.get_state()`/`set_state()` around the lookahead, in case an episode is ever reset later
  in the same process or a task env starts using RNG in step.

## Restore checklist for the tool (outside task envs)

1. MjData: deepcopy snapshot + in-place full restore (INTEGRATION copyState + scalars + arrays).
2. Wrapper: `obs`, `_raw_obs`, `_done`, `_success`, `last_stay_state` (and its existence).
3. Tap: `last_obs`, `last_info`, `ever_true`, `sequences` (deep copies), or step `tap._env` directly.
4. Session: never call `_execute`; `step_id`, `in_stay`, `terminated`, `success`, `obs`, video and
   operator files must be unchanged (assert after restore).
5. RNG: numpy global, `random`, `raw._random`.
6. Task env (other notes): `env_step` counters, latches/flags, `MjModel` edits, `hz` sleep.
7. Verify in a test: obs/state/object_states and every MjData field (minus the arena-noise list) are
   equal before vs after a lookahead, and a real chunk after lookahead equals the same chunk in a
   twin session that never looked ahead.
