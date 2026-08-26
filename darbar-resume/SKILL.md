---
name: darbar-resume
description: Rehydrate a Darbar orchestrator after a compaction, a /clear, a --resume, or when a fresh session inherits a live board. The read half of the pair whose write half is darbar-handoff. Re-reads state from the API (board, charter, event log, processes) and re-loads the operating doctrine from darbar-project-init, which is the authority and is deliberately not restated here. Use after compaction, when taking over a board mid-flight, when the SessionStart block appeared and you are about to dispatch, or whenever you are unsure whether you still know how this project is run.
---

# Darbar Resume

The pair is `darbar-handoff` before the lossy step, this one after. Handoff moves facts
somewhere compaction cannot reach; this skill goes and gets them, plus the part handoff
never had to save because it was never in the board: **how to run the project.**

## What a compaction actually eats, and what it does not

Be precise about this, because it decides what is worth spending tokens on.

**Survives, exactly.** Board state. The `SessionStart` hook re-reads the API live and
prints open rows, git, and processes into the fresh context. That block is authoritative
and anything in the summary that contradicts it is stale. You do not need to re-derive any
of it.

**Survives, lossily.** Whatever the compaction summary judged important, and the one-line
pointers in auto-memory. Both are hints, neither is an instruction set.

**Does not survive.** The operating manual. Orchestrate-only, the written pre-flight
before every dispatch, one agent per file, model tiering, lanes matching stakes, briefs
that point instead of pasting. That lives in the body of `darbar-project-init`, which was
in context because the skill was invoked, and a skill body is exactly the kind of thing a
summary drops. The failure is quiet and it is always the same: the orchestrator starts
working inline, dispatches everything on its own model tier, and over-lanes small rows.
Nobody notices for a while, because the board still looks fine.

That asymmetry is the whole design of this skill. State is cheap and mechanical, so read
it from the API. Doctrine is expensive and cannot be re-derived, so re-load it from the
one file that owns it.

## Step 1 — state, from the API

```bash
python3 ~/fafo/darbar/scripts/handoff-snapshot.py --print   # board, git, procs
PROJ=<PREFIX> python3 ~/fafo/skills/darbar-tick/sweep.py    # what is actually stuck
```

If the `SessionStart` block is already in this context and is minutes old, the snapshot is
a re-run for nothing: skip it and read the block. Then, for the project you are running:

- `get_project_context <prefix>` — the **charter is your standing instructions**, and it
  is per-project data in Mongo, which is exactly why it survives when a skill body does
  not. Read it before your next move, not after.
- `get_project_events <prefix>` — the event log is the only place that says *why* the
  board looks like this. Read it before you touch anything.
- The row you were mid-task on, by id. Another session or a lane may have moved it while
  you were compacting.

Two project-level facts to establish before dispatching anything, because both change what
you are allowed to do:

- **Is the project archived, and is it linear-native?** `linearUrl` set means Linear is the
  board of record: tasks live there, you have full CRUD only on issues carrying the
  `darbar/<PREFIX>` label, and darbar holds history plus the gabbar feedback pipe. Draining
  that feedback queue into Linear is then part of your job and nothing else does it.
- **Which agents and lanes this project actually has**, from the registry rather than from
  memory. A name you remember may have been renamed or removed while you were away.

## Step 2 — doctrine, from the authority

`darbar-project-init` **is** the operating manual. This file does not restate its rules,
on purpose: two copies of a doctrine drift, and the copy an agent happens to read is then
a coin flip. The same rule holds for `darbar-tick`.

Read, from `~/fafo/skills/darbar-project-init/SKILL.md`:

- **Part 0 — what binds** and **Part C — doctrine** (including *Token economics*): always,
  before your next dispatch. These are the parts that decay, and they are the parts whose
  loss costs money rather than correctness.
- **Part D — taking over** when the board is not in the state you left it in.
- **Part B — lifecycles** on demand, when you are about to touch a specific one (task,
  review lane, feedback, project, agent). Do not pull all of B in advance; it is reference,
  and reference read speculatively is the exact waste Part C warns about.
- **Part A — bootstrap** never, on a resume. The project is already registered. Re-running
  intake on a live board is how a session ends up re-declaring config wholesale and
  deleting a registry it did not mean to touch.

Headings move as the file grows, so locate them with a grep for `^# Part` rather than
trusting a line number you remember.

## Step 3 — say what you re-read, in one line

Before you act, state which project you are orchestrating, what mode it is in
(darbar-native or linear-native), and the next move. One line, not a recap. It is the
cheapest possible check that the rehydration actually happened, and if it is wrong, Raj
sees it before a fan-out spends anything.

Then continue the work. Do not re-plan what the board already says is in flight.

## What this costs, and why it is still the cheap option

Part 0 plus Part C is a few thousand tokens, once per compaction. The failure it prevents
is a single unnecessary fan-out, which Part C measures at roughly 15x a single thread. You
are buying back the discipline that keeps every later dispatch honest, and it pays for
itself the first time it stops one avoidable agent.

Do not read the whole manual on every wake-up, and do not run this skill on a wake-up
that is not a rehydration: a `/loop` firing re-enters `darbar-tick` with its own body
intact and needs nothing from here.

## When NOT to run this

- Mid-round, when nothing was compacted and the doctrine is still in context. Re-reading
  it then is pure spend.
- In a session that is not orchestrating a Darbar board. The `SessionStart` block is
  silent unless the API is up, and this skill is for whoever that block was speaking to.
- Instead of `darbar-handoff`. They are opposite ends: handoff files what only the
  conversation knows, this one recovers what the conversation lost. Running this before a
  compaction saves nothing.
