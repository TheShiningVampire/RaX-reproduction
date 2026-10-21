# RaX + privileged object state: task prompts

Prompts for a quick trial: RaX (arXiv 2610.22496) on 5 DexJoCo tasks, with one extra tool,
`dexjoco_object_states`, at its `full` privileged level (`RAX_PRIVILEGED_STATE=full`, exported in every
job script). It gives the agent and its program the simulator's object poses, joint and hinge angles,
named points, velocities, collision sizes, contacts, and the task's official success conditions with
their thresholds, targets and hold counters (`goal`, from `services/dexjoco/goals.py`). Nothing about
how success is measured is hidden from the agent. We compare each task with the paper's Table 5
vision-only number at budget 8. This is an extension, not a reproduction.

- `COMMON.md`: the shared protocol (parameters, rules, auth, phases P0-P5, gates, lessons, reporting).
- `<task>.md`: one file per task, with its parameters, facts, paper row and object-state checklist.
- Two arms: `ARM = A` (default, object state only, `exp/add-state-info/object`) and `ARM = B` (object state
  plus the exact `dexjoco_lookahead` tool, `exp/add-state-info/lookahead`; COMMON section 1c). For B, set
  `ARM = B` in the task file, and fill in its CODE_COMMIT once `scripts/lookahead_acceptance.py` passes on a GPU for
  all 5 tasks.

Launch order (one task at a time; each needs your go-ahead before it spends usage):
1. `water_plant`: single arm, 1000-step cap, paper @8 91.3%; shortest episodes, so the best smoke run.
2. `fold_glasses`: single arm, 1200 steps, paper @8 100% (but 55.3% @16); the temple hinge angles are in the tool.
3. `bimanual_microwave_cook`: first bimanual run, 1100 steps, paper @8 84.0%; the door angle is in the tool.
4. `bimanual_photograph`: bimanual, 1000 steps, paper @8 86.7%; aiming and a cross-hand press are harder.
5. `bimanual_hanoi`: longest (1500 steps, ~2.3 h formal eval in v1); last, and it has our v1 vision-only
   54.7% as an extra reference.

To start a task, open a fresh Claude Code session on babel-cpu in `~/my_things/codes/rax` and paste:

    Read ~/my_things/codes/rax-reproduction/prompts/state-info/COMMON.md and <task>.md, then follow them.

What you must do by hand:
- Fill `CODE_COMMIT` in each task file (now `<fill in after GPU smoke passes>`) with the full hash on
  `exp/add-state-info/object` once `scripts/object_states_smoke.py` passes for all 5 tasks on a GPU at
  the full level (223f1a8 or later; not yet run).
- Commit your own `RAX_ALLOW_PERSONAL_CLAUDE_LOGIN` opt-in in `harness/claude_cli/experiment_login.py`
  (in CODE_COMMIT), and run `cd <CODE_WORKTREE> && RAX_ALLOW_PERSONAL_CLAUDE_LOGIN=1 bash scripts/setup_claude_experiment_login.sh --email <your account>`
  once in your own terminal (after the run worktree exists).
- Approve each launch and say how much usage limit is left. Run only one task's agent at a time.
- Afterwards, revoke the setup-token and delete `~/.config/rax/claude-experiment.token`.
