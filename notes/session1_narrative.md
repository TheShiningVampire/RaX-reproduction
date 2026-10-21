# What the agent did: RaX on DexJoCo bimanual_hanoi (session 20261020T031742Z_f1e2aa9d11)

Abbreviations: `S` = `$ROOT/runtime/auto-research/20261020T031742Z_f1e2aa9d11`,
`MEM` = `S/agent-workspace/memory`, `TL` = `$ROOT/session1/timeline.jsonl`.
All times are EDT, 2026-10-19/20. Costs are cumulative Claude spend from TL, sampled once a minute, so they can be off by up to one minute.
Episode start times come from `episode_start` events in `S/mcp.jsonl`. End times come from `evaluation.decided_at_unix_s` in `S/state.json`.
The narrative comes from the agent's own status lines in the transcript
(`S/claude-home/projects/*/37931746-8883-4fac-ba8c-04bcd1f71387.jsonl`) and from `MEM/PROGRESS.md` and `MEM/TIPS.md`.
The transcript contains 5 context compactions, at 23:45, 00:13, 00:46, 01:14 and 01:38.

## 1. Chapter table

| # | Episode (state.json id) | Wall clock | Cum. $ at end | What the agent tried | What it learned | Outcome |
|---|---|---|---|---|---|---|
| 0 | Setup | 23:18 to 23:19 | 0.69 | Read the task docs, skills and 3 demo terminal-state images, wrote a plan to memory | n/a | Started E1 |
| 1 | E1 interactive (`exploration_0_da9ed218`) | 23:19:32 to 23:56:07 | 8.59 | Wrote a depth/colour perception helper and measured disks, pegs and board. Then manual grasps on red: a rolled side grasp, palm-down claws, and a front pinch with index j1 1.42. It retried the pinch with the thumb closer | Hand geometry: the thumb tip is about 15 cm below the flange. The index rested on the board 2.5 cm below the thumb. A straight pinch gap (6.8 cm) is smaller than the red disk (7.5 cm) | Fail at step 1497. Red lifted about 1.9 cm, then dropped |
| 2 | E2 interactive (`exploration_1_0d1e1fe1`) | 00:06:54 [corrected] start (offline design from 23:56) to 00:26:15 | 14.41 | Added a wrist-depth-to-flange tool and peg detection for exact centres. Designed a front-facing hook grasp (index distal wraps the far face, thumb presses the near face) | The red move works end to end: hook grasp, a 1.5 cm lift check, a staged 20 cm lift, transport, then placing on blue (TIPS 1-2). The left R_LEFT pose is unreachable because yaw saturates at 11.4 deg (TIPS 5) | Fail at step 1498. Red was on the right peg, but only 59 steps were left for yellow |
| 3 | E3 interactive (`exploration_2_88a3aed5`) | 00:30:56 to 00:45:25 | 18.49 | Previewed left-arm reach (14 preview runs). Tried both hands; probed which left finger sits beside the thumb | It closed while the hand was still sliding and lifted too fast (19 cm in 60 steps), so red slipped and fell rotated 45 deg (TIPS 7, 8). Palm pushes cannot un-rotate a disk (TIPS 10). On the left hand the finger beside the thumb is j8-11 | Fail at step 1500. The left lift check was cut off by the step limit |
| 4 | E4 interactive (`exploration_3_2cf995c1`), first controller-driven run | 00:56:04 to 01:09:40 | 22.94 | Wrote `code/hanoi/controller.py` (stages perceive to check) and a dev wrapper `experiments/ctl.py`. Previewed the full plan (18 preview runs) and ran it stage by stage | The low right-arm park tangled with the left arm, so the right now parks at home (TIPS 14). Rotation converges with tau about 28 steps, so the rotation integral was dropped (TIPS 13). The left needed a deep curl (TIPS 9, 9b). Per-stage step costs showed it needed to cut to about 1070 steps | Fail at step 1500. Both disks were lifted and red was transported, then it ran out of steps |
| 5 | E5 interactive (`exploration_4_cf44bbe9`) | 01:16:17 to 01:23:49 [corrected] | 25.76 [corrected] | Ran a step-economy rewrite stage by stage: concurrent grasps, a fast 50-step eased place, and left staging during the right place | Red was placed and seated on blue. A manual xy correction on the still-lagging left arm overshot by 2.8 cm. Its conclusion: "never correct xy before settle". The red hook worked only 1 time in 3 | Fail at step 1447. Yellow fell off the board |
| 6 | E6 rehearsal of v1 bundle `2966a2af...` (`exploration_5_fa90e43c`) | 01:29:52 to 01:32:51 | 28.11 | Registered v1 and rehearsed it with no agent in the loop | The run was clean (rc 0, 1213 steps, 180 s) but did not succeed. After a compaction, ego-frame contact sheets showed that the right peg had been knocked about 20 deg during transport_r (TIPS 15) | No success. v1 became rehearsal-qualified and was kept as the fallback |
| 7 | E7 interactive dev run of v2 (`exploration_6_b01a245d`) | 01:47:11 to 01:53:29 (episode ended at step 306) | 33.66 | Tested v2 stage by stage: CLEAR 0.06, height settle after lift, staged place, mean offset | The red was wedged and tilted by the right hook. The regrasp opened 2.5 cm up and flipped the red off the board, which triggered the failure condition (TIPS 16). Fixes: lower the closed hand before opening, and a stronger right hook (untested live) | Fail at step 306 |
| 8 | E8 rehearsal of v2 bundle `7bc56ae7...` (`exploration_7_dca36ae7`) | 01:53:30 [corrected] to 01:56:14 | 33.81 | Registered v2 at 01:53:22 and rehearsed it | Both grasps worked on the first try. Lift 188 steps, transport 123, place_r 141, handover 165, place_l 141 | **Success** at step 1081 (rc 0, 165 s). Submitted at 01:56:33. Final spend $34.08 |

Afterwards the formal batch ran v2 on 150 episodes and got 82/150 = 54.7% (`S/state.json` formal_batch). The agent did not see this result.

## 2. Key measurements and decisions (sources: MEM/PROGRESS.md, MEM/TIPS.md)

- **Workspace geometry varies per episode.** Board top b ranged 0.9568 (E5) to 0.993 (E7) [corrected] and peg x ranged -0.207 to -0.2465 across E3-E8. The agent noted: "Layout b=0.9868, pegs x -0.228, peg_top 1.1649 (b varies 0.964-0.987 across episodes!)."
- **Hand geometry.** "Thumb inner surface local x~-0.010, y -0.025..-0.045 (descends 18deg), tip z 0.17. Index MCP x~0.066". "Straight pinch gap ~6.8cm < red 7.5 -> use hook".
- **Right grasp design (E2).** "R_RIGHT = [[0,0,1],[1,0,0],[0,1,0]] (fingers +y, palm +x, index down)". Hook H_G = [0,0.9,1.4,1.2,...,1.396,0,0.4,0.2]. The flange is held at b+0.07 because "b+0.065 -> thumb hits board, hand twists 20 deg" (TIPS 3).
- **Wrist-camera collision constraint.** "wrist camera mount (world flange+(0.04,-0.14,-0.03)) hits blue front face".
- **Left hand.** "j0-3 finger is on the side AWAY from the thumb ... Finger beside thumb is j8-11". The shallow hook failed 3 times. The deep curl [0]*9+[1.2,1.6,1.4]+[1.396,0,.4,.2] "lifted it 22 cm".
- **Control lessons.** "Rotation: converges to the command EXACTLY, time constant ~28 steps ... SEED rot = 0". "Large moves converge slowly: 60-step move + 10 hold still 3.3cm short in y".
- **Root cause of the v1 failure.** "the RIGHT PEG WAS KNOCKED OVER during transport_r (upright at s757, tilted ~20deg by s806". "Pegs are LOOSE bodies".
- **Failed approaches.**
  - "E1: rolled side grasp, palm-down claws (palm hits peg), front pinch with index j1 1.42 (knuckle jams on +v face)."
  - Closing while the hand was still moving, and a fast lift, both dropped the red (TIPS 7-8).
  - A manual xy correction before the arm settled overshot (E5).
  - Opening high during a regrasp flipped the red (E7).
  - A low right park tangled the arms (E4 preview).
- **Final decision.** "DECISION: submit v2 (fixes the peg-knock root cause; only bundle with a successful run)."

## 3. Bundles in `S/bundles/`

Only two bundles were registered by the agent (`mcp__auto_research__register`, source `code/hanoi`). The third directory is a harness checkpoint, not a controller.

| Bundle | When | What it is |
|---|---|---|
| `2966a2af454647b0825719b49aa06143` (v1, sha a1f1139c...) | 01:29:47 | Controller and skills after the E5 lessons: deep-curl right hook [0,1.2,1.6,1.4,...], place_fast, CLEAR 0.03, REGRASP_BEFORE 620. Rehearsed in E6: clean run, no success |
| `7bc56ae7250d439d93baa365d5c58c08` (v2, sha 0a219e5c...) | 01:53:22 | Submitted bundle (diff vs v1 below). Rehearsed in E8: success |
| `4a28212094344b9887b84fad9389ce84` (kind `agent_checkpoint`) | frozen at exploration_end (about 01:57) | Harness snapshot: session transcript, memory (3 files) and code (5 files). See `package.json` |

Diff v1 to v2 (`diff -u` of the two bundle dirs; only `controller.py` and `skills.py` changed; motion/perception/robot are identical):

- `CLEAR` went from 0.03 to 0.06, so the held disk passes at least 6 cm above the peg tops. This is the fix for the knocked peg.
- `lift_both` now uses `correct=True`, so it settles height before the lateral move. The loaded lift had ended about 2 cm low.
- `place_fast` was replaced by a new `place_staged`. It does a goto to 1.5 cm above the peg top, removes the xy error, then does one eased descent, with at most 3 tries in total: the first unshifted, the later ones shifted 5 mm (`max_tries=3`, `search=0.005`) [corrected].
- `measure_offset` now accepts a wrist estimate within 12 mm (was 6 mm) and uses the midpoint of the wrist and default offsets. The yellow wrist estimate had been 7-9 mm off.
- `regrasp` first lowers the closed hand back to the grasp height before it opens (the E7 fix).
- The right hook changed from `[0,1.2,1.6,1.4,...,0.4,0.2]` to `[0,1.5,1.6,1.4,...,0.6,0.3]`, giving a stronger squeeze. A per-arm `LIFT_RATIO` was added: r 0.6, l 0.5.
- `REGRASP_BEFORE` went from 620 to 540.

`S/agent-workspace/code` has **no git history** (`git log` reports that it is not a repository), so the only version evidence is the two bundle snapshots plus the transcript.

## 4. Tool-call counts

From `S/mcp.jsonl` (980 mcp_request events, plus 1 mcp_error). This file covers simulator tools only, and includes calls made by the controller during rehearsals.

| Tool | Requests |
|---|---|
| dexjoco_step | 692 (each request carries a list of actions; about 1,500 env steps per full episode) |
| dexjoco_observe | 249 |
| dexjoco_preview_run | 36, plus 1 error ("No interactive episode") at 23:59:45 |
| dexjoco_preview_describe | 2 |
| dexjoco_status | 1 |

Per window (each window runs from one episode start to the next; harness `supervisor-start`/`supervisor-end` observes are included, so the controller itself made 11 observes in E6 and 6 in E8 per `S/state.json` timing) [corrected]:

| Window | step | observe | preview_run |
|---|---|---|---|
| E1 | 56 | 73 [corrected] | 4 |
| E2 | 75 | 49 | 0 |
| E3 | 120 | 43 | 14 |
| E4 | 116 | 29 | 18 |
| E5 | 124 | 27 | 0 |
| E6 (controller) | 89 | 13 | 0 |
| E7 | 26 | 7 | 0 |
| E8 (controller) | 86 | 8 [corrected] | 0 |

Agent-side tool uses in the transcript, deduplicated by tool_use id, total 654:

| Tool | Count |
|---|---|
| Bash | 272 |
| Read | 151 |
| Edit | 104 |
| Write | 93 |
| ToolSearch | 9 |
| start_episode | 6 |
| status | 5 |
| finish | 5 |
| evaluate | 2 |
| register | 2 |
| rehearse | 2 |
| preview_describe | 2 |
| submit | 1 |

The agent called simulator steps through its own scripts via Bash: `experiments/drive.py` 74 times and `experiments/ctl.py` 11 times.

**Offline previews:**
- 36 successful `dexjoco_preview_run` calls on the robot-only simulator, which costs no episode steps.
- 12 runs of the agent's own offline mock (`experiments/mock_run.py`) to dry-run the controller for code errors and step counts. Reported results: 815, 712/702 and 755 steps on clean paths, and 1176-1309 steps with regrasps.

## 5. Robustness and overfitting

The agent was explicit that its evidence was thin. From its final message (transcript, 01:57):
- "One success only: the full chain has worked once, on one layout. The step count from one rehearsal says nothing reliable about the formal success rate."
- "the right-hand grasp on the red has worked first time in about 3 of 5 episodes."
- "with three regrasps the run is estimated at about 1485 of 1500 steps" (little margin).
- The stronger right hook was "untested live" before E8 (MEM/PROGRESS.md, E7 section).
- `manual_success_confirmed` stayed false because no `evaluate` call ever returned success. The only success was the E8 rehearsal.

Hard-coded constants that may not generalise:
- `BOTTOM_DZ` 0.0698, measured in E2.
- The `SEED` biases.
- The `HOME_POS` park pose.

On the other hand, the controller re-perceives board height, peg positions and disk poses each episode (`perceive` stage), which addresses the layout variation it measured.

Generalisation risks the agent noted:
- Layouts vary: b 0.9568 to 0.993 [corrected].
- Loose pegs.
- Marginal hook grasps: the red hook worked 1 in 3 in E5, "2 of 4" in E4/E5 per the skills.py comment.
- The formal 54.7% is consistent with that.

The agent did not run any multi-seed evaluation of the bundle: the budget allowed only one rehearsal per bundle.

## Verification

Independent fact-check, 2026-10-20. Sources were re-read directly; no agent code was executed.

1. **Formal result 82/150 = 54.7% on bundle `7bc56ae7...` (sha 0a219e5c...)**: CONFIRMED. `S/state.json` formal_batch: success_count 82, episode_count 150, success_rate 0.5467, error_count 0.
2. **Episode outcomes and end steps (E1 1497, E2 1498, E3 1500, E4 1500, E5 1447, E6 1213 no success, E7 306, E8 1081 success; E6 rc 0 / 180 s; E8 rc 0 / 165 s)**: CONFIRMED. `S/state.json` results[0..7] (end_step_id, task_complete, returncode, timing.total_seconds 179.8 and 164.7).
3. **Episode wall-clock times**: WRONG (corrected) in three places. The E2 start is 00:06:54, not 00:06:50 (`S/mcp.jsonl` episode_start time 1792469214.50). The E5 end is 01:23:49, not 01:25:41 (`S/state.json` results[4].evaluation.decided_at_unix_s 1792473829.95), so the E5 cumulative cost is 25.76 (TL sample 01:23:09), not 26.21 (that is the 01:25:10 sample). The E8 rehearsal started at 01:53:30 (results[7].started 1792475610.61); 01:53:29 is when E7 ended. The other starts and ends match. E8's 33.81 is the TL sample at 01:56:28, 14 s after the end, which is within the stated one-minute tolerance. `chapters.json` E5 was fixed to match.
4. **Submission at 01:56:33, final spend $34.08**: CONFIRMED. `S/state.json` submission.at 1792475793.60 is 01:56:33 EDT. The last TL row has cost_usd 34.0769.
5. **Diff v1 to v2 (only controller.py and skills.py changed; CLEAR 0.03 to 0.06; lift correct=True; measure_offset 6 mm to 12 mm plus midpoint; regrasp lowers first; hook [0,1.2,...,0.4,0.2] to [0,1.5,...,0.6,0.3]; LIFT_RATIO r 0.6, l 0.5; REGRASP_BEFORE 620 to 540)**: CONFIRMED by `diff -u S/bundles/2966a2af.../ S/bundles/7bc56ae7.../`. Bundle mtimes are 01:29:47 and 01:53:22. One detail was WRONG (corrected): `place_staged` makes at most 3 tries in total (`max_tries=3`), the first unshifted. It does not make 3 shifted retries.
6. **Layout variation "b ranged 0.9568 to 0.9897 across E3-E8"**: WRONG (corrected). `MEM/PROGRESS.md` line 24 records E7 b=0.993, so the range is 0.9568 to 0.993. The peg-x range of -0.207 to -0.2465 is CONFIRMED (PROGRESS lines 24, 39, 56, 66, 93, 18).
7. **MCP tool counts (980 requests and 1 error; step 692, observe 249, preview_run 36, preview_describe 2, status 1; error "No interactive episode" at 23:59:45)**: CONFIRMED by a recount of `S/mcp.jsonl`. Per-window counts: steps and preview_runs CONFIRMED. Observes WRONG (corrected): with start-to-start windows, E1 has 73 (not 72) and E8 has 8 (not 9). E8 is 6 controller observes plus 2 supervisor observes, matching `state.json` timing.mcp_tools.
8. **Transcript tool-use counts (654 total; Bash 272, Read 151, Edit 104, Write 93, ...), drive.py 74, ctl.py 11, mock_run.py 12, 5 compactions at 23:45, 00:13, 00:46, 01:14, 01:38**: CONFIRMED by re-parsing the transcript jsonl, deduplicated by tool_use id, with `compact_boundary` events. The mock step figures 815, 712, 702, 755 and 1176-1309 are CONFIRMED in PROGRESS lines 84, 89 and 32, and in the transcript ("702 steps clean, 1260 with 5 regrasps").
9. **Quoted memory text (rotation tau ~28, peg knocked "upright at s757, tilted ~20deg by s806", "never correct xy before settle", 1/3 red hook in E5, "2 of 4" skills comment, DECISION line, wrist-camera constraint, E8 stage step counts)**: CONFIRMED verbatim in `MEM/PROGRESS.md` lines 21, 47-48, 62-63, 67, 116, 18-19, `MEM/TIPS.md` rows 3, 13, 15-16, and the skills.py comment in bundle v2.
10. **Final-message quotes ("One success only ...", "about 3 of 5 episodes", "about 1485 of 1500 steps", manual_success_confirmed false)**: CONFIRMED. The last assistant text in the transcript (01:57:05) contains them, and every `manual_success_confirmed` value in the transcript is false.

Not checked independently (left as stated): the E1-row hand-geometry figures ("thumb tip about 15 cm below the flange", "index 2.5 cm below the thumb"). They come only from transcript narration and are not in MEM. Also not checked: the "no git history" claim. There is no `.git` in `S/agent-workspace` or `code/`, but `git log` was not re-run.
