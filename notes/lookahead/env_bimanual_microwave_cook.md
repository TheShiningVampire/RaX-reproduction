# Lookahead state audit: bimanual_microwave_cook

Source root: `/home/vawale/my_things/codes/rax/.worktrees/dexjoco-v2/DexJoCo/dexjoco/dexjoco/`
(paths below are relative to it). `ENV` = `sim/envs/panda_bimanual_microwave_cook_env.py`.
Versions in the runtime env: mujoco 3.4.0, gymnasium 1.0.0.

Call chain from the harness: `DexJoCoOpenPIEnv.step` (dexjoco_openpi_client/dexjoco_openpi_env.py:106)
-> `DexjocoObsAdapter` (tasks/obs_adapters.py:8, stateless) -> `DualArmPolicyWrapper.action`
(tasks/policy_wrappers.py:60, stateless) -> `PandaBimanualMicrowaveCookGymEnv.step` (ENV:455).

## Headline (verified empirically, CPU-only, real XML + real opspace)

**Restoring only `mj_setState(mjSTATE_INTEGRATION)` is NOT enough.** The first substep of the
next real `step()` calls `opspace()` *before* `mj_step`, so it reads derived mjData fields left over
from the last `mj_step` (site_xpos, site_xmat, qM, qfrc_bias, and everything `mj_jacSite` uses).
After a lookahead those are the lookahead's values. `mj_forward` after setState doesn't fix it either,
because the live values are the stale *pre-integration* kinematics of the last substep, not
kinematics at the current qpos.

Test: scratchpad `la_mw/t2.py` (15 warm steps, 10 lookahead steps, then 5 real steps, comparing
qpos, sensordata and ctrl to a run with no lookahead):

| restore method | result |
|---|---|
| clone vs clone (determinism control) | bit-identical |
| A: `mj_setState(INTEGRATION)` only | DIFF, max abs 0.225 |
| B: `mj_setState(INTEGRATION)` + `mj_forward` | DIFF, max abs 4.7e-3 |
| A2: `mj_copyState(FULLPHYSICS|CTRL|WARMSTART|MOCAP)` + setState | DIFF, max abs 0.225 |
| G: setState(INTEGRATION) + `np.copyto` every public ndarray field of MjData from a `copy.copy(d)` snapshot | **bit-identical** |
| E: run the lookahead on `copy.copy(d)`, leave the original MjData untouched | **bit-identical** |

`mujoco.mj_copyData` is not exposed in the Python bindings (3.4.0); `copy.copy(MjData)` is
(a full clone with derived fields and contacts that shares the same MjModel).

Recommended: **E (swap a clone in)**. Set `raw._data = copy.copy(live)` (and point the renderer's
`data` refs at it if rendering during lookahead), run the rows, read state, then set `raw._data = live`
again and restore the Python attributes. The live MjData is never written. G also works, but note
that it does not restore `d.ncon`/`d.contact` (they aren't ndarrays); this doesn't matter for the next
`mj_step`, but code that reads contacts right after the restore and before stepping
(`_geom_in_contact`, ENV:420) would see the lookahead's contacts.

## (a) mjData covered by mjSTATE_INTEGRATION

In 3.4.0 INTEGRATION = TIME, QPOS, QVEL, ACT, WARMSTART, CTRL, QFRC_APPLIED, XFRC_APPLIED,
EQ_ACTIVE, MOCAP_POS, MOCAP_QUAT, USERDATA, PLUGIN (checked at runtime). Model: na=0, nuserdata=0,
neq=0, nplugin=0, nmocap=2, integrator=Euler, sleep disabled, `noslip_iterations=5` (xml line 7).

- `d.mocap_pos[0/1]`, `d.mocap_quat[0/1]`: read at ENV:492-495 and written at ENV:505-506 / 509-510
  (right) and 514-515 / 518-519 (left). They persist across steps; a zero action keeps them.
- `d.ctrl[panda_right_ctrl_ids]` and `d.ctrl[panda_left_ctrl_ids]`: written every substep (ENV:539, 553).
- `d.ctrl[allegro_ctrl_ids]`: written only when the action isn't zero (ENV:558-560). **These persist
  across steps** (a zero action, ENV:489, reuses the last hand ctrl), so ctrl must be restored.
- `d.qpos`, `d.qvel`, `d.time`, `d.qacc_warmstart`: advanced by `mj_step` (ENV:566). opspace reads
  qpos/qvel (opspace.py:109-110).

## (a') Derived mjData fields NOT in INTEGRATION but read before or after stepping

These are the reason INTEGRATION alone fails. All live in mjData, so E and G cover them.

- opspace, before the first `mj_step` of a step: `site_xpos`/`site_xmat` (opspace.py:127, 138),
  `mj_jacSite` (opspace.py:115, uses xpos/xmat/subtree_com/cdof), `qM` through `mj_fullM`
  (opspace.py:152), `qfrc_bias` (opspace.py:179).
- `_compute_observation` (ENV:618), after stepping: `d.sensordata` for flange pos/quat/vel and
  allegro joint sensors (ENV:622-650).
- `_compute_success` (ENV:592): `d.joint("microjoint").qpos` (ENV:594; this one is in qpos);
  `hot_dog_inside_microwave` reads `sensor("hot_dog_pos")` and `body("microwave_object").xpos/xmat`
  (ENV:701-702, 708); `_geom_in_contact("start_button")` reads `d.ncon` and `d.contact[i]`
  (ENV:425-451).
- Note: after `mj_step` these derived values are the *pre-integration* kinematics of the last
  substep. So success/obs are evaluated one physics substep behind qpos. That's existing env behaviour,
  but a restore has to reproduce it exactly, which means copying the fields rather than recomputing them.

## (b) mjModel fields mutated during step

**None.** `step()`, `opspace()`, `_compute_observation`, `_compute_success` and the renderer only read
the model: `opt.timestep`; `site("int_p0/px/py/pz").pos` (ENV:714-717); ids. `mj_step` doesn't write
the model.

Model *is* mutated in `reset()` (only snapshot this if a lookahead could ever trigger a reset, which it must not):
table `body_pos` (ENV:326-328, in-place view), leg `geom_pos`/`geom_size` (ENV:342-343),
microwave `body_pos`/`body_quat` (ENV:365-366); with `randomize`: `light_pos/dir/diffuse`,
`vis.headlight` (ENV:255-266), `geom_matid` (ENV:273), `cam_pos/cam_quat` (ENV:316-317); with
`randomize_dynamics`: `dof_frictionloss` (ENV:394), `body_mass` (ENV:397, 399). These stay
constant during an episode. The restorer in tasks/state_restorers.py:193-201 also writes model fields.

## (c) Python attributes

Mutated in `step()`:
- `self.env_step += 1` (ENV:570). It drives `terminated = env_step >= 1100` (ENV:572-573). **Must
  be saved and restored.**
- Local `start_time`/`dt` with `time.sleep(max(0, 1/self.hz - dt))` (ENV:457, 583-584). This isn't
  state, but every lookahead row costs at least 33 ms of wall clock (hz is hard-coded to 30 at ENV:44).

Read only in step: `_n_substeps` (=10, base mujoco_gym_env.py:36), `_site_*_id`, `_panda_*_dof_ids`,
`_panda_*_ctrl_ids`, `_allegro_ctrl_ids`, `render_mode`, `image_obs`, `randomize`, `camera_id`,
`hz`, `_hot_dog_ori_pose`, `_microwave_ori_pose`, `delta_h` (ENV:664-666).
- Caveat for goal readers: `obs["state"]["hot_dog_ori_pose"]` and `["microwave_ori_pose"]` are the
  **reset-time** poses held by reference (ENV:664-665), not live state. Read live object state from
  `sensor("hot_dog_pos")`, `body(...).xpos/xquat` and `joint("microjoint").qpos`. The obs dict
  aliases those env arrays; the ObsAdapter concatenates (copies) them, but a raw consumer that
  mutated them would corrupt the env.
- `self.intervened` (ENV:70) is never touched in step.

Wrapper and harness layers (stateful, must be saved and restored if lookahead goes through them):
- `DexJoCoOpenPIEnv`: `_done` / `_success` (dexjoco_openpi_env.py:119-120), `obs` (:123),
  `_raw_obs` (:122, :229), `last_stay_state` (:137, set by `stay()`).
- The RaX `_Tap` in services/dexjoco/session.py and any frame or video recorder: check that
  separately (not audited here).
- `DualArmPolicyWrapper` and `DexjocoObsAdapter`: no state.

Renderer (`image_obs=True` by default, so every step renders 3 cameras, ENV:653-659 and 610-614):
- gymnasium 1.0.0 `MujocoRenderer.render(render_mode)` doesn't take `camera_id`, so the DexJoCo
  wrapper falls back and sets `self._viewer.camera_id = camera_id` (rendering.py:33-50). The
  OffScreenViewer's `cam.type`/`cam.fixedcamid` are also set on every call (gymnasium
  mujoco_rendering.py:210-215). These are re-set on every render, so they don't affect physics or later
  frames. `_get_viewer` caches `self.viewer`. GPU framebuffer contents change.
- `render_mode == "human"` would push lookahead frames to a window (ENV:576-578). The harness uses
  rgb_array.
- `mjv_updateScene` only reads mjData.

## (d) RNG use during step

**None.** `step()` and its helpers make no `np.random`, `random`, `self._random` or `np_random` draws.
RNG use is limited to `__init__` (`random.seed`, `np.random.seed`, ENV:59-60;
`np.random.RandomState(seed)` at mujoco_gym_env.py:38, never used) and `reset()`
(`np.random.uniform` at ENV:324, 349, 354, 392, 396, 398; `random.*` at ENV:259-266, 271, 277).
The physics has no noise. A lookahead that doesn't call reset leaves the global RNG streams
untouched, so later resets are unaffected.

## Deepcopy hazards

- `self._viewer`: a `MujocoRenderer` holding `OffScreenViewer`s with an `mjrContext` and an EGL GL
  context, plus `__del__ -> free()` (gymnasium mujoco_rendering.py:200). **Never deepcopy it** (or the
  whole env): a copied context that later frees itself can tear down the live context. If you
  swap `_data`, also update `self._viewer.data` and each `self._viewer._viewers[k].data` (they keep
  their own refs), or skip rendering during lookahead.
- `self._model` (MjModel): don't copy it. Share it; nothing in step mutates it.
- `self._data` (MjData): use `copy.copy(d)`. It is a full native clone that shares the model and is verified
  bit-exact. Don't hold `d.sensor(...).data` or `d.mocap_pos[i]` views across a swap, because they point
  into the old buffer.
- The gym `action_space`/`observation_space` carry their own lazily created `np_random`. They aren't
  used in step, so leave them alone.

## Minimal lookahead recipe for this env

```
raw = env.unwrapped (PandaBimanualMicrowaveCookGymEnv); live = raw._data
saved = dict(env_step=raw.env_step)   # plus wrapper _done/_success/obs/_raw_obs/last_stay_state, _Tap
raw._data = copy.copy(live)           # (+ renderer data refs, or image_obs=False / skip render)
for row in actions: wrapper_stack.step(row); read object state from raw._data
raw._data = live; restore saved attrs (and renderer refs)
```
Avoiding the 33 ms per-step sleep and the 3 renders per step would mean replicating ENV:491-566 in the
harness, which risks drift if upstream changes. Otherwise accept roughly 40-60 ms per row.
