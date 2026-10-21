# RaX + privileged object state on DexJoCo: shared protocol (COMMON)

Every task session reads this file and one task file (`<task>.md` in this folder). The task file sets
the parameters (section 1) and the task-specific sections (section 1b). If the two files disagree, the
task file wins for task facts and this file wins for protocol.

## 0. Who you are working for and what this is

I am a PhD student. My advisor asked for a quick trial: **does RaX (arXiv 2610.22496) do better on
DexJoCo when the agent can read the simulator's object state?** This is not a reproduction. It is an
extension, and I am "just trying it out". We run 5 tasks: `water_plant`, `fold_glasses`,
`bimanual_microwave_cook`, `bimanual_photograph`, `bimanual_hanoi`. We compare each task with the
paper's Table 5 vision-only number at the same budget (8 episodes).

RaX in one paragraph: a coding agent (Claude Code + Opus 5.5) controls a simulated robot through MCP
tools, explores the task for a budget of N episodes, then writes `code/<project>/controller.py:main(ctx)`,
a program that runs the task with no agent. The harness rehearses it, the agent submits it, and the
harness scores it alone on the 150 official test layouts (seeds 0, 1, 2 x 50).

**What is new here: one privileged tool, at the `full` level.** The MCP tool `dexjoco_object_states`
(no arguments) is available during exploration and to the compiled program via
`ctx.call("dexjoco_object_states", {})`. Its level comes from the environment variable
`RAX_PRIVILEGED_STATE` (`objects` or `full`; default `full`; any other value is an error), read by
`services/dexjoco/objects.py` `privileged_level()` on the host and simulator side. **These runs use
`full`, and every job script exports `RAX_PRIVILEGED_STATE=full` explicitly** (do not rely on the
default). Every reply carries `"privileged_level"`. At `full` the reply holds, in the world frame:
- `objects`: live poses of the task's objects and fixtures (`position_m` + `quaternion_wxyz`),
  articulation angles (`angle_rad`: microwave door, glasses temples, watering-can trigger), named object
  points (`position_m`: nozzle, glasses centre, food centre, Hanoi pegs), the photograph logo's pose,
  Hanoi's three disks; and, for every free-joint or body object, `linear_velocity_mps`,
  `angular_velocity_radps` and `size` (`half_extents_m`, `center_offset_m`: the collision geoms'
  bounding box in the object's own frame, computed once per episode at reset);
- `arm_joint_positions_rad`: the 7 arm joints per arm (hand joints stay in the official state vector);
- `contacts`: current MuJoCo contacts on task objects and the hands, summed per pair (`a`, `b`,
  `normal_force_n`, `count`, `position_m`), robot-robot contacts left out, at most 64 pairs, strongest
  first;
- `goal`: the task's **official success check written out** (`services/dexjoco/goals.py`): a
  `description`, `conditions` and `failure_conditions` (each `name`, `satisfied`, `measured`,
  `threshold`, `note`), `targets` (positions and regions to reach), `holding` (`steps_satisfied` of
  `steps_required` consecutive steps) for tasks that must hold, and `satisfied_now`. The thresholds are
  the official constants (read from the env object or its module; a few local literals of the official
  checks are copied in goals.py and guarded by a unit test against the official source).
So the agent now sees the success thresholds, region sizes, targets and hold counters. Nothing is
hidden from it about how success is measured. The harness still strips evaluation fields (`success`,
`reward`, `terminated`, `native_*`, ...) from every reply at any depth (`services/mcp_reply.py`
`_agent_safe`); the tool uses none of those names, and a unit test checks the full reply survives the
filter unchanged.
Cameras, depth and vision skills stay. The agent-facing rule text changed. AGENTS.md went from "There
is no internet or simulator access. Do not seek simulator internals ..." to "There is no internet or
direct simulator access. The simulator's object state comes through `dexjoco_object_states`: use it.
Do not seek other simulator internals ...". The robot-interface skill's "## Object state" section
dropped "no object positions in the state; find objects in the images" and, at `full`, describes the
velocities, sizes, contacts and goal fields (it says "Its `privileged_level` here is `full`"); the MCP
tool description says the same. The tool is committed on `exp/add-state-info/object` (a42f98b, dcbf92f,
full level bf68e11 + 8294953 + 223f1a8). You do not implement or change it; you verify it (P1) and run it.

**You are the orchestrator for ONE task.** You run one Claude Code session for the whole task (P0 to
P5). You delegate reading and writing work to subagents (section 2). The RaX agent itself is NOT one of
your subagents: it is a separate headless Claude Code process that the harness launches. It uses my
personal Claude subscription, the same limits as you and your subagents.

## 1. Parameters every task file must set

```
TASK          = <one of the 5 task ids>
ARM           = A | B    # A (default): object state only; B: object state + dexjoco_lookahead (section 1c)
ROOT          = /data/user_data/vawale/rax_state/<TASK>_<ARM>   # runtime, logs, results, notes, report
CODE_COMMIT   = <fill in after GPU smoke passes>   # I fill this in (Arm A: full hash on exp/add-state-info/object; Arm B: see 1c)
CODE_WORKTREE = ~/my_things/codes/rax/.worktrees/state-run-<TASK>[-B]   # detached at CODE_COMMIT, see P1
REUSE_ENVS    = /data/user_data/vawale/rax_repro_v2/runtime/envs   # host + dexjoco conda envs, read-only
GPU_JOB       = <optional: id of a running katef GPU job to reuse; empty = submit new jobs (P1.4, P2.5)>
```

Fixed for all tasks (do not change): budget 8 episodes, `--agent-cli claude`,
`--agent-provider claude-login`, `--agent-effort xhigh`, `--demonstration-context terminal_state`,
`--task-rules public`, empty workspace (no adaptation source), `--formal-episodes 150`,
`--formal-workers 4`, Gemini off (no OpenRouter key, `--episode-reviews off`), one fresh session,
and `export RAX_PRIVILEGED_STATE=full` in every job script (gates and session) before any harness
command. Record the level in STATE.md and DECISIONS.md at P0 ("privileged level: full, exported
explicitly") and again with each launch.
Arm B (`ARM = B`) also exports `RAX_LOOKAHEAD=on RAX_LOOKAHEAD_ROWS_FACTOR=3` and records them the same
way (section 1c).

Why a per-task worktree: the harness hard-codes `<worktree>/runtime` (scripts/configure_auto_research.py
uses `PROJECT/'runtime'`, the launcher uses `runtime/envs/host/bin/python`). A detached worktree per task
lets `runtime` point at that task's `ROOT/runtime`, and it freezes the code: nobody edits it while the job
runs. The development worktree `~/my_things/codes/rax/.worktrees/add-state-info` is never used to run.

### 1b. Sections every task file must provide

- **A. Parameters** (the block above, filled in).
- **B. Task facts:** goal, success and fail conditions, robot (single or dual arm), step cap, scene
  variation. Cite `services/dexjoco/tasks.py` and `services/dexjoco/task_rules/<TASK>.md`.
  Also the task's `goal` as `services/dexjoco/goals.py` implements it: conditions, failure conditions,
  targets and holding, with goals.py line citations. The agent sees all of it through the tool.
- **C. Paper reference:** the TASK's Table 5 row at budgets 2/4/8/16/32 and the best ME-Dex baseline
  (from `~/my_things/codes/rax-reproduction/notes/paper_claims_vs_evidence.md`, section 2).
- **D. Object-state smoke checklist:** every label `dexjoco_object_states` should return for TASK, with
  the sane range for each (e.g. z above table height, unit quaternion, hinge angle near closed at reset),
  plus the full-level rows: velocities and sizes of the free/body objects, contacts at rest, and the
  goal's condition names and their expected values at step 0.
- **E. What to watch:** likely failure stages and task pitfalls (grasp, articulation, aiming, timing).
- **F. Breakthrough candidates:** what moments to look for when cutting clips.

### 1c. Arm B: lookahead (only when the task file sets `ARM = B`)

Arm A (the default) is everything else in this file. Arm B is Arm A plus one more tool. Everything in
this file still applies to Arm B, with the changes below. Run the arms as separate sessions, each with
its own ROOT (`<TASK>_A`, `<TASK>_B`) and its own run worktree. One RaX agent session at a time across
all tasks and both arms.
Never run Arm A from the lookahead branch: there lookahead is on by default.

**What Arm B adds.** The MCP tool `dexjoco_lookahead` (`services/dexjoco/lookahead.py`). It takes the
same rows `dexjoco_step` takes (plus an optional `report_every`). It runs them from the live episode
state on a copy of the simulator state, through the episode's own physics, controller and contacts. It
reports `final.state` and `final.object_states` (plus `reports`). The real episode is never advanced or
rewound. After every call an exactness check compares fingerprints taken before and after. On a
mismatch the episode ends, invalid for scoring (`invalid_reason: lookahead_restore_mismatch`).
- Limits per episode: rows = `RAX_LOOKAHEAD_ROWS_FACTOR` (default 3) x the task's step cap; 300 calls;
  30 s wall time per call. Every reply carries `lookahead_budget`. A lookahead uses the episode's
  wall clock but no episode steps.
- It holds the same per-environment lock as the motion tools. The compiled program can call it in
  formal evaluation via `ctx.call("dexjoco_lookahead", {...})`, exactly as in exploration.
- Agent text: the tool's MCP description, plus a "## Lookahead" section in
  `agent_skills/control/dexjoco/robot-interface/SKILL.md`. That section includes the rule "lookahead
  never changes the episode; use it to compare candidate rows, then execute the chosen rows with
  `dexjoco_step`", and says it costs wall time and budget. AGENTS.md is unchanged. With
  `RAX_LOOKAHEAD=off` the tool refuses, and none of this text is rendered.

**Parameters for B.** Branch `exp/add-state-info/lookahead` (the implementation is 798111f, 43bd0ae,
7e87b69, 8e780f3, built on 223f1a8). `CODE_COMMIT = <fill in after GPU acceptance passes>`. I fill it
in with the full hash of the branch tip plus my auth opt-in (2b), the way 943da37 is 223f1a8 plus the
opt-in for Arm A. If it is still a placeholder, stop at P1 and ask me.
`ROOT = /data/user_data/vawale/rax_state/<TASK>_B`, `CODE_WORKTREE = ~/my_things/codes/rax/.worktrees/state-run-<TASK>-B`.

**Switches.** Every job script (gates and session) exports all three settings explicitly, right after
`RAX_PRIVILEGED_STATE`, and echoes them into the log. Do not rely on defaults.
```
export RAX_PRIVILEGED_STATE=full RAX_LOOKAHEAD=on RAX_LOOKAHEAD_ROWS_FACTOR=3
echo "RAX_PRIVILEGED_STATE=$RAX_PRIVILEGED_STATE RAX_LOOKAHEAD=$RAX_LOOKAHEAD RAX_LOOKAHEAD_ROWS_FACTOR=$RAX_LOOKAHEAD_ROWS_FACTOR"
```
Record "lookahead: on, rows factor 3, exported explicitly" in STATE.md and DECISIONS.md at P0 and
with each launch. These variables are in `SESSION_KEPT_ENV`, so they reach the launcher frontend, the
exploration simulators and formal evaluation. The session also records them in
`<session>/session-env.json` at first launch. A resume or a post-hoc formal batch adopts the recorded
values. If the shell sets a different value, the launch is refused. After launch, check that
`session-env.json` shows `RAX_LOOKAHEAD: "on"` and record it in STATE.md.

**Acceptance gate (decides CODE_COMMIT; I or the other agent run it once for all 5 tasks).** On an
RTX PRO 6000 node (not babel-z9-16), from the run worktree, with the exports above:
`RAX_RUNTIME_ROOT=<runtime> PYTHONPATH=. runtime/envs/host/bin/python scripts/lookahead_acceptance.py --gpu $G --out <dir>`
(no `--task`: all 5 tasks). It must exit 0. Its `<dir>/lookahead_acceptance.json` must pass every
check for every task: control, continuation (bit-identical state and object states for every
following real row), prediction, unchanged (observe/object_states/step_id/operator files),
frames, episode_end (stops with `episode_end` without ending the episode), budget, and timing per
row (recorded; a note above 15 ms/row). Until this passes, CODE_COMMIT stays a placeholder.

**Phase changes for B.**
- P1.1 diff: the expected set is the Arm A set plus `services/dexjoco/lookahead.py`,
  `services/controller/{session_env,batch,parallel_batch}.py`, `services/mcp_contract.py`,
  `scripts/lookahead_acceptance.py`, `local_tests/unit/test_dexjoco_lookahead.py`,
  `local_tests/unit/test_dexjoco_lookahead_physics.py`, `local_tests/unit/test_session_env.py`.
  Also check `git -C WT diff --stat 223f1a8 HEAD`: only the lookahead files plus `experiment_login.py`.
  Anything else: stop and ask me.
- G1b adds `local_tests/unit/test_dexjoco_lookahead.py` and `local_tests/unit/test_session_env.py`.
  At 8e780f3 the four files collect 97 tests (36 + 18 + 39 + 4). Re-count with `--collect-only`.
  All must pass, none skipped. The non-GPU suite was `874 passed, 25 skipped` on babel-cpu at 8e780f3.
- G1c (new) CPU physics test: `PYTHONPATH=.:R/tools/pytest_overlay runtime/envs/dexjoco/bin/python -m pytest -q -p no:cacheprovider local_tests/unit/test_dexjoco_lookahead_physics.py`.
  The simulator env has no pytest, so `R/tools/pytest_overlay` is a directory of symlinks to the host
  env's `pytest`, `_pytest`, `pluggy`, `iniconfig`, `pygments` packages and their `*.dist-info`, from
  `REUSE_ENVS/host/lib/python3.12/site-packages`. Pass: "8 passed" (bit-identical continuation on
  real single-arm and bimanual task models). The host interpreter skips this file; that is expected.
- G3: goldens "identical" (they record the defaults, now including lookahead on). The rendered
  robot-interface/SKILL.md (`--out`) must contain "## Lookahead" and "lookahead never changes the
  episode", and the rendered tool list must contain `dexjoco_lookahead`.
- G6 (new): `scripts/lookahead_acceptance.py --gpu $G --task TASK --out R/results/lookahead_acceptance`
  inside the gates job at CODE_COMMIT. Pass: rc=0 and every check passes. Copy its timing rows into
  STATE.md.
- P2.2 dry deploy: the deployed SKILL.md must contain the "## Lookahead" section. If it does not, the
  export did not reach the deploy: stop and tell me. P2.3: also grep `session.sbatch` for
  `RAX_LOOKAHEAD=on`. P2.4: there is no usage reference for B yet. Say "Arm A reference; B may be longer".
- P3: count `dexjoco_lookahead` calls in `mcp.jsonl` as well. At the first call, record its
  `lookahead_budget`. Tell me at once if any of these appears: a reply saying the tool "is off in this
  session" (the export was lost); `lookahead_restore_mismatch` in any episode's `evaluation_outcome.json`;
  or an exploration episode that hit its wall limit.
- P4: formal evaluation takes longer when the program looks ahead. Each formal episode's wall limit
  still applies. Report progress as n/150 only. Record the formal wall time from start to end.
- P5 extra fields in `R/results/TASK.json`, all from operator-side files (the agent never sees them).
  Each episode's `summary.json` / `evaluation_outcome.json` has a `lookahead` record with `calls`,
  `rows`, `seconds`, `rejected` and the limits.
  - Per exploration episode and per formal episode: lookahead calls, rows and seconds. Give the
    totals and the per-episode median/max for the formal run.
  - The share of formal wall time spent in lookahead.
  - Formal episodes invalidated by `lookahead_restore_mismatch` (expected 0) and formal episodes that
    hit the wall limit.
  - Whether the submitted `controller.py` calls `dexjoco_lookahead` (static grep), and how often per
    formal episode (from the records).
  - Formal-eval wall time for Arm B vs Arm A on the same task. Take A's from
    `rax_state/<TASK>_A/results/TASK.json`; if A has not run, write "A not yet run".
  The session note also says how the agent used lookahead: what it compared, at which decisions, and
  whether the program uses it to search among candidate rows at run time.
- Report wording (add to section 7's paragraph for B): "In this arm the agent could also simulate
  candidate rows exactly from the live state before executing them (a perfect, rewindable model of
  the simulator), and its program could do the same during evaluation. A program that does this is
  an agent-written, simulator-based expert (planning with the true simulator), not a policy learned
  purely from exploration. Its success rate is not comparable to a vision-only or a model-free
  controller, and the evaluation took X h of wall time vs Y h for Arm A." Never present Arm B's
  number as a better learned controller.

## 2. Operating rules (these override convenience)

1. **Disk is the memory, not the conversation.** Keep three files under `ROOT/`:
   - `STATE.md`: current phase, what is running (job ids, node, PIDs, session dir), the privileged
     level (`RAX_PRIVILEGED_STATE=full`), what is done, what is next, latest evidence with timestamps. Overwrite it at every phase boundary and after every
     launch or finish.
   - `DECISIONS.md`: append-only. Every decision with date, reason, and who decided (me or you).
   - `MANIFEST.md`: append-only index of every artifact path (session dir, logs, scripts, clips, notes).
   Re-read all three at the start of every phase and whenever you resume.
2. **Numbers only come from scripts.** Every number in a note, the summary, or a message to me comes
   from a script under `ROOT/tools/` that reads raw files (`state.json`, `formal-scores.json`,
   `formal-report.json`, `mcp.jsonl`, `agent-lifecycle.json`, transcripts) and writes
   `ROOT/results/*.json`. Re-run it right before you quote. If a number was not just regenerated, say so.
3. **Delegate to subagents; keep your own context thin.** You stay in this one session. Give these jobs
   to subagents (Agent/Task tool), each with a precise brief and output path:
   - reading transcripts, `mcp.jsonl`, stage logs and the 150 formal runs;
   - writing `ROOT/notes/session.md` and other notes;
   - skeptical fact-checks of any load-bearing claim (default verdict "wrong" when unsupported);
   - building clips and the summary page data.
   Each subagent writes its findings to `ROOT/notes/<topic>.md` and returns a summary of at most 200
   words. Never cat a large file into your own context. Run independent subagents in parallel.
4. **Verify before you claim.** Never generalize from a partial batch; label partial numbers
   "n/N so far". A RUNNING job state or a growing log is not evidence; see P3 for what is.
5. **Never edit code a running job imports.** Code changes happen only in the development worktree,
   by the other agent or by me, and reach a run only through a new CODE_COMMIT and a new run worktree.
6. **Commits:** you do not need to commit to the code repo. If you ever commit anything, the author is
   `Vinit Awale <awale.vinit@gmail.com>`, and the message has no AI attribution lines (no
   `Co-Authored-By: Claude`, no "Generated with Claude Code").
7. **Cluster rules** in `~/.claude/CLAUDE.md` apply: no heavy work on login nodes or babel-cpu; sbatch
   or allocations with explicit resources; logs in `ROOT/logs/`; data never in `/home`; release GPUs.
8. **Ask, do not assume.** Stop and ask me before any step that spends Claude usage, deletes data, or
   departs from this protocol. Write questions as a numbered list with your recommendation first.

## 2b. Authentication: my personal Claude subscription (no API key)

These runs bill my **personal Claude subscription** through Claude Code's own login, not the Anthropic
API. I chose this knowingly. The authors' harness deliberately refuses the operator's personal account,
so it needs one small, explicit, documented change:

- **Provider:** the harness's `claude-login`. It gives Claude Code a long-lived `claude setup-token`
  token (env `CLAUDE_CODE_OAUTH_TOKEN`) read from `~/.config/rax/claude-experiment.token` (mode 600),
  with the account identity in `~/.config/rax/claude-experiment.json`.
- **The one code change is mine, not yours.** I make it myself in `harness/claude_cli/experiment_login.py`:
  an opt-in `RAX_ALLOW_PERSONAL_CLAUDE_LOGIN=1` that lets the `install` and `check` commands accept my
  personal account, and nothing else (`~/.claude` paths and credential files stay refused). Do not write
  or modify this check yourself. Before launch, ask me whether it is done, then confirm it is contained in
  CODE_COMMIT (`git -C CODE_WORKTREE log --oneline -- harness/claude_cli/experiment_login.py` and
  `git diff bcd748c CODE_COMMIT -- harness/claude_cli/experiment_login.py`, that file only). Record it in
  DECISIONS.md as a deviation ("auth only; does not touch the agent, prompts, tools or evaluation") with
  its commit hash. If it is missing, stop and ask me.
- **Setup is interactive and needs me at a browser** (once for all 5 tasks, unless the token is gone).
  Ask me to run, in my own terminal on babel-cpu:
  `cd CODE_WORKTREE && RAX_ALLOW_PERSONAL_CLAUDE_LOGIN=1 bash scripts/setup_claude_experiment_login.sh --email <my account>`.
  It signs in under its own config dir (`~/.config/rax/claude-experiment-home`; my `~/.claude` is never
  read or copied), issues the token with `claude setup-token`, and stores it. Never attempt the browser
  sign-in yourself, and never read, print or copy the token.
- **Check before every launch:**
  `cd CODE_WORKTREE && RAX_ALLOW_PERSONAL_CLAUDE_LOGIN=1 PYTHONPATH=. runtime/envs/host/bin/python -m harness.claude_cli.experiment_login check`
  (a free count_tokens probe). Record the result in STATE.md. This helper has no usage command, so ask
  me how much of my usage limit is left (I see it in Claude's settings).
- **Shared limits:** the RaX agent draws on the same limits as my interactive use, including you and
  your subagents. One RaX agent session at a time across all 5 tasks: before launch, run
  `squeue -u $USER` and check `ROOT/../*/STATE.md` for another live agent session; if one runs, stop
  and tell me. While the agent runs, keep your own usage low (few subagents, short checks).
- Do not pass `--claude-key-file` or `--key-file`, and do not use `~/.config/rax/anthropic_api_key`.
- **Afterwards** (after the last of the 5 tasks): remind me that I can revoke the setup-token (Claude
  settings) and delete `~/.config/rax/claude-experiment.token`.

## 3. Phases

Each phase ends with an update of STATE.md (and DECISIONS/MANIFEST if needed) and a one-line message to
me. Paths below: `WT` = CODE_WORKTREE, `R` = ROOT, `G` = the GPU UUID of the task's job.

### P0. Orient (no GPU, no usage)
1. Read this file and the task file. If `R/STATE.md` exists, you are resuming: read STATE, DECISIONS,
   MANIFEST and continue from the recorded phase; do not redo passed gates.
2. Run `hostname`, `echo $SLURM_JOB_ID`, `squeue -u $USER`. Do not touch jobs you did not start
   (e.g. my rc-cpu front-desk job). Write the job list into STATE.md.
3. Create `R/{logs,notes,results,tools,report,jobs,runtime}`, `STATE.md`, `DECISIONS.md`,
   `MANIFEST.md`. Copy COMMON.md and the task file into `R/prompts/`.
4. Copy the reusable tools into `R/tools/`: `~/my_things/codes/rax-reproduction/tools/watch_session.py`
   (usage watcher) and `make_source_copy.py`. `make_clips.py` and `runs_table.py` are Hanoi-specific
   (stage captions, log regexes; `make_clips.py` reads `runs_table.json`): read them and adapt them, or
   write new task versions. `make_results_and_chart.py` is a template for `make_results.py`. Read each
   before use.

### P1. Verify code, environments and gates (GPU job, no usage)
1. **Code.** CODE_COMMIT must be filled in. If it is still a placeholder, stop and ask me.
   `git -C ~/my_things/codes/rax fetch fork` (remote `fork` = `TheShiningVampire/rax`), then
   `git -C ~/my_things/codes/rax worktree add --detach .worktrees/state-run-<TASK> CODE_COMMIT`.
   If the task file names an EXISTING worktree as CODE_WORKTREE (e.g. `.worktrees/add-state-info`), do
   not create one: use it as WT, and treat it as frozen (no edits, checkouts or commits in it by anyone
   until this run's formal evaluation ends; record that in DECISIONS.md). An existing `WT/DexJoCo`
   symlink is fine if it resolves to `/data/user_data/vawale/rax_repro_v2/DexJoCo`.
   Gate: `git -C WT rev-parse HEAD` == CODE_COMMIT and `git -C WT status --short` is empty.
   Record both outputs. Re-check this right before launch.
   Then `git -C WT diff --stat bcd748c HEAD` and have a subagent summarize every changed file in
   `R/notes/code_diff.md`. The expected set of changed files is exactly:
   `services/benchmarks.py`, `services/dexjoco/{backend,benchmark,session,tools,objects,goals}.py`,
   `services/exploration/pool.py` and `harness/codex_cli/auto_research.py` (both keep
   `RAX_PRIVILEGED_STATE` in the exploration workers' and the launcher frontend's environment, via
   `SESSION_KEPT_ENV` in objects.py), `scripts/render_workspaces.py` (goldens render at the default
   level), `local_tests/unit/test_dexjoco_object_states.py`, `local_tests/unit/test_dexjoco_goals.py`,
   `scripts/object_states_smoke.py`, `auto_research_agent/AGENTS.md`, `auto_research_agent/FORMAL_AGENTS.md`,
   `agent_skills/control/dexjoco/robot-interface/SKILL.md`, `agent_skills/task/manual-robot-control/SKILL.md`,
   `local_tests/goldens/workspaces.json`, and `harness/claude_cli/experiment_login.py` (my auth opt-in).
   Anything else: stop and ask me.
   Also write in DECISIONS.md what the agent can read about success for TASK: the `goal` conditions,
   failure conditions, targets and holding counter (task file section B, citing `services/dexjoco/goals.py`
   lines; re-check the line numbers at CODE_COMMIT), and tell me at the end of P1.
2. **Runtime links.** `ln -s R/runtime WT/runtime`; `ln -s /data/user_data/vawale/rax_repro_v2/DexJoCo WT/DexJoCo`
   (check where it resolves); `R/runtime/envs/{host,dexjoco}` -> symlinks to `REUSE_ENVS/{host,dexjoco}`;
   also link `miniforge3` and `pip-cache` from `/data/user_data/vawale/rax_repro_v2/runtime/`. Use the
   links read-only: never run `setup_host_env.sh` or `setup_dexjoco_env.sh` through them (they
   pip-install into the shared envs). Fresh dirs: `reference-demos`, `auto-research`, `diagnostics`,
   `integration-tests`, `xdg-*`.
3. **GPU jobs.** Do not hold a GPU while waiting for me. The gates run as their own batch job (P1.4);
   the session runs as a second batch job submitted only after my go-ahead (P2.5). Request
   `--gres=gpu:RTX_PRO_6000:1 --exclude=babel-z9-16` on katef/katef_qos, 8 CPU, 60 GB, for the gates
   AND the session job. Never use an A100 (MuJoCo's MSAA framebuffer fails with `error 0x8cdd`).
   babel-z9-16 (RTX PRO 6000) has broken EGL since 2026-10-21 (0x8cdd even without MSAA; jobs 10880136,
   10880177); I approved excluding it (2026-10-21). The same tool passed its GPU smoke on babel-l9-16
   (jobs 10880362, 10880424). If G2, G4 or G5 fail with 0x8cdd on any OTHER node, stop. Report job,
   node and error, and tell me to post in #babel-babble. Do not exclude further nodes without my OK. If you use a `gpu_hold.sbatch` hold job anyway (or GPU_JOB is set), scancel it if I
   have not answered within 1 h. Record job id, node, GPU name and driver from `R/logs/<id>.out`.
4. **Gates.** Run them as one batch script modeled on `/data/user_data/vawale/rax_repro_v2/jobs/phase1_gates.sbatch`
   (copy it to `R/jobs/gates.sbatch`, set V2->R, WT, TASK, `--time=3:00:00`, `--output=R/logs/%j.out`;
   it records `rc=` per gate and exits non-zero if any gate fails). Either `sbatch` it, or run it inside
   GPU_JOB with `srun --jobid=<GPU_JOB> --overlap -n1 bash R/jobs/gates.sbatch < /dev/null`. Environment inside:
   `export RAX_RUNTIME_ROOT=R/runtime; unset XDG_CACHE_HOME XDG_RUNTIME_DIR; source scripts/host_env.sh; export PATH=/data/user_data/vawale/rax_repro_v2/bin:$PATH`
   (pinned Claude Code; record `claude --version`), `export TMPDIR=/scratch/$USER/rax_state_<TASK>_$SLURM_JOB_ID`
   (create it), never `/tmp`, and `export RAX_PRIVILEGED_STATE=full` (echo it into the log). `host_env.sh`
   keeps inherited XDG_* values, so the `unset` is required.

   | Gate | Command (from WT) | Pass evidence |
   |---|---|---|
   | G1 sandbox | `bash scripts/doctor.sh`; `python -m pytest -m 'not gpu' -q -rs local_tests/unit` | doctor rc=0; pytest rc=0 or only the known failure `test_runaway_output_stops_the_controller` |
   | G1b object-state tests | `python -m pytest -q local_tests/unit/test_dexjoco_object_states.py local_tests/unit/test_dexjoco_goals.py` (run on the GPU node) | "54 passed" at 223f1a8 (36 + 18; re-count at CODE_COMMIT with `--collect-only`), none skipped; includes `test_the_full_reply_survives_the_agent_filter_unchanged` and `test_copied_literals_match_the_official_source`; list test names in STATE |
   | G2 simulator | `python scripts/dexjoco_doctor.py --gpu $G --task TASK --output R/runtime/diagnostics/g2-TASK` | rc=0 (cameras, depth, determinism); look at its `sensors.mp4` |
   | G3 prompts | `python scripts/render_workspaces.py --check local_tests/goldens/workspaces.json`, then `--out R/prompts/golden --case dexjoco/auto-research/exploration-claude/rgbd/env1-sub0` (pick_bucket, single arm) and `--out R/prompts/golden-bimanual --case dexjoco/auto-research/exploration-bimanual/rgbd/env1-sub0` (Hanoi, bimanual) | "identical" against the goldens at CODE_COMMIT (the goldens record the default level, `full`); the rendered AGENTS.md contains "object state comes through `dexjoco_object_states`: use it"; robot-interface/SKILL.md no longer contains "find objects in the images" and does contain "Its `privileged_level` here is `full`" and the `contacts` and `goal` bullets (`--out` renders at the shell's level, so this also shows the export reached it) |
   | G4 demos | `python scripts/setup_dexjoco_demos.py --gpu $G --task TASK` | rc=0; terminal-state images exist under `R/runtime/reference-demos/` |
   | G5 object-state smoke | step 1: `PYTHONPATH=. $RAX_PYTHON scripts/object_states_smoke.py --gpu $G --task TASK --out R/results/smoke` with `RAX_PRIVILEGED_STATE=full` exported (real backend through the agent's reply filter, exploration layout 0 = env seed 1000; reads at step 0 and after 10 holds); step 2: `R/tools/smoke_object_states.py` reads `R/results/smoke/object_states_smoke.json` and applies the task file's section D ranges, including its goal rows | step 1 exits 0 and prints `TASK: OK`: every label, finite values, unit quaternions, reset-tail match, and the full-level checks (`check_full`): `privileged_level == "full"`; every free/body object has finite 3-vector velocities, about 0 at step 0, and a `size` with 3 non-negative half extents; `contacts` a list of well-formed rows, at most 64, sorted by force; `goal.available` with non-empty `conditions`, every row shaped, `targets` non-empty, `holding` well-formed where present, `satisfied_now` False at step 0. Step 2 writes `R/results/smoke_object_states.json` with every section D range passing |

   If a gate fails because the cluster is broken (mounts, drained nodes, QoS errors), stop and tell me to
   post in `#babel-babble` with username, job id, node and exact error. Do not retry in a loop.
5. Record Claude Code version, GPU model, driver, bwrap version, and every deviation from the authors'
   tested setup (`WT/docs/SETUP.md`) in DECISIONS.md.

### P2. Configure, ask, launch (spends usage after my go-ahead)
1. **Configure** (from WT, on a GPU node: for the dry run, as the last step of the gates job or a short
   katef job; for the real run, again inside `R/jobs/session.sbatch` with that job's GPU UUID):
   ```
   runtime/envs/host/bin/python scripts/configure_auto_research.py --task TASK --sim-gpu $G \
     --episodes 8 --agent-cli claude --agent-provider claude-login --agent-effort xhigh \
     --demonstration-context terminal_state --task-rules public --episode-reviews off \
     --formal-episodes 150 --formal-workers 4
   ```
   Leave `--exploration-start-seed` at its default (the CLI forces 0 for DexJoCo: the paper's layouts).
   There is no CLI flag for the tool or its level: the level is only `RAX_PRIVILEGED_STATE`, which must
   be exported (`full`) in the same shell before configure and launch. `operator-input.json` does not
   record it, so record it in STATE.md and DECISIONS.md. The config lands in
   `R/runtime/auto-research/<id>/operator-input.json`.
2. **Dry deployment:** `bash scripts/start_auto_research_agent.sh --config <dir>/operator-input.json --prepare-only`
   (no model, no episode). Diff the deployed workspace against `R/prompts/golden/` (single-arm tasks)
   or `R/prompts/golden-bimanual/` (the 3 bimanual tasks); a subagent explains every difference in
   `R/notes/workspace_diff.md`. The only expected ones: task name, task rules, single-arm vs dual-arm
   text, and (for the bimanual golden) codex vs claude files. The goldens at CODE_COMMIT already contain
   the object-state text, the tool and the full-level sentences: these must NOT differ. The deployed
   robot-interface/SKILL.md must contain "Its `privileged_level` here is `full`". If it says "It reports
   no success information" instead, the export did not reach the deploy: stop and tell me.
3. **Pre-launch checks:** HEAD == CODE_COMMIT and clean tree; `session.sbatch` exports
   `RAX_PRIVILEGED_STATE=full` (grep it); auth opt-in confirmed (2b); experiment login `check` passes; no other RaX agent session is live; no gates or hold job left holding a GPU.
   After submitting `session.sbatch`, confirm it RUNS on a non-A100 GPU (record node, GPU, driver).
4. **Ask me** (and wait): "Ready to launch TASK. Expected usage (v1 reference, budget-8 Hanoi session):
   about 0.65 M output tokens and 57 M cache-read tokens over 2.6 h of agent time. How much of your
   usage limit is left? Go?" Record my answer in DECISIONS.md.
5. **Launch headless** (default, v2 decision D12): write `R/jobs/session.sbatch` with `-p katef
   --qos=katef_qos --gres=gpu:RTX_PRO_6000:1 --exclude=babel-z9-16 --cpus-per-task=8 --mem=60G --time=1-12:00:00
   --output=R/logs/%j.out`. It runs configure (P2.1, with this job's GPU UUID), then the launch, then
   waits for formal eval to finish, and exits non-zero if the launcher fails. Body:
   ```
   cd WT && export RAX_RUNTIME_ROOT=R/runtime && unset XDG_CACHE_HOME XDG_RUNTIME_DIR \
     && source scripts/host_env.sh && export PATH=/data/user_data/vawale/rax_repro_v2/bin:$PATH \
     && export TMPDIR=/scratch/$USER/rax_state_<TASK>_$SLURM_JOB_ID && mkdir -p $TMPDIR \
     && export RAX_ALLOW_PERSONAL_CLAUDE_LOGIN=1 && export RAX_PRIVILEGED_STATE=full \
     && echo "RAX_PRIVILEGED_STATE=$RAX_PRIVILEGED_STATE" \
     && bash scripts/start_auto_research_agent.sh --config <dir>/operator-input.json --non-interactive
   ```
   Submit it only after my go-ahead in P2.4. No key-file flag: the launcher reads the experiment token
   and runs its own preflight. Option (only if I agree): `setsid nohup srun --jobid=<GPU_JOB> --overlap
   -n1 bash -c '<same body>' > R/logs/launch_<UTC>.log 2>&1 < /dev/null &` from babel-cpu. Use it only
   if my front-desk job's renewal (`squeue -u $USER`, rc-cpu job 10830840) falls outside the whole run
   (session + formal); the renewal kills the srun client.

### P3. Monitor (usage is being spent)
1. Start the usage watcher on babel-cpu:
   `setsid nohup python3 -I R/tools/watch_session.py <session_dir> R/results/watch 1000000 WT > R/logs/watch.log 2>&1 < /dev/null &`.
   The cap is set huge on purpose: it must never stop the session. It sums transcript tokens by message
   id, logs a per-minute timeline (`R/results/watch/timeline.jsonl`), and copies the deployed workspace.
   Its dollar figure is an API-equivalent cost for the report only; nothing is billed per token.
2. **Evidence of a healthy session** (paste it in STATE.md with timestamps): across two checks at least
   2 minutes apart, the episodes-used count in `state.json` or the number of MCP calls in `mcp.jsonl`
   rises, or output tokens in the timeline rise; and `nvidia-smi` on the node shows non-zero utilisation
   while an episode is open (low utilisation is normal: physics is CPU-bound, v1 ~5%).
3. Check every 20-30 minutes with short commands, not by reading transcripts. Count
   `dexjoco_object_states` calls in `mcp.jsonl` as you go. At the first call, confirm the reply (if
   `mcp.jsonl` or the transcript records it) says `"privileged_level": "full"` and has `goal` and
   `contacts`; record the evidence in STATE.md. If it says `objects`, tell me at once (the launcher
   frontend keeps `RAX_PRIVILEGED_STATE` since 223f1a8; a mismatch means the export was lost).
4. **usage_wait:** if `agent-lifecycle.json` shows `usage_wait`, report it to me right away (time,
   `usage_limited_until`), record it, and do not start anything that uses Claude. Open episodes stay
   live during a wait and can hit their per-task wall limit (water_plant 5600 s, fold_glasses 6600 s,
   bimanual_microwave_cook 6100 s, bimanual_photograph 5600 s, bimanual_hanoi 8100 s); the harness
   counts that as it counts it. Compare `usage_limited_until` + about 3 h of formal eval with the GPU
   job's TimeLeft (`squeue -j <id> -o %L`). If it does not fit, tell me at once.
5. If the session fails or stops, record the state, do not relaunch or `--resume` without asking me,
   and ask me whether to scancel the GPU job.

### P4. Formal evaluation (no usage)
- It starts automatically after submit (150 episodes, 4 workers; Hanoi took about 2.3 h in v1; others
  should be shorter). It needs no Claude usage.
- Do not interpret partial results. Report progress only as "n/150 done". The verdict comes from the
  simulator (`task_complete` in `state.json` / `formal-report.json` / `formal-scores.json`), never from
  the program's printed `task_complete`.
- When `formal-scores.json` is complete, stop the watcher.

### P5. Results, notes, clips, summary; release the GPU
1. **Results script:** write `R/tools/make_results.py` that writes `R/results/TASK.json` with: success
   n/150 and per official seed; failure stages (from formal runs' logs); agent time and wall time
   (separately, usage_wait excluded from agent time); usage_wait periods; tokens by kind and
   API-equivalent cost (Opus 5.5: $4 in / $20 out / $0.20 cache read / $8 per MTok 1 h cache write);
   exploration episodes used; `dexjoco_object_states` calls during exploration (count, first call time,
   episode); whether the submitted `controller.py` calls it (static grep) and how often per formal
   episode (from logs); which full-level fields the program reads (static grep for `goal`,
   `satisfied_now`, `conditions`, `holding`, `contacts`, `velocity`, `size`); the privileged level
   (`full`, from the first reply); the paper's @8 number for TASK; CODE_COMMIT, Claude Code version, GPU.
2. **Session note** (subagent): `R/notes/session.md`: episode-by-episode chapters (wall time, what it
   tried, learned, outcome); when and how the agent used `dexjoco_object_states` (which labels, for
   what: localisation, checking grasps, closing loops), and how it used the full-level fields: whether
   it read `goal` (conditions, thresholds, targets, holding) to plan or to decide when it was done,
   `contacts` to check grasps or button presses, velocities to wait for things to settle, `size` for
   grasp widths; whether and how the program calls it; what it
   still takes from cameras; hard-coded constants; failure handling; failure stages in the formal run.
   Then a skeptical fact-check subagent checks it against raw files; fix what it rejects.
3. **Clips** (subagent): 2-3 breakthrough clips from the episodes' `sensors.mp4` (30 fps, frame k = sim
   step k) into `R/report/clips/`, using the task file's section F; captions in plain short sentences.
4. **Summary:** `R/report/summary.md`, at most one page: TASK, paper @8 (vision only) vs ours @8 (with
   full privileged state, `RAX_PRIVILEGED_STATE=full`) as n/150 and %, agent time, usage and waits, how
   the agent used the tool (including `goal` and `contacts`), 2-3 clips,
   caveats (section 7). Every number re-read from `R/results/TASK.json` just before writing.
5. **Release:** `scancel` the session job (and any hold job) once formal eval, clips and any GPU work are done. Confirm with
   `squeue -u $USER`. Remove the run worktree only if I say so (`git worktree remove`).
6. Tell me: "TASK done", the headline line, the summary path, and anything open.

## 4. Deliverables (per task, all under ROOT)
`STATE.md`, `DECISIONS.md`, `MANIFEST.md`, `prompts/` (copies of COMMON and the task file),
`notes/code_diff.md`, `notes/workspace_diff.md`, `notes/session.md` (+ its fact-check), `tools/*.py`,
`results/smoke_object_states.json`, `results/TASK.json`, `results/watch/`, `report/clips/`,
`report/summary.md`, `logs/`.

## 5. Budget and resource rules
- Stop and ask before anything that spends subscription usage. State the expected usage (v1 budget-8
  session: about 0.65 M output tokens, 57 M cache-read tokens, 2.6 h agent time; paper Table 17 median
  at budget 8: 1.34 h, range 0.59-3.02 h). Ask how much limit is left. One RaX agent session at a time.
- One 1-GPU katef job per task (8 CPU, 60 GB). The bottleneck is CPU (MuJoCo physics + the program),
  not the GPU. Keep `--formal-workers 4` (the protocol); do not add workers.
- Release the GPU job as soon as its work ends (v1 once left one idle for 8 hours). Do not leave a
  batch job holding a GPU it never uses.
- Storage: everything under ROOT on `/data/user_data/vawale`. Nothing in `/home` except the worktree
  code. `/tmp` is node-local: anything a GPU node must read or write lives under ROOT or `/scratch`.

## 6. Lessons from v1 and v2 that still apply
6.1 Setup
- Cluster bubblewrap 0.6.3 lacks `--size`, so 12+ sandbox tests fail. The reused host env already has
  conda-forge `bubblewrap>=0.9` and `socat` (on PATH via `scripts/host_env.sh`); check `bwrap --version`.
  Known remaining failure: `test_runaway_output_stops_the_controller` (output guard on NFS), off path.
- The default `--agent-cli` is codex and the default provider is openrouter: always pass both.
- `rc-box gpu` fails if `~/rc/env/babel-gpu-box` is not trusted in Claude Code; use `gpu_hold.sbatch`
  and attach with `srun --jobid=<id> --overlap`.
- `/tmp` is node-local. In zsh never name a variable `path` (it clobbers PATH). Inside `while read`
  loops give `srun` `< /dev/null`, or it eats the loop's input.
- `dexjoco_doctor.py`'s simulator checks build their own env, not through the session; verify
  session-level behaviour (including the new tool) through the session path, not the doctor.
- The launcher used to strip every `RAX_*` variable from the frontend (which serves the tool text, the
  exploration simulators and formal evaluation), so they fell back to the default level while the
  workspace was rendered at the shell's level. 223f1a8 keeps `RAX_PRIVILEGED_STATE`
  (`SESSION_KEPT_ENV`). Exporting `full`, the default, keeps every component at the same level even if
  something still drops it; check the first reply anyway (P3.3).
- A100 GPUs fail the official scenes' MSAA framebuffer; request `gpu:RTX_PRO_6000:1` (v2 ran there).
  babel-z9-16 (RTX PRO 6000) has broken EGL (0x8cdd); always pass `--exclude=babel-z9-16` (approved).
  If G2, G4 or G5 fail with 0x8cdd on any other node, stop. Report job, node and error, and tell me to
  post in #babel-babble. Do not exclude further nodes without my OK.
- Never run setup scripts through the shared env symlinks.

6.2 Running and measuring
- The harness uses 1 h prompt caching; about 85-90% of token volume is cache reads.
- Use the simulator's verdict (`task_complete` in state.json / formal-report.json), never the
  program's printed `task_complete` (in v1 it was always False at the end).
- Never interpret partial batches: in v1 a 9-episode sample suggested a "working window" of layouts
  that the full 150 did not show.
- Waiting time (`usage_wait`) is not agent time: report agent time and wall time separately.
- The Gemini skill stays advertised to the agent although Gemini is off; its calls fail with "Gemini
  is not configured". Do not change it; count such calls.
- `services.controller.parallel_batch` fingerprints planner files (incl. `services/dexjoco/session.py`)
  at start and aborts ("Planner infrastructure changed during the batch") if they change. Never edit
  code a running batch imports. It also holds an exclusive lock on its source session; for any extra
  re-scoring use a copy (`R/tools/make_source_copy.py`).
- Single session per cell, like the paper: a gap to the paper's number can be session-to-session
  spread. v1 vision-only Hanoi: 54.7% fresh vs the paper's 100%.

6.3 Reporting
- My advisor wants it easy to read, honest and fair. Plain short sentences.
- Lead with the agent's breakthroughs; show what it found and when.
- The agent's private reasoning is not stored. Activity lines come from visible messages, tool calls,
  notes and stage logs. Say so.

## 7. What changed vs the authors, and how to say it
Changed on purpose (the experiment):
1. The `dexjoco_object_states` MCP tool at the `full` privileged level (`RAX_PRIVILEGED_STATE=full`),
   available in exploration and to the compiled program: object poses, joint and hinge angles, named
   points, velocities, collision sizes, contacts, and the task's official success conditions with their
   thresholds, targets and hold counters (`goal`).
2. The agent-facing rule text in `auto_research_agent/AGENTS.md` ("The simulator's object state comes
   through `dexjoco_object_states`: use it. Do not seek other simulator internals ..."), plus matching
   text in `auto_research_agent/FORMAL_AGENTS.md`, `agent_skills/control/dexjoco/robot-interface/SKILL.md`
   (no longer "find objects in the images"; cameras remain available; at `full` its "## Object state"
   section and the MCP tool description list the velocity, size, contact and goal fields) and
   `agent_skills/task/manual-robot-control/SKILL.md`.

Arm B only: 3. the `dexjoco_lookahead` tool and its "## Lookahead" skill text (`RAX_LOOKAHEAD=on`);
add section 1c's report paragraph to the one below.

Changed for running only (not the experiment): my auth opt-in in `experiment_login.py` (auth only);
Claude Code version (pinned binary, record it); no Gemini; newer bubblewrap; one session per task.
Unchanged: the agent, model, effort, other skills, other tools, budget, demonstrations, task rules apart from
the text above, seeds and formal evaluation.

How to say it in the report, word for word in spirit: "This is an extension, not a reproduction. The
agent could read the simulator's privileged state through one extra tool at its full level, which the
paper's agent did not have: object poses, joint angles, named object points, velocities, object sizes,
contacts, and the task's success conditions written out, with their thresholds, target regions and
hold counters, and whether each holds at the current step. Everything else follows the paper's DexJoCo protocol at a budget of 8 episodes. The paper's numbers are vision only
and come from one session per task, and so do ours, so a difference of one task can be session-to-session
spread." Never call the comparison a reproduction, and never call a higher number "solving" the paper's
setting.
