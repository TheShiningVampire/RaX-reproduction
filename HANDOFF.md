# HANDOFF: RaX privileged-state trial (written 2026-10-21)

The previous session (babel-y9-12, job 10879750) designed and built everything below. Start here.

## Goal
Advisor wants RaX (arXiv 2610.22496) results on ~5 domains using privileged simulator information
(possible "data engine" direction). Decided: DexJoCo only (Isaac Sim not installed), 5 tasks
(bimanual_hanoi, bimanual_microwave_cook, bimanual_photograph, water_plant, fold_glasses), paper protocol
(budget 8, Claude Code Opus 5.5 xhigh, terminal_state demos, 150 official formal layouts), personal Claude
login. Compare with paper Table 5 @8 (vision only). Not a reproduction; an extension.

## Code (public fork https://github.com/TheShiningVampire/rax)
| Arm | Branch | Commit | Worktree | Status |
|---|---|---|---|---|
| A: `dexjoco_object_states` at RAX_PRIVILEGED_STATE=full (poses, joints, velocities, sizes, contacts, `goal` = official success/failure conditions with thresholds, targets, hold counters) | exp/add-state-info/object | 943da37 (= 223f1a8 + auth opt-in) | .worktrees/add-state-info (FROZEN while Hanoi A runs) | GPU smoke passed (jobs 10880362, 10880424) |
| B: A + `dexjoco_lookahead` (simulate up to 150 rows from the live state on a copy of MjData, exact restore, budget 3x step cap/episode, 300 calls, 30 s/call; RAX_LOOKAHEAD=on) | exp/add-state-info/lookahead | 8c2b77d (= 8e780f3 + auth opt-in) | .worktrees/lookahead (FROZEN while Hanoi B runs) | GPU acceptance passed on all 5 tasks (job 10881011: continuation max abs diff 0.0, ~2-4 ms/row) |

Other worktrees: smoke-dcbf92f, smoke-223f1a8, accept-8e780f3 (detached, for GPU checks; removable),
dexjoco, dexjoco-pert, dexjoco-v2 (older v1/v2 repro).
RAX_* settings are recorded per session in `session-env.json` (resume/re-score reuse them).

## Prompts (this repo, branch exp/state-info-trial)
`prompts/state-info/`: COMMON.md (protocol, Arm B in section 1c), README.md, one file per task;
`bimanual_hanoi.md` = Arm A (ROOT /data/user_data/vawale/rax_state/bimanual_hanoi_A),
`bimanual_hanoi_B.md` = Arm B (ROOT .../bimanual_hanoi_B). Launch: "Read .../COMMON.md and <file>, then follow them."
Design notes: notes/lookahead/DESIGN.md. Job scripts: jobs/object_states_smoke.sbatch, jobs/lookahead_acceptance.sbatch.

## Running now (at handoff)
- Hanoi Arm A session job 10881100 (katef, RTX PRO 6000, babel-l9-16), driven by its own Claude session.
- Hanoi Arm B: TWO pending session jobs, 10881905 (katef, gres/gpu:1 untyped, no z9-16 exclude) and
  10882081 (preempt, A6000). Likely a duplicate; user to keep at most one (RTX_PRO_6000, --exclude=babel-z9-16).

## Cluster facts
- babel-z9-16 has broken EGL (MuJoCo 0x8cdd even without MSAA; jobs 10880136/10880152/10880177). Always
  `--exclude=babel-z9-16` for simulator GPU jobs (user approved). Works: babel-l9-16 (RTX PRO 6000), y9-08 (A100, toy test).
  User to post in #babel-babble. CPU-only work on z9-16 is fine.
- Runtime for checks: /data/user_data/vawale/rax_state/runtime (envs -> rax_repro_v2/runtime/envs).

## Open items
1. Two optional agent-text additions on Arm A/B (not done; would need new commits + regenerated goldens,
   only in NEW worktrees, after the Hanoi runs): TASK.md pointer to `goal` thresholds; autonomous-control
   skill line "program checks goal/contacts after each stage and retries".
2. Remaining 4 tasks: prompts exist (ARM A default, ROOT <task>_A); fill CODE_COMMIT (943da37 for A).
3. Tier 3 (export successful formal episodes as training data in the official demo format; train the
   benchmark's vision policy on it) = the real data-engine test; not started.
4. Revoke the setup-token and delete ~/.config/rax/claude-experiment.token when all runs end.
