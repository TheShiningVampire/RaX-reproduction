# RaX on DexJoCo bimanual_hanoi: results

`$S` = `$ROOT/runtime/auto-research/20261020T031742Z_f1e2aa9d11`. Numbers computed by `results.json` (same directory) from `$S/formal-scores.json`, `$S/state.json`, `$ROOT/session1/runs_table.json` and `$ROOT/session1/timeline.jsonl`.

## Headline

The controller written by the agent after 8 exploration episodes succeeded on **82/150 (54.7%)** of the formal episodes (`formal-scores.json` average_score 0.5467). The paper reports 100% at budget 8. The three evaluation seeds give almost the same rate, so the gap is not noise from one seed.

| Seed | Successes | Rate |
|---|---|---|
| 0 | 28/50 | 56% |
| 1 | 27/50 | 54% |
| 2 | 27/50 | 54% |

## Where failures happen

Failures are grouped by the last controller stage in the log (`stages[-1]` in runs_table.json). Success or failure always comes from the evaluator (`task_complete` in state.json). The controller's own `task_complete` printout is False on every formal run, so it is not used.

| Last stage reached | Failures |
|---|---|
| grasp | 46 (68% of 68) |
| lift | 15 (22% of 68) |
| check | 7 (10% of 68) |

Successful episodes end at `release_l` (73) or `check` (9).

**Grasp is the main failure.** Every episode where the controller logged a failed grasp on either arm was a failure. Every grasp failure involved the right hand, which picks the red disk first.

| Final grasp flag | Episodes | Successes | Rate |
|---|---|---|---|
| none failed | 104 | 82 | 79% |
| right failed | 36 | 0 | 0% |
| both failed | 10 | 0 | 0% |

The right-hand lift-check sequence (T = disk rose with the hand, F = it did not) shows that the retry occasionally recovers:

| Right lift checks | Episodes | Successes |
|---|---|---|
| F | 10 | 0 |
| FF | 33 | 0 |
| FFF | 3 | 0 |
| FT | 12 | 11 |
| T | 92 | 71 |

Even when both grasps pass, success is 79%. The rest of those runs end during `lift` (env ended the episode mid-lift with both grasps reported ok) or at `check` (the disks were not stacked as required).

## Success by layout

Red-disk x position (red_ctr[0], m), 1 cm bins:

| Bin (m) | Episodes | Rate |
|---|---|---|
| [-0.26, -0.25) | 26 | 62% |
| [-0.25, -0.24) | 29 | 69% |
| [-0.24, -0.23) | 30 | 53% |
| [-0.23, -0.22) | 32 | 41% |
| [-0.22, -0.21) | 30 | 53% |
| [-0.21, -0.20) | 3 | 33% |

Board height (board_top, m), 1 cm bins:

| Bin (m) | Episodes | Rate |
|---|---|---|
| [0.95, 0.96) | 13 | 54% |
| [0.96, 0.97) | 36 | 64% |
| [0.97, 0.98) | 26 | 58% |
| [0.98, 0.99) | 32 | 38% |
| [0.99, 1.00) | 31 | 61% |
| [1.00, 1.01) | 12 | 50% |

Neither variable shows a strong monotone trend; bins with more than 25 episodes range from about 40% to 69%. Layout geometry alone does not explain the failures.

## Episode duration

| | n | Median wall s | p90 wall s | Median end step | p90 end step |
|---|---|---|---|---|---|
| Success | 82 | 171 | 201 | 1081 | 1292 |
| Fail | 68 | 54 | 172 | 314 | 1091 |

Failures are mostly short, because grasp failures end around step 250 to 520.

## Cost and tokens

Total $34.08 (all claude-opus-5-5), 461 API calls: input 922, output 647,590, cache read 57,041,891, cache write (1h) 1,214,126. The cost stops increasing when the formal stage starts at 2026-10-20T01:57:28-0400, so the formal evaluation itself used no API spend. Minutes since 2026-10-19T23:18:32-0400 at which each exploration episode count was first reached: E1@1, E2@49, E3@73, E4@98, E5@119, E6@132, E7@149, E8@156. `results.json` stores the downsampled cost curve as `cost_timeline.points` (61 points).

## Representative formal episodes (videos)

Every formal episode has a video at `$S/formal-workers/episode-NNN/native/results/*/sim/sensors.mp4` (150/150). The published run dirs (`$S/published/runs/<run_id>/`) contain no mp4. All videos are h264, 1920x640, 30 fps, at about 1 frame per sim step.

| Kind | Episode idx | Seed | Layout | run_id | End step | Last stage | Video | Size | Dur |
|---|---|---|---|---|---|---|---|---|---|
| success | 3 | 0 | 2 | `formal-008f5e5938b04265bc8109cdae0ce214` | 1080 | release_l | `$S/formal-workers/episode-003/native/results/bimanual_hanoi_formal_20261020T055706Z_6ac981f2/sim/sensors.mp4` | 5.3 MB | 36.0 s |
| success | 5 | 0 | 4 | `formal-7d29e95757c54a99a482c2b6781cb556` | 1082 | release_l | `$S/formal-workers/episode-005/native/results/bimanual_hanoi_formal_20261020T055753Z_85672cdf/sim/sensors.mp4` | 5.3 MB | 36.1 s |
| grasp_failure (right) | 4 | 0 | 3 | `formal-f8eedeb98b0542ea9d6cda1e8a0b18c7` | 518 | grasp | `$S/formal-workers/episode-004/native/results/bimanual_hanoi_formal_20261020T055706Z_b7f8fe42/sim/sensors.mp4` | 3.0 MB | 17.3 s |
| grasp_failure (both) | 1 | 0 | 0 | `formal-948180510e8d4924ac855b3fc496dc88` | 255 | grasp | `$S/formal-workers/episode-001/native/results/bimanual_hanoi_formal_20261020T055706Z_3798627c/sim/sensors.mp4` | 1.8 MB | 8.5 s |
| lift_failure | 30 | 0 | 29 | `formal-b6344b5102874d1f8117dd54bee1e155` | 425 | lift | `$S/formal-workers/episode-030/native/results/bimanual_hanoi_formal_20261020T061317Z_2231620c/sim/sensors.mp4` | 2.7 MB | 14.2 s |
| check_failure | 6 | 0 | 5 | `formal-2bd2fc266a294684a7c775fdc9695b01` | 1444 | check | `$S/formal-workers/episode-006/native/results/bimanual_hanoi_formal_20261020T055754Z_cab19e76/sim/sensors.mp4` | 6.3 MB | 48.2 s |

Notes: the lift-failure example (idx 30) passed both grasp checks. The environment then ended the episode at step 435 during lift (`ended=True`). The check-failure example (idx 6) ran to step 1444 and failed at the final stack check (`$S/published/runs/formal-2bd2fc266a294684a7c775fdc9695b01/stdout.log`).

## Exploration episodes (budget 8)

| Ep | Mode | run_id | End step | Success | Video | Size | Dur |
|---|---|---|---|---|---|---|---|
| E1 | interactive | - | 1497 | False | `$S/native/results/bimanual_hanoi_exploration_20261020T031928Z_a9e1f1d2/sim/sensors.mp4` | 5.5 MB | 49.9 s |
| E2 | interactive | - | 1498 | False | `$S/native/results/bimanual_hanoi_exploration_20261020T040651Z_c0cfca4e/sim/sensors.mp4` | 5.3 MB | 50.0 s |
| E3 | interactive | - | 1500 | False | `$S/native/results/bimanual_hanoi_exploration_20261020T043053Z_59e19b98/sim/sensors.mp4` | 6.9 MB | 50.0 s |
| E4 | interactive | - | 1500 | False | `$S/native/results/bimanual_hanoi_exploration_20261020T045601Z_0d8a7e1c/sim/sensors.mp4` | 6.0 MB | 50.0 s |
| E5 | interactive | - | 1447 | False | `$S/native/results/bimanual_hanoi_exploration_20261020T051614Z_de2e0b4c/sim/sensors.mp4` | 7.0 MB | 48.3 s |
| E6 | rehearsal | `rehearsal-c967110e6ade4cdbb7261ae07fcce763` | 1213 | False | `$S/native/results/bimanual_hanoi_exploration_20261020T052952Z_20e506a5/sim/sensors.mp4` | 5.4 MB | 40.5 s |
| E7 | interactive | - | 306 | False | `$S/native/results/bimanual_hanoi_exploration_20261020T054707Z_902d6734/sim/sensors.mp4` | 2.0 MB | 10.2 s |
| E8 | rehearsal | `rehearsal-52fb2c2829ee430787bc7a534d51fd5e` | 1081 | True | `$S/native/results/bimanual_hanoi_exploration_20261020T055330Z_e034716b/sim/sensors.mp4` | 5.2 MB | 36.1 s |

E1 is the first interactive exploration episode. E8 is the only successful run during development: a rehearsal of the controller (`rehearsal-52fb2c2829ee430787bc7a534d51fd5e`). Each exploration video is matched to its episode by the `sim/<episode_id>` subdirectory next to `sensors.mp4`.
