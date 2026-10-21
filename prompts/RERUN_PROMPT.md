# Prompt: rerun the RaX reproduction experiment (v2)

Paste everything below the line into a fresh Claude Code session started in
`~/my_things/codes/rax` (on babel-cpu or a katef-cpu box). Edit the PARAMETERS block first.

---

## 0. Who you are working for and what this is

I am a PhD student. My advisor asked: **can the RaX paper (arXiv 2610.22496, "Scaling Online Exploration
for Robot Agents"; repo already cloned at `~/my_things/codes/rax`) be reproduced from what the authors
released, and how robust is the code-as-policy it produces?** A previous attempt (v1) answered this for one
task. This is v2: **a cleaner, pre-registered rerun of the same experiment**, designed so results do not
depend on one long, drifting conversation. Treat v1 as a pilot: reuse its lessons (section 6), not its numbers.

RaX in one paragraph: a coding agent (Claude Code + Opus 5.5) controls a robot (here: simulated) through MCP
tools, explores a task for a budget of N episodes, then writes `code/<project>/controller.py:main(ctx)`, a
program that runs the task with no agent. The harness rehearses it, the agent submits it, and the harness
scores it alone on the benchmark's official test layouts. The repo's `main` branch is only an index; code
lives on branches (`dexjoco/native` is the one we use).

## 1. PARAMETERS (edit before starting)

```
ROOT            = $ROOT_v2     # all runtime data, logs, results
CODE_WORKTREE   = ~/my_things/codes/rax/.worktrees/dexjoco-v2        # agent + formal runs (frozen once a run starts)
PERT_WORKTREE   = ~/my_things/codes/rax/.worktrees/dexjoco-v2-pert   # perturbation hooks (separate copy, see 6.3)
TASK            = bimanual_hanoi           # DexJoCo, two Franka arms + Allegro hands
BUDGET          = 8                        # exploration episodes per session (paper: 100% at 8)
N_SESSIONS      = 3                        # INDEPENDENT fresh sessions at BUDGET (the paper runs 1; v1 suggested large spread)
ADAPT           = yes                      # after the fresh sessions: continuation runs (see Phase 4)
GEMINI          = off                      # set to "on" only if an OpenRouter key exists at ~/.codex/secrets/openrouter_api_key
AUTH            = claude-login             # Claude Code SUBSCRIPTION login, not the API (see section 2b)
CLAUDE_ACCOUNT  = <my personal Claude account email>   # I chose my personal account, one-off, for today (section 2b)
MAX_CONCURRENT_AGENT_SESSIONS = 1          # my personal limits are shared with my own interactive Claude Code use
GPU_JOBS_MAX    = 4                        # concurrent 1-GPU katef jobs (8 CPU, 60 GB each)
REUSE_V1_ENVS   = yes                      # may symlink v1's conda envs/DexJoCo checkout read-only; otherwise rebuild
DEADLINE        = <date/time>              # report must be published by then
```

## 2. Operating rules against context rot (read twice; these override convenience)

The v1 run lasted ~20 hours in one conversation. It worked, but long context caused stale numbers, a
claim made from a 9-episode sample that the full 150 overturned, and code edits that broke running jobs.
v2 must be robust to that. Concretely:

1. **Disk is the memory, not the conversation.** Keep three files under `ROOT/` and treat them as the
   single source of truth:
   - `STATE.md`: current phase, what is running (job ids, PIDs, output dirs), what is done, what is next.
     Overwrite it (do not append) at every phase boundary and after every launch/finish.
   - `DECISIONS.md`: append-only; every decision with date, reason, and who decided (me vs you).
   - `MANIFEST.md`: append-only index of every artifact path (session dirs, logs, scripts, clips, reports).
   **At the start of every phase, and whenever you resume, re-read all three before doing anything.**
2. **Numbers only come from scripts, never from memory.** Every number that reaches a report or a message
   to me must be produced by a script under `ROOT/tools/` that reads the raw files (state.json,
   formal-scores.json, formal-report.json, mcp.jsonl, stdout logs) and writes `ROOT/results/*.json`.
   Re-run the script right before quoting. If you quote a number you did not just regenerate, say so.
3. **One phase, one fresh context.** Each phase below ends with a written handoff
   (`ROOT/handoff/phase<N>.md`: what was done, what is true now, file paths, open issues, next actions).
   After writing it, tell me "Phase N done, handoff written" and recommend continuing in a NEW session with
   the prompt "Continue the RaX v2 experiment: read ROOT/STATE.md, DECISIONS.md, MANIFEST.md and
   ROOT/handoff/phase<N>.md, then do phase N+1 of ROOT/RERUN_PROMPT.md." Long-running jobs keep running
   across sessions; nothing important may live only in a conversation.
4. **Keep the main thread thin.** Delegate reading of large things (transcripts, mcp.jsonl, branches,
   the paper, logs of 150 runs) to subagents or a workflow. They write findings to files under
   `ROOT/notes/` and return <=200-word summaries. Never cat large files into the main context.
5. **Verify before you claim.** Any load-bearing claim (a cause of failure, what changed between
   programs, "X never happens") gets an independent skeptical fact-check pass that defaults to "wrong"
   when unsupported. Never generalize from a partial batch; label partial numbers "n/N so far".
6. **Pre-register.** Before any paid run, write `ROOT/PREREG.md`: hypotheses, exact configs, seeds,
   budgets, caps, the metrics and comparisons you will report, and what would count as reproduced.
   Deviations later go into DECISIONS.md with reasons; never silently change the plan.
7. **Never edit code that a running job imports** (see 6.3). All code changes happen in a separate
   worktree or between runs, and are committed (author Vinit Awale <awale.vinit@gmail.com>, no AI
   attribution lines) so every result names the exact code commit it ran with.
8. Follow my global cluster rules in `~/.claude/CLAUDE.md` (no heavy work on login/babel-cpu, sbatch or
   allocations with explicit resources, logs in `ROOT/logs/`, data never in /home, release idle GPUs).

## 2b. Authentication: my personal Claude subscription (no API key)

This rerun bills my **personal Claude subscription** through Claude Code's own login, not the Anthropic API.
I chose this knowingly, as a one-off for today. The authors' harness deliberately refuses the operator's
personal account, so this needs one small, explicit, documented change:

- **Provider:** the harness's `claude-login`. It gives Claude Code a long-lived `claude setup-token` token
  (env `CLAUDE_CODE_OAUTH_TOKEN`) read from `~/.config/rax/claude-experiment.token` (mode 600), with the
  account identity in `~/.config/rax/claude-experiment.json`.
- **The one code change (v2 only) is mine, not yours.** I will make it myself in CODE_WORKTREE's
  `harness/claude_cli/experiment_login.py`: an opt-in `RAX_ALLOW_PERSONAL_CLAUDE_LOGIN=1` that lets the
  `install` and `check` commands accept my personal account, and nothing else (`~/.claude` paths and
  credential files stay refused). Do not write or modify this check yourself. Your job: before any
  session starts (rule 7), ask me whether it is done, then confirm it is committed (`git log`/`git diff`
  on that file only) and record it in DECISIONS.md as a deviation ("auth only; does not touch the agent,
  prompts, tools or evaluation"), with the commit hash. If it is missing, stop and ask me.
- **Setup is interactive and needs me at a browser.** Ask me to run, in my own terminal on babel-cpu:
  `cd CODE_WORKTREE && RAX_ALLOW_PERSONAL_CLAUDE_LOGIN=1 bash scripts/setup_claude_experiment_login.sh --email CLAUDE_ACCOUNT`.
  It signs in under its own config dir (`~/.config/rax/claude-experiment-home`; my `~/.claude` is never
  read or copied), issues the token with `claude setup-token`, and stores it. Never attempt the browser
  sign-in yourself, and never read, print or copy the token.
- **Check before every launch:** `RAX_ALLOW_PERSONAL_CLAUDE_LOGIN=1 PYTHONPATH=. runtime/envs/host/bin/python -m harness.claude_cli.experiment_login check`
  (a free count_tokens probe). Record the result in STATE.md. There is no usage command in this helper,
  so before each launch ask me how much of my usage limit is left (I can see it in Claude's settings).
- **Shared limits:** these sessions draw on the same limits as my interactive Claude Code use, including
  the session running you. Run one agent session at a time (MAX_CONCURRENT_AGENT_SESSIONS = 1), and tell
  me before each launch so I can avoid heavy interactive use meanwhile. If a session enters `usage_wait`,
  report it, and do not start another.
- Do not pass `--claude-key-file` and do not use `~/.config/rax/anthropic_api_key` in this rerun.
- **Afterwards:** when the rerun is finished, remind me that I can revoke the setup-token (Claude settings)
  and delete `~/.config/rax/claude-experiment.token`.

## 3. Phases (each ends with STATE/handoff update and my go-ahead before spending usage)

### Phase 0: Ground truth on what is released (no GPU, no money)
- Subagents (parallel): (a) per-branch inventory of what is released vs not (prompts, skills, task rules,
  harness, eval code, compiled controllers, session logs, configs, licence); (b) the paper's claims,
  especially DexJoCo Table 5/17 and the TASK's row, protocol details (agent, effort, Gemini, seeds,
  sessions per cell); (c) the authors' project-page case study for TASK (chapters, published program
  excerpt, video list) from https://robot-agent-exploration.com/ (`assets/js/simcases.js`).
- Output: `ROOT/notes/released.md`, `ROOT/notes/paper_claims.md`, `ROOT/notes/authors_case.md`, each with
  a verification section. Then grill me briefly (numbered questions, your recommendation first) only on
  decisions the PARAMETERS block leaves open.

### Phase 1: Environment and prompt verification (CPU job + 1 GPU job, no Claude usage)
- Worktree `CODE_WORKTREE` from `origin/dexjoco/native`; `RAX_RUNTIME_ROOT=ROOT/runtime`. Read every setup
  script before running it. Build envs inside a katef-cpu sbatch job (or reuse v1's if REUSE_V1_ENVS).
- Gates (record pass/fail with evidence in STATE.md):
  G1 sandbox: `doctor.sh`, then the unit tests (`pytest -m "not gpu" local_tests/unit`) on the GPU node.
  G2 simulator: `dexjoco_doctor.py --gpu <uuid> --task TASK` passes (cameras, depth, determinism).
  G3 prompts: `render_workspaces.py --check local_tests/goldens/workspaces.json` → "identical"; render the
     TASK case to `ROOT/prompts/golden/`; after the first launch, diff the deployed workspace against it
     and explain every difference.
  G4 demos: `setup_dexjoco_demos.py --task TASK` (and `TASK_random` if Phase 5 will use it).
- Also record the exact Claude Code version, GPU model and driver, and every deviation from the
  authors' tested setup (`docs/SETUP.md`).

### Phase 2: Pre-registration (no money)
Write `ROOT/PREREG.md` (rule 6) and ask for my go-ahead. Must include: N_SESSIONS fresh sessions at BUDGET
with identical configs except the exploration seed block (session k uses `--exploration-start-seed 100*k`
so practice layouts never repeat across sessions), formal evaluation 150 official episodes each, usage limits and concurrency,
and the analysis plan (mean and spread across sessions; per-seed; failure stages; paired comparisons).

### Phase 3: Fresh sessions (paper protocol), the core result
- Configure each with `configure_auto_research.py --task TASK --episodes BUDGET --agent-cli claude
  --agent-provider claude-login --agent-effort xhigh --demonstration-context terminal_state
  --formal-episodes 150 --formal-workers 4 --exploration-start-seed <block>` (+ Gemini if on).
- Launch headless: `start_auto_research_agent.sh --config <dir>/operator-input.json --non-interactive`
  (no key-file flag: the launcher reads the experiment token itself and runs a preflight check), via
  `setsid nohup srun --jobid=<gpu job> --overlap ... < /dev/null &`.
- Run a usage watcher per session (`ROOT/tools/watch_session.py`: sums Claude transcript token usage by
  message id and logs a per-minute timeline). Also convert tokens to an **API-equivalent cost** (Opus 5.5:
  $4 in / $20 out / $0.20 cache read / 1h cache write $8 per MTok) for the report only; nothing is billed
  per token. It does not stop sessions on cost; instead it records `usage_wait` periods from
  `agent-lifecycle.json`.
- Subscription limits: the harness pauses a session when the account hits its usage limit and resumes
  after the reset (`usage_wait`, up to 10 times). Waiting time is NOT agent time: report agent time and
  wall time separately. Run at most MAX_CONCURRENT_AGENT_SESSIONS at once, and before each launch ask me
  how much of my usage limit is left; if I say it is low, wait for my go-ahead.
- Formal evaluation starts automatically after submit and uses no Claude usage (the program runs alone).
- Per session, a subagent writes `ROOT/notes/session<k>.md`: episode-by-episode chapters (wall time,
  cumulative $, what it tried, learned, outcome), the submitted program's structure, hard-coded constants,
  failure handling, and comparison with the authors' published program. Fact-check it.

### Phase 4: Continuation runs (beyond the paper; only if ADAPT=yes and I approve the usage)
- For each fresh session (or the one I pick), an adaptation session on the same TASK with
  `--adaptation-source <session> --transfer-parts memory,code --adaptation-context compact --episodes 6
  --exploration-start-seed <new block>` (the default seeds REPEAT the source's layouts; always set them).
- In the watcher, carried transcripts are counted again (the copied conversation appears in the new
  session's files): report new usage as total minus the source's total.

### Phase 5: Robustness tests of the best program (GPU only, no Claude usage)
- Re-score frozen bundles with `services.controller.parallel_batch` on the official layouts, one condition
  at a time, on layouts 0..74 (every perturbed run has an unperturbed twin; report the unperturbed rate on
  those same layouts). Conditions (all via an opt-in env-var hook in PERT_WORKTREE, see 6.3):
  `mass` (official disk-mass randomization), `texture`, `lighting`, `camera` (each the official env's own
  randomizer, called alone after reset), `rand_full` (official combined visual randomization), and
  `colors_new` (disks recoloured, sizes unchanged). Verify each condition visually (frame grab) before the
  batch.
- Fair-chance follow-up (needs my approval): an adaptation session on `TASK_random` (with Gemini if
  available) and a re-test of the visual conditions on its program. Report visual failures as "not practised
  yet" until this is done.

### Phase 6: Report (advisor-facing artifact)
- One page, plain language, built for a busy advisor; numbers read from `ROOT/results/*.json` via a
  generated `data.js`. Lead with short answers (prompts shared? code runs? numbers reproduced? robust?),
  then "what we did, step by step" with a helped/hurt verdict, agent time and API-equivalent cost per step, then the rest.
- Mirror the project page's presentation: each video beside a time-synced log of what the agent or program
  was doing (lines from tool calls, messages, notes, stage logs; frame k = simulator step k at 30 fps),
  chapter chips coloured explore/fail/fix/success. **Lead with breakthroughs** (open agent videos at the
  moment the right approach appears; star key lines); failures appear as data, not as the headline.
- Include: verified prompts (exact first message and TASK.md), session-to-session spread (the new
  headline v2 can add), ours-vs-authors comparison, perturbation table with paired twins and fair framing,
  deviations, caveats, and usage (tokens, agent time, usage-limit waits, API-equivalent cost). Captions in ASD-STE100 style. Every number fact-checked once more
  against `ROOT/results/` right before publishing.

## 4. Deliverables
`ROOT/PREREG.md`, `STATE.md`, `DECISIONS.md`, `MANIFEST.md`, `handoff/phase*.md`, `notes/*.md`,
`results/*.json`, `tools/*.py`, the published report artifact, and a 10-line summary for my advisor.

## 5. Budget and resource rules
- Stop and ask before any run that spends subscription usage; state the expected usage (v1 reference:
  a fresh budget-8 session ≈ 0.65 M output tokens and 57 M cache-read tokens over 2.6 h of agent time; a
  6-episode continuation ≈ 0.37 M output tokens over 3.1 h), and ask me how much of my usage limit is left.
- GPU: the bottleneck is CPU (MuJoCo physics + the program), not the GPU (v1: ~5% GPU util, 8 cores
  saturated). Scale with more 1-GPU jobs, not more workers per job (`parallel_batch` max 8 workers; use 6
  on 8 cores). Release every GPU job as soon as its work ends (v1 left one idle for 8 hours).
- GPU jobs have a 12 h limit in my `jobs/gpu_hold.sbatch` template; start agent sessions early enough
  that session + formal eval (2–5 h) fit, or use a fresh job.

## 6. Lessons from v1 (pilot) - apply all of them

6.1 Setup
- Cluster bubblewrap is 0.6.3 and lacks `--size` → 12+ sandbox tests fail. Install conda-forge
  `bubblewrap>=0.9` and `socat` into `runtime/envs/host` (on PATH via `scripts/host_env.sh`). Remaining known
  failure: `test_runaway_output_stops_the_controller` (output-flood guard on NFS), not on the task path.
- v1 used `--agent-provider anthropic` with an API key. v2 uses `claude-login` with my personal account
  (section 2b), which needs my own opt-in change to the harness's account check. The default
  `--agent-cli` is codex; the paper used Claude Code: set it.
- My `rc-box gpu` fails if `~/rc/env/babel-gpu-box` is not trusted in Claude Code; use a plain
  `gpu_hold.sbatch` (sleep infinity) and attach with `srun --jobid=<id> --overlap`.
- `/tmp` is node-local: write anything a GPU node must read or write under ROOT.
- In zsh never name a variable `path` (it clobbers PATH). Inside `while read` loops give `srun` `< /dev/null`
  or it eats the loop's input.
- `dexjoco_doctor.py`'s simulator_checks part builds its own env (not through the session), so its image
  stats do not reflect session-level hooks; verify hooks from the doctor run's `sensors.mp4` instead.

6.2 Running and measuring
- The harness enables 1 h prompt caching; ~85–90% of token volume is cache reads. v1 (API-billed): fresh budget-8
  session $34 (2.6 h), 6-episode continuation $21 (3.1 h).
- Formal eval: 150 episodes at 4 workers ≈ 2.3 h; each successful Hanoi episode ≈ 170 s wall.
- Use the simulator's verdict (`task_complete` in state.json / formal-report.json), never the program's own
  printed `task_complete` (it is always False at the end).
- v1 mid-run sample of 9 episodes suggested a narrow "working window" of layouts; the full 150 showed no
  such dependence. Never interpret partial batches.
- In adaptation sessions, the default exploration seeds restart at 0 (repeating the source's layouts) →
  always pass `--exploration-start-seed`. Adaptation to `TASK_random` needs its demos installed.

6.3 Perturbations
- `parallel_batch` fingerprints planner files (incl. `services/dexjoco/session.py`) at start and ABORTS
  ("Planner infrastructure changed during the batch") if they change → never edit code a running batch
  imports; keep perturbation hooks in PERT_WORKTREE from the start and commit before launching.
- `parallel_batch` holds an exclusive lock on its source session → to run batches in parallel, give each its
  own source copy (copy ALL top-level *.json + bundles/, rewrite `sim_gpu` and `root` in configuration.json,
  operator-input.json and state.json['configuration']; touch owner.lock). Copies without
  configuration.json error on every episode.
- There is no working layout offset for fresh batches (a `formal_seed` override did not change the layouts
  workers run): use layouts 0..N-1 and parallelize across conditions, not within one.
- Hook design that worked (in `services/dexjoco/session.py`, `_Tap.reset`): env var RAX_PERTURB tokens.
  `rand_full`/`mass` map to the official wrapper flags (`rand_full=True`, `randomize_dynamics=True`); for
  rand_full rename obs key `random_camera`→`ego` so a nominal-task program keeps its interface (calibration
  stays correct; camera ids are positional). Single factors call `raw.randomize_lighting()`,
  `randomize_camera()`, `randomize_desktop_texture()` after reset; colours set `mat_rgba` of
  `hanoi_disk_{large,medium,small}_mat`; then `mj_forward`, `_prime_rgb_array_renderer()`, and swap ONLY the
  re-rendered images into the already-flattened obs (returning the raw nested obs causes KeyError 'ego').
- v1 results for reference only (do not reuse as v2 numbers): session-1 program 54.7%; continuation 96.7%;
  perturbed (75 layouts, base 73/75): mass 72, texture 66, lighting 53, camera 29, rand_full 14, colours 0.

6.4 Reporting
- My advisor wants it super easy to read, honest, and fair: do not call something bad without giving it a
  chance (e.g. visual robustness without visual practice / without Gemini is "not practised yet").
- Keep the agent's breakthroughs front and centre; show what it found and when.
- The agent's private reasoning is not stored; activity lines come from visible messages, tool calls,
  notes and stage logs. Say so on the page.

## 7. First actions
1. Create ROOT and its STATE/DECISIONS/MANIFEST files; copy this prompt to `ROOT/RERUN_PROMPT.md`.
2. Check `hostname`, `$SLURM_JOB_ID`, `squeue -u $USER` (do not touch jobs you did not start).
3. Start Phase 0 with parallel subagents. Then show me a short plan for Phases 1–3 with costs and times,
   and wait for my go-ahead before Phase 3.
