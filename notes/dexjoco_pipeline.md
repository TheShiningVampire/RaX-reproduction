# What happens in a RaX DexJoCo session — research notes

Source: `origin/dexjoco/native` (all refs below are `path:line` on that branch unless marked
`[container]`). Extracted read-only with `git archive` into `scratchpad/src/`. Nothing was run.

Big caveat: the **official DexJoCo source is not vendored**. Task prompts, camera mappings and
the randomization ranges live in the upstream repo `https://github.com/brave-eai/dexjoco.git` at
commit `8d23b0fab23b17a58c4b55f3942e17013aaf8267` (`dependencies.lock`), in
`configs/rand_obj/<task>.yaml` and `configs/rand_full/<task>.yaml`, plus the env code. They are
cloned at setup time (`scripts/bootstrap_sources.sh`) and are NOT in any RaX branch, so the
numeric ranges below are marked UNKNOWN.

---

## 1. Lifecycle of a session

### 1.1 One-time setup (docs/SETUP.md, README.md:56-70)

```bash
git clone --branch dexjoco/native https://github.com/robot-agent-exploration/rax.git
cd rax
export RAX_RUNTIME_ROOT=/fast-disk/rax/runtime            # optional; default .local-runtime/
bash scripts/bootstrap_sources.sh                         # links runtime/, clones DexJoCo at pinned commit as DexJoCo/
bash scripts/setup_host_env.sh                            # runtime/envs/host: Py3.12 harness + agent Python (CPU torch)
bash scripts/setup_dexjoco_env.sh                         # runtime/envs/dexjoco: Py3.11, MuJoCo 3.4.0, gymnasium 1.0.0, dexjoco, openpi-client
runtime/envs/host/bin/python scripts/setup_dexjoco_demos.py --gpu 0 --task click_mouse --task pick_bucket   # 3 expert demos/task
bash scripts/setup_claude_experiment_login.sh [--email ...]   # only for --agent-provider claude-login
bash scripts/doctor.sh                                    # host checks (bwrap, socat, CLIs, keys, GPUs)
runtime/envs/host/bin/python scripts/dexjoco_doctor.py --gpu 0 --task click_mouse   # real simulator check
runtime/envs/host/bin/python -m pytest -m "not gpu" -q local_tests/unit              # ~2 min, no paid calls
bash scripts/run_operator_dashboard.sh                    # loopback dashboard, port 8765 (services/dashboard/server.py:219)
```

### 1.2 Per session (docs/USAGE.md:13-21, 40-45, 88-104)

| Step | Terminal command |
| --- | --- |
| Prepare (writes config only, no model/sim) | `runtime/envs/host/bin/python scripts/configure_auto_research.py --task click_mouse --sim-gpu 0 --episodes 16` (add `--agent-cli claude --agent-provider claude-login` etc.) |
| Launch | `bash scripts/start_auto_research_agent.sh --config runtime/auto-research/<session-id>/operator-input.json` (interactive TUI by default; `--non-interactive` = headless) |
| Stop | `bash scripts/stop_auto_research_agent.sh --config <session>/operator-input.json` |
| Resume | `bash scripts/start_auto_research_agent.sh --config <session>/operator-input.json --resume` |
| Move GPU | `bash scripts/move_session_gpus.sh --config <session>/operator-input.json --sim-gpu <idx/UUID>` |
| Extra live-copy eval of a finished code-mode session | `... start_auto_research_agent.sh --config ... --resume --agent-formal` |
| Re-evaluate a rehearsed bundle without a model | `PYTHONPATH=. runtime/envs/host/bin/python -m services.controller.parallel_batch --source-session <session> --bundle <bundle-id> --output runtime/auto-research/<new-dir> --episodes 150 --workers 4` (USAGE.md:282-290) |

"Budget N" = `--episodes N` (default 5, range 1..1000). There is no separate "formal eval"
command in code mode: the formal batch runs automatically when the agent's process ends with
exploration closed (submission made). Formal flags at prepare time: `--formal-episodes`
(default 150, 1..150), `--formal-workers` (default 4, 1..16), `--formal-seed` (first formal
layout, 0..149).

Other prepare flags worth showing (USAGE.md:55-79): `--exploration-envs` (1..8),
`--subagents` (0..8), `--agent-cli codex|claude` (default codex), `--agent-provider
openrouter|claude-login|anthropic`, `--agent-effort xhigh|max`, `--observation-profile
rgbd|rgb-only`, `--task-rules public|code-summary`, `--demonstration-context
none|terminal_state|completion_sequence` (default terminal_state), `--expert-demonstrations 0|3`,
`--episode-reviews off|on|detailed`, `--agent-formal off|on`, `--formal-context
resume|compact|clear`, `--transfer-parts`, `--transfer-mb`, `--write-handoff`,
`--adaptation-source`, `--recording-gib`. Fixed for DexJoCo: `--formal-eval-seed 1`,
`--expert-content full` (services/benchmarks.py:152-155).

### 1.3 What the launcher does / processes (docs/ARCHITECTURE.md:26-61, 275-388)

`scripts/start_auto_research_agent.sh` → `runtime/envs/host/bin/python -m harness.codex_cli.auto_research` (the same entry for both CLIs; dispatches to `harness/claude_cli/auto_research.py` when `agent_cli: claude`, harness/codex_cli/auto_research.py:740-760).

Order of operations (harness/codex_cli/auto_research.py:700-850):
1. Takes `launch.lock` (flock) so only one launcher per session; writes `agent-lifecycle.json` (`preparing` → `running` → `formal` → `exited`/`stopped`/`failed`).
2. **Deploy** (first launch): builds `agent-workspace/` from templates + skills (services/workspace/), writes the CLI home (`claude-home/` or `codex-home/`), `agent-login.json` (provider/model/key path, never the secret). For Claude: `CLAUDE.md` = `@AGENTS.md`, `.claude/skills -> ../.agents/skills` (harness/claude_cli/auto_research.py:45-50).
3. **MCP frontend** process: `python -m services.controller.frontend --config ... --workspace ... --socket <unix socket> --agent-pid-file ...` in its own session (harness/codex_cli/auto_research.py:454-466). It is the session's only MCP server (lifecycle + robot tools + Gemini), owns `state.json` via the Supervisor, and spawns simulators.
4. **Simulators** (started lazily by the frontend's gateway/backend on `start_episode`): `DEXJOCO_PYTHON -m services.dexjoco.server` per episode (one fresh process per episode, `services/dexjoco/session.py:219-221` "One fresh episode per process; no reset"), and `services.dexjoco.preview_server` (robot-only preview) on first preview use. Env: `CUDA_VISIBLE_DEVICES=<sim gpu>`, `MUJOCO_GL=egl`, `MUJOCO_EGL_DEVICE_ID` (services/dexjoco/process.py:48-63). msgpack RPC over `services/simulator/`.
5. **Agent CLI**: Claude Code command (harness/claude_cli/auto_research.py:256-272):
   `claude --model <claude-opus-5-5 | anthropic/claude-opus-5.5> --effort xhigh --mcp-config claude-home/mcp.json --strict-mcp-config --disallowedTools WebFetch WebSearch [Agent Task] [--resume <id>] [-p ... --output-format text --verbose] -- "<START_PROMPT>"`.
   `mcp.json` registers one stdio server `auto_research` = `<agent python> -I harness/mcp_bridge.py <socket>` (auto_research.py:232-234); the bridge just pipes stdio to the frontend's Unix socket (harness/mcp_bridge.py).
   Env (auto_research.py:275-297): `CLAUDE_CONFIG_DIR=claude-home`, the credential, `MCP_TOOL_TIMEOUT` ≈ 20 days, `CLAUDE_CODE_AUTO_COMPACT_WINDOW=250000`, `ENABLE_PROMPT_CACHING_1H=1`, `DISABLE_AUTOUPDATER=1`.
6. **Sandbox for the agent's commands** = Claude Code's own sandbox (bubblewrap + socat), configured in `claude-home/settings.json` (auto_research.py:197-224): `defaultMode: acceptEdits`, allow `mcp__auto_research`, deny WebFetch/WebSearch; `sandbox.enabled`, `failIfUnavailable`, `allowUnsandboxedCommands: false`; writes only to workspace + socket dir; `denyRead` hides repo, `runtime/auto-research/*` (other sessions), DexJoCo source, `~/.ssh`, `~/.claude`, `~/.codex`, ... (ARCHITECTURE.md:109-130); network `allowedDomains: []` (only Unix sockets). No GPU visible. Codex uses its own permission-profile sandbox instead.
   [container] branch: the agent instead runs inside an offline Docker container (`rax-auto-research:dev`, ~12 GB) with a capped loop-mounted ext4 workspace; the Claude/Codex model traffic goes through relays (`harness/claude_cli/messages_relay.py`, `harness/codex_cli/model_relay.py`); Gemini is capped per task.
7. Headless auto-relaunch while exploration is open: turn ended → `CONTINUE_PROMPT` (max 3); run failed → wait 300 s, `ERROR_PROMPT` (max 5 in a row); claude-login usage limit → `usage_wait` until reset (max 10) (USAGE.md:211-223; harness/codex_cli/auto_research.py:557-569).
8. Agent ends → **freeze** (memory, code, handoff, conversation; services/agent_formal/checkpoint.py) → **formal batch** (code mode: the submitted bundle; agent-formal: live copies) → results (`formal-scores.json`). If the agent stopped with episodes left and no submission: `formal.json: exploration_incomplete`, nothing runs (ARCHITECTURE.md:328-334).
9. **Dashboard** (optional): `scripts/run_operator_dashboard.sh` → `python -m services.dashboard.server` on 127.0.0.1:8765; front-end to the same commands; shows stage, episodes used, success rate, tokens, Gemini spend, live frames, per-episode videos, logs (USAGE.md:142-146). SSH tunnel `ssh -L 8765:127.0.0.1:8765 <host>`.

### 1.4 Session directory (USAGE.md:24-26, 148-168)

`runtime/auto-research/<YYYYMMDDTHHMMSSZ_random10>/`, e.g. `20261013T120000Z_1a2b3c4d5e`:
`operator-input.json`, `configuration.json`, `state.json` (episodes, bundles, submission, formal batches, Gemini ledger), `agent-lifecycle.json`, `agent.log`, `frontend.log`, `mcp.jsonl` (every MCP call), `agent-login.json`, `provider-errors.jsonl`, `agent-workspace/`, `claude-home/`|`codex-home/`, `native/results/<run>/sim/` (sim records + `sensors.mp4`), `exploration/` (parallel ledger), `bundles/`, `formal.json`, `formal-scores.json` / `agent-formal-scores.json`, `formal-workers/episode-NNN/` / `agent-formal/`, `published/` (agent-readable run tree), `operator-analysis/` (episode reviews), `subagents.json`, `gpu-moves.jsonl`.

### 1.5 Agent workspace contents (ARCHITECTURE.md:473-486)

| Path | Contents |
| --- | --- |
| `AGENTS.md` (`CLAUDE.md` = `@AGENTS.md`) | workflow + episode lifecycle |
| `START_PROMPT.md` | first message |
| `TASK.md` | task prompt/rubric (+ demonstration section) |
| `MCP_CONTRACT.json`, `MCP_SESSION.md` | this session's tool contract |
| `.agents/skills/` (`.claude/skills` symlink) | skills |
| `api/runtime.py` | development `Context` |
| `code/`, `memory/`, `output/` | agent's own work |
| `runtime/autonomous_controller/` | published run artifacts (symlink to `<session>/published`), read-only |
| `runtime/demonstrations/` | demo images (default: 3 terminal-state images) |
| `runtime/experts/` | 3 expert episodes, read-only (only with `--expert-demonstrations 3`) |

Agent's Python = `runtime/envs/host/bin/python` (NumPy, SciPy, Pillow, OpenCV, h5py, CPU PyTorch), offline, no GPU, 4-CPU thread pools (SETUP.md:81-83).

---

## 2. Prompts

`local_tests/goldens/workspaces.json` contains only **sha256 hashes** per rendered file (no text), so the
renderings below are done by hand from the Jinja templates. Golden case used by the generator:
task `pick_bucket` (scripts/render_workspaces.py:36). Default assumed: code mode, Claude, 1 env,
0 subagents, rgbd, `demonstration_context=terminal_state` (3 images), method skills on (DexJoCo
has `method_skills=True`, services/benchmarks.py:140), wrist cameras present.

### 2.1 START_PROMPT.md (auto_research_agent/START_PROMPT.md:1-4) — VERBATIM template

```
Read AGENTS.md, then MCP_SESSION.md and TASK.md, and call `status`. Follow the AGENTS.md
workflow{% if agent_formal %}: solve the task by hand, automate it, and practise with your
controller in every episode; when no episode remains, follow `status.next_step` and end
your turn{% endif %}.
```

Rendered, code mode (the default) — this is the entire kickoff message (read via
`startup_prompt()`, harness/codex_cli/auto_research.py:677):

```
Read AGENTS.md, then MCP_SESSION.md and TASK.md, and call `status`. Follow the AGENTS.md
workflow.
```

Resume prompt instead (harness/codex_cli/auto_research.py:557-559): "This session was interrupted
and has now been resumed in the same workspace. Reread memory/PROGRESS.md, call status, and continue
from the live state. Do not repeat finished work, and do not restart an episode merely because the
conversation resumed."

### 2.2 MCP_SESSION.md (rendered from services/workspace/contract_files.py:8-37)

```
# Session tools

Role: exploration. Observation profile: rgbd.

RGB images, depth and camera calibration are supplied; get metric positions with [object-localization](.agents/skills/object-localization/SKILL.md).

Tools: `dexjoco_hold`, `dexjoco_observe`, `dexjoco_pixel_to_position`, `dexjoco_preview_describe`, `dexjoco_preview_run`, `dexjoco_rotation_math`, `dexjoco_status`, `dexjoco_step`, `evaluate`, `finish`, `gemini_generate`, `register`, `rehearse`, `start_episode`, `status`, `submit`. The live tool schemas give arguments and limits. `status` reports budgets, bundles and episode state; `dexjoco_status` reports the live robot and episode.
```

### 2.3 TASK.md (rendered from services/dexjoco/task_rules.py:32-63 + services/controller/demonstrations.py:16-47), pick_bucket, `public`

```
# Task: pick_bucket

**Instruction:** <official prompt from DexJoCo configs/rand_obj/pick_bucket.yaml — NOT in repo>

## Episode

- Robot: one Franka Panda arm with a 16-DoF Allegro hand, on a table.
- Cameras: <official camera_mapping values, e.g. `front`, `wrist` — UNCERTAIN for nominal; pick_bucket_random is `random_camera`, `wrist` per local_tests/unit/test_dexjoco_backend.py:79>.
- Step limit: 1200 steps of 20 ms of physics each (paced at 30 per second); the episode ends there, on success, or on a failure condition.
- Wall-clock limit per episode: about 110 minutes, including simulator startup.
- Object placement and the table height change between episodes.
- Exploration episodes use their own layouts; formal episodes are the 150 official DexJoCo evaluation layouts, which exploration never uses.

## Success

- An episode succeeds or fails. There is no partial credit: an episode that ends without the success condition, hits the step limit, triggers a failure condition or errors does not succeed.

## Visual demonstration

Supplied: 3 terminal-state images.
Read [the image manifest](runtime/demonstrations/manifest.json) and view the
local images before acting. `ordered_images` paths are relative to
`runtime/demonstrations/`.
Use the in-context-action-learning skill. These images explain task goals;
their layout may differ from the current scene. They contain no executable
actions or simulator state. Satisfy the conditions above in the current layout.
Rehearsals and the formal batch do not see these images; include any reference
image your controller needs in its bundle.
```
With `--task-rules code-summary` a "## Task rules (summarized from the official task code)" section with `task_rules/<task>.md` is inserted after the instruction. With episode reviews on, an "Episode reviews" section is appended (task_rules.py:66-77).

### 2.4 AGENTS.md (auto_research_agent/AGENTS.md, 232 template lines) — section summary (code mode, Claude, 1 env)

- `# DexJoCo auto-research` + goal (l.14-19): "Your goal is an autonomous controller that completes the configured robot task without live intervention: satisfy every condition in `TASK.md`. Solve the task by hand first to learn what the controller must do. The final evaluation is the formal batch: your submitted code run alone on held-out layouts."
- `## Start here` (l.21-30): read TASK.md, memory/PROGRESS.md, memory/INDEX.md, call `status`; don't start an episode just because the conversation resumed; skill links are entry points.
- `## Workflow` (l.54-164), four steps:
  1. Understand and solve the task yourself (manual-robot-control, in-context-action-learning for the demos; wrist-camera-inspection; confirm with `evaluate` / `task_complete: true`).
  2. Reproduce your decisions in an autonomous controller (autonomous-control; simple motion functions and heuristics; gemini for perception).
  3. Pressure-test, freeze and rehearse (VERBATIM l.115-127 rendered):
     > Test the controller across layouts as autonomous-control's "Pressure-test across layouts" describes. Put `controller.py:main(ctx)`, the modules it imports and its data files under `code/<project>/`. Rehearsals and the formal batch run this frozen controller alone, against the context they supply, as autonomous-control shows. `register(source=...)` freezes the directory, and `rehearse(bundle=...)` runs that bundle end to end as a fresh process in a fresh exploration episode, without you. Inspect the returned evaluation and logs, not just the exit code. Fix failures while budget remains; any edit needs a new registration and a new rehearsal. `submit` accepts only a bundle whose own rehearsal ran cleanly to its end, with no error, timeout or simulator exit; the task need not succeed. Confirm it in `status.bundles` (`rehearsal_qualified`) and the `rehearse` return or its run's `result.json`, not from your notes. Development tests do not count.
  4. Submit the rehearsed bundle (VERBATIM l.128-136 + 142-143 rendered, binary score):
     > Call `submit` once with that exact bundle. It closes exploration, freezes the bundle and returns no score. After you end your turn, the formal batch runs it from a freeze of your work: `status.formal_episode_count` formal episodes, each a fresh process in a fresh environment, with no live intervention, edits or retries. You do not see its result. Each episode succeeds or fails by the condition in `TASK.md`; the result is the share of successes over that fixed count, and errors count as failures. Submit the bundle you expect to succeed most often, even if no rehearsal fully succeeded. If a prerequisite cannot be met within the budget, report the blocker; do not bypass it or claim success.
  - Method-skills paragraph (l.145-164): spend-the-budget, engineer-the-controller, change-discipline, evidence-and-regression, rehearse-the-controller; after each episode update prioritize-by-funnel and learn-from-incidents tables, check avoid-overfitting; while acting keep-trying, measure-success, verify-committal-actions, match-precision-to-error.
- `## Episodes and budgets` (l.166-191): all robot/Gemini access via MCP tools listed in MCP_SESSION.md (+ image-forwarding note); `start_episode` → next layout, `finish` to close; layouts differ, reacquire geometry; each rehearsal uses one exploration episode; Gemini has no spend limit; Python uses `from api.runtime import Context`, `ctx.call(tool, **arguments)`.
- `## Workspace and artifacts` (l.193-207): workspace is the only writable place, no internet/simulator access, don't seek simulator internals; run records read-only under `runtime/autonomous_controller/`; "Your commands pause during registration and rehearsals."; don't load whole recordings.
- `## Intermediate notes and compaction` (l.209-232): keep `memory/PROGRESS.md` current (step, episode, results, failed approaches, parameters, bundle/rehearsal IDs, budgets, next step), `memory/TIPS.md` via experience-memory; context auto-compacts; final report: controller path, submitted bundle, rehearsal outcomes, unresolved issues.

Live-copy mode (`--agent-formal on`) uses different goal/step 2-4 text (practise with the controller in every episode, keep carried folders current) and each formal copy gets `FORMAL_AGENTS.md` (sections: `# DexJoCo episode`, `## Start here`, `## How the episode ends`, `## Tools and code`, `## Time and budgets`, `## Workspace`).

### 2.5 Skills (`agent_skills/**/SKILL.md`; layered per services/workspace/recipes.py:18-51)

Default code-mode Claude session with 1 env, 0 subagents, demos, no experts gets everything except multi-env-exploration, multi-agent-exploration, learn-from-experts, transfer-handoff (recipes.py:23-51).

| Skill | Purpose (frontmatter description, condensed) |
| --- | --- |
| task/manual-robot-control | Solve the task by directly choosing robot actions from observations; recovery; preparing scenes for script tests |
| task/experience-memory (+references/format.md) | Save successful action tips to memory/TIPS.md and retrieve them by observable conditions |
| task/in-context-action-learning | Infer task goals from the supplied terminal-state images / completion sequence (only with demos) |
| coordination/multi-env-exploration | Operate parallel envs and the shared budget (only with >1 env) |
| coordination/multi-agent-exploration | Divide exploration among subagents (only with subagents) |
| perception/common/wrist-camera-inspection | Move an empty arm's wrist camera closer for close-ups |
| perception/depth-dexjoco/object-localization | Pixels → world 3-D points via depth (rgbd) |
| perception/rgb-only-dexjoco/object-localization | Locate objects from RGB + flange poses without depth (rgb-only) |
| control/dexjoco/robot-interface (+references/pose-records.md) | Panda + Allegro official action rows, state vector, frames, cameras, control response |
| control/dexjoco/hand-control | Shape/close/open the 16-DoF Allegro hand(s); grasp postures, squeezing, verifying grasps |
| control/dexjoco/motion-preview | Dry-run rows on the robot-only preview simulator before spending episode steps |
| control/dexjoco/learn-from-experts | Use the 3 recorded human teleop episodes in runtime/experts/ (only with experts) |
| auto-research/autonomous-control | Python control from the workspace; register, rehearse, submit a frozen controller (`SKILL.formal-episode.md` variant for live copies) |
| auto-research/gemini (+references/api.md) | Gemini 3.8 Flash via MCP: images, JSON schema output, function calling, usage tracking |
| auto-research/transfer-handoff | Write handoff/README.md for a later session on new layouts (only with handoff/agent-formal) |
| auto-research/experience-memory/SKILL.formal-episode.md | Formal-copy variant of experience-memory |
| method/spend-the-budget | Plan step limit, wall-clock and model calls; action length by risk |
| method/engineer-the-controller | Main loop that never crashes/hangs, preconditions, verified results, stall detectors, timeouts, escalation |
| method/change-discipline | Changelog of controller versions with evidence; when to switch methods |
| method/evidence-and-regression | k/n with intervals, falsifiable claims, offline regression suite replaying archived episodes |
| method/rehearse-the-controller | Rehearsal pass rate predicts the formal batch; rehearse early, time table per phase |
| method/prioritize-by-funnel | Cumulative per-stage funnel; fix the stage that loses most |
| method/learn-from-incidents | Table of falls/near-falls/unexpected contacts, hazard zones |
| method/avoid-overfitting | Warning signs of layout-specific code/constants/replays |
| method/keep-trying | Use every step: recovery, retries, practise other subtasks |
| method/measure-success | Measure margin vs the success condition, aim well inside |
| method/verify-committal-actions | Define/verify outcome of irreversible actions (strikes, releases) |
| method/match-precision-to-error | Compare needed vs delivered precision before retrying |

### 2.6 One task rules file VERBATIM — `services/dexjoco/task_rules/pick_bucket.md`

```
**Goal:** Put the boxed food into the bucket, then lift the bucket.

**Success requires, at the same step:**
- The boxed food's centre is inside the bucket (within the box spanned by the bucket's corner markers, which turns with the bucket).
- The bucket's bottom is raised a set height above where it started.

**Scene variation:** the bucket's and the boxed food's positions and headings, and the table height, change between layouts. The bucket has a hinged handle.
```
`pick_bucket_random.md` VERBATIM:
```
**Rules:** identical to `pick_bucket`.

**Scene variation:** as `pick_bucket`, and in addition the third-person camera's viewpoint, the lighting and the table texture change between layouts.
```
These are only shown to the agent with `--task-rules code-summary` (default `public` = official prompt only).

---

## 3. MCP tools (DexJoCo)

Contract: services/mcp_contract.py:16-19, 187-196. Robot tool schemas: services/dexjoco/tools.py:79-152. Lifecycle tool schemas: services/controller/frontend.py:85-93. Gemini schema: services/controller/gateway.py:88-105.

### Robot tools (benchmark `dexjoco`)
| Tool | Args | What it does |
| --- | --- | --- |
| `dexjoco_status` | none | Episode status, step budget, official action/state layouts, cameras, instruction. No physics |
| `dexjoco_observe` | none | Official observation: each eval camera's RGB at 640x640 + depth attachments (rgbd), calibration, state vector (23/46-D), instruction. Cached after last motion |
| `dexjoco_step` | `actions`: 1..150 rows of 22 (single arm) or 44 (dual arm) numbers | Executes official policy action rows, one 30 Hz step each (20 ms physics). Row = [flange xyz (m, world), flange rotvec (rad, world), 16 Allegro joint targets]; dual = right then left. Absolute targets. Stops early at episode end; returns final frame, saves every 10th frame |
| `dexjoco_hold` | `steps`: 1..150 | Official `stay()`: hold current measured pose; counts against step limit |
| `dexjoco_pixel_to_position` | `observation_step_id`, `selections` [{camera,u,v}] 1..32, `depth_window_radius` 0..5 | Depth back-projection to world points (rgbd only; removed in rgb-only) |
| `dexjoco_rotation_math` | `operation` (convert_rotation, compose_pose, relative_pose, flange_target, row_from_state), rotation/pose_a/pose_b/point_target_m/point_offset_m/near_rotation_vector/state | Pure rotation/pose arithmetic (scipy Rotation); unscoped, needs no episode |
| `dexjoco_preview_describe` | none | Contract of the robot-only preview |
| `dexjoco_preview_run` | `actions` (1..150 rows), optional `initial_state` | Dry-runs rows on a robot-only sim (robot on floor plane, official controller/gains, no table/objects/contacts), fixed `preview_front/side/top` cameras; never spends episode steps |

Perception = `dexjoco_observe` + `dexjoco_pixel_to_position` (+ `gemini_generate`). Control = `dexjoco_step`, `dexjoco_hold` (no motion planner, ARCHITECTURE/DEXJOCO_BACKEND.md:43-47).

### Lifecycle tools (services/controller/frontend.py:85-93)
| Tool | Args | Description (VERBATIM where quoted) |
| --- | --- | --- |
| `status` | none | "Task, manual success evidence, episode state, episode timeout, remaining exploration episodes, registered bundles (rehearsal_qualified: whether each bundle has had a clean rehearsal), workspace storage, and Gemini budgets: total and formal usage." Adds `next_step` once exploration is closed (frontend.py:173-210) |
| `start_episode` | none (no layout/seed) | "Start the next exploration episode on the next layout; closes the previous one." Charges one episode |
| `evaluate` | none | "Check the current exploration episode against the task; a success confirms manual success." Returns binary `task_complete` |
| `finish` | none | "Close the current exploration episode. Does not submit." |
| `register` | `source` (e.g. `code/reach`) | "Freeze a controller.py bundle without running it; main(ctx) must use only the ctx it is given." |
| `rehearse` | `bundle` | "Run the whole registered controller in a fresh exploration episode under the same limits as each formal episode ... Consumes one exploration episode. Returns wall-time breakdown in timing; timeouts identify timeout_stage." |
| `submit` | `bundle` | One final submission; closes exploration; formal batch runs after the agent ends; agent never sees result. Binary-score wording substituted for DexJoCo (frontend.py:71-73) |

In live-copy mode (`--agent-formal on`) `register/rehearse/submit` are absent. Isolated runs (rehearsal, formal bundle) get robot tools + `gemini_generate` only. With N>1 envs every env-scoped tool gains a required `env_id`.

### `gemini_generate` (gateway.py:88-105)
Args: `messages` (1..64, required), `max_tokens` (1..16384), `temperature` (0..2), `response_format` (text/json_object/json_schema), `tools` (client function declarations ≤64), `tool_choice`, `reasoning`. "OpenRouter-style chat completion via Gemini 3.8 Flash: text/images, JSON schema output and client function calling. ... Gemini spending, call and token counts are not limited." Model `google/gemini-3.8-flash` on OpenRouter; key held by the frontend, never by the agent. Without an OpenRouter key: "Gemini is not configured".

No tool named "formal"; "rehearsal"/"submit" are `rehearse`/`submit` above.

---

## 4. Exploration budget mechanics

- `--episodes N` → `exploration_seeds = range(start, start+N)` (services/dexjoco/benchmark.py:56-58); exploration layout `i` = first reset of seed `1000 + i` (services/dexjoco/tasks.py:21-22, 116-117). Never an official eval seed (0,1,2).
- Counter `state["exploration_started"]`. `start_episode` → `Supervisor.start_interactive()` raises `"Exploration episodes exhausted"` when `index >= len(exploration_seeds)`, else increments and **saves before creating the simulator** (services/controller/supervisor.py:414-423), so a failed startup or stop stays charged (single env).
- **Each `rehearse` also consumes one episode** (supervisor.py:886-913; error "No exploration episode remains for rehearsal").
- `register` and `submit` cost nothing. `dexjoco_preview_run`, `dexjoco_rotation_math`, `gemini_generate` cost no episodes.
- Within an episode: step limit (1000-1500, see §6) and wall limit 600 s + 5 s/step incl. startup (tasks.py:128-136). Each `dexjoco_step`/`dexjoco_hold` row is one step.
- Parallel envs (>1): one shared ledger; episodes ending with `error`/`interrupted` are refunded and their layout replayed (ARCHITECTURE.md:400-406).
- When exhausted: exploration closes once no episode is live (frontend.py:173-177); `status.next_step` then tells the agent (frontend.py:192-206): if submitted → update notes, end turn; if a rehearsal-qualified bundle exists but no submission → "Call submit with the rehearsal-qualified bundle you choose ... without a submission no formal batch runs"; if none qualifies → "no formal batch can run", end turn. Exhausted budget blocks new starts but not actions in a live episode.
- Seeds: exploration = seeds 1000+i (collection 0); formal = official eval (collection 1): layout L → seed `L // 50`, reset number `L % 50 + 1` (tasks.py:110-115; DEXJOCO_BACKEND.md:62-69). `--exploration-start-seed` shifts i.

---

## 5. Compilation and formal evaluation

- **Bundle**: `register(source="code/<project>")` copies and sha256-hashes the directory's regular files (no links; size/count limits; path is part of the hash) into `<session>/bundles/` without running it (ARCHITECTURE.md:313-314). Entry point must be `controller.py` defining `main(ctx)` (sandbox.py:154).
- **ctx API** (auto_research_agent/api/runtime.py): `ctx.call(tool, **arguments)` → MCP result dict (`content` blocks: JSON text first, then images); raises `RuntimeError("MCP tool failed: ...")` on error (l.106-113). `ctx.request(method, params)` (raw JSON-RPC). `ctx.env(env_id)` → `Environment` bound to an exploration env (development only; l.87-91). `Context()` as context manager connects to `$RAX_MCP_SOCKET` (development). Inside a frozen run, `api/runtime.py` `main()` loads `controller.py` and calls `main(ctx)` with a stdio-backed Context; `print` goes to a log channel, native output to stderr (l.132-146). Only robot tools + `gemini_generate` are reachable from the frozen controller (no start_episode/finish/register/...).
- **Clean rehearsal requirement** (`qualifying_rehearsal`, supervisor.py:44-55): mode rehearsal, same bundle id and sha256, boolean `task_complete`, no `simulator_exited`/`evaluation_error`/`error_type`/`output_error`/`recording_errors`, reason in {`episode_ended`,`exit`}, and returncode 0 (or a finalization timeout). Task success NOT required. `submit` refuses otherwise (supervisor.py:549-560). One submission only.
- **Isolated runner** (services/controller/sandbox.py:103-136): `bwrap --unshare-all --die-with-parent --new-session --cap-drop ALL`, read-only `/usr,/etc,/opt` + Python env, empty read-only workspace layout with the bundle at `code/<project>` and `api/runtime.py`, writable `output/`, 1 GiB `/tmp`, `--clearenv`; runs `python -u api/runtime.py <mode> <project> controller.py`. 8 GiB RLIMIT_DATA, 128 files, 4-CPU math threads, no GPU, no network. During register/rehearse the agent CLI process tree is SIGSTOPped (ARCHITECTURE.md:180-182).
- **Formal batch (code mode)**: after the agent ends and is frozen, `Supervisor.run_submission()` (supervisor.py:567-580) runs `formal_episodes` (default 150) official layouts, `formal_workers` (default 4) at a time, each its own worker process (services/controller/formal_worker.py) + fresh simulator + fresh sandbox; no retries; Gemini brokered by parent. Worker killed 10 min past wall limit (SIGTERM, SIGKILL +3 min). `services/controller/parallel_batch.py` is the operator-only re-evaluation/migration tool (CLI above).
- **Scoring**: per episode official binary `info["succeed"]` → `native_score` 1.0/0.0 (DEXJOCO_BACKEND.md:70-72). `formal_outcome` (supervisor.py:58-68): success only if healthy run AND `task_complete is True`; else `unsuccessful` or `error`. Batch = successes / scheduled count; missing scores count as zero (`missing_score_policy: zero_in_fixed_denominator`).
- **Output files**: `published/formal_batch.json`, `formal-scores.json` (schema `native_formal_scores_v1`: `episode_count`, `recorded_score_count`, `missing_score_count`, `average_score`, `average_score_percent`, `official_seeds: {per_seed: {"0": {episodes, average_score}, ...}, mean, std}`, `episodes[]`; services/scoring.py:54-119), `formal.json` (status), `formal-workers/episode-NNN/`. Live copies: `published/agent_formal_batch.json`, `agent-formal-scores.json`, `agent-formal/episode-NNN/`.
- Live-copy mode (`--agent-formal on`): each formal layout is played by a fresh copy of the frozen agent (conversation `compact` by default, carried `handoff,memory,code` ≤100 MB), copies start 60 s apart, 120 s wrap-up after episode end (USAGE.md:248-270).

---

## 6. DexJoCo tasks

From services/dexjoco/tasks.py:27-42 (step caps), task_rules/*.md (descriptions). Every task has 150 formal episodes (3 official seeds × 50). Wall limit = 600 s + 5 s × step limit.

| Task | Arms | Step limit | Wall limit | One-line (from task_rules/<task>.md) |
| --- | --- | --- | --- | --- |
| hammer_nail | single | 1000 | 5600 s (~93 min) | Pick up hammer, drive nail to a set depth (needs fast downward strikes) |
| click_mouse | single | 1200 cap − 30 preroll = 1170 | 6450 s | Move mouse onto purple pad and left-click; display turns blue |
| pick_bucket | single | 1200 | 6600 s | Put boxed food in bucket, then lift bucket |
| pinch_tongs | single | 1000 | 5600 s | Pick up tongs, squeeze shut and open 3 times while held up |
| fold_glasses | single | 1200 | 6600 s | Fold both temples, place glasses in the case |
| water_plant | single | 1000 | 5600 s | Pick up watering can, pull trigger with nozzle near plant (fails if triggered elsewhere) |
| bimanual_unlock_ipad | dual | 1200 | 6600 s | Pick up iPad, enter password 1-2-3 with right hand (wrong digit ends episode) |
| bimanual_hanoi | dual | 1500 | 8100 s | Last two moves of 3-disk Hanoi (medium→right peg with right hand, small onto it with left) |
| bimanual_assembly | dual | 1500 | 8100 s | Left hand grasps tray, right grasps peg, insert peg into tray hole |
| bimanual_microwave_cook | dual | 1100 | 6100 s | Open door, put food in, close door, press start |
| bimanual_photograph | dual | 1000 | 5600 s | Left hand lifts camera, aims at logo; right hand presses shutter |

Action dims 22 (single) / 44 (dual); state 23 / 46. 30 Hz control, 20 ms physics per step (10 × 2 ms substeps, tasks.py:43-45).

Scene variation per nominal task (task_rules, qualitative only):
- hammer_nail: hammer position+heading, nail position on board, table height.
- click_mouse: mouse position+heading (pad follows), table height; display fixed. 30-step preroll to a fixed hand pose.
- pick_bucket: bucket and boxed-food positions+headings, table height.
- pinch_tongs: tongs position, table height.
- fold_glasses: glasses and case positions+headings, table height.
- water_plant: can and plant positions, table height.
- bimanual_unlock_ipad: stand position, table height.
- bimanual_hanoi: base position along the table only; starting arrangement fixed.
- bimanual_assembly: peg and tray positions+headings, table height.
- bimanual_microwave_cook: food position+heading, table height; microwave fixed.
- bimanual_photograph: logo position on wall, camera position.

`_random` variants (`configs/rand_full`): same object randomization **plus third-person camera viewpoint, lighting and table texture** (task_rules.py:50-54; DEXJOCO_BACKEND.md:59-60). Implemented by the official env flag `rand_full=True` passed to `DexJoCoOpenPIEnv` (services/dexjoco/session.py:163-166). For `_random` the third-person camera key is `random_camera` (test_dexjoco_backend.py:79).

**Numeric ranges: UNKNOWN from this repo.** Object pose ranges, table-height range, camera-pose/lighting/texture ranges are defined in the upstream DexJoCo env/configs (`DexJoCo/configs/rand_obj/<task>.yaml`, `configs/rand_full/<task>.yaml` and env code at commit 8d23b0f), which RaX loads at `services/dexjoco/tasks.py:70-80` (`official_config`) but never vendors. Task-rules files deliberately omit exact values ("summarized ... without its exact values", task_rules.py:5-6). One data point: untouched objects settle by up to ~3 cm / 20° after reset (DEXJOCO_BACKEND.md:181-182).

**Physics params / perturbation hooks:**
- RaX sets `randomize_dynamics=False` when constructing the official env: services/dexjoco/session.py:165 (also checks.py:37, demo_tools.py:68). The official wrapper therefore has a built-in dynamics randomization option that RaX turns off — the most natural hook for friction/mass perturbations (what it randomizes and its ranges are in upstream code; UNKNOWN here).
- `_Tap` pass-through wrapper around the gym env (session.py:60-97) intercepts every `reset()`/`step()`; it has access to `self.tap.unwrapped._model/_data` (MuJoCo model/data, see session.py:182-195), so per-episode edits of `model.geom_friction`, `model.body_mass`, etc. could be applied after `reset()` in `DexjocoSession.reset()` (session.py:219-240) without touching the official checkout. No friction/mass handling exists today (grep finds none).
- Note: the DexJoCo principle is "the official DexJoCo, unchanged" (DEXJOCO_BACKEND.md:9-13); `services/dexjoco/checks.py` verifies layout determinism, so perturbations should not consume the env RNG or formal layouts will drift.
- The preview simulator replicates the official controller gains (services/dexjoco/preview_session.py:14) — would need matching changes if dynamics change.

---

## 7. Setup requirements (docs/SETUP.md)

- Linux x86_64 (tested Rocky Linux 8). **One NVIDIA GPU with EGL (`libEGL_nvidia`)**; MuJoCo renders headless via EGL on the session's sim GPU; physics on CPU. **A100 fails** (8× MSAA offscreen framebuffer error 0x8cdd) → use RTX or H100 (SETUP.md:21-25). One sim process per live exploration env (+preview) and per concurrent formal episode; CPU cores bound concurrency.
- `bubblewrap` with unprivileged user namespaces (bundle sandbox + Claude Code sandbox), `socat` (Claude Code sandbox), git, git-lfs, curl, sha256sum, nvidia-smi. No Docker on native ([container] branch needs rootful Docker, privileged containers, `/dev/loop-control`, ~12 GB image).
- Disk: DexJoCo src 0.3 GB, host env 2 GB, dexjoco env 1.7 GB, demos ~0.1 GB/task, sessions few-to-tens of GB.
- Envs: `scripts/setup_host_env.sh` (Miniforge 26.7.2-0, Py3.12, numpy 2.5.2, scipy, opencv 5.0, torch 2.11.0 CPU, h5py...), `scripts/setup_dexjoco_env.sh` (official `environment-dexjoco.yaml` from conda-forge only: Py3.11, MuJoCo 3.4.0, Gymnasium 1.0.0, NumPy 1.26.4; pip `dexjoco`, `openpi-client` editable). Pins in `dependencies.lock`.
- Demonstrations: `scripts/setup_dexjoco_demos.py` downloads from HF `DexJoCo/DexJoCo-Datasets-Raw` (rev 125df5c...), replays, keeps 3 that succeed and do not match any of the 150 eval layouts. Needed unless `--demonstration-context none --expert-demonstrations 0`.
- Agent CLI: Claude Code (tested 2.1.296) or Codex CLI (tested 0.162.1). Claude providers (SETUP.md:170-204; harness/claude_cli/login.py:18-25):
  - `openrouter` (default): model `anthropic/claude-opus-5.5`, key from `--key-file` / `~/.codex/secrets/openrouter_api_key` / `OPENROUTER_API_KEY` (passed as `ANTHROPIC_AUTH_TOKEN` + OpenRouter base URL).
  - `claude-login`: `claude-opus-5-5` with a **dedicated experiment account** token (`claude setup-token`) stored at `~/.config/rax/claude-experiment.token` via `scripts/setup_claude_experiment_login.sh`; passed as `CLAUDE_CODE_OAUTH_TOKEN`. **Personal `~/.claude` login is refused** (login.py:36-42, 56-58). Usage-limit waits are handled.
  - `anthropic`: `claude-opus-5-5` with `ANTHROPIC_API_KEY` or `--claude-key-file`. → **Yes, ANTHROPIC_API_KEY is supported.**
  - Subagent aliases: sonnet → Sonnet 5.5, haiku → Haiku 4.5.
- Codex: default OpenRouter `openai/gpt-6-astra`; needs the key file; other Responses-API providers via profile TOML; ChatGPT plan login supported.
- **Gemini is optional** (SETUP.md:206-212): needs an OpenRouter key (same file or `OPENROUTER_API_KEY`); without it `gemini_generate` stays listed but answers "Gemini is not configured". Episode reviews also use OpenRouter Gemini, capped at $10/session operator budget.
- Cluster note (not from repo): babel nodes are compute nodes; the A100 restriction matters for which GPU partition to use.

---

## 8. Paper numbers

- No DexJoCo-specific result numbers appear anywhere in `origin/dexjoco/native` or `origin/dexjoco/container` (only links to the paper: README.md:3 → https://robot-agent-exploration.com/rax.pdf).
- `origin/main` README (README.md:50-53; arXiv 2610.22496): "Mean success on unseen scenes rises from **25%** to **79%** as the exploration budget grows from 4 to 128 episodes, against **41.2** for the best prior SOTA." and "🖥️ **Simulation.** RAX beats the top baseline models by **+37.4%** on average." It does NOT say these are DexJoCo numbers — UNCERTAIN which benchmark(s) they refer to (the "Simulation" bullet plausibly includes DexJoCo; check the paper). Also "program runs up to 241× faster than the agent" (Air fryer, a real-robot task — not DexJoCo).
