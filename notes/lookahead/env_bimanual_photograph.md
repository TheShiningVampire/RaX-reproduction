# Lookahead state audit: bimanual_photograph

Source: `/home/vawale/my_things/codes/rax/.worktrees/dexjoco-v2/DexJoCo/dexjoco/dexjoco/`
(abbreviated `E` = `sim/envs/panda_bimanual_photograph_env.py`, `O` = `sim/controllers/opspace.py`,
`B` = `sim/mujoco_gym_env.py`, `T` = `tasks/bimanual_photograph/config.py`).
MuJoCo 3.4.0, gymnasium 1.0.0 in `/data/user_data/vawale/rax_repro_v2/runtime/envs/dexjoco`.

## Call chain as RaX runs it

`DexJoCoOpenPIEnv.step` (dexjoco_openpi_client/dexjoco_openpi_env.py:106-124) -> `_Tap.step`
(services/dexjoco/session.py:90) -> `DexjocoObsAdapter` (tasks/obs_adapters.py:8-39, stateless
ObservationWrapper) -> `DualArmPolicyWrapper` (tasks/policy_wrappers.py:36-75, stateless ActionWrapper)
-> `PandaBimanualPhotographGymEnv.step` (E:794-880).
Construction (T:30): `render_mode="rgb_array"`, `hz=30`, `randomize=rand_full`, `seed`, `randomize_dynamics=False`;
`camera_screen_effect` NOT passed -> default False (E:109); `image_obs` default True (E:104).
Not built with `gym.make`, so no TimeLimit / OrderEnforcing / PassiveEnvChecker wrappers (no hidden counters).

## step() inventory

| # | What | file:line | Read/Write | Class |
|---|------|-----------|-----------|-------|
| 1 | `data.mocap_pos/mocap_quat` (both arms) read, then overwritten with action target or old value | E:798-820 | R/W | (a) |
| 2 | `self._n_substeps` (=10) loop | E:822, B:36 | R | const |
| 3 | `data.ctrl[panda ctrl ids]` written each substep with opspace torque | E:835, E:849 | W | (a) |
| 4 | `data.ctrl[allegro ids]` written ONLY if `allegro_angles is not None` (zero action keeps previous ctrl) | E:851-852 | W (cond.) | (a) - ctrl is carried state |
| 5 | opspace reads `data.qpos[dof]`, `data.qvel[dof]` | O:109-110 | R | (a) |
| 6 | opspace reads DERIVED fields: `site_xpos`, `site_xmat` (O:127,138), `mj_jacSite` (O:115, uses xpos/xanchor/cdof...), `qM` via `mj_fullM` (O:152), `qfrc_bias` (O:179) | O:115-179 | R | NOT in mjSTATE_INTEGRATION - see Restore section |
| 7 | `mujoco.mj_step` x10: integrates qpos, qvel, act, qacc_warmstart, time; recomputes all derived fields/contacts/sensors | E:854 | R/W | (a) + derived |
| 8 | `_compute_success_metrics`: reads `geom_xpos/geom_xmat` (target region, camera_axis_z), `site_xpos` (view site), `data.ncon`, `data.contact[i].geom1/geom2` | E:882-927 | R | derived (post-step, freshly computed) |
| 9 | `self._latest_shutter_pressed = metrics["shutter_pressed"]` | E:857 | W | (c) |
| 10 | `_compute_observation`: sensors `franka/flange_pos/quat_*`, `allegro_*/..._pos` (sensordata) | E:949-972 | R | derived |
| 11 | obs state also returns `self.camera_ori_pose`, `self.logo_ori_pose`, `self.delta_h` (set only in reset E:722,733,748; returned by reference, not mutated in step) | E:981-983 | R | (c) read-only during step |
| 12 | `render()` (image_obs=True): `_update_camera_screen_texture` returns immediately because `_camera_screen_effect` False | E:935, E:539 | - | - |
| 13 | `_set_offscreen_geom_group_visibility(5, False)` writes renderer `vopt.geomgroup[5]=0` (idempotent, renderer object not mjModel) | E:937, E:484-512 | W | renderer state (idempotent) |
| 14 | `self._viewer.render("rgb_array", camera_id)` x3 cameras (back, handcam_rgb_left/right); gymnasium OffScreenViewer only calls `mjv_updateScene` (reads mjData, writes mjvScene) | E:939-940; gymnasium mujoco_rendering.py:389 | R data / W scene | renderer, no physics effect |
| 15 | `self.env_step += 1` | E:859 | W | (c) |
| 16 | `terminated = env_step >= 1000 or success` | E:861 | R | (c) |
| 17 | `render_mode=="human"` branch (texture update, human geomgroup, viewer.render) | E:863-872 | skipped in RaX (rgb_array) | - |
| 18 | `time.time()` + `time.sleep(max(0, 1/hz - dt))` (hz=30 -> >=33 ms per step) | E:795, E:874-875 | wall clock | not state, but lookahead cost |
| 19 | `self._random` (np.random.RandomState) in base class | B:38 | never used in step | (d) none |

### Only-if-enabled (not active in RaX config)
- `camera_screen_effect=True`: `_update_camera_screen_texture` mutates `self._captured_image`, `self._capture_flash_frame` (E:556-565) (c), reads `self._latest_shutter_pressed` (E:554), and writes `model.tex_data[adr:adr+n]` (E:609) (b) plus GPU upload `mjr_uploadTexture` (E:642). It also renders the `cam_pos_z` camera. If ever enabled, all three must be snapshotted and the texture re-uploaded after restore.
- `render_mode="human"`: passive-viewer patch writes `model.geom_group[target_region]` (E:73) (b); `_set_human_geom_group_visibility` writes viewer opt (E:478).

## Classification summary

(a) mjData covered by `mj_getState(mjSTATE_INTEGRATION)`: qpos, qvel, act (na=0), qacc_warmstart, ctrl (both panda and allegro; allegro ctrl is genuinely carried over on zero-action rows), mocap_pos/mocap_quat (nmocap=2), qfrc_applied, xfrc_applied, eq_active (neq=0), userdata (0), plugin (0), time. State size 858 doubles.

(b) mjModel fields mutated during step: NONE in the RaX configuration (rgb_array, camera_screen_effect False). Model fields mutated in `reset()` only (table body_pos E:725, table-leg geom_size E:727, logo geom_pos/quat/size E:734-736, target-region geom_pos/size E:739-742, lights/cam_pos/cam_quat/geom_matid under rand_full E:649-667,711-712, body_mass if randomize_dynamics E:774) are constant across a lookahead. Caveat: `tex_data` if camera_screen_effect is ever turned on.

(c) Python attributes mutated by step: `self.env_step` (E:859), `self._latest_shutter_pressed` (E:857). (Plus `_captured_image`, `_capture_flash_frame` only with camera_screen_effect.) Outside the raw env, if the lookahead goes through the outer layers: `DexJoCoOpenPIEnv._done/_success/obs/_raw_obs` (dexjoco_openpi_env.py:119-123), `last_stay_state` (only on stay), `_Tap.last_obs/last_info/ever_true/sequences` (session.py:91-98), and the session's own counters/video. Recommended: call the gym chain below the Tap (`tap._env.step(env_action)`, i.e. DexjocoObsAdapter, whose wrappers are stateless) with an action produced by `DexJoCoOpenPIEnv._process_action`, so wrapper/Tap/session state is never touched; still snapshot/restore `env_step` and `_latest_shutter_pressed` on the raw env.

(d) RNG during step: none. No `np.random`, `random`, `self._random`, or `np_random` call anywhere in step / opspace / success / observation / render paths. All RNG use (np.random.uniform E:722,729,744,773; random.* E:653-671) is in reset(). MuJoCo itself is deterministic (sensor noise fields are not applied by the engine). So RNG state need not be saved, but saving `np.random.get_state()` / `random.getstate()` is cheap insurance.

## Restore: mj_getState(INTEGRATION) alone is NOT enough (verified)

Reason: after `mj_step`, derived quantities in mjData (site_xpos/xmat, qM, qfrc_bias, jacobian inputs, sensordata, geom_xpos, contacts) are those computed at the START of the last substep (pre-integration q), while qpos/qvel are post-integration. The first opspace call of the next real step (O:115-179) reads those stale derived fields, so they are part of the effective state.

CPU-only test (`/tmp/claude-6011310/.../scratchpad/la_photo.py`; loads the photograph XML, replicates the step loop with the real `opspace`, 5 warm steps, 10-step lookahead, restore, then 4 real steps compared against a never-looked-ahead reference over qpos, qvel, ctrl, sensordata, geom_xpos, qacc_warmstart, ncon):

| restore method | max abs diff after 4 real steps | bit-identical |
|---|---|---|
| `mj_setState(INTEGRATION)` only | 6.4e-3 | no |
| `mj_setState(INTEGRATION)` + `mj_forward` | 1.2e-5 | no (forward recomputes kinematics at post-integration q) |
| in-place copy of every ndarray attribute of a `copy.copy(data)` backup (np.copyto; settable int/float scalars via setattr) | 0.0 | yes |
| same + `mj_setState` | 0.0 | yes |

Notes on the in-place field copy: arena-sized arrays whose length changed (efc_*, iefc_*, island_*, map_efc2iefc, iLDiagInv, iacc...) cannot be np.copyto'd and were skipped, and `data.contact` is an `_MjContactList` (not an ndarray) so contact pos was NOT restored (geom1 matched by chance). These are all recomputed inside the next `mj_step` before use, so the real step is still bit-identical, but any reader that inspects contacts/efc between restore and the next step (e.g. a call to `_compute_success_metrics()` or an object-state tool reading `data.contact`) would see lookahead residue. ncon/nefc scalars were restored by setattr.

Cleanest alternative (strictly safer): never touch the live MjData. For the lookahead, `scratch = copy.copy(raw._data)` (full mj_copyData incl. arena/contacts), temporarily point `raw._data`, `raw._viewer.data` and every `raw._viewer._viewers[*].data` at `scratch` (or set `raw.image_obs=False` to skip rendering entirely), run rows, read state from `scratch`, then swap the original object back. The live data is untouched, so bit-identity is trivial. `raw.data`/`raw.model` are properties over `_data`/`_model` (B:62-68). Check nothing else holds a reference to the old `_data` during the swap (session `_calibration` reads `raw._data` only at reset).

## Deepcopy hazards (do not `copy.deepcopy(env)`)

- `self._viewer`: gymnasium `MujocoRenderer` holding `OffScreenViewer`s with EGL/OSMesa GL contexts, `mjrContext` (`con`), `mjvScene`, `mjvOption` (E:235, rendering.py). Not deepcopy-safe; must be shared, not copied.
- `self._model` / `self._data`: MjModel/MjData support `copy.copy`/deepcopy in bindings, but the renderer and module global `_PASSIVE_MODEL_TARGET_REGION` (E:31-35, keyed by `id(model)`) hold the original objects; a copied model would not be registered.
- Module-level monkeypatch of `mujoco.viewer.launch_passive` (E:38-89) - global, irrelevant to rgb_array.
- `_camera_params` (np.load'ed array, E:267), id arrays, `_texture_names`: read-only, safe.
- Snapshot only: `env_step` (int), `_latest_shutter_pressed` (bool), and (if enabled) `_captured_image.copy()`, `_capture_flash_frame`, `model.tex_data` slice.

## Practical notes for dexjoco_lookahead
- Cost per lookahead row: 10 substeps x 2 opspace calls + 3 offscreen renders (640x640 default render_spec) + `time.sleep` padding to 1/30 s. Setting `raw.image_obs=False` during lookahead (attribute read at E:974) removes rendering; the sleep remains unless `raw.hz` is temporarily raised (E:875) - both are plain Python attrs to restore afterwards.
- Termination inside lookahead: `env_step` increments, so a lookahead near step 1000 may report `terminated` from the counter; report `success` separately.
- Goal/object state to read after rows: `metrics` dict from `_compute_success_metrics()` (region_pass, angle_pass, shutter_pressed, radial_dist, region_height_dist, view_angle_deg, shutter_contact_count) and camera pose from `data.jnt("camera_root").qpos`.
