# Lookahead state audit: fold_glasses (PandaFoldGlassesGymEnv)

Source root: `/home/vawale/my_things/codes/rax/.worktrees/dexjoco-v2/DexJoCo/dexjoco/dexjoco/sim`
Files: `envs/panda_fold_glasses_env.py` (E), `mujoco_gym_env.py` (B), `controllers/opspace.py` (C), `rendering.py` (R).
MuJoCo 3.4.0 (env python `/data/user_data/vawale/rax_repro_v2/runtime/envs/dexjoco/bin/python`).
Model: `envs/xmls/arena_arm_hand_glass_v2.xml` (+ `panda_allegro_copy.xml`, `glass.xml`). Default Euler integrator, timestep 0.002, noslip_iterations=5. All actuators are `motor` or `position` (no dyntype -> na=0, no act state). 1 mocap body (`target`). No plugins, no user data, no actuator history/delay.

## step() call graph (E:436-510)
1. `time.time()` (E:437) - wall clock only.
2. Parse action; missing hand dims -> zeros (E:444-447).
3. Read `data.mocap_pos[0]`, `data.mocap_quat[0]` (E:449-450).
4. Write mocap target: unchanged if pos and quat all ~0, else absolute `tpos/tquat` (E:455-460). No normalisation of the quaternion.
5. `self._n_substeps` (=10, B:36) iterations of:
   - `opspace(...)` (C:139-260) reads `data.site_xpos[site]`, `data.site_xmat[site]`, `data.qpos`, `data.qvel`, `data.qM` (via `mj_fullM`, C:232), `data.qfrc_bias` (C:259), `mj_jacSite` (uses `xpos/xmat/subtree_com/cdof`-derived kinematics). Pure function, no state of its own.
   - write `data.ctrl[panda_ctrl_ids] = tau` (E:475)
   - write `data.ctrl[allegro_ctrl_ids] = action[7:23]` (E:483)
   - `mujoco.mj_step` (E:489)
6. `_compute_observation()` (E:491, 576-609): reads `data.sensor(...)` (sensordata), `self.glass_ori_pose`, `self.open_box_ori_pose`, `self.delta_h`; if `image_obs` calls `self.render()` -> 4x `self._viewer.render(rgb_array, cam_id)` (E:568-572, R:21-50).
7. `self.env_step += 1` (E:493); `terminated = env_step >= 1200` (E:495-496).
8. `render_mode == "human"` -> viewer render (E:498-499).
9. `time.sleep(max(0, 1/self.hz - dt))` with `self.hz = 30` (E:43, E:502) - every step costs >= 33 ms wall time.
10. `_compute_success()` (E:512-564): reads sensors `glass_pos`, `glass_quat`, `glass_joint_0_pos`, `glass_joint_1_pos`, reads `model.body_pos[glass]` (unused) and `model.body_pos[open_box]` (E:525); updates `self._success_trigger_count` (+1 or reset to 0, E:556-561); success iff count >= `self._success_trigger_target` (=50, E:193).
11. `if self.reset_trigger: self.reset()` (E:507-508). `reset_trigger` is False (E:69); only set by `tasks/sim_teleop.py`, not by the RaX path.

## State inventory

### (a) mjData, covered by mj_getState(mjSTATE_INTEGRATION)
| field | where |
|---|---|
| `qpos`, `qvel` | integrated by mj_step (E:489); read by opspace (C:189-190) |
| `act` (empty, na=0) | - |
| `time` | advanced by mj_step |
| `ctrl` | written E:475, E:483 (glass motors `glass_joint_0/1`, glass.xml:48-49, never written -> stay 0) |
| `mocap_pos[0]`, `mocap_quat[0]` | read E:449-450, written E:456-460, read by opspace E:468-469 |
| `qacc_warmstart` | written by mj_step, used by solver next step |
| `qfrc_applied`, `xfrc_applied`, `eq_active` | not touched in step but part of INTEGRATION |

### (a') mjData NOT covered by INTEGRATION but READ before the next mj_step  (CRITICAL)
After `mj_step` (Euler), the derived quantities hold values computed at the PRE-integration state (mj_step = forward at q_t, then integrate to q_{t+1}). The next step's first `opspace` call reads them before any mj_forward:
- `site_xpos`, `site_xmat` (C:156,160,207,218)
- `qM` (C:232), `qfrc_bias` (C:259)
- Jacobian inputs for `mj_jacSite` (C:195): `xpos`, `xmat`, `subtree_com`, `cdof`, ...
- `sensordata` read by `_compute_observation`/`_compute_success` is likewise one physics substep stale relative to qpos.

Measured (scratch check, physics-only replica of step(), 20 warm-up steps, 5-step lookahead, then 5 real steps compared to a no-lookahead reference):
- `mj_setState(INTEGRATION)` only: NOT bit-identical, max |dqpos| = 1.4e-5 after 5 steps.
- `mj_setState(INTEGRATION)` + `mj_forward`: NOT bit-identical, max |dqpos| = 1.7e-7 (derived fields now reflect q_{t+1} instead of q_t).
- 60 derived arrays differ after INTEGRATION restore (site_xpos, qM, qfrc_bias, sensordata, efc_*, qacc, solver_niter, ...).
- Run lookahead on `copy.deepcopy(env._data)` and leave the live MjData untouched: BIT-IDENTICAL qpos and sensordata.

The Python bindings in 3.4.0 have no `mj_copyData`; `mj_copyState` only copies state signatures. A full in-place copy-back is not available (efc_/contact array sizes depend on nefc/ncon). Therefore restore must be "do not mutate the live MjData" rather than "snapshot/restore":
```
live = env._data
env._data = copy.deepcopy(live)   # MjData.__deepcopy__ = full mj_copyData
... run candidate rows ...
env._data = live
```
(`MujocoGymEnv.data` property returns `self._data` (B:67), and step/opspace/_compute_* only use `self._data`, so swapping the attribute redirects all physics.)

### (b) mjModel fields mutated during step
None. step() only reads `model.body_pos` (E:517, E:525) and model constants. Model mutations happen only in `reset()` (body_pos/geom_size table E:357-361, open_box body_pos/quat E:392-393, lights/cam/matid when `randomize` E:236-260, 346-347) and `_randomize_dynamics()` (dof_frictionloss, jnt_stiffness, body_mass E:289-303, called at end of reset when `randomize_dynamics`). Only reachable from step via `reset_trigger` (see (c)). Snapshot of model not required if `reset_trigger` stays False; guard it anyway (assert False during lookahead).

### (c) Python attributes on the env object
| attr | access in step | lookahead handling |
|---|---|---|
| `env_step` | `+= 1` E:493; terminate at >= 1200 E:495 | save/restore int |
| `_success_trigger_count` | inc / zero E:556-561 | save/restore int; lookahead must start from the live value to predict success (needs 50 consecutive frames) |
| `_success_trigger_target` (50) | read E:564 | constant |
| `reset_trigger` | read E:507 -> full `reset()` | must be False; if True a lookahead would consume RNG and mutate model |
| `glass_ori_pose`, `open_box_ori_pose`, `delta_h` | read E:596-598 (obs only) | set at reset, constant during episode |
| `hz` (30), `render_mode`, `image_obs`, `randomize` | read E:498-502, 601-604 | constants |
| `_n_substeps`, `_site_id`, `_panda_dof_ids`, `_panda_ctrl_ids`, `_allegro_ctrl_ids`, `camera_id` | read | constants |
| `_viewer` (gymnasium MujocoRenderer) | `render()` E:571 sets `self._viewer.camera_id` (R:48 path) and its own `viewer`/scene | rendering state only, not physics; last cam is always wrist so idempotent. Holds a reference to the ORIGINAL MjData (`_viewer.data`, and each OffScreenViewer `.data`), so with the swap approach images rendered during lookahead would show the LIVE state, not the hypothetical one. |

Recommendation: during lookahead set `env.image_obs = False` (skip 4 renders/step, also avoids stale-image confusion; no EGL needed) and bypass/zero `time.sleep` (e.g. temporarily set `env.hz = float('inf')`, giving sleep(max(0, 0-dt)) = 0). Restore both after. Neither affects physics.

### (d) RNG use during step
None. step(), opspace, _compute_observation, _compute_success draw no random numbers (`random`, `np.random`, `self._random`/`np.random.RandomState` from B:38 all unused in step). RNG is used only in `reset()` (np.random E:354,375,380,397,403) and its helpers (`random` E:243-259, np.random E:290-301). `time.time()` / `time.sleep` are wall-clock only and do not affect results. Still recommend snapshotting `np.random.get_state()` and `random.getstate()` around lookahead as a cheap guard against `reset_trigger`.

## deepcopy safety
- `copy.deepcopy(env._data)`: safe and is the recommended path (MjData supports `__deepcopy__`; result bound to the same MjModel). Cost: one MjData allocation per lookahead call.
- Do NOT deepcopy the env object or `_viewer`: `_viewer` is a gymnasium MujocoRenderer holding OffScreenViewer(s) with an EGL/GL context (`mujoco.MjrContext`), `MjvScene`, `MjvCamera`; not copyable/picklable and would create GL resources. `_model` (MjModel) is copyable but unnecessary since step does not mutate it.
- `obs` returned by `_compute_observation` contains views into `data.sensordata` slices? No: `tcp_pose` is a concatenation (new array), `allegro_qpos` a new array; but `glass_ori_pose` / `open_box_ori_pose` are the env's own arrays (aliasing; do not mutate them in the tool).

## Minimal correct lookahead for fold_glasses
```
live = env._data
saved = (env.env_step, env._success_trigger_count, env.image_obs, env.hz)
assert not env.reset_trigger
env._data = copy.deepcopy(live); env.image_obs = False; env.hz = float('inf')
try:
    for row in actions: obs, rew, term, trunc, info = env.step(row); read sensors / goals from env._data
finally:
    env._data = live
    env.env_step, env._success_trigger_count, env.image_obs, env.hz = saved
```
Wrapper-level state (DexJoCoOpenPIEnv, _Tap, step counters/histories in services/dexjoco/session.py) is out of scope here and must be handled separately; the wrapper file `dexjoco_openpi_client/dexjoco_openpi_env.py` does not touch `env_step`, `_success_trigger_count`, `reset_trigger` or `np.random`.

Check script: `/tmp/claude-6011310/-home-vawale-my-things-codes-rax/225404c8-1331-4992-bf2b-a931f32452d4/scratchpad/fg_check.py`
