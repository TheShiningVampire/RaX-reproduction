# RaX (arXiv 2610.22496): paper claims vs evidence

Sources:
- `P:<line>` = $SCRATCH/paper/full2.txt. This is the HTML-extracted paper. Figure 1's chart values are not in the extracted text.
- `README:<line>` = main:README.md in ~/my_things/codes/rax.
- `<branch>:<path>:<line>` = read with `git show` or `git grep` on origin/<branch>. Nothing was checked out or run.
- Arithmetic checks were run with `python3 -I` on numbers copied from the tables.

## 0. Protocol facts that apply to every simulation claim

- **Agents.** Claude Code with Opus 5.5 everywhere, except Codex (GPT-6) on four RoboDojo tasks and one BEHAVIOR task. Effort is xhigh unless stated otherwise (P:2192-2194).
- **Weights and memory.** No model weights are updated. The workspace starts empty and nothing is remembered across sessions (P:2196-2202).
- **Budget.**
  - The budget counts exploration episodes, and rehearsals count against it.
  - It is an upper bound, because submitting ends exploration (P:2213-2217, P:2226-2233).
  - Exploration scenes come from the training distribution and never from the evaluation set (P:2217-2219).
- **Two evaluation forms** (P:2234-2243):
  - **Fully automated program:** the frozen bundle runs alone, with no edits or retries, and the agent never sees the results.
  - **Agent-in-the-loop:** a fresh copy of the agent starts from the frozen workspace on each test scene. This is used on BEHAVIOR for 5 of the 6 tasks.
- **Scoring.** Each benchmark's native evaluator. Errors and timeouts count as failures (P:2244-2247).
- **Gemini 3.8 Flash.** Available to the agent and its programs. The paper says the budget is $10 per session, shared between exploration and evaluation (P:2223-2224, P:2582).
  - **DISCREPANCY:** the released DexJoCo branch says Gemini spending "has no session limit":
    - dexjoco/native:docs/USAGE.md:353-359
    - dexjoco/native:docs/ARCHITECTURE.md:161
    - dexjoco/native:auto_research_agent/AGENTS.md:183
  - So the released defaults differ from the protocol the paper reports.
- **Repetitions:**
  - No table reports seeds, repeated sessions, error bars or confidence intervals.
  - DexJoCo says explicitly "One session per task" for each budget (P:2592).
  - RoboDojo and Table 8 say "Cells with more than one run report the mean" (P:538, P:1446), but never say which cells, or how many runs.
  - The repo's formal-score output already computes a per-seed mean and standard deviation over the 3 official seeds (dexjoco/native:docs/USAGE.md:346-348). The paper does not report these.
- **What was released** (verified with `git ls-tree` on all code branches):
  - No compiled `controller.py`, `formal-scores.json`, `formal_batch.json` or `.jsonl` files on any of the 8 code branches: dexjoco/{native,container}, humanoid-arena/{native,container}, robodojo-behavior/{native,container}, real/{franka,rainbow} [corrected: the container branches of humanoid-arena and robodojo-behavior were not listed before; re-checked, also absent]. Files matching `formal` are harness code and tests only (e.g. services/controller/formal_worker.py, local_tests/unit/test_formal_batch.py).
  - So none of the simulation sessions' submitted programs or logs are released.
  - Real-robot session logs and agent code are on Hugging Face only (README:182-188). I did not inspect them.
  - The harness, prompts, skills, task rules, simulator adapters and evaluation code are released (see notes_inventory.md).
  - **Consequence:** a third party can re-run the protocol at their own API cost, but cannot re-score the paper's own programs or audit its transcripts for any simulation number.
- **Baseline numbers** are all copied from other papers and leaderboards (table captions P:537, P:659, P:763, P:954-956, P:1218-1220). None were re-run under the RAX harness.

## 1. Claims table

| # | Claim (ref) | How it was measured | Third party can check? | Robustness caveats |
|---|---|---|---|---|
| 1 | **Mean success on unseen scenes rises 25% -> 79% as the budget goes 4 -> 128, vs 41.2 for the best prior model.** README:52. In the paper this is only Figure 1's left chart plus §13 (P:3194-3220). The 25 and 79 values are not in the paper text. | §13: average the tasks within each benchmark at each budget, then average the 5 benchmarks with equal weight. A task with no result at a budget takes its result from the largest smaller budget (P:3214-3216). Benchmarks: RoboDojo, BEHAVIOR, HumanoidArena, DexJoCo (bimanual tasks only), LIBERO-Pro. **My reconstruction:**<br>• At 128 the mean is (78.3 + 46.5 + 89.8 + 94.26 + 84.4) / 5 = **78.65**.<br>• The prior mean is (24.9 + 8.2 + 81.9 + 48.8 + 42.3) / 5 = **41.22** (matches the 41.2 in README:52).<br>• At 4, the mean is **24.92**, but only if cells never run at or below budget 4 count as **0**: the 3 RoboDojo random tasks, all of BEHAVIOR (128 only), and all of LIBERO-Pro (plotted at 16). | **Partly.** Every input is in Tables 2-6, so the arithmetic can be checked. The underlying runs cannot be audited. The 0-fill rule is my inference (UNCERTAIN): it reproduces 25% to 0.1 pt, but the paper does not state it. | • The low end is pulled down by benchmarks that were never run at small budgets (UNCERTAIN, see the reconstruction). So it is not a like-for-like scaling curve.<br>• The 79% uses LIBERO-Pro *with* adaptation on the perturbed distribution (84.4). Without adaptation (76.0) the high end is 76.97.<br>• DexJoCo enters as bimanual tasks only (P:3203-3206).<br>• BEHAVIOR is agent-in-the-loop for 5 of 6 tasks.<br>• Every cell is a single session, or an unspecified number of runs. |
| 2 | **+37.4 pts over the top learned models, on average across 5 simulation benchmarks.** Abstract P:223, intro P:242 and P:254, §13 P:3207-3209. | The mean of 5 margins, each RAX at its largest budget minus the strongest *learned* prior: +53.4 RoboDojo (vs VPP2 24.9), +38.3 BEHAVIOR, +7.9 HumanoidArena (vs WB-WAM), **+45.5 on DexJoCo bimanual only** (94.3 vs ME-Dex 48.8), and +42.1 on LIBERO-Pro (vs VPP2 42.3; **excludes ASPIRE at 63.2**) (P:3197-3209). I recomputed: VPP2 = 24.89, ME-Dex bimanual = 48.8, mean of margins = 37.44. | **Partly.** The arithmetic checks out. The inputs are unaudited single sessions plus copied baselines. | • Selection choices raise the number:<br>&nbsp;&nbsp;– DexJoCo is limited to its 5 bimanual tasks (all 11 gives +31.4, P:3211-3212).<br>&nbsp;&nbsp;– Agents such as ASPIRE are excluded on LIBERO-Pro (using ASPIRE gives +21.2).<br>• The abstract writes "+37.4%", but the quantity is points, not percent.<br>• The comparison mixes agent-in-the-loop BEHAVIOR scores with learned policies.<br>• HumanoidArena RAX uses 3 teleoperated demonstrations (P:735-736). |
| 3 | **"241x faster" than the agent.** README:46, 60. The paper's Table 9 (P:1523-1549) gives the raw numbers. The 241x figure itself does not appear in the paper text. | Real Franka, air fryer, **inference time only** (wall-clock outside robot calls): agent 72.3 min (its first completion, *including online exploration*, P:1522) vs program 18 s, so 4338 / 18 = **241.0**. Bandu: 17.2 min / 10 s = **103.2**. | **Partly.** The real-robot logs are on Hugging Face (README:182-188, not inspected). The paper's numbers come from one run per mode. | • It counts inference latency only. Robot time is 2.9 min vs 2.5 min.<br>• End to end, my own arithmetic gives only about 27x for the air fryer: (72.3 + 2.9) min vs (0.3 + 2.5) min.<br>• For Bandu end to end: about 26.5 min for 6 pieces vs about 11.1 min for 7 pieces, which is about 2.4x. The pieces differ (P:1525-1526).<br>• The agent figure includes exploration, so this compares learning time with execution time.<br>• Programs still run background monitoring of up to 2.2k tokens (P:1522). |
| 4 | **RoboDojo, Table 2.** RAX averages 78.3 vs 24.9 for VPP2 and exceeds every baseline on all 7 tasks (P:535-650). | • Single agent, single environment, empty workspace. Budgets 4 to 64 (P:531).<br>• Fully automated program, evaluated on 30-50 unseen layouts per task (Table 13: 45/50/30/50/50/50/50, P:2275-2323).<br>• Partial credit where the benchmark defines it.<br>• 4 tasks use Codex, 3 use Claude Code (P:2282-2324).<br>• Baselines come from the RoboDojo-Sim leaderboard. | **Partly.** The harness, task rules and rubrics are released. Programs and logs are not. | • "Cells with more than one run report the mean", with no count and no spread given (P:538).<br>• Non-monotonic: hang mugs goes 36.9 -> 33.3 -> 39.2. Make kong submitted no program at 8 episodes, scoring 0 (P:625).<br>• Each task's "Max" is its largest budget, so budgets differ per task.<br>• The RAX evaluation layouts (a specific collection, P:2266-2270) may not match the leaderboard's protocol (UNCERTAIN).<br>• Plug in charger and pour by language receive a summary of the official task code (P:2260-2261). |
| 5 | **BEHAVIOR-1K, Table 3.** Average Q-score 46.5 vs 8.2 for the best 2025 challenge entry (P:658-722). | • 128 episodes with 2-8 parallel environments and cooperating agents (Table 14, P:2357-2408).<br>• Evaluated on the 10 public test instances (301-310).<br>• **Only boxing books (26.7) is a fully automated program**, and it ran on Codex without keyframes or the VLM. The other 5 tasks are **agent-in-the-loop**, with one fresh agent copy per instance (P:653, P:2348-2350).<br>• Step limit is 1.5x the mean demo length, vs 2x in the 2025 challenge (P:2336-2338). | **Partly to no.** The integration is released (100 task rules). Agent-in-the-loop results depend on frozen workspaces and conversations that are not released. Each test instance is a single attempt. | • N = 10 instances per task, with no spread reported.<br>• **Test leakage:** on sorting items, clearing food and clean up desk, each agent copy also receives Gemini review reports of the fully automated program's runs on the *other nine test instances* (P:2350-2353).<br>• During exploration, a review model gives feedback after every run (P:654-655).<br>• Baselines are challenge entries under different conditions. |
| 6 | **HumanoidArena, Table 4.** Average 89.8 vs 81.9 for WB-WAM (+7.9). Budget scaling goes 52.1 at 2 to 80.7 at 32 (P:750-918). | • 3 teleoperated demonstrations, with actions, seen only by the exploring agent. Programs may reuse motion segments cut from them (P:735-736, P:2424-2428).<br>• Budget up to 32, and up to 128 on DoubleDesk and P&PBox. Above 32 there are 2 environments plus subagents (P:2431-2432).<br>• Fully automated program on 60 official test episodes (seeds 0-2 × 20).<br>• Baselines (100 demonstrations each) come from the benchmark's papers. | **Partly.** As for RoboDojo: the harness is released, the programs and logs are not. | • Single sessions per cell, no error bars.<br>• Non-monotonic: P&PBox goes 23.3 -> 20.0 -> 51.7 -> 46.7 -> 83.3, and DoubleDesk 28.3 -> 25.0 -> 25.0 -> 56.7.<br>• "Max" mixes budgets of 32 and 128.<br>• This is not zero-demonstration.<br>• RAX⋆ (no actions) reaches 81.9, but uses larger budgets of 64-256 (P:1554). |
| 7 | **DexJoCo, Table 5** (details in §2). Average of 11 tasks is 31.9 / 44.8 / 86.9 / 91.3 / 96.7 at budgets 2/4/8/16/32. RAX beats the best published result on every task at 32. The best session per task averages 99.5 (+45.4 vs the benchmark's own baselines, +34.2 vs the best published) (P:943-952). | • One agent (Claude Code Opus 5.5, xhigh), one environment, **no subagents**.<br>• Three completion images; no action demonstrations.<br>• rand-obj setting only.<br>• Fully automated program on the 150 official episodes (seeds 0, 1, 2 × 50 resets) (P:2560-2591). | **Partly.** The released branch reproduces the evaluation layouts exactly (dexjoco/native:services/dexjoco/tasks.py:3-8, 17-22). No programs, logs or scores are released. | See §2. Main points:<br>• One session per cell.<br>• Strong non-monotonicity.<br>• The "best session" figure picks the maximum over budgets *on the test set*.<br>• Evaluation is synchronous, while the official client is asynchronous (P:2589-2591). |
| 8 | **LIBERO / LIBERO-Pro, Table 6.** 98.5% on LIBERO with no demonstrations. On LIBERO-Pro position perturbation: 76.0 zero-shot, 84.4 after adaptation, vs VPP2 42.3 and ASPIRE 63.2 (P:1203-1380). | • Up to 20 exploration episodes per task on the official placement distribution (seed 1000+i), with 2 environments.<br>• Optionally up to 5 adaptation episodes on the perturbed distribution (seed 2000+). Used on 5 of 40 tasks (P:3170-3171).<br>• Fully automated program on 50 official initial states and 50 perturbed states (P:2650-2658).<br>• 37 of 40 tasks had a budget of 15 (P:3216-3219). | **Partly.** No LIBERO branch appears in the branch list I was given (UNCERTAIN whether the code ships on another branch). No programs or logs are released. | • Single session per task.<br>• Adaptation draws episodes from the evaluation *distribution* (but never from evaluation states).<br>• VPP2 uses only 10 initial states per task (P:1220).<br>• The PatchWAM perturbed number is a mean only.<br>• The ASPIRE comparison uses a different model (Opus 4.6) and a different protocol (§12, P:3138-3193). The paper argues this favours ASPIRE. |
| 9 | **Parallelization, Table 7.** On make toast, 4 Claude agents in 4 environments score 92.2 in 4.9 h, vs a single agent at 63.3 in 13.7 h (P:1395-1435). | 32 evaluation scenes. A different task description from Table 2: it includes numeric thresholds and keyframes (P:2271-2273). | **Partly.** | • One session per row.<br>• The single-agent row has a *larger* budget (48 vs 32).<br>• Claude and Codex are not compared at equal settings. |
| 10 | **Depth vs RGB-only, Table 8.** Depth adds +17.3 on average over 4 pairs (P:1443-1475). | The same tasks and budgets as Table 2. | **Partly.** | • n = 4 pairs.<br>• One pair is 2.5 vs 0.0.<br>• "More than one run" is given as a mean without a count. |
| 11 | **Real robots, Franka.** Five tasks "mastered" with zero demonstrations (P:525, P:3221-3589):<br>• **Find the cube.** 12 trials. Trials 4-6 are three consecutive unattended successes. Later variants needed manual help and resumes (P:3252-3268).<br>• **Air fryer.** Run 1 by the agent's own direct tool calls, not by a human [corrected] (about 75 min including exploration), then 9 program runs. Runs 6, 7, 9 and 10 are clean unattended successes. Runs 4, 5 and 8 needed resumes. Run 2 was a safety stop (P:3300-3309).<br>• **Wiping.** 13 trials and resumes. The last two (6, 7b) succeeded in one pass with no intervention. In the paper-towel variant, leftover sheets were cleared by supervised scripts (P:3497-3516).<br>• **Peg-in-hole.** L1-L3 reached. It **never ran an unattended program**. The user gave advice, the operator taped the board down and extracted the pegs, and L4 was not attempted (P:3539-3557).<br>• **Bandu.** 15 runs. One final fully automatic rebuild (7/7). The operator reset once, restarted or re-homed the gripper twice, and moved one piece the arm could not reach; the user also asked for visual alignment of the knob [corrected] (P:3576-3589). | Single sessions with a human operator. Success is judged by the agent's own measurements plus camera views (P:3269, P:3309-3310, P:3503-3505). | **Partly.** The Hugging Face logs claim full transcripts, tool calls, state, video and code for 5 Franka sessions (README:184-188). I did not inspect them. | • These are narratives, not success rates.<br>• n is 1-4 clean runs per task.<br>• Operator resets and interventions are frequent, and the user gave in-session advice on the peg and Bandu tasks.<br>• No held-out evaluation protocol.<br>• "Mastered" overstates the peg task (agent-driven, supervised). |
| 12 | **Real robots, RB-Y1.** A long-horizon tidy-up of six subtasks, composed from skills learned in 5 earlier sessions (P:526, P:1692-1705, P:3590-3624). | 3 trials. All 6 subtasks completed in each. Trial 3 took 98 min, **with the agent at every checkpoint**. The operator reset before each trial, stayed in the loop and gave advice, and re-armed the robot after controller faults (P:3611-3622). | **Partly.** There are 7 RB-Y1 sessions on Hugging Face (README:186). | • Agent-in-the-loop, not an autonomous program.<br>• n = 3.<br>• Human advice was given during trials.<br>• Success was judged by the agent from head-camera images. |
| 13 | **Inference falls as more is compiled** (Figure 7, P:1510). Loading the car: the first success took 123 min and 254k output tokens, the last 4 min and 4k tokens. Make toast random: 17 min falling to 6 s. | Measured over successful exploration episodes only. | **No.** No simulation logs are released. | • Success-conditioned.<br>• Running median over 5 episodes.<br>• Parallel tokens are attributed heuristically (P:1519-1520). |

## 2. DexJoCo in detail

### Tasks (Table 16, P:2498-2559; dexjoco/native:services/dexjoco/tasks.py:27-39)

**Single-arm** (one Franka Panda with a 16-DoF Allegro hand):

| Task | Benchmark id | Step limit |
|---|---|---|
| Hammer | hammer_nail | 1000 |
| Mouse | click_mouse | 1200, including a 30-step pre-roll |
| Bucket | pick_bucket | 1200 |
| Tongs | pinch_tongs | 1000 |
| Glasses | fold_glasses | 1200 |
| Water | water_plant | 1000 |

**Bimanual** (two Franka Panda arms, each with an Allegro hand):

| Task | Benchmark id | Step limit |
|---|---|---|
| iPad | bimanual_unlock_ipad | 1200 |
| Hanoi | bimanual_hanoi | 1500 |
| Assembly | bimanual_assembly | 1500 |
| Microwave | bimanual_microwave_cook | 1100 |
| Photo | bimanual_photograph | 1000 |

**Interface** (P:2484-2497):
- Actions: an absolute flange pose plus 16 hand joints, so 22 dimensions per arm and 44 for two arms. The official operational-space controller tracks the flange, with no motion planner. Each step is 20 ms, and one call executes 1-150 rows.
- Observations: RGB-D at 640×640.
- The agent gets no force, tactile or simulator-state signal.

### Per-task success (%), Table 5 (P:1099-1180 [corrected line range])

Each budget row is **one session per task** (P:2592).

| Budget | Hammer | Mouse | Bucket | Tongs | Glasses | Water | iPad | Hanoi | Assembly | Microwave | Photo | Avg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 98.7 | 100 | 0.0 | 36.7 | 0.7 | 0.0 | 100 | 0.0 | 14.7 | 0.0 | 0.0 | 31.9 |
| 4 | 98.7 | 97.3 | 93.3 | 2.7 | 0.0 | 0.0 | 100 | 100 | 0.7 | 0.0 | 0.0 | 44.8 |
| 8 | 94.0 | 100 | 100 | 100 | 100 | 91.3 | 100 | 100 | 0.0 | 84.0 | 86.7 | 86.9 |
| 16 | 98.0 | 100 | 96.7 | 99.3 | 55.3 | 98.7 | 100 | 98.7 | 96.0 | 93.3 | 68.7 | 91.3 |
| 32 | 100 | 100 | 100 | 100 | 93.3 | 99.3 | 100 | 100 | 72.0 | 99.3 | 100 | 96.7 |
| Best ME-Dex† (baseline) | 86.0 | 76.0 | 92.0 | 92.0 | 56.0 | 72.0 | 48.0 | 32.0 | 28.0 | 88.0 | 48.0 | 65.3 |

Recomputed averages:
- The 11-task averages all match the table: 31.89, 44.79, 86.91, 91.34, 96.72.
- Bimanual averages by budget: 22.9, 40.1, 74.1, 91.3, 94.26.
- "Best session" average: 99.51. Eight tasks reach 100, Assembly 96.0, Water 99.3 and Microwave 99.3. This matches P:948-950.

### Robustness flags

- **Not monotonic in budget.** Every budget is an independent single session, so the jumps reflect session-to-session variance:
  - Tongs: 36.7 -> 2.7 -> 100.
  - Glasses: 100 -> 55.3 -> 93.3.
  - Assembly: 14.7 -> 0.7 -> 0.0 -> 96.0 -> 72.0.
  - Photo: 86.7 -> 68.7 -> 100.
  - No seed or session repeats are reported. The 150 episodes measure the variance of *one program* over layouts, not the variance between *sessions*.
- **The 99.5% "best session" figure selects the maximum over 5 budgets using test-set scores** (P:948-950, P:3213-3214). It is optimistically biased.
- **Evaluation differs from the baselines'.** RAX runs synchronously and free of inference latency, while the official benchmark client is asynchronous (P:2589-2591). The baselines come from four different papers, and ME-Dex uses simulated tactile input and one policy for all tasks (P:957-958).
- **Agent time per session** (median, with range) (Table 17, P:2595-2630):

  | Budget | Agent time (h) |
  |---|---|
  | 2 | 0.70 (0.44-1.28) |
  | 4 | 1.05 (0.51-2.46) |
  | 8 | 1.34 (0.59-3.02) |
  | 16 | 1.52 (0.72-2.89) |
  | 32 | 1.76 (0.98-3.89) |

  - Episodes used / budgeted: 22/22, 44/44, 86/88, 160/176, 280/352. That is 592 of 682 over 55 sessions (P:2577).
  - Sessions that submitted early: 0, 0, 2, 5 and 8 of 11.
- **Budgets 2/8/32.** The paper runs N ∈ {2, 4, 8, 16, 32} (P:2572). Budgets 2, 8 and 32 are the rows above. The text highlights 31.9 (2), 86.9 (8) and 96.7 (32) (P:944-945).
- **Episode reviews.** The repo can attach Gemini ground-truth episode reviews to DexJoCo exploration. They are **off by default** (dexjoco/native:docs/USAGE.md:67) and have a separate $10 operator budget (dexjoco/native:docs/DEXJOCO_BACKEND.md:128-132). The paper does not say whether the Table 5 sessions used them (UNCERTAIN). The paper mentions review reports only for BEHAVIOR.

### `_random` variants

- **What they are.** Every official DexJoCo task has a second harness task, `<task>_random`, which uses the official `configs/rand_full` instead of `configs/rand_obj`. In `rand_full`, the camera, lighting and table texture are also randomized (dexjoco/native:services/dexjoco/tasks.py:3-5, 23, 57-66).
- **How the rule files work.** They reuse the base rules and replace the scene-variation paragraph. For example, hammer_nail_random.md reads: "Rules: identical to `hammer_nail` ... in addition the third-person camera's viewpoint, the lighting and the table texture change between layouts" (dexjoco/native:services/dexjoco/task_rules/hammer_nail_random.md:1-3; merge logic in services/dexjoco/task_rules.py:21-28). There are 11 `_random` rule files.
- **Does the paper report them?** **No.**
  - The paper evaluates only "the rand-obj setting" (P:929, P:953, P:2481-2483).
  - A grep of the paper for "rand_full", "rand-full" or DexJoCo "random" finds no hits.
  - So no `_random` (rand_full) results exist in the paper.
  - Whether they were run and not reported: UNCERTAIN.

## 3. Cost statements (for estimating one DexJoCo session)

**What the paper states:**
- **Total spend.** "Across all experiments in this paper, simulated and real, the agents' model calls consumed over 100k US dollars of API credits" (§15, P:3625-3627). This is the only dollar figure. It gives no per-session, per-benchmark or token breakdown, and it is unclear whether it includes development runs.
- **Gemini.** Capped at $10 per session in the paper (P:2223, P:2582). The released code has no limit by default (see §0).
- **DexJoCo wall clock.** Median agent time is 0.70 h at budget 2 up to 1.76 h at budget 32, with a maximum of 3.89 h (Table 17). No token counts are given for DexJoCo.
- **Other token and time data points:**
  - Air fryer, first agent completion: 262.4k output tokens over 72.3 min of inference (P:1536).
  - Bandu: 88.4k output tokens over 17.2 min (P:1545).
  - Loading the car, first success: 254k output tokens over 123 min (P:1510).
  - ASPIRE's loop on Claude Opus 5, as reported by Kang et al. (2026), not measured by RAX: a median of 0.99 h and 91k output tokens per task *and perturbation* [corrected] (P:3160-3161).
  - All of these are **output** tokens only. Input and cache tokens, which usually dominate Claude Code cost, are never reported.
- **Resources per session.** The agent container has 16 GB of memory and 4 CPUs. Each program container has 8 GB and 4 CPUs. There is no network access (P:2203-2205). DexJoCo evaluation runs 4 episodes in parallel over 150 episodes (P:2587).

**Crude estimate:**
- At about 1-2 h, a DexJoCo session would produce something like 100-300k output tokens. This is an extrapolation from the data points above (UNCERTAIN).
- Cost per session ≈ (input + cache tokens × price) + (output tokens × price) + up to $10 of Gemini.
- Opus 5.5 prices need to be looked up. I did not assume any.
- An upper-end sanity check: there are about 55 DexJoCo + ~46 HumanoidArena + ~29 RoboDojo + 6 BEHAVIOR + 40 LIBERO + ~12 real sessions, roughly 190 in all. Dividing $100k by 190 gives about $500 per session on average.
  - That figure is inflated by the long BEHAVIOR and real-robot sessions and by any unreported development runs.
  - DexJoCo sessions are short, so they are probably well below that average (UNCERTAIN).
- A full Table 5 reproduction is 55 sessions.

## Verification

An independent re-check of the claims that carry the most weight. Every check reads the cited source again: `git show` on origin/<branch>, `sed -n` on the paper text and on main:README.md, and arithmetic redone by hand from the table cells. Nothing was checked out or run.

1. **CONFIRMED.** The Gemini cap is $10 per session in the paper (P:2223-2224, P:2582). The released DexJoCo branch says there is no limit:
   - dexjoco/native:docs/USAGE.md:356 says "Spending has no session limit"; the section runs 353-359.
   - dexjoco/native:docs/ARCHITECTURE.md:161 and dexjoco/native:auto_research_agent/AGENTS.md:183 say the same ("Gemini spending has no limit").
   - The separate $10 operator budget for episode reviews is at dexjoco/native:docs/DEXJOCO_BACKEND.md:132 and USAGE.md:359.
   - Episode reviews are off by default (USAGE.md:67).
   - Extra point, not in the notes: the released default `--agent-cli` is `codex` (USAGE.md:60), while the paper's DexJoCo runs used Claude Code.
2. **CONFIRMED.** DexJoCo runs "One session per task" (P:2592, the Table 17 caption). "Cells with more than one run report the mean" appears at P:538 (Table 2) and P:1446 (Table 8). Per-seed mean and standard deviation in `formal-scores.json`: USAGE.md:346-348.
3. **CONFIRMED, with one corrected omission.** No programs, scores or logs are released.
   - `git ls-tree -r` on all 8 code branches finds no `controller.py`, no `formal-scores.json` / `formal_batch.json` and no `.jsonl`.
   - The only `.json` files are fixtures and config: local_tests/goldens/workspaces.json, services/robodojo/task_rubrics.json and similar.
   - The notes had left out the humanoid-arena and robodojo-behavior container branches. They are now listed [corrected].
4. **CONFIRMED.** README:46 and README:60 say 241x. README:52 says 25% -> 79% and 41.2. README:182-188 points to the Hugging Face logs, and README:186 says "5 Franka and 7 RB-Y1".
5. **CONFIRMED.** The +37.4 points are the mean of the margins 53.4 / 38.3 / 7.9 / 45.5 / 42.1, which is 37.44 (P:3207-3209).
   - The abstract writes "+37.4\%" (P:223).
   - VPP2's RoboDojo mean is 174.2 / 7 = 24.89 (Table 2 row, P:540-650).
   - ME-Dex bimanual: (48 + 32 + 28 + 88 + 48) / 5 = 48.8 (P:1101).
   - The ASPIRE alternative gives 84.4 - 63.2 = 21.2 (P:3213).
6. **CONFIRMED (arithmetic).** The 25% at budget 4 is reproduced with zero-fill. RoboDojo at 4 = 154.4 / 7 = 22.06 (Table 2). HumanoidArena at 4 = 62.4 (Table 4 Avg column). DexJoCo bimanual at 4 = 40.14. BEHAVIOR = 0 and LIBERO-Pro = 0. The total is 124.6 / 5 = 24.92. That the paper uses the 0-fill rule is still UNCERTAIN: P:3214-3216 describes only carry-forward from a smaller budget.
7. **CONFIRMED.** The Table 9 numbers (P:1534-1545) are 72.3 min / 18 s / 262.4k and 17.2 min / 10 s / 88.4k. The ratios are 4338 / 18 = 241.0 and 1032 / 10 = 103.2. End to end, air fryer is 75.2 / 2.8 = 26.9x and Bandu is 26.5 / 11.07 = 2.4x. "Including online exploration" and "at most 2.2k tokens" both appear at P:1522.
8. **CONFIRMED.**
   - Table 5 cells, recomputed from P:1101-1180: the 11-task averages, the bimanual averages (22.9 / 40.1 / 74.1 / 91.3 / 94.26), the best-session average of 99.51 with 8 tasks at 100, and all four non-monotonic sequences.
   - The 45.4 and 34.2 figures are at P:948-950. Table 17 times and the 592/682 episode count are at P:2577 and P:2595-2630.
9. **CONFIRMED.** The DexJoCo code citations hold:
   - tasks.py:3-8 and 17-22 give the 3 official seeds × 50 resets and an exploration seed base of 1000.
   - tasks.py:27-39 gives the task ids and step caps, all matching. tasks.py:42 gives the 30-step pre-roll for click_mouse.
   - The rand_full mapping is at tasks.py:3-5, 23 and 57-66.
   - The hammer_nail_random.md quote is accurate, but the original sits on lines 1 and 3 with formatting, and the notes elide part of it with "...".
   - The merge logic is at task_rules.py:21-28. There are 11 `_random` rule files.
   - The paper has no hit for rand_full / rand-full.
10. **CONFIRMED.**
    - BEHAVIOR test leakage: copies receive Gemini reviews of the program's runs on the "other nine test instances" (P:2350-2352).
    - HumanoidArena uses 3 teleoperated demonstrations (P:735-736).
    - Table 7 scores are 92.2 / 4.9 h vs 63.3 / 13.7 h. These are the *Score* column. The *Success* column gives 87.5 vs 50.0 (P:1398-1435).
11. **WRONG, corrected in place.** These real-robot details were wrong or incomplete:
    - Air fryer run 1 was not done "by hand". The agent did it by direct tool calls (P:3300).
    - The Bandu operator interventions also included moving one unreachable piece (P:3576-3578).
    - The peg-in-hole "never ran an unattended program" claim is CONFIRMED (P:3547-3548).
    - The RB-Y1 claims (3 trials, 98 min, agent at every checkpoint, operator advice and re-arming) are CONFIRMED (P:3611-3622).
12. **WRONG, corrected in place.** The ASPIRE cost data point needed fixing:
    - The 0.99 h / 91k tokens is reported by Kang et al. (2026), and it is per task *and perturbation* (P:3160-3161).
    - The ASPIRE baseline itself used Opus 4.6 (P:3140), so the claim 8 caveat is CONFIRMED.
13. **CONFIRMED.** The total spend quote, "over 100k US dollars of API credits", is at P:3626-3627.

Minor citation fix: Table 5's range was P:1115-1180; the ME-Dex row is at P:1101 and the RAX rows follow it [corrected]. The ~190-session count in §3 is an estimate and was not verified (UNVERIFIABLE from the text alone).
