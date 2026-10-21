# RaX reproduction inventory: released vs not released

Method: `git ls-tree` / `git show` / `git grep` on `origin/<branch>` in ~/my_things/codes/rax (no checkout, nothing run, nothing downloaded). Date of inspection: 2026-10-19.

## Branches (commit count, dates, file count)

| Branch | Commits | First / last commit | Files | LICENSE file on branch |
|---|---|---|---|---|
| main | 19 | 2026-10-14 / 2026-10-19 | 27 (index: README, LICENSE, NOTICE, docs/, skills/) | yes (Apache-2.0) |
| robodojo-behavior/container | 2 | 2026-10-13 / 2026-10-15 | 426 | **no** |
| robodojo-behavior/native | 2 | 2026-10-13 / 2026-10-15 | 417 | **no** |
| humanoid-arena/container | 1 | 2026-10-17 | 260 | yes + NOTICE |
| humanoid-arena/native | 1 | 2026-10-17 | 255 | yes + NOTICE |
| dexjoco/container | 1 | 2026-10-17 | 249 | yes + NOTICE |
| dexjoco/native | 1 | 2026-10-17 | 244 | yes + NOTICE |
| real/franka | 1 | 2026-10-13 | 85 | **no** |
| real/rainbow | 1 | 2026-10-13 | 101 | **no** |

All code branches are squashed single/two-commit snapshots, so no development history is released.

## Inventory

| Item | Status | Where | Why it matters |
|---|---|---|---|
| Agent prompts (START_PROMPT / AGENTS / FORMAL_AGENTS templates) | released | every code branch: `auto_research_agent/{AGENTS.md,START_PROMPT.md}`; sim branches also `FORMAL_AGENTS.md` (real branches have no FORMAL_AGENTS). Jinja templates, e.g. robodojo-behavior/container:auto_research_agent/AGENTS.md:1,60,138 and START_PROMPT.md:1-4; rendered via `services/workspace/` + `agent_blocks/blocks.toml`; goldens in `local_tests/goldens/workspaces.json` | The prompt is the method. Rendered text depends on template vars (benchmark, demonstration context, agent_formal), so a reproducer must match flags. |
| Skills (universal) | released | main:skills/ (README with tool-role table and per-branch matrix, `templates/robot-interface`) | Robot-agnostic skill text the agent loads. |
| Skills (per-branch, as actually loaded) | released | `agent_skills/` on each branch (auto-research, control/<bench>, perception depth vs rgb-only, task, coordination; humanoid & dexjoco add 12 `method/*` skills e.g. spend-the-budget, avoid-overfitting) | Branch versions differ from main:skills; the branch copy is what ran. UNCERTAIN whether paper runs used exactly these revisions (snapshots are post-hoc squashes). |
| Task skills learned on real robots | released (external) | github.com/robot-agent-exploration/skills-lib, branches rby1/franka (main:README.md:162-180) | Seeds continual-learning on real robots; not inspected here. |
| Per-task rules | released | robodojo-behavior: `services/robodojo/task_rules/` (54) + `task_rubrics.json`; `services/behavior/task_rules/` (100) + `tasks.json`. humanoid-arena: `services/humanoid/task_rules/` (7). dexjoco: `services/dexjoco/task_rules/` (22). `--task-rules public|code-summary` (robodojo-behavior/container:docs/USAGE.md:65) | Agent's task spec; choice of public vs code-summary changes results. Which mode each paper table used: UNCERTAIN. |
| Harness / MCP servers | released | `harness/` (claude_cli, codex_cli relays, session_*), `services/controller/` (frontend, supervisor, sandbox, gateway, gemini, formal_worker), `services/mcp_contract.py`, `services/*/mcp_server.py`; native variants add `harness/agent_host.py`, `harness/mcp_bridge.py`. Real: `services/controller/`, `harness/claude_cli/{launcher,mcp_bridge}.py` | Core of the system; looks complete with unit tests (`local_tests/unit/`). |
| Sim integrations | released | RoboDojo `services/robodojo/` (54 task configs), BEHAVIOR-1K `services/behavior/` (100 tasks), HumanoidArena `services/humanoid/` (+ g1/, sim/), DexJoCo `services/dexjoco/` | All four sim benchmarks covered. |
| Real-robot integrations | partial | real/franka `services/franka/`; real/rainbow `services/rby1/`, scripts/rby1_*.py, RBY1.md | Franka arm/gripper HTTP bridges in front of Polymetis are **not released** (real/franka:README.md:51-56). Hardware-specific calibration needed anyway. |
| Pinned deps & patches | released (sim) / partial (real) | robodojo-behavior/container:dependencies.lock:1-34 (RoboDojo commit ee67a14, assets rev, Isaac Sim 5.1.0.0, torch 2.7.0+cu128, BEHAVIOR v3.9.3-post1 + dataset SHAs); `patches/robodojo.patch`, `patches/robodojo-pr48-drive-reset.patch` (patches/README.md says rewards/success/layouts unchanged). humanoid-arena: lock pins HumanoidArena commit 6847928, assets SHA, Isaac Sim 6.1 image, `patches/isaaclab-isaacsim61.patch`, docker/humanoid/. dexjoco: lock pins DexJoCo commit 8d23b0f (unmodified), demos rev. Agent CLIs: "Tested with" Codex 0.162.1 / Claude Code 2.1.296 (robodojo-behavior/container:docs/SETUP.md:132,134) - documented, not enforced. Real: only loose pip lists (real/rainbow:README.md:84-92, rby1-sdk==0.8.3) | Good sim pinning. Agent image base pinned by digest at build (scripts/build_agent_image.py:69) but the digest itself is not recorded in repo. HumanoidArena assets come from a Google Drive link (fragile). |
| Seeds / eval protocol | released (as defaults) | robodojo-behavior/container:docs/USAGE.md:67-72 (formal 50 RoboDojo / 10 BEHAVIOR, held-out collection 1, exploration seeds skip formal layouts); services/benchmarks.py:127,153; humanoid-arena/container:services/benchmarks.py:145 (60 formal); dexjoco/container:services/benchmarks.py:149 (150 formal). Scoring definition: robodojo-behavior/container:docs/USAGE.md:343-360. Two modes: code mode vs live copies (`--agent-formal`) | Protocol is reproducible in principle. Which mode/defaults each paper number used: UNCERTAIN (no per-table mapping). LLM sampling is non-deterministic regardless of layout seeds. |
| Eval scripts | released | `services/agent_formal/` (runner, worker, checkpoint, code_runs), `services/controller/formal_worker.py`, `services/scoring.py`, `services/*/scoring.py`; outputs `formal-scores.json`, `published/formal_batch.json` | Can score new runs; no aggregation script that rebuilds paper tables found. |
| Compiled controllers / bundles for sim results | **not released (confirmed)** | `git ls-tree` on all 9 branches: 0 files named `controller.py`; only "bundle" hit is local_tests/unit/test_bundle_sandbox.py (native branches) | Cannot re-evaluate the paper's frozen programs or verify the 241x/103x speed-up claims without rerunning exploration. |
| Sim session logs | **not released** | no .jsonl/.log files on any branch; main README only links real-robot logs (main:README.md:182-188) | No transcripts/scores to audit sim numbers. |
| Real-robot session logs | released (external, not inspected) | HF dataset robot-agent-exploration/robot-session-logs: 5 Franka + 7 RB-Y1 sessions, transcripts, tool calls, state logs, camera recordings, operator instructions, agent code/notes/skills (main:README.md:184-188) | Only evidence of real-robot runs. Contents per README only; UNCERTAIN until inspected. |
| Real-robot compiled code | released per README (inside HF logs) | same HF dataset ("the code ... the agent wrote", main:README.md:187-188) | Lets one inspect/replay air-fryer etc. programs on matching hardware. UNCERTAIN whether every task in paper has its controller. |
| Gemini prompts | not released as fixed artifacts (by design) | agent writes them at runtime: robodojo-behavior/container:agent_skills/auto-research/gemini/SKILL.md:12 ("Write your own prompts"); model `google/gemini-3.8-flash` (services/controller/gemini.py:15), $10/session budget (docs/USAGE.md:364-368) | Only recoverable from session logs; absent for sim. |
| Baselines code | **not released** | no baseline policy/VLA code on any branch; `test_subagent_baseline.py` is a multi-agent harness test, not a paper baseline | "+37.4% over top baselines" and "41.2 best prior SOTA" (main:README.md:52-53) cannot be reproduced from this repo. |
| Per-table experiment configs (e.g. 4->128 budget sweep) | **not released** | no config/sweep files; only CLI flag `--episodes` (1..1000, default 5; docs/USAGE.md:57 [corrected: was :56]) and `--exploration-envs`/`--subagents` | Must reconstruct sweeps (tasks, budgets, effort, observation profile, task-rules mode, CLI/model) from paper text. |
| Model access | closed APIs required | Claude Opus 5.5 via OpenRouter/Anthropic (harness/claude_cli/messages_relay.py:44-49; auditor/fast models Sonnet 5.5 / Haiku 4.5), Codex default `openai/gpt-6-astra` (harness/codex_cli/model_relay.py:18; docs/SETUP.md:172), Gemini 3.8 Flash | Results tied to model versions that may be deprecated; cost per run is non-trivial. |
| License | partial | Apache-2.0 on main (LICENSE, NOTICE, main:README.md:214-220) and humanoid-arena/dexjoco branches; **no LICENSE/NOTICE on robodojo-behavior/* or real/* branches** | Main README claims Apache-2.0 for "RAX's original source code"; branch-level license file missing on 4 branches. Third-party sims/assets keep their own licenses. |

## Bottom line
Released: full harness, prompts, skills, task rules, sim integrations, pins/patches, eval/scoring code. Not released: sim compiled controllers/bundles, sim session logs, baselines, per-table configs/sweeps, Franka Polymetis bridges. Real-robot logs + code exist only on HF (not inspected).

## Verification

Independent re-check via `git rev-list/ls-tree/show/grep` on `origin/<branch>` (2026-10-19). Default was WRONG unless source found.

1. **Branch table (commits, dates, file counts, LICENSE/NOTICE presence)** - CONFIRMED for all 9 branches (rev-list/ls-tree). No LICENSE/NOTICE on robodojo-behavior/{container,native} or real/{franka,rainbow}; present on main, humanoid-arena/*, dexjoco/*. Added main file count (27).
2. **0 `controller.py` and 0 `.jsonl`/`.log` files on any branch** - CONFIRMED (ls-tree -r on all 9). Only "bundle" path is `local_tests/unit/test_bundle_sandbox.py` on the 3 native branches - CONFIRMED.
3. **`test_subagent_baseline.py` is a harness test, not a paper baseline** - CONFIRMED: docstring "Multi-agent baseline: subagents scale independently of exploration environments." (robodojo-behavior/container:local_tests/unit/test_subagent_baseline.py:1).
4. **Franka HTTP bridges not released** - CONFIRMED: "The bridges are not part of this repository." (real/franka:README.md:56).
5. **dependencies.lock pins (RoboDojo ee67a14, Isaac Sim 5.1.0.0, torch 2.7.0+cu128, BEHAVIOR v3.9.3-post1)** - CONFIRMED (robodojo-behavior/container:dependencies.lock:1-34). HumanoidArena 6847928 (humanoid-arena/container:dependencies.lock:24), DexJoCo 8d23b0f (dexjoco/container:dependencies.lock:21), Google Drive assets URL (humanoid-arena/container:dependencies.lock:26) - CONFIRMED.
6. **"Tested with" Codex 0.162.1 / Claude Code 2.1.296** - CONFIRMED (robodojo-behavior/container:docs/SETUP.md:132,134). Codex default `openai/gpt-6-astra` - CONFIRMED (harness/codex_cli/model_relay.py:18; docs/SETUP.md:141,172).
7. **Agent base image digest resolved at build, not recorded in repo** - CONFIRMED: `BASE = 'python:3.12-slim'` (scripts/build_agent_image.py:25), digest read at :69, written only to a build record (:90); no `python@sha256:` literal in branch.
8. **Formal defaults 50/10/60/150** - CONFIRMED (robodojo-behavior/container:services/benchmarks.py:127,153; humanoid-arena/container:services/benchmarks.py:145; dexjoco/container:services/benchmarks.py:149; docs/USAGE.md:67).
9. **`--episodes` 1..1000 default 5** - WRONG line cite: row is at docs/USAGE.md:57, not :56. Fixed in place [corrected]. Content CONFIRMED. `--task-rules` at :65 CONFIRMED.
10. **Task-rule counts 54 / 100 / 7 / 22** - CONFIRMED (ls-tree of services/{robodojo,behavior,humanoid,dexjoco}/task_rules/).
11. **Gemini `google/gemini-3.8-flash`, $10/session budget, "Write your own prompts"** - CONFIRMED (services/controller/gemini.py:15; docs/USAGE.md:364; agent_skills/auto-research/gemini/SKILL.md:12).
12. **Claude models Opus 5.5 / Sonnet 5.5 / Haiku 4.5** - CONFIRMED with nuance: Sonnet 5.5 auditor only on the OpenRouter provider; `anthropic` and `claude-login` providers use Haiku 4.5 as auditor (harness/claude_cli/messages_relay.py:44-50).
13. **README quotes: "+37.4%" and "41.2" (main:README.md:52-53); 5 Franka + 7 RB-Y1 sessions with agent code (main:README.md:184-188); skills-lib rby1/franka (main:README.md:162-180); Apache-2.0 (main:README.md:214-220)** - CONFIRMED. Note: these are README claims; HF/skills-lib contents remain UNVERIFIED (not downloaded).
14. **real/rainbow loose deps, rby1-sdk==0.8.3** - CONFIRMED (real/rainbow:README.md:84-92).
