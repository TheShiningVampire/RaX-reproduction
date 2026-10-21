# dexjoco_lookahead: implementation design

Branch: a new branch off `exp/add-state-info/object` (worktree `.worktrees/add-state-info`), because
the tool depends on `object_states(...)` (services/dexjoco/objects.py) and `goal(...)`
(services/dexjoco/goals.py) from that branch. Inputs: the six notes in this directory
(env_water_plant, env_fold_glasses, env_bimanual_microwave_cook, env_bimanual_photograph,
env_bimanual_hanoi, wrapper_and_mujoco). Line refs: `S:` services/dexjoco/session.py,
`W:` dexjoco_openpi_client/dexjoco_openpi_env.py, `A:` dexjoco/tasks/obs_adapters.py.

## 0. What the tool does

`dexjoco_lookahead(actions, report_every?)` simulates 1..150 official action rows (same rows
as `dexjoco_step`) from the **current live state, in the same env object and the same MjData /
MjModel**, reads object states and the goal at the end (and every k rows), then restores
everything so a later real `dexjoco_step` is bit-identical to one that never looked ahead. It
does not change `step_id`, does not write video frames or operator files, and never ends the
episode.

Key decisions (each one is backed by a measurement in the notes):

1. **Restore in place, on the live MjData.** Do not swap `raw._data` for a scratch copy. The
   renderers (`_viewer`, water_plant `_mj_viewer`) hold references to the original MjData and
   MjModel, and after the lookahead `observe`/depth/object_states must read exactly the
   pre-lookahead derived fields.
2. **`mj_setState(INTEGRATION)` alone is not enough.** In all 5 tasks it was not bit-identical:
   water_plant 1.9e-3, fold_glasses 1.4e-5, microwave 0.225, photograph 6.4e-3, hanoi 1.23.
   `mj_forward` afterwards does not fix it either (1.7e-7 to 4e-3). The reason: after
   `mj_step`, the derived fields (`site_xpos/xmat`, `qM`, `qfrc_bias`, the Jacobian inputs,
   sensordata) hold the kinematics from *before* integration, and `opspace` reads them on the
   first substep of the next step. A full in-place copy of MjData was bit-identical in every
   task.
3. **Bypass the wrapper's and the Tap's bookkeeping, keep the physics path.** For each row:
   `env_action = self.env._process_action(row)` (W:204, the same conversion that
   `DexJoCoOpenPIEnv.step` uses at W:116), then `self.tap._env.step(env_action)`. That runs the
   official gym chain `DexjocoObsAdapter -> {Single,Dual}ArmPolicyWrapper -> Panda*GymEnv`, the
   same chain `chunk_step` reaches through `wrapper.step -> _Tap.step`. The only things skipped
   are the wrapper's post-processing (`_done`, `_success`, `_raw_obs`, `obs`, W:119-123) and the
   Tap's history (S:90-99). Neither affects physics.
4. **No rendering and no sleep during the lookahead.** Set `raw.image_obs = False` and
   `raw.hz = float("inf")` for the rollout. A row then costs physics only, with no 33 ms sleep
   and no 2 to 4 camera renders. `DexjocoObsAdapter.observation` uses `obs.get("images", {})`
   (A:35), so the chain still works without images. Do not call `DexJoCoOpenPIEnv.step` with
   images off: `_process_obs` indexes `env_obs[camera]` and would raise `KeyError`.

## 1. Snapshot contents

All of this lives in a new module `services/dexjoco/lookahead.py` (pure functions plus a
`Snapshot` dataclass), so it can be unit-tested without the env.

### 1.1 MuJoCo data (`raw._data`, the live object `d`)

- `snap_d = copy.deepcopy(d)`. MuJoCo 3.4.0 bindings have no `mj_copyData`. The deepcopy is a
  full independent MjData, about a few MB at most.
- Also keep `state0 = mj_getState(m, d, mjSTATE_INTEGRATION)` (8191). It includes time, qpos,
  qvel, act, warmstart, ctrl, applied forces, eq_active, mocap and userdata. Mocap and ctrl
  carry over between steps: a zero arm action keeps the previous mocap target, and Allegro
  ctrl is written only for non-zero hand actions. Do **not** use FULLPHYSICS (4111): it drops
  warmstart, mocap and ctrl.

Restore, `restore_mjdata(m, d, snap_d)`, in this order (verified CPU-only, including
`ncon` 4 -> 16 during the lookahead):

1. `mujoco.mj_copyState(m, snap_d, d, mjSTATE_INTEGRATION)`.
2. Every int/float scalar attribute of MjData except `signature` (read-only): `ncon, ne, nf, nl,
   nefc, nJ, nA, nisland, nidof, time, parena, pstack, pbase, narena, nbuffer, maxuse_*,
   n*_awake, nplugin, threadpool`. Build the list once by introspection (`dir(d)`, isinstance
   int/float, minus `signature`). Scalars must go **before** arrays, so the variable-size views
   (`efc_*`, contact) take the snapshot's shape.
3. `np.copyto(getattr(d, n), getattr(snap_d, n))` for each of the 164 ndarray attributes. If a
   shape differs, raise; do not skip.
4. **Contacts explicitly.** `d.contact` is a `_MjContactList` view into the arena, not an
   ndarray attribute, so step 3 leaves it with the lookahead's values. In my check, `dist` and
   `pos` still differed after steps 1-3. For each ndarray field `f` of `snap_d.contact` (`H,
   dim, dist, efc_address, elem, exclude, flex, frame, friction, geom, geom1, geom2,
   includemargin, mu, pos, solimp, solref, solreffriction, vert`), do
   `getattr(d.contact, f)[...] = getattr(snap_d.contact, f)`. This gave zero diffs and an
   identical later trajectory.
5. `d.warning.{number,lastinfo}`, `d.solver.*` and `d.timer.*`: same field-wise copy. These are
   diagnostics, but the fingerprint covers them, so they are copied too.

The derived-field restore matters for two reasons. It makes the next real step bit-identical
(decision 2). It also means `object_states`, `observe` and depth renders right after a
lookahead read pre-lookahead values, which `mj_forward` cannot guarantee.

### 1.2 MuJoCo model (`raw._model`)

No task writes MjModel inside `step()` on the RaX path, except the visual-only water_plant
cone alpha. Model writes in `reset()`/`_randomize_dynamics()` are made unreachable by the
guards in section 2.1.

- Per-task `MODEL_FIELDS` (snapshotted with `np.copy` and restored with `np.copyto`):
  - `water_plant`: `geom_rgba` (cone visual alpha, E:528-531), plus `geom_group` (written only
    when `render_mode=="human"`; listed for safety).
  - `click_mouse` (not a trial task, but cheap): `geom_rgba`, `mat_rgba` (display turns blue).
  - `bimanual_photograph`: `tex_data`, only if `camera_screen_effect` is True. The RaX config
    has it False, so assert False and refuse otherwise (copying tex_data each call is costly).
  - All others: none.
- Model fingerprint (checked, not restored): a blake2b hash of `body_pos, body_quat, body_mass,
  geom_size, geom_rgba, geom_matid, geom_friction, dof_damping, actuator_gainprm,
  actuator_biasprm, cam_pos, cam_quat, light_pos, light_diffuse, opt.timestep`, taken before and
  after. A mismatch raises (section 4). This catches a model write that slips in.

### 1.3 Python attributes: a generic snapshot

Objects to snapshot (each with `vars(obj)`):

| object | why |
|---|---|
| `raw = self.tap.unwrapped` | task counters, latches and the step counter |
| each gym wrapper between `self.tap._env` and `raw` (walk `.env`) | normally stateless; snapshot defensively |
| `self.env` (DexJoCoOpenPIEnv) | bypassed, but snapshotted: `obs`, `_raw_obs`, `_done`, `_success`, `last_stay_state` |
| `self.tap` (`_Tap`) | bypassed; `last_obs`, `last_info`, `ever_true`, `sequences` are fingerprinted |

Rules for each attribute value (`snapshot_attrs(obj, exclude)`):

- **Excluded** (identity only: record `id(value)`, assert it is unchanged after): the name is
  in `EXCLUDE_NAMES = {"_model", "_data", "model", "data", "_viewer", "_mj_viewer", "viewer",
  "renderer", "_renderer", "env", "_env", "_random", "np_random", "_np_random", "observation_space",
  "action_space", "spec", "metadata"}`; or the type's module starts with `mujoco` or `gymnasium`,
  or the type name contains `Render`/`Viewer`/`Context`; or it is a module, function, method,
  thread, lock or file handle. **Never deepcopy the env, `_viewer` or `_mj_viewer`**: they hold
  EGL/GL contexts.
- **Immutable** (`None, bool, int, float, str, bytes, np.generic`, tuples of these): store the
  value, restore with `setattr`.
- **`np.ndarray`**: store `(ref, ref.copy())`. Restore with `np.copyto(ref, saved)` and then
  `setattr(obj, name, ref)`. This restores the content *and* the object identity, so aliases
  stay valid. An example is `last_stay_state`, which aliases the old `obs["state"]`, a view
  into env memory.
- **Containers** (`list, dict, set`, nested; checked recursively to contain only the allowed
  kinds): store `(ref, copy.deepcopy(ref))`. Restore in place (`ref.clear(); ref.update(...)` /
  `ref[:] = ...`) and `setattr(obj, name, ref)`. In-place restore matters for `_Tap.sequences`
  and `ever_true`, which are mutated in place (S:95-98).
- **Anything else**: excluded with an identity check, and logged once per class in a debug
  list. The unit test fails if a `REQUIRED_ATTRS` entry falls into this bucket.
- **Added or removed names**: compare `set(vars(obj))` before and after. Delete names that
  appeared during the lookahead and restore names that vanished. `last_stay_state` does not
  exist before the first `stay()`.

`REQUIRED_ATTRS` per task (these must be found and be in the "snapshotted" bucket; a unit test
asserts this against the official source with an AST scan for `self.<name> =` in `step()` and
the helpers it calls):

| task | raw-env attributes changed by `step()` |
|---|---|
| water_plant | `env_step`, `_trigger_pulled` (latch), `_cone_alpha_counter`, `_success_counter` |
| fold_glasses | `env_step` (terminates at 1200), `_success_trigger_count` (50 in a row) |
| bimanual_microwave_cook | `env_step` (terminates at 1100) |
| bimanual_photograph | `env_step`, `_latest_shutter_pressed` |
| bimanual_hanoi | `env_step`, `_success_trigger_count`, `_illegal_trigger_count`, `_illegal_trigger_reason`, `_pending_illegal_reset`, `_pending_illegal_deadline`, `_pending_illegal_info` |

Lookahead-only overrides (`image_obs`, `hz`) are set after the snapshot and returned to their
snapshotted values by the generic restore. Restore them also in a dedicated `finally`, so an
exception between set and restore cannot leave rendering off.

### 1.4 Session fields (checked, never written)

`step_id, terminated, truncated, success, in_stay, invalid_reason, finish_reason,
episode_id, id(obs), id(scene)`, and the video writer's frame count (keep a `self._video_frames`
counter in `_write_video_frame`). They go into the fingerprint; any change raises. The lookahead
code never assigns any of them.

### 1.5 RNG

No task draws random numbers in `step()`, opspace or the success check. Every draw happens in
`__init__`/`reset`/`_randomize_*`. As cheap insurance, save and restore
`np.random.get_state()`, `random.getstate()` and `raw._random.get_state()`, and include their
hashes in the fingerprint.

## 2. Rollout

```python
def lookahead(self, actions, report_every=0):           # session op "lookahead"
    rows = validated float64 matrix (same checks as chunk_step, S:321-326)
    require(not (self.terminated or self.truncated), "Episode already ended")
    guards (2.1); budget check (5)
    snap = take_snapshot(self)                           # 1.1-1.5
    fp0 = fingerprint(self)                              # 4
    reports, end = [], None
    t0 = time.monotonic()
    try:
        raw.image_obs, raw.hz = False, float("inf")
        for i, row in enumerate(rows, 1):
            obs, _r, term, trunc, info = self.tap._env.step(self.env._process_action(row))
            if report_every and i % report_every == 0 and i < len(rows): reports.append(self._la_report(i, obs))
            if term or trunc: end = ("episode_end", i, info); break
            if hanoi and raw._pending_illegal_reset: end = ("illegal_move", i, info); break
            if time.monotonic() - t0 > LOOKAHEAD_WALL_S: end = ("wall_time", i, None); break
        final = self._la_report(i, obs)                  # always read before restore
    finally:
        restore_snapshot(self, snap)                     # also image_obs/hz
    fp1 = fingerprint(self)
    if fp1 != fp0: self.invalid_reason = "lookahead_restore_mismatch"; write operator state; raise LookaheadRestoreError(diff keys)
    self._lookahead_rows += i; self._lookahead_calls += 1
    return reply (6)
```

`_la_report(i, obs)` returns `{"row": i, "state": obs["state"][:23|46].tolist(),
"object_states": object_states(raw._data, env_name, dual_arm, level=self.privileged,
model=raw._model, env=raw, scene=self.scene)}`. At the `full` level this includes `goal`
(goals.py `goal(env, data, env_name)`, read-only, with `holding.steps_satisfied` read from the
counters). The state slice is the same official state the wrapper builds (W:194-198). Reports
are read *before* restore, so they show the lookahead state.

### 2.1 Guards (refuse before touching anything: `RejectedBeforeAction`)

- No active episode, or the episode has ended (as `chunk_step`).
- `raw.reset_trigger` is truthy (fold_glasses E:507; it is set only by sim_teleop).
- hanoi: `raw._pending_illegal_reset` is set. The auto-reset at H:546 calls `reset()`, which
  draws from the global RNG and writes MjModel. The deadline is wall-clock.
- photograph: `raw.camera_screen_effect` is True.
- `raw.render_mode == "human"`.
- Budget exhausted (section 5).

### 2.2 Ending inside the lookahead

The env's own `terminated` (the `env_step` cap, or official success) or `truncated` stops the
rollout on that row. It is reported as `stop_reason: "episode_end"` with `end_row`. This is a
prediction only; the session's flags are untouched. At the `full` privileged level, also report
`end_cause` (`"step_cap"` if `raw.env_step >= cap`, else `"task_condition"`). At the `objects`
level, give no cause, because the cause discloses official success. hanoi illegal move: stop on
the row that sets `_pending_illegal_reset` (`stop_reason: "illegal_move"`, plus
`_illegal_trigger_reason` at the full level), before any later row can trigger the auto-reset.

## 3. Restore

`restore_snapshot` runs in `finally`, in this order:

1. MjData (1.1).
2. Model fields (1.2).
3. Python attributes for wrappers, raw, the OpenPI wrapper and the Tap (1.3).
4. RNG (1.5).

It must not call `mj_forward` or `mj_step`.

## 4. Exactness check (always on)

`fingerprint(self)` is a blake2b-256 digest of the following, compared before and after the
lookahead:

- `mj_getState(m, d, mjSTATE_INTEGRATION).tobytes()`, the cheap core (at most 858 doubles).
  Do not use FULLPHYSICS for this; it misses ctrl, mocap and warmstart.
- Every MjData ndarray attribute's bytes, **excluding the arena-noise list** (`efc_AR_colind,
  efc_AR_rowadr, efc_AR_rownnz, iefc_J_colind, iefc_J_rowadr, iefc_J_rowsuper`; they differ
  even between two fresh identical runs), plus the contact fields and MjData scalars (minus
  `signature`, `threadpool` and `maxuse_*`). The `maxuse_*` scalars are high-water marks that
  are restored, but excluding them keeps the check robust.
- The model-fingerprint arrays (1.2).
- A canonical hash of each snapshotted Python attribute (arrays as dtype, shape and bytes;
  containers recursively, sets sorted by repr) plus the identity of each excluded attribute.
- The session fields (1.4) and the RNG states.

Cost: a few MB hashed, about 1 to 5 ms, negligible next to the rollout. On a mismatch, raise
`LookaheadRestoreError` with the names of the differing components. Mark the episode
`invalid_reason="lookahead_restore_mismatch"` (written to operator_state, not shown to the
agent), because later real steps can no longer be trusted. A debug env var
`RAX_LOOKAHEAD_VERIFY=full` also compares every attribute against the snapshot field by field,
to name the culprit.

## 5. Limits

| limit | value | reason |
|---|---|---|
| rows per call | 1..150 (`MAX_ACTION_ROWS`, the same as `dexjoco_step`) | one chunk; with no render or sleep, about 0.5 to 2 s physics |
| `report_every` | 0 (final only) or 5..150; at most 15 intermediate reports | reply size (object_states at the full level includes contacts) |
| rows per episode | `3 * native_step_limit` (water_plant/photograph 3000, microwave 3300, fold_glasses 3600, hanoi 4500) | lets the agent try about 3 alternatives per real step budget without turning the tool into exhaustive search |
| calls per episode | 300 | bounds JSON traffic |
| wall time per call | 30 s (`LOOKAHEAD_WALL_S`); stop early with `stop_reason: "wall_time"` and still restore | the episode wall clock (`600 + 5*steps` s) keeps running during the lookahead; nothing extra is granted |

Measure the per-row cost in the GPU test and record it in DESIGN results. If bimanual is
above 15 ms/row, lower the cap per call.

Gating: the tool is offered only when `RAX_LOOKAHEAD=1` (default off), like
`RAX_PRIVILEGED_STATE`. Record `lookahead_enabled`, `lookahead_calls` and `lookahead_rows` in
`metadata`, operator_state and summary.json, so formal results with the oracle are labelled.

## 6. Agent/program interface

Wiring:

- `services/dexjoco/tools.py`:
  - Add `LOOKAHEAD = "dexjoco_lookahead"` to `ROBOT_TOOLS`, but **not** to `MUTATING`.
  - Add a definition to `tool_definitions()`.
  - Add a `validate_request` branch:
    `_only(arguments, ("actions", "report_every"))`, then `validate_actions`, then a
    `report_every` int check of 0 or 5..150.
- `services/benchmarks.py:17`: add the name to the DexJoCo tool list.
- `services/dexjoco/backend.py` `_call`: `result = sim.request("lookahead",
  actions=np.asarray(...), report_every=...)`, then `return _agent_safe(_jsonable(result)), []`.
  Afterwards assert `(sim.episode_id, sim.step_id) == before` and do **not** reset
  `self._evaluation`.
- `session._dispatch`: add `if op == "lookahead": return self.lookahead(data["actions"],
  int(data.get("report_every", 0)))`. This goes after `_check_identity`, so a stale `step_id`
  is rejected. `action_execution_scope` sees no `step_id` delta, so a rejection stays
  `RejectedBeforeAction`.

Reply. `_agent_safe` drops these keys at any depth: success, terminated, truncated, score,
reward, `native_*`, valid_for_success_rate. Also avoid `done` and `succeed`.

```json
{"episode_id": "...", "step_id": 412,             // live step, unchanged
 "rows_requested": 150, "rows_simulated": 97,
 "stop_reason": null | "episode_end" | "illegal_move" | "wall_time",
 "end_row": 97 | null, "end_cause": "step_cap" | "task_condition" | null,   // full level only
 "reports": [{"row": 10, "state": [...], "object_states": {...}}, ...],
 "final": {"row": 97, "state": [...], "object_states": {..., "goal": {...}}},
 "live_state_restored": true,
 "lookahead_budget": {"rows_used": 840, "rows_left": 2160, "calls_used": 9, "calls_left": 291},
 "elapsed_s": 0.84}
```

MCP description text:

> Simulate 1..150 dexjoco_step rows from the current live state of this episode, read the object
> states (and, at the full privileged level, the goal) after the last row and every report_every
> rows, then rewind the simulator exactly. Nothing is executed: step_id, the episode budget,
> frames and the recording are unchanged, and a later dexjoco_step behaves as if no lookahead had
> happened. The physics, controller and contacts are the episode's own, unlike
> dexjoco_preview_run. Stops early when the episode would end (stop_reason episode_end, end_row).
> Returns state vectors and object states, no images. Limited to 3x the episode step limit in
> simulated rows and 30 s per call; the episode's wall clock keeps running.

Skill paragraph, for `agent_skills/control/dexjoco/robot-interface/SKILL.md`:

> **Look before you commit (`dexjoco_lookahead`).** Pass the exact rows you would send to
> `dexjoco_step`. The simulator runs them from the current state, reports where the objects end
> up (`final.object_states`, and `final.object_states.goal` with each condition's measured value
> and threshold), and then rewinds, so you spend no episode steps. Use it to compare 2 or 3
> candidate chunks (an approach height, a grasp closure, a pour angle) and send the best one with
> `dexjoco_step`. The rows run through the real contact physics, so the prediction equals what
> `dexjoco_step` would do from this same state. It stops being exact once you send different
> rows. `stop_reason: "episode_end"` means those rows would end the episode. Each call costs
> wall-clock time and draws on a per-episode lookahead budget (`lookahead_budget`), so look
> ahead at decision points, not on every chunk. Use `report_every` to see the trajectory, not
> only the end.

## 7. Test plan

### CPU unit tests (`local_tests/unit/test_dexjoco_lookahead.py`, no env, no EGL)

1. **MjData restore**: a toy XML (4 stacked boxes on a plane, a slide actuator, a mocap body)
   and the real task XMLs loaded CPU-only. Steps: pre-roll 30, snapshot, run 25 different
   rows, restore, then compare every ndarray, scalar and contact field to the snapshot (minus
   the noise list). Then continue 40 rows and compare bitwise against a twin that never looked
   ahead. Include a case where `ncon` changes (4 -> 16).
2. **Negative control**: restoring with `mj_setState(INTEGRATION)` only must *fail* the
   fingerprint and twin comparison on a task XML with the real opspace controller (as in
   the scratchpad la_mw/t2.py). This guards that the test can detect the bug.
3. **Generic attribute snapshot**: a fake env object with an int counter, a latch bool, an
   ndarray aliased by another attribute, a dict of lists mutated in place, a set, an attribute
   added during the step, an attribute deleted during the step, a `MjData`, a fake viewer and a
   lambda. Mutate, restore, and assert: values equal, identities preserved, the alias still
   shared, the new name gone, the deleted name back, excluded objects not copied (a fake
   viewer whose `__deepcopy__` raises).
4. **REQUIRED_ATTRS coverage**: for each of the 5 tasks, an AST scan of the official env file
   (from `T.source_root()`) collects `self.X =` targets inside `step` and its callees.
   Assert each one is in REQUIRED_ATTRS and would be snapshotted, and that every MjModel write
   in `step` (`self._model.<field>[...] =`) is in MODEL_FIELDS.
5. **Session plumbing with a fake raw env** (stub `step` that changes qpos and counters, and
   counts renders and sleeps): `lookahead` leaves `step_id`, the flags, `obs` identity, the
   video frame count and the operator-file mtimes unchanged. `image_obs`/`hz` come back even
   when the stub raises mid-rollout. `stop_reason` is `episode_end` when the stub terminates.
   The guards reject the cases in 2.1. Budgets count down and reject. A forced restore bug
   (monkeypatched `restore_mjdata` that skips contacts) raises `LookaheadRestoreError` and sets
   `invalid_reason`.
6. **Reply filter**: a reply through `_agent_safe` keeps every documented key. Assert no key
   in `_agent_safe`'s drop list appears at any depth. `validate_request` rejects extra keys,
   bad `report_every`, and wrong row widths.

### GPU acceptance test (`scripts/lookahead_acceptance.py`, sbatch on katef, 1 GPU)

For each task in `water_plant, fold_glasses, bimanual_microwave_cook, bimanual_photograph,
bimanual_hanoi`, run two sessions with the same exploration layout. The rows R are a
recorded demo chunk (`demonstrations.py`) or hold rows.

- **A (reference)**: reset, then `chunk_step(R1)` (40 rows), then `chunk_step(R2)` (60 rows).
- **B (lookahead)**: reset, then `chunk_step(R1)`, then `lookahead(Rx)` (150 different rows,
  for example R2 offset by 5 cm), then `lookahead(R2)`, then `chunk_step(R2)`.

Pass criteria:

- (i) B's `chunk_step(R2)` is bitwise equal to A's: every per-step `state`, `object_states`,
  and the final MjData fingerprint, comparing qpos, qvel, sensordata and the raw env's
  attribute hash.
- (ii) B's `lookahead(R2).final` equals A's state after R2 bitwise, so the prediction is
  exact.
- (iii) The RGB frames after the lookahead equal A's at the same step. The renderer sees the
  restored derived fields.
- (iv) `observe`/`object_states` called right after the lookahead equals the call made before
  it.

**Episode-end case**: on a microwave or water_plant episode, use `chunk_step` to bring
`env_step` to cap-60, then `lookahead` 150 rows. Expect `stop_reason == "episode_end"` and
`end_row == 60`. Then `chunk_step(60 rows)` ends the episode at the same row, and before that,
`status` still shows the episode active after the lookahead.

**Success case**: replay a successful demo to just before it completes, then run a lookahead
over the remaining rows. Expect `end_cause == "task_condition"` at the full level, and no
`end_cause` at the objects level.

**Hanoi illegal move**: a lookahead that drops a disk on the table stops with `illegal_move`,
and the following real step does not auto-reset.

Record per-row lookahead cost per task. Following the definitions of done, paste the
evidence: per-task pass/fail, max diff (must be 0), and timings.

## 8. Risks

1. **An unlisted MjData-side state.** Examples: plugin state, which is 0 in all XMLs today,
   or a future MuJoCo field that is not an ndarray attribute (like `contact`). Mitigation: the
   fingerprint plus the GPU twin test. Pin `mujoco==3.4.0` in the test, and re-run the
   introspection test when it changes.
2. **`image_obs=False` changes physics or task logic.** Example: photograph's shutter or
   screen effect reading a render. Restore stays exact, but the *prediction* would diverge from
   the real step. GPU criterion (ii) detects this. The fallback is a per-task
   `RENDER_DURING_LOOKAHEAD=True`, which costs renders but no sleep.
3. **A hidden Python state on objects excluded by type**, for example state held inside a
   gym wrapper's helper object. The identity check would not see content changes. Mitigation:
   the AST coverage test, and the per-class debug list of excluded attributes reviewed once.
4. **Wall-clock-dependent logic**: the hanoi illegal-reset deadline, and `time.sleep`-based
   pacing. A lookahead with `hz=inf` runs faster than real time, so any wall-clock condition
   behaves differently from a real step. Mitigated by refusing and stopping on
   `_pending_illegal_reset`. Any new wall-clock logic needs a guard.
5. **Benchmark validity**: lookahead is an oracle-grade planner, since it runs exact physics.
   Keep it gated (`RAX_LOOKAHEAD`, default off), labelled in summaries, and budgeted.
6. **Cost**: a deepcopy of MjData plus hashing on each call (a few ms), and 150 rows of
   bimanual physics (possibly over 1 s). The 30 s cap and budgets bound it. Measure in the GPU
   test.
7. **Partial-failure state**: an exception inside the env step (for example a MuJoCo
   instability warning that becomes an error). The `finally` restore runs, and the fingerprint
   decides whether the episode is still valid. If the restore itself raises, mark the episode
   invalid and stop the session: never continue on an unverified state.
8. **Concurrency**: none expected (the session handles one request at a time). If an async
   observer, such as the operator live view, ever reads `_data` during a lookahead, it would
   see lookahead state. It only reads files today.
9. **Disagreement between the notes**: the per-env notes favoured swapping a scratch `_data`,
   and the wrapper note favoured in-place restore. Both were bit-identical for the physics.
   In-place is chosen because the renderer and anything holding `raw._data` keep pointing at
   the live object. That only works if the contact arrays are copied explicitly (1.1 step 4),
   which the wrapper note's det3 did not check field by field.
