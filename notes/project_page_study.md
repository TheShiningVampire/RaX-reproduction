# How robot-agent-exploration.com shows what the robot is reasoning and doing

Source: https://robot-agent-exploration.com/ (fetched 2026-10-20). Files read: `index.html`,
`assets/js/{data,content,sessions,activity,code,simcases,interactive,how,boxing}.js`,
`assets/css/interactive.css`. No videos were downloaded. Local copies:
`$SCRATCH/site/`.

## 0. Page map, and the most important find

| Section (anchor) | What it shows | Is the video synced to text? |
|---|---|---|
| `#overview` | One overview film (mp4). It starts at low quality and swaps to the HQ file in place once that file is buffered. | No |
| `#tasks` "Real-robot sessions" | Tabs, one per task, each playing a full raw session video (`tasks/v3/<id>.mp4`). | No: raw footage only |
| `#method` "How RAX works" (`how.js`) | Four "acts" of the air-fryer session. Each act pairs a clip with an architecture diagram, a caption and a code or activity panel. | **Yes, by wall clock** (§4) |
| `#method` "Exploration compiles into code" | Two speed cards: "241× faster on the air fryer: Agent, 72 min / Fully automated program by RAX, 18 s", and "103×… Bandu 17 min / 10 s". | n/a |
| `#cases` "Robot rollout sessions" (`interactive.js` `caseCard`) | One tab per task. Each tab has a **Session** row (chapter clips, each with an activity feed) and a **Program** row (step clips, each with highlighted code lines). | Yes, **in proportion** to clip progress (§1–3) |

**The authors' page includes our exact task.** `simcases.js` adds a tab called
"DexJoCo: Tower of Hanoi" (key `hanoi`) with this description: *"Simulation · two Franka arms,
Allegro hands · 47 exploration episodes, 2 h 17 min session … writes a program that completed all
150 formal episodes on unseen layouts."* Its 8 chapters, 8 program steps and 35 condensed code lines
show exactly what our page needs to show. They are also the authors' account of the behaviour we did
not reproduce: a **rolled vertical pinch, `ROLL = 0.44`**, where we used a front hook grasp, and
**lag-predictive alignment**, where we tried a manual correction on an arm that was still moving.
Our page should put our chapters next to theirs.

## 1. "Session" view: chapter cards paired with clips

Data: `RAX.sessions[key].chapters[]` (sessions.js; the simulated cases come from simcases.js).

```json
{ "title": "A decoy cup", "when": "20:45", "status": "fix",
  "text": "The operator moves the cube and leaves a decoy cup on its old spot. The controller, which assumed the cube stays put, picks the decoy; the agent rewrites identification to follow the cube by its shape and height in depth, checks it on the recording, and completes the pick.",
  "quote": "Template matching breaks once the cube moves. I'll use depth instead and follow the cube's shape and height above the table.",
  "vid": "assets/vid/sess/cube_03.mp4", "poster": "assets/vid/sess/cube_03.jpg" }
```
An example from their Hanoi case:
```json
{ "title": "A pinch at the wall swings", "when": "episode 2", "status": "fail",
  "text": "A palm-down pinch has to sit at the wall of the red disk, because the peg stands 13 cm above it. The pinch lifts the disk up the peg, but the pinch line passes 2.8 cm from the disk's centre of mass and the disk swings by about 40°. A firmer squeeze drops it off the pegs, which ends the episode after 397 steps.",
  "vid": "assets/vid/hanoi/hanoi_s03.mp4" }
```
- **Chapters map to clips one to one.** Every chapter has its **own pre-cut short clip**
  (`cube_01…08.mp4`, `hanoi_s01…s08.mp4`). There is **no seeking inside a long video**. Chapters do
  not hold timestamps into a master file. `when` is a display label only: a wall-clock time for
  real-robot tasks, `"episode N"` for simulated ones.
- **Fields:** `title` is a short headline. `text` has 2–4 sentences in the third person, giving concrete
  numbers and the cause of each failure. `quote` is optional and gives the agent's own words in
  first person, shown in italics. Sometimes it is the operator's words instead, e.g.
  `"you grasped them together"`. `status` is one of `explore | fail | fix | success`.
- **Arc:** 7–8 chapters per session, in the order explore → fail → fix → success. A failure is
  always followed by a fix chapter that names the change, e.g. `"grips cups 1.2 cm below the top at 8 N"`.
- **Rendering:** each chapter becomes a numbered dot in a row labelled "Session". The side panel
  shows a kicker in the status colour, such as `Session 3/8 · fix, 20:45`, then the h3 title, the
  text, and the quote as a blockquote.

## 2. "Activity" view: what the agent was doing during each chapter

Data: `RAX.activity[key].chapters[i] = {span, lines[]}`. Index i matches session chapter i.
The file header says the data comes *"from the session's tool-call log and transcript."*

```json
{"span":"21:05–21:08","lines":[
 {"time":"21:05:08","kind":"run","text":"python3 code/find_cube/controller.py > output/runs/run4_stdout.txt 2>&1"},
 {"time":"21:05:10","kind":"call","text":"request_operator('reset', 'Robot is watching from above. Please now place ...')"},
 {"time":"21:05:29","kind":"say","text":"Trial 4 is running: the cube was found at (0.501, −0.173) along with all four cups"},
 {"time":"21:06:13","kind":"operator","text":"done"},
 {"time":"21:06:49","kind":"call","text":"franka_gripper('grasp', width=0.04, force=15, speed=0.05)"},
 {"time":"21:08:25","kind":"say","text":"SUCCESS end-to-end, 166 s, no intervention"}]}
```
An example from their Hanoi case, chapter 3 (a failure ends with a lesson written to memory):
```
20:07:35 run   python3 experiments/ep2.py 0 squeeze right
20:10:20 log   disk now {'c': array([-0.233, -0.020]), 'top': 1.1976, ... 'yaw': 0.3098, 'n': 273}
20:18:50 log   {"env_id": 0, "episode": 2, "status": "closed", "task_complete": false, ...}
20:18:54 edit  edit memory/TIPS.md
20:18:54 edit  + - Dropping a disk off the pegs (red fell onto board/table) ENDED the episode ~10 steps later
```
- **Kinds and their labels** (`KIND` map): `call` is labelled "robot" (MCP tool call), `run` "shell",
  `edit` "edit", `say` "agent" (a short paraphrase of the agent's reasoning), `operator` "operator",
  and `log` "output" (a measured value printed by a script). The method player also uses `error`
  ("stop", red) and `ok` ("done", bold green).
- **Counts across six real sessions:** edit 122, say 117, run 104, call 98, operator 53, log 39.
  Each chapter has about 11–14 lines, so each one is a **curated sample**, not the full log.
- **Edit lines** come in pairs: first `"edit path/file.py"`, then one or two `"+ …"` or `"- …"`
  lines that show the important constant or signature (rendered green or red), e.g.
  `- COVER_PX = 45` then `+ COVER_PX = 65`. A continuation line leaves its time blank.
- **Panel layout:** a header reads "What the agent was doing, 21:05–21:08", followed by a
  monospace grid with three columns (`9.5ch | 8ch | 1fr`) for time, kind label and text.
  Text is shortened with `...`.
- **Sync with the clip (case cards):** the sync is *proportional, not timestamp-based*. At clip
  progress k between 0 and 1, lines `0..floor(k·n·1.05)` are shown. Lines fade in, and the newest
  line gets a teal tint and a left bar. The panel auto-scrolls to keep the newest line in view.

## 3. "Program" view: phases, steps and linked code

Data: `RAX.programs[]` holds `{id, name, summary, phases:{key:label}, steps[]}`. `RAX.code[key]` holds
`{file, lines:[{t, s:[stepIdx…]}]}`.

- **Phases:** 2–4 named groups of steps, e.g. their Hanoi has
  `{see:"Measure and grasp", red:"Move 1: red onto blue", yellow:"Move 2: yellow onto red"}`.
  The phase decides the step's colour (`--ph-1..4`: teal, amber, green, violet) and kicker.
- **Steps:** 6–8 per program, each with its **own clip**: one program run is cut into one
  segment per step. A step contains `title`, `text` (what the code does, with numbers measured
  in this run), an optional `tag` (an overlay on the video such as `"0.8 mm off at the first look"`
  or `"Step 1064 of 1500"`), an optional `branch` (the recovery path, shown with a ↺ icon:
  `"If the disk rose less than half the lift, it opens, backs off and pinches again."`), and an
  optional `viz` (images "Computed by its program", which open in a lightbox).
- **Code links:** the program is condensed to about 30 lines of real code plus explanatory
  `#` comments. Each line has `s`, the list of the step indices it belongs to. A line can belong to
  several steps (`hz.lower(...)` has `s:[3,4]`). Header lines can list every step
  (`# controller.run` has `s:[0..7]`). Blank separators have `s:[]`. From their Hanoi code:
  ```
  [2]   if bottom is None or bottom < start_bottom + 0.5 * dz:
  [2]       self.log(f"GRASP FAILED for {color}: ...")   # open, back off, pinch again
  [3,6] lag = bot.measured(side)[0] - arm.pos
  [3,6] err = np.asarray(peg_xy) - (c - lag[:2])
  ```
- **Rendering:** a header reads "Running: code/hanoi/controller.py, task.py (the submitted
  program, condensed)". Lines not in the current step drop to 40% opacity. Lines in the step get
  a teal tint. The panel scrolls to the first lit line. A ▶ pointer **walks through the lit lines
  in proportion to clip progress**. Keywords are highlighted, and failure paths such as `raise`,
  `StepFailure`, `return False` and `Unsure` are shown in red.

## 4. Interaction

- **Case card** (`interactive.js`): a grid of video (1.45fr) and side panel (1fr), with a
  full-width code or feed panel below. Two rows of numbered dots, "Session" and "Program", form
  one playlist. **Clicking a dot plays that clip from 0.** Clips **auto-advance** 200 ms after
  they end. Arrow keys step between clips, and there is a play/pause button. Playback starts only
  when the card is in view (IntersectionObserver). The next clip is prefetched. Past dots are
  tinted, and the current dot is filled. For a step with no video, a still image is held for 3.2 s
  with a progress bar.
- **Method player** (`how.js`) is the **one place with true time sync**. Each act lists
  `segs: [[wallStart, wallEnd, speed], …]`, which maps clip seconds to wall-clock seconds through
  piecewise speed-ups. Example: `[['09:19:15','09:19:45',10], ['10:03:35','10:06:20',48], …]`.
  `wallAt(t)` turns the video's currentTime into wall time, and a feed line appears once
  `hms(line.time) <= wall`. For the "program runs alone" act, `sched: [[secAfterStart, codeLine], …]`,
  built "from the run's own call log", moves the ▶ marker line by line in real time. An SVG
  architecture diagram (Memory, Coding agent, Robot program, Robot, with an "isolation boundary")
  lights the active nodes. It sends animated "packets" along edges labelled with the function
  name for each feed line. The agent's status pill reads "exploring", "fixing the code" or
  "not in the loop", and a red warn state shows on an `error` line. Each act ends with a stat
  line, e.g. `"72 min of the agent's own inference, 262k output tokens"` or
  `"178 s unattended; 18–23 s of inference per run, against 72 min in run 1"`.
- **Agent compared with program:** done through (a) the two rows on the same card, Session
  (agent) and Program (compiled code), and (b) the speed cards (bars for agent minutes against
  program seconds, with a large "241×").
- **Before/after:** a `compare()` slider widget is available for a step that has `compare: [before, after]`.

## 5. Visual style

- **Status colours** (light / dark): explore `--rax` #00a3a6 / #2cc7c9 (teal), fail `--warn`
  #d03b3b / #e66767, fix `--amber` #c98500 / #e0a12a, success `--new` #0e8a5f / #2fb380.
  Labels: "exploring", "failure", "fix", "success".
- **Feed kind colours:** robot uses teal, shell amber, edit violet (`--code` #5b4fcf), agent
  grey italic sans-serif, operator green, output muted, stop red, done bold green. `+`/`-` diff
  text is green/red.
- **Typography:** Archivo for text, JetBrains Mono at 0.74rem for feed and code, Unbounded for the
  display numbers. The palette is white with very light rules (#dde4e7) and has a full dark theme.
- **Layout:** cards with 12px radius. The feed or code panel has a fixed height of 250px and
  scrolls. Below 860px the layout becomes one column. A dark pill tag sits in the bottom-left of
  the video.
- **Writing style:** short and concrete, with real numbers ("50 N", "12.6 cm", "step 1064 of
  1500"), every failure explained by its cause, and no adjectives.

## 6. Spec for our page (one static HTML file, vanilla JS)

### 6.1 Data schema (`report/v2/page_data.js`, `window.REPRO = {...}`)
```js
REPRO = {
  meta: { task, paper_claim: "150/150 (authors' Hanoi case)", ours: [{session:"S1", formal:"82/150", cost:34.08}, {session:"S2", formal:"…", cost:…}] },
  sessions: {                       // "s1", "s2"
    s1: {
      title, span: "23:18–…", cost_usd, episodes,
      chapters: [{
        id: "E2", title, when: "episode 2 · 23:56–00:26", status: "explore|fail|fix|success",
        text,                        // 2–4 sentences, third person, with numbers and causes
        quote,                       // optional: the agent's own words, quoted exactly from the transcript
        cost_usd: 14.41,             // cumulative at chapter end (from timeline.jsonl)
        outcome: "fail (out of steps, red placed)",
        vid, poster,                 // one pre-cut clip per chapter (clips/…)
        segs: [["23:56:10","23:58:40",20], …],   // optional: clip t -> wall clock; without it, sync is proportional
        feed: { span, lines: [{time, kind:"call|run|edit|say|log|operator|error|ok", text, cont?:true}] },
        authors: "hanoi:3"           // optional: matching chapter in the authors' Hanoi case, for a side-by-side
      }]
    }
  },
  program: {                        // the submitted bundle (c8712bc…), one formal episode
    file, bundle, phases: {see, red, yellow},
    steps: [{phase, title, text, tag, branch, vid, poster, sched?: [[sec, codeLine]]}],
    code: [{t, s:[stepIdx]}]         // about 30 lines, condensed by hand from the bundle's controller.py
  },
  perturbation: [{                   // the test the user just asked for
    name: "+8 mm yellow align offset", what, expected, result: "k/n", delta_vs_base, verdict: "helps|hurts|neutral",
    vid, why                        // one sentence: the mechanism behind the result
  }],
  speed: { agent_min, program_s }
}
```

### 6.2 UI, top to bottom
1. **Header strip:** task, our results compared with the authors', and cost. Each number is a
   pill, with no prose.
2. **Case card** (copy of `caseCard`): video on the left. On the right: `Session 3/9 · fail, ep 3`,
   then the title, text, quote, and a cost/outcome chip. Below that, rows of numbered dots coloured
   by status: **Session 1**, **Session 2**, **Program**. Below the whole card, the feed or code
   panel (250px, 3-column grid, kind colours as in §5).
   - Sync: use `segs` when present (the `wallAt` algorithm); otherwise reveal lines in proportion
     to progress (`floor(k·n·1.05)`). For program steps, move the ▶ through the lines with
     `s ∋ step`, by `sched` when available and otherwise in proportion.
   - Click a dot to load that clip at 0 and autoplay. Clips auto-advance. Add arrow keys and play/pause.
3. **"Authors' version" toggle** on each chapter that has an `authors` link: shows their chapter
   text in a muted card beside ours (e.g. our E1 "front pinch, finger hits peg" next to their ep 2
   "pinch at the wall swings"; our hook grasp next to their `ROLL = 0.44` rolled vertical pinch).
   This is the clearest way for an advisor to see *where* our reproduction went a different way.
4. **Perturbation panel** (answers the user's "what is done and how it helps/hurts"): one row per
   perturbation. Each row has a plain-language description of what was changed, a success bar
   (base compared with perturbed, k/n), a coloured verdict chip (helps green / hurts red /
   neutral grey), a one-sentence mechanism, and a clip button that plays the representative failure
   in the main player.
5. **Speed card:** agent wall-time (session minutes) against program seconds per episode, in the
   style of "241×".
6. Light/dark tokens copied from §5, layout down to 360px, and no external JS. Keep only the clips
   locally (`report/v2/clips/`, one ≤10 s mp4 per chapter or step, cut with ffmpeg by speeding up
   the wall-clock span and recording that speed in `segs`).

### 6.3 Authoring rules (as the authors do it)
- Each chapter has its own clip. Cut clips, speed them up, and keep the `[start, end, speed]` list
  so the feed can sync exactly.
- About 12 feed lines per chapter. Choose the lines that explain the decision: the probe call, the
  measured log value, the `say` line with the conclusion, and the edit with the key constant.
- Every `fail` is followed by a `fix` that names the concrete change.
- Quotes are the agent's exact words, never paraphrased.
- Quote the agent's numbers only after checking them against logs and results.json.
