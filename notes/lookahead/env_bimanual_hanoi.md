# Lookahead state audit: bimanual_hanoi

Files read (the runtime imports the copy under `/data/user_data/vawale/rax_repro/DexJoCo/dexjoco/`;
`diff -q` against `.worktrees/dexjoco-v2/DexJoCo/...` shows the env, base class, controller, renderer and
XML are identical, so the line numbers below hold for both):

- `dexjoco/sim/envs/panda_bimanual_hanoi_env.py` (abbreviated `H:`), 934 lines
- `dexjoco/sim/mujoco_gym_env.py` (`B:`), `dexjoco/sim/controllers/opspace.py` (`O:`), `dexjoco/sim/rendering.py` (`Rn:`)
- `dexjoco/tasks/bimanual_hanoi/config.py`: wraps as `DexjocoObsAdapter(DualArmPolicyWrapper(PandaBimanualHanoiGymEnv(hz=30, ...)))`
- `dexjoco_openpi_client/dexjoco_openpi_env.py` (`W:`)
- XML `arena_arm_hand_bimanual_hanoi.xml`: `<option timestep=".002" noslip_iterations="5">`, Euler integrator,
  na=0, neq=0, nuserdata=0, nplugin=0, 2 mocap bodies (`target_right`, `target_left`).

## Call graph of one `step()`

`W:106 step` -> `_process_action` -> `_Tap.step` -> `DexjocoObsAdapter` (`observation()` only, stateless)
-> `DualArmPolicyWrapper.action()` (stateless, 46 -> {"right","left"}) -> `H:542 step`:

1. `H:543-558` pending-illegal branch (wall-clock gated, may call `reset()`).
2. `H:560` `start_time = time.time()`.
3. `H:562-587` parse action (zero-action detection).
4. `H:589-611` read old mocap, write new mocap pos/quat (both arms).
5. `H:613-645` 10 substeps (`_n_substeps = int(0.02 // 0.002)`, `B:36`): two `opspace()` calls, write `ctrl`, `mj_step`.
6. `H:647` `_compute_success_metrics()` (mutates trigger counters).
7. `H:648` `_compute_observation()` (renders 3 cameras when `image_obs`, default True).
8. `H:649` `env_step += 1`; `H:652` terminate at 1500.
9. `H:655-659` human render (not used; render_mode is rgb_array).
10. `H:661-662` `time.sleep(max(0, 1/hz - dt))` (hz=30 -> up to 33 ms per step).
11. `H:681-684` latch pending illegal reset.

## (a) MuJoCo mjData state covered by `mj_getState(mjSTATE_INTEGRATION)`

| State | Where read / written |
|---|---|
| `qpos`, `qvel`, `time`, `qacc_warmstart` | advanced by `mj_step` `H:645`; read by `O:109-110` (`data.qpos[dof_ids]`, `data.qvel[dof_ids]`), `H:690` (disk qvel for static check) |
| `mocap_pos`, `mocap_quat` | read `H:589-592`, written `H:600-611`, read by opspace targets `H:619-620, 633-634`, `H:902-912` |
| `ctrl` | written `H:626` (right arm torques), `H:640` (left arm), `H:643` (32 allegro targets; NOT written on zero action, so previous ctrl persists) |
| `act`, `qfrc_applied`, `xfrc_applied`, `eq_active`, `userdata`, plugin | not touched by step (na=neq=nuserdata=nplugin=0) but cheap and included |

### (a') mjData fields NOT in mjSTATE_INTEGRATION that step() reads (critical)

`mj_step` runs `mj_forward` *before* integrating, so after a step the derived fields in mjData describe the
pre-integration state, not the current `qpos`. The next step's first substep reads these stale values:

- `O:152` `mj_fullM(model, M, data.qM)` -> `qM`
- `O:179` `data.qfrc_bias[dof_ids]` (gravity/Coriolis comp)
- `O:115` `mj_jacSite` -> uses `site_xpos`, `xpos`/`subtree`-chain, `cdof`
- `O:127, 138` `data.site_xpos`, `data.site_xmat` (EE pose for the PD error)
- `H:690, 694, 700, 712` `_compute_success_metrics` reads `data.site_xpos` (post sites), `data.body(...).xpos` (base, disks)
- `H:862-885` observation reads `data.sensor(...).data` -> `sensordata` (flange pos/quat, allegro joint pos)
- rendering reads `xpos/xmat/geom_xpos/...` via `mjv_updateScene`

Measured (CPU-only check, real XML + real `opspace`, 30 warm-up steps, 10 lookahead steps with different
actions, restore, 10 real steps compared against never-looked-ahead; script
`/tmp/claude-6011310/.../scratchpad/hanoi_restore_check.py`):

| Restore method | max abs diff over qpos/qvel/sensordata/xpos | bit-identical |
|---|---|---|
| `mj_setState(INTEGRATION)` | 1.23 | no |
| `mj_setState(FULLPHYSICS)` | 1.23 | no |
| `mj_setState(INTEGRATION)` + `mj_forward` | 4.2e-3 | no (forward recomputes at current qpos, not the stale pre-step qpos) |
| `INTEGRATION` + copy back `qM, qfrc_bias, site_xpos, site_xmat, xpos, xquat, xmat, sensordata, qLD, qLDiagInv, cdof, cinert, crb, cdof_dot, cvel, xanchor, xaxis, xipos, ximat, subtree_com` | 0.0 | yes |
| in-place copy of every ndarray field of MjData (164 fields) from `copy.copy(data)` snapshot | 0.0 | yes |

Recommendation: snapshot with `snap = copy.copy(env._data)` (MjData copy) and restore IN PLACE:
`for n in ndarray_fields: getattr(env._data, n)[...] = getattr(snap, n)` (plus `mj_setState(INTEGRATION)` for
clarity; `time` is a scalar property, set it explicitly). Do NOT replace `env._data` with a new object:
`self._viewer = MujocoRenderer(self.model, self.data)` (`H:313`) holds a reference to the original MjData,
and the python bindings have no `mj_copyData` (mujoco 3.4.0; only `mj_copyState`/`mj_getState`/`mj_setState`).

## (b) mjModel fields mutated during step

None on the normal path. `mj_step` does not write the model; `step()` writes no model fields.
Model writes happen only in `reset()` (`H:459-519`), which `step()` calls ONLY via the pending-illegal
auto-reset at `H:546`:

- `H:463-465` `model.body("table").pos[2]` (table height `delta_h`)
- `H:468` `model.geom_size[table_leg, 1]`
- `H:474` `model.body_pos[hanoi_base]`
- `H:394-405` (randomize=rand_full) `light_pos`, `light_dir`, `light_diffuse`, `vis.headlight.ambient/diffuse`
- `H:412` `geom_matid[table_visual]`; `H:455-456` `cam_pos`, `cam_quat` of front camera
- `H:519` (randomize_dynamics, False in RaX) `body_mass` of disks
- also `mj_resetData` `H:460`, `_prime_rgb_array_renderer` `H:502`

If lookahead never lets the auto-reset branch run (see below), no model snapshot is needed. A defensive
snapshot of `body_pos, geom_size, body_mass, light_*, geom_matid, cam_pos, cam_quat` is cheap.

## (c) Python attributes on the env object read/mutated by step

| Attribute | Lines | Notes |
|---|---|---|
| `_pending_illegal_reset` (bool) | read `H:543`, set `H:682`, cleared in reset `H:506` | latch; once set every later step short-circuits |
| `_pending_illegal_deadline` (float, wall clock) | read `H:544`, set `H:683` | `time.time()+3.0` |
| `_pending_illegal_info` (dict or None) | read `H:545,556`, set `H:684` | plain dict copy of info |
| `_success_trigger_count` (int) | `H:832/834` in `_compute_success_metrics`, read `H:666,836` | 20 consecutive good frames -> success |
| `_illegal_trigger_count` (int) | `H:805/808/811`, read `H:667,813` | 10 consecutive -> illegal_state |
| `_illegal_trigger_reason` (str) | `H:804/807/810` | |
| `env_step` (int) | `H:649`, read `H:652` | terminates at 1500 |
| read-only during step: `_n_substeps`, `_mocap_*_id`, `_site_*_id`, `_panda_*_ids`, `_allegro_ctrl_ids`, `_disk_*`, `_post_*`, tolerances, `_disk_half_height`, `_base_upper_top_local_z`, `base_ori_pos`, `delta_h` (`H:895-896`, put in obs by reference), `image_obs`, `randomize`, `render_mode`, `hz`, `camera_id` | | constant between resets |
| `_viewer.camera_id` (gymnasium renderer attr) | `Rn:48` / gymnasium sets it on each `render(camera_id=...)` (`H:855`) | always ends on the last camera of `self.camera_id`; harmless but is mutated |

Wrapper-level state (outside the env class but in the same object chain the session steps):

- `W:119-123` `DexJoCoOpenPIEnv._done`, `_success`, `_raw_obs`, `obs` (and `last_stay_state` set by `stay()` `W:136-137`)
- `services/dexjoco/session.py:91-99` `_Tap.last_obs`, `last_info`, `ever_true`, `sequences`
- `DualArmPolicyWrapper`, `DexjocoObsAdapter`: stateless. No gymnasium TimeLimit/OrderEnforcing wrapper.

Best: drive lookahead through `tap._env` (the `DexjocoObsAdapter`) directly so wrapper/_Tap/session
state (video frames, step counters, operator files) is never touched; then only the 6 env attributes
above plus MjData need snapshotting.

## (d) RNG use during step

- Normal path: NONE. No `np.random`, `random`, `self._random` (`B:38`) or `np_random` use in `step`,
  `opspace`, `_compute_success_metrics`, `_compute_observation`. MuJoCo has no noise options set.
- Auto-reset path `H:546 -> reset()`: `np.random.uniform` for `delta_h` (`H:462`) and base xy (`H:470`);
  with rand_full: `random.uniform` x many (`H:398-405`), `random.choice` (`H:410`), `random.randint` (`H:416`);
  with randomize_dynamics: `np.random.uniform` x3 (`H:517`). These consume the GLOBAL generators the
  session seeded via `_set_seed` (`eval_dexjoco_openpi.py:50-53`), so an auto-reset inside lookahead would
  shift every later layout. Guard: refuse lookahead when `_pending_illegal_reset` is already True, and
  snapshot/restore `np.random.get_state()` and `random.getstate()` anyway (cheap insurance).

## Other non-determinism / cost hazards

- `H:544, 683` wall-clock deadline: lookahead that sets the latch must have it cleared on restore; if the
  real env already has the latch set, a lookahead step would either return immediately without physics
  or auto-reset (if >3 s elapsed). Refuse lookahead in that state.
- `H:662` `time.sleep` up to 1/30 s per step: no state effect, but makes a 50-row lookahead take ~1.7 s.
  Can temporarily set `env.hz = float("inf")`... note `1.0/inf = 0.0`, OK; restore after.
- `H:648/890` three offscreen renders per lookahead step (EGL). No physics effect (`mjv_updateScene`
  only reads mjData), but it costs time and leaves GL scene state; temporarily setting `image_obs=False`
  skips it (obs then lacks images; restore the flag). Lookahead needs only state, not images.
- `H:567-572` zero-action shortcut: a scalar 0 / None action leaves `ctrl[allegro]` at previous value;
  `ctrl` is in INTEGRATION state so this is covered.
- Obs `hanoi_base_ori_pos` is the same ndarray object as `self.base_ori_pos` (`H:895`); not mutated by step.

## Deepcopy safety

- Unsafe / do not deepcopy: `self._viewer` (gymnasium `MujocoRenderer` with an EGL `mjrContext`,
  `MjvScene`), the whole env object, the wrapper chain.
- `self._model`/`self._data`: copyable (`copy.copy(MjData)` works), but restore must be in place because
  the renderer aliases them (`H:313`).
- Safe to deepcopy: the 6 counters/flags, `_pending_illegal_info` (dict of bool/str/float/dict/list),
  `_Tap.last_info`, `ever_true`, `sequences`; `last_obs`/wrapper `obs` are dicts of ndarrays (copy is fine
  but large with images; better not to touch them by bypassing the wrappers).

## Minimal correct lookahead for hanoi

```
env = tap._env.unwrapped            # PandaBimanualHanoiGymEnv
assert not env._pending_illegal_reset
snap_d  = copy.copy(env._data); t0 = env._data.time
attrs   = {k: copy.deepcopy(getattr(env, k)) for k in ("_success_trigger_count", "_illegal_trigger_count",
           "_illegal_trigger_reason", "_pending_illegal_reset", "_pending_illegal_deadline",
           "_pending_illegal_info", "env_step")}
rng     = (np.random.get_state(), random.getstate())
flags   = (env.image_obs, env.hz); env.image_obs, env.hz = False, float("inf")
try: run rows through tap._env.step(row) (the ObsAdapter), read metrics/info/object state each row;
     stop if info["illegal_state"] or auto_reset
finally: in-place copy of all ndarray fields of snap_d into env._data; env._data.time = t0;
         setattr attrs; restore rng; restore flags
```
