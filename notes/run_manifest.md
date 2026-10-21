# RaX Hanoi reproduction: file manifest

Root: `$ROOT/`. Code: `~/my_things/codes/rax/.worktrees/dexjoco` (branch `repro/dexjoco`
tracking `origin/dexjoco/native` @ bcd748c). Upstream DexJoCo @ 8d23b0f at `DexJoCo/` (unmodified).

## Phase 0: setup (2026-10-19)

| What | Path | Notes |
|---|---|---|
| Runtime root | `runtime/` (`RAX_RUNTIME_ROOT`) | host env (Py3.12), dexjoco env (Py3.11, MuJoCo 3.4.0) |
| Setup job log | `logs/10861456.out` | bootstrap, envs, doctor, unit tests |
| GPU allocation | job 10861458 (katef, RTX 6000 Ada, driver 610.43) | attach: `srun --jobid=10861458 --overlap` |
| Demo replay log | `logs/demos_hanoi.log` | 8 candidates all replay successfully; 2 excluded as overlapping formal layouts; 3 kept as experts |
| Demos | `runtime/reference-demos/dexjoco/bimanual_hanoi/{experts,manifest.json}` | kept demos sit 3.0–3.5 mm from the nearest formal layout (the scene distribution is tiny) |
| Simulator doctor | `scripts/dexjoco_doctor.py --gpu 0 --task bimanual_hanoi` | ego + both wrist cameras render, depth valid, 3/3 episodes deterministic |

### Deviations from the authors' tested setup
- System bubblewrap 0.6.3 lacks `--size` (12 sandbox tests failed). Installed conda-forge bubblewrap 0.13.1 and socat
  into `runtime/envs/host`; `scripts/host_env.sh` puts it first on PATH. After that: 791 pass, 1 fail
  (`test_runaway_output_stops_the_controller`, the output-flood guard; runtime is on NFS). Not on the Hanoi path.
- Claude Code 2.1.303 (authors tested 2.1.296).
- No OpenRouter key, so `gemini_generate` answers "not configured" (paper: Gemini available, $10 cap).
- Provider `anthropic` with an API key (key file `~/.config/rax/anthropic_api_key`, mode 600).

## Prompts (Gate 2: verified)

| What | Path | Status |
|---|---|---|
| Golden check, all cases | `render_workspaces.py --check local_tests/goldens/workspaces.json` | **identical** (byte for byte) |
| Rendered Hanoi workspace (golden case, codex, no demos) | `prompts/golden_hanoi_v1/dexjoco/auto-research/exploration-bimanual/rgbd/env1-sub0/workspace/` | START_PROMPT, AGENTS.md (117 lines), TASK.md, MCP_SESSION.md, MCP_CONTRACT.json, 24 skill files |
| Real session workspace | (to add at launch) `runtime/auto-research/<id>/agent-workspace/` | diff against the golden render |

## Hanoi scene variation (upstream `dexjoco/sim/envs/panda_bimanual_hanoi_env.py`)
- Nominal (`rand_obj`): base x ~ U[-0.25, -0.20] m (5 cm), y fixed; table height +U[0, 0.05] m; tower start state
  fixed (`_HANOI_RESET_STATES[2]`, random choice commented out at line 361).
- `rand_full` (`bimanual_hanoi_random`): + light pos ±0.3, dir ±0.4, diffuse U[0.3, 0.8], headlight ambient/diffuse;
  camera from preset `random_cameras.npy`; random table texture.
- `randomize_dynamics` (RaX passes False): disk mass ×U[0.75, 1.25]. No friction randomization.

## Their published Hanoi material
- Project page case study: `https://robot-agent-exploration.com/` → `assets/vid/hanoi/hanoi_s01..08.mp4`
  (exploration chapters), `hanoi_p01..08.mp4` (program on formal layout 40); condensed controller excerpt in
  `assets/js/simcases.js` (copy at session scratchpad `projjs/simcases.js`).

## Session 1 (launched 2026-10-19 23:18 EDT)

| What | Path | Notes |
|---|---|---|
| Session dir (harness) | `runtime/auto-research/20261020T031742Z_f1e2aa9d11/` | operator-input.json, state.json, mcp.jsonl, claude-home/ (transcripts), agent-workspace/ (code, memory), native/results/*/sim/ (sensors.mp4 per episode), bundles/, formal-scores.json |
| Config | budget 8, Claude Code + Opus 5.5 xhigh, provider anthropic, rgbd, 3 terminal-state images, 150 formal episodes x 4 workers, formal_eval_seed 1, no Gemini, no subagents, task_rules public | |
| Launcher log | `session1/launcher.out` | |
| Spend + progress timeline | `session1/timeline.jsonl` (one row per minute) | written by `tools/watch_session.py`, $60 cap enforced via the harness stop script; raised to $90 at 00:2x EDT on 10-20 (user request) |
| Workspace the agent received | `session1/deployed_workspace/` | diff vs golden render: only the demonstration blocks (in-context-action-learning skill, TASK.md "Visual demonstration", AGENTS.md step 1, experience-memory provenance, manual-robot-control) and Claude-vs-Codex blocks (CLAUDE.md = `@AGENTS.md`, gemini api.md drops the Codex `view_image` note). No other differences. |

## Session 1 result
- Formal: 82/150 = 54.7% (seeds 56/54/54%, std 0.9 pt). Paper: 100% at budget 8. Spend $34.08; agent 23:18-01:55 EDT.
- Failures by last stage: grasp 46, lift 15, check 7. No dependence on base x or table height (40-69% in every 1 cm bin).
- Parsed per-run table: `session1/runs_table.json` (`tools/runs_table.py`).
- GPU job 10861458 sat idle 03:19-11:02 after the eval (should have been released) and hit its time limit.

## Session 2 (continuation / adaptation, launched 2026-10-20 14:01 EDT) - DEVIATION from paper protocol
| What | Path | Notes |
|---|---|---|
| Session dir | `runtime/auto-research/20261020T180046Z_b52a07ed8c/` | `--adaptation-source` session 1, `--transfer-parts memory,code`, `--adaptation-context compact`, 6 episodes, **exploration seeds 8-13** (new layouts) |
| GPU | job 10867474, babel-z9-16, RTX PRO 6000 Blackwell (authors' tested GPU) | |
| Timeline / watcher | `session2b/timeline.jsonl` | cost there INCLUDES session 1's $34.08 (carried transcripts); cap $89 total |
| Aborted attempt | `runtime/auto-research/20261020T175803Z_f5834fd49b/` | stopped at $0: default seeds 0-5 repeated session 1's layouts |

## Session 2 result and perturbations
- Session 2 submitted bundle `c8712bc7f03f4abf8d6a6fab4c00aae5` (2/2 rehearsals succeeded). Formal: see `runtime/auto-research/20261020T180046Z_b52a07ed8c/formal-scores.json`.
- Perturbation switch (reproduction-only patch, branch `repro/dexjoco`, `services/dexjoco/session.py`): `RAX_PERTURB=rand_full` turns on the official visual randomization (camera viewpoint from preset list, lighting, table texture) on the nominal task and presents the moved camera under its nominal key `ego` (calibration stays correct: camera ids are positional). `RAX_PERTURB=mass` turns on the official disk-mass randomization (x U[0.75, 1.25]). Unset = unchanged behaviour. Checked with `dexjoco_doctor.py` (frame confirms moved camera).
- Batches (same 150 official layouts as formal, eval seed 1, 6 workers, no agent, no API): `runtime/auto-research/perturb_rand_full_s2/`, `runtime/auto-research/perturb_mass_s2/`; launcher `jobs/run_perturb.sh`; logs `logs/perturb_{rand_full,mass}.log`. They run one after the other because parallel_batch holds the source session's owner lock.

## Session 2 final + perturbations (parallelised, 2026-10-20 ~19:35 EDT)
- Session 2 formal FINAL: 145/150 = 96.7% (seeds 96/96/98%).
- Bottleneck was CPU (8 cores saturated, GPU 5% util, 3/98 GB), so perturbations were split over 4 GPU jobs (8 cores each):
  10867474 (babel-z9-16), 10870214 + 10870215 (babel-y9-08), 10870234 (queued at launch).
- parallel_batch holds an exclusive lock on its source session, so each batch reads its own copy (`tools/make_source_copy.py`:
  top-level JSON + bundles/, sim_gpu and root rewritten): `runtime/auto-research/srccopy_{rf_a,mass_a,rf_b,mass_b}`.
- Second reproduction-only patch: `RAX_FORMAL_START` in `services/controller/parallel_batch.py` sets the first official layout,
  so one 150-layout test runs as two 75-layout halves. Outputs: `runtime/auto-research/pert_{rand_full,mass}_{0_74,75_149}/`.
- First attempt (`perturb_rand_full_a`, `perturb_mass_a`) errored 150/150 at startup (copies lacked configuration.json); ignore.
- Early finding: under rand_full the program crashes at step 0 (skills.py:83 `d["center"]` is None: colour masks find no disk).

## Perturbation redesign (2026-10-20 ~19:45-20:00 EDT) - read this, it supersedes the section above
- MY ERROR: editing `services/dexjoco/session.py` while batches ran tripped parallel_batch's safety check
  ("Planner infrastructure changed during the batch") and aborted the running rand_full and mass batches (~19:44).
  Their partial results are kept as a repeat check: `pert_rand_full_0_74` (3/25 completed), `pert_rand_full_75_149`, `pert_mass_0_74`.
- `RAX_FORMAL_START` never took effect (workers still ran official layouts 0-74; checked via operator_state.json), so the
  "75_149" dirs are repeats of layouts 0-74, not new layouts. The patch is reverted.
- Final design: EVERY condition runs official layouts 0-74 (75 episodes), compared with the unperturbed session-2 program
  on the same 75 layouts.
- New single-factor switches (RAX_PERTURB = lighting | camera | texture | colors_new) live in a SECOND worktree
  `~/my_things/codes/rax/.worktrees/dexjoco-pert` (branch repro/dexjoco-pert), so running batches in the first worktree
  are never touched again. They call the official env's own randomize_lighting / randomize_camera /
  randomize_desktop_texture after reset; colors_new sets disk materials to orange/green/purple (sizes unchanged),
  then re-renders the first observation. Verified visually: `runtime/diagnostics/verify_<cond>/`.
- First colors_new attempt (`pert_colors_new_0_74`) errored 75/75 on an observation-format bug (fixed in the second worktree).
- Clean runs: `pert_rand_full_r2`, `pert_mass_r2` (first worktree), `pert_colors_new_v2`, `pert_{lighting,camera,texture}_v2` (second worktree).
- colors_new result: 0/75; every episode ends at step 0 (skills.py:83 colour mask finds no disk).

## Session 3: adaptation to the randomized variant (launched 2026-10-20 20:30 EDT) - beyond the paper's main protocol
| What | Value |
|---|---|
| Session dir | `runtime/auto-research/20261021T003013Z_5d4081e99d/` |
| Task | `bimanual_hanoi_random` (official rand_full: camera viewpoint, lighting, table texture change every episode) |
| Source | session 2 (memory + code + compacted conversation), 6 exploration episodes, seeds 20-25, no Gemini (no OpenRouter key) |
| GPU | job 10870214 (babel-y9-08), formal 150 episodes x 6 workers on the rand_full official layouts |
| Watcher | `session3/timeline.jsonl`, cap $89 total (cost includes carried sessions 1-2: $55.23 at start) |
| Demos | installed for bimanual_hanoi_random (same 3 demos) |
- ADAPTATION.md tells the agent: "This environment is the randomized variant ... do not assume earlier poses or colors still hold."
- Baseline to compare: session-2 program on rand_full layouts 0-74 = 14/75 (`pert_rand_full_r2`).
- Released idle GPU jobs 10867474 and 10870307 at 20:25.

## Program walkthrough page (2026-10-20 evening)
- Artifact: https://claude.ai/artifact/GLjzKHTE5xei9zSdxGRTYW ("Hanoi Program Walkthrough"), private until shared.
- Source + assets: `report/program_page/` (hanoi-program.html, clips/episode108.mp4 = copy of report/v2/clips/feed_s2_formal_108.mp4, img/).
- Explains session-2 bundle c8712bc7 stage by stage on formal layout 108 (success, task_complete at step 1242). Stage step ranges come from that episode's
  `formal-workers/episode-109/rax-controller-*/files/hanoi_log.txt`; mask images re-apply perception.py colour rules to the raw frame
  (`masks.py`, `wmask.py`). Texture perturbation row shows "running" (50/59 when built).
- Code tour page: https://claude.ai/artifact/YcEWJW1nooVJJ5hqQ5zfBe (source report/program_page/hanoi-code-tour.html): annotated listings of the bundle's five files, worked numbers from layout 108.
