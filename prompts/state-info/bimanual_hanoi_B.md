# bimanual_hanoi, Arm B (lookahead)

This file is the Arm B variant of `bimanual_hanoi.md`. Read `bimanual_hanoi.md` in full and follow it
with COMMON.md section 1c (Arm B), but use the PARAMETERS below instead of the ones in its section A.
Its "For `ARM = B`" paragraph applies, except that CODE_WORKTREE is the existing lookahead worktree
(not a new detached one).

## A. Parameters (override bimanual_hanoi.md section A)

```
TASK          = bimanual_hanoi
ARM           = B   # object state + success info + dexjoco_lookahead (exp/add-state-info/lookahead)
ROOT          = /data/user_data/vawale/rax_state/bimanual_hanoi_B
CODE_COMMIT   = 8c2b77da20157d73683f2e2ac2a1c812b3cbeefa   # 8e780f3 (GPU acceptance passed: job 10881011) + my auth opt-in (cherry-pick of 943da37)
CODE_WORKTREE = ~/my_things/codes/rax/.worktrees/lookahead   # existing worktree, frozen for this run (COMMON P1.1)
REUSE_ENVS    = /data/user_data/vawale/rax_repro_v2/runtime/envs
GPU_JOB       = <optional: running katef GPU job id; empty = submit new jobs (COMMON P1.4, P2.5)>
```

Job scripts export `RAX_PRIVILEGED_STATE=full RAX_LOOKAHEAD=on RAX_LOOKAHEAD_ROWS_FACTOR=3`.

## Running beside Arm A

- Arm A (`bimanual_hanoi_A`, `.worktrees/add-state-info`, 943da37) may run at the same time in another
  session. Never read from, write to, or cancel anything under `bimanual_hanoi_A` or its jobs, and never
  touch `.worktrees/add-state-info`.
- Both arms use the same exploration seeds (`--exploration-start-seed` default) and the same 150 official
  formal layouts, so their formal results pair layout by layout. Do not change the seeds.
- Both arms draw on my one personal Claude subscription. Before launch, ask me whether Arm A is running
  and how much usage is left; if a session enters `usage_wait`, report it and do not retry.
- GPU acceptance evidence for this code (job 10881011, babel-l9-16, 8e780f3): all 5 trial tasks passed
  control, continuation (60 rows, max abs diff 0.0), prediction, unchanged, frames, budget and
  episode_end; Hanoi lookahead cost about 4.4 ms per row. Report:
  `/data/user_data/vawale/rax_state/accept/10881011/lookahead_acceptance.json`.
