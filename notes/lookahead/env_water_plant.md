# water_plant: state touched by step(), for dexjoco_lookahead

Source root: `/home/vawale/my_things/codes/rax/.worktrees/dexjoco-v2/DexJoCo/dexjoco/dexjoco`
(`E` = `sim/envs/panda_water_plant_env.py`, `B` = `sim/mujoco_gym_env.py`,
`C` = `sim/controllers/opspace.py`, `T` = `tasks/...`). mujoco 3.4.0.

## Wrapper stack (what `session.py` actually steps)

`DexJoCoOpenPIEnv` -> `_Tap` (session.py:65) -> `DexjocoObsAdapter` (T/obs_adapters.py:8)
-> `SingleArmPolicyWrapper` (T/policy_wrappers.py:5) -> `PandaWaterPlantGymEnv`.
Built by `T/water_plant/config.py:32-43` with `hz=30`, no `gym.make`, so there is **no
TimeLimit / OrderEnforcing / PassiveEnvChecker** wrapper. The two gym wrappers have no state:
`action()` is a dtype/shape check and `observation()` flattens the state. Stepping after
`terminated` is not blocked.

## Call graph of `step()` (E:475-555)

1. E:478-488: split the action. If xyz and quat are not both ~0, write `data.mocap_pos[0]` /
   `data.mocap_quat[0]`.
2. E:490-507: `_n_substeps` (=10, B:36) times: `opspace(...)` (C:59-180) -> `data.ctrl[panda]=tau`,
   `data.ctrl[allegro]=angles`, `mj_step`.
3. E:510-531: read the trigger sensor, update the trigger latch and cone counter, write
   `model.geom_rgba[cone_visual][3]`.
4. E:533 `_compute_observation()` (E:589-617) -> `render()` (E:577-586) -> offscreen renderer.
5. E:535-536 `env_step += 1`, terminated at 1000.
6. E:539-547: only when `render_mode=="human"` (the harness uses `rgb_array`): geom_group swap.
7. E:549-550 `time.sleep(max(0, 1/hz - dt))`. That is a wall-clock throttle of about 33 ms per step.
8. E:551 `_compute_success()` (E:557-575).

## (a) mjData fields covered by `mj_getState(mjSTATE_INTEGRATION)`

| State | Where | Notes |
|---|---|---|
| `qpos, qvel, act, qacc_warmstart, time` | `mj_step` E:507 | integrated |
| `ctrl` (panda 7, allegro 16) | written E:503, E:505 | |
| `mocap_pos[0], mocap_quat[0]` | written E:487-488, read E:496-497 | **the "cached target"**: a zero arm action holds the previous target, so this must be restored |
| `qfrc_applied, xfrc_applied, eq_active, userdata, plugin_state` | not written by step | nuserdata=0, nplugin=0, neq=0 |

## (a') mjData fields NOT in INTEGRATION state but READ before the next `mj_step` recomputes them

These are the main problem. After `mj_step`, the derived fields hold values from the forward pass
at the **pre-integration** state. `opspace` on the first substep of the *next* step reads these
stale values:

- `data.site_xpos[site], data.site_xmat[site]`: C:76, C:80, C:127, C:138
- `data.qM`: C:152 (`mj_fullM`)
- `data.qfrc_bias`: C:179 (gravity comp)
- `data.cdof, data.subtree_com`: read inside `mj_jacSite` C:115

Observation and success code also read derived fields after the substeps. Those are recomputed by
the step itself, but the harness may read them right after a restore without stepping:
- `sensordata`: E:510 (`spray_joint_0_pos`), E:593-600 (flange pos/quat, allegro joints)
- `site_xpos[ref_point]`: E:559; `xpos[plant]`: E:560

**Measured (CPU-only, same MjModel and the same step logic copied from E:478-507, 20 warm-up
steps, 15 lookahead steps with different actions, then 15 real steps compared bitwise against a
never-looked-ahead reference over qpos, qvel, act, sensordata, site_xpos, qacc_warmstart and
time):**
- `mj_setState(INTEGRATION)` only: **NOT identical** (max diff 1.9e-3)
- `mj_setState(INTEGRATION)` + `mj_forward`: **NOT identical** (3.8e-5). `mj_forward` computes
  the derived fields at the post-integration qpos, but the cached ones came from the
  pre-integration qpos.
- `mj_setState(INTEGRATION)` + copying the derived set `{cdof, qM, qfrc_bias, site_xmat, site_xpos, subtree_com}`:
  identical. This was the greedy-minimal set.
- `mj_setState(INTEGRATION)` + copying all 140 fixed-size ndarray fields of MjData (all public
  ndarray attrs except `efc_*` and any field whose shape depends on ncon/nefc): **identical**.
- Lookahead on a scratch `copy.copy(env._data)`, live data untouched: **identical**.

Recommendation: snapshot = `copy.copy(env._data)` (a full mj_copyData). Restore in place, because
the renderer holds a reference to the `_data` object: `mj_setState(INTEGRATION)` from the
snapshot, then copy every fixed-size ndarray field and `time`. Skip `efc_*` and `contact`:
their size depends on `nefc/ncon`, and the next `mj_step` recomputes them before reading.
Copying them blindly can raise a shape mismatch when the contact count differs. A plain
`mj_forward` is NOT a substitute. Script:
`/tmp/claude-6011310/-home-vawale-my-things-codes-rax/225404c8-1331-4992-bf2b-a931f32452d4/scratchpad/wp_check.py`.

## (b) mjModel fields mutated during step

| Field | Where | Effect |
|---|---|---|
| `model.geom_rgba[cone_visual, 3]` (alpha 0.5 or 0.0) | E:528-531 | visual only: it appears in rendered images, not physics. Snapshot `geom_rgba[cone_id]` (or all of `geom_rgba`) and restore it |
| `model.geom_group[group5 ids]` 5->0->5 | E:541-547 | only when `render_mode=="human"`, and restored in `finally`. Not reached in the harness |

Model fields mutated only in `reset()`/randomizers, never in step: `body_pos` (table, plant)
E:404,E:435, `geom_size` legs E:409, `geom_rgba` cone E:415, `light_pos/dir/diffuse`, `vis.headlight`
E:284-295, `geom_matid` E:302, `cam_pos/cam_quat` E:392-393, `dof_frictionloss/jnt_stiffness/body_mass`
E:339-342. Note that E:419-421 and E:431-433 write in place through the `model.body("...").pos` views,
so `body_pos` for `link_2` and `plant` is changed at reset. That is still reset-only.

## (c) Python attributes on the env objects

Raw env (`PandaWaterPlantGymEnv`), mutated in step:
- `self._trigger_pulled` (bool latch): read E:512, written E:514/E:516, read E:519, E:567, E:569
- `self._cone_alpha_counter` (int): set E:520, decremented E:524
- `self._success_counter` (int, success needs 30 consecutive steps): E:570/E:572, read E:574
- `self.env_step` (int, termination at 1000): E:535-536

Read-only in step, so no restore is needed (they are reset-only): `_spray_ori_pose`,
`_plant_ori_pose` (the same array objects are put into obs E:612-613, so never mutate obs in
place), `delta_h` E:614, `image_obs`, `randomize`, `render_mode`, `hz`, `_n_substeps`, the id
caches, `_group5_geom_ids`, `_camera_params`.

Wrapper and harness objects that a real step mutates and lookahead must not leave changed, if the
lookahead goes through them:
- `DexJoCoOpenPIEnv`: `obs`, `_raw_obs`, `_done`, `_success` (dexjoco_openpi_env.py:119-123), and
  `last_stay_state` (:137, only via stay()).
- `_Tap`: `last_obs`, `last_info`, `ever_true`, `sequences` (session.py:90-99).
- Better: lookahead calls the **raw env** `.step` (unwrap via `.env` / `.unwrapped`), feeding
  the 23-d quaternion action. That bypasses all of the above. If the action is a rotvec, convert
  it with `_process_action`, which is pure.

## (d) RNG during step

**None.** step, opspace, `_compute_observation` and `_compute_success` make no `np.random.*`,
`random.*`, `self._random` (B:38) or `self.np_random` calls. All RNG use is in `reset()` and the
randomizers (E:288-306, E:329-333, E:400, E:418, E:430). The dm_robotics transformations used by
opspace are deterministic. No RNG snapshot is needed for water_plant, but it is still cheap
insurance across tasks.

## Other hazards

- **time.sleep throttle** E:549-550: every lookahead step sleeps up to 1/30 s. 100 rows take
  about 3.3 s or more. Patching `time.sleep` in the module namespace (`panda_water_plant_env.time`)
  during lookahead is safe: `time` is not otherwise used in state.
- **Rendering cost**: `_compute_observation` renders 2 cameras every step when `image_obs`
  (E:602-607). For a state-only lookahead, set `env.image_obs=False` temporarily. It is a plain
  attribute, read only at E:602, and must be restored. Only do this when calling the raw env,
  because the wrapper `_process_obs` indexes the image keys. Rendering does not mutate mjData
  (`mjv_updateScene` only reads it), but the renderer's GL scene buffer will hold
  lookahead frames until the next real render. That is harmless.
- **deepcopy unsafe**: `env._mj_viewer` (gymnasium `MujocoRenderer` holding an EGL/GL context,
  E:156) and `B._viewer` (`mujoco.Renderer`, which stays None because E:577 overrides render). Do not
  deepcopy the env or the wrappers. `MjData` copies fine with `copy.copy`. Do not swap
  `env._data` for a scratch copy unless the renderer's `.data` (and its viewers' `.data`) is swapped
  too, otherwise lookahead images show the live state.
- `opspace` uses `np.linalg.inv/pinv/det`, which are deterministic on the same process and BLAS
  thread count.
