---
name: darbar-handoff
description: Run this immediately BEFORE /compact (or before ending a session) so nothing that matters is lost when the conversation is summarised. Sweeps for facts, decisions, gotchas and half-finished work that exist ONLY in this conversation and routes each to its one home - a task row, a note, the charter, CLAUDE.md or memory - then writes the deterministic snapshot the SessionStart hook prints back after compaction. Records, unanswered questions and things already visible elsewhere are NOT rows, and on any board colleagues read it proposes rather than files. Use when about to compact, about to clear, wrapping up, handing off, or when asked whether everything is in sync with the board.
---

# Darbar handoff

One job: **after this runs, a fresh session that has read only the board and the snapshot
knows everything you know.** Compaction is lossy and you cannot predict what it drops, so
the fix is not a better summary, it is moving the facts somewhere compaction cannot reach.

The board is the handoff. `data/handoff.md` is only a cache the `SessionStart(compact)`
hook prints; the durable store is Darbar itself, because that is what a fresh session, a
lane, and Raj all read anyway.

## Step 1 — the facts a shell can read

```bash
python3 ~/fafo/darbar/scripts/handoff-snapshot.py --print
```

Board rows, git dirty/unpushed, which of the five processes are actually up, recent
commits. This costs no judgement, so do not re-derive any of it by hand.

## Step 2 — the part only you can do

Read back over this conversation and find what is **not** in that snapshot. This is the
whole point of the command; skipping it makes the hook a status printer.

Look for exactly these, they are what has actually been lost before:

- **Work discussed but never filed.** A bug noticed in passing, a follow-up agreed in
  prose, a "we should also…" nobody ticketed. `backlog` is a fine status for it — but read
  *What is NOT a row* below before you file, because most of what this sweep surfaces is
  not work.
- **A decision and its reasoning.** Rejected options are the expensive part. A row saying
  what was chosen, without why, gets re-litigated in a week.
- **Gotchas bought with time.** A command whose obvious form is wrong, an env var that
  must be sourced rather than passed, a flag that means something other than it reads.
  These never survive compaction and always cost the same hour twice.
- **State that contradicts the code.** Something running, migrated, deployed or killed
  that no file records.
- **Undrained feedback on a linear-native project.** A project with `linearUrl` set keeps
  its tasks in Linear; darbar holds only history and the gabbar feedback intake. If this
  session saw feedback rows arrive there and did not carry them into Linear (comment on
  the right ticket, or a new labelled issue) and resolve them, that queue is invisible to
  everyone working in Linear: drain it now, or say in the report exactly which rows wait.
- **Blocked work and what it waits on**, named as a person or an event, not "later".
- **Anything you told Raj you would do next.** An intention in prose is not a plan.

Where each goes:

| what | where |
|---|---|
| pending work, however small | a task row (`backlog`/`todo`) |
| why a route was taken | `description` or `notes` on the row it concerns |
| a durable rule about how to work | the project charter, so lanes read it too |
| a gotcha about this machine or repo | the repo's `CLAUDE.md`, in one line |
| a fact about Raj's preferences | auto-memory, not the board |

**File it, do not describe it.** "Worth remembering that X" in your reply is exactly the
thing that will not survive.

**One fact, one home.** That table is a routing decision, not a menu. A gotcha that went
into `CLAUDE.md` does not also get a ticket; a preference in auto-memory does not also get
a ticket. Filing the same fact twice is not thoroughness, it is two things to keep in sync
and one board somebody now has to read past.

### What is NOT a row

This is the half the sweep gets wrong, and it gets it wrong in the same three ways every
time. Before you file anything, it must pass this test: **a row is work somebody will
pick up and do.** If no one would ever be assigned it, it is not a row.

- **A record is not a row.** "So a future session knows the tests were deleted on purpose"
  is a note, a `CLAUDE.md` line, or a memory entry. The moment your justification for a
  ticket is *so nobody is confused later*, you have written the reason it should not be a
  ticket. Existing rows take notes; history does not need its own card.
- **An unanswered question is not a row.** If you asked Raj something and the session moved
  on, the honest move is to ask it again in the report, not to file the shape of the
  question as work and let a board decide it by default. A question filed as a ticket looks
  answered to everyone who reads it afterwards.
- **A thing already visible is not a row.** An open PR, a live CI failure, a Linear issue
  somebody else owns: those already have a home where the people concerned are looking.
  Duplicating them into the board buys nothing and ages badly.

And if you find yourself writing "this one is the weak one" while filing it, stop. That
sentence is the finding. Put it in the report instead and let Raj say yes.

### Filing onto a board other people read

**On a shared or company-facing board, propose before you write.** DAR is Raj's own
infrastructure board and you may file there freely. Anything with human stakeholders — a
linear-native project, a Linear team, any board colleagues open — is different: a ticket
there is a message to other people, and three speculative ones filed at compaction time
are noise they have to triage.

So on those boards: list what you propose to file, one line each, and file only what Raj
confirms in that turn. The exceptions you may file without asking are the two where
silence is the expensive outcome: work that is genuinely blocked on a named person, and a
row that already exists needing its status or notes corrected.

If the sweep turns up more than about three candidate rows, that is itself the finding:
the session was under-filing all along, and dumping the backlog into a shared board at
compaction time is the wrong place to fix it. Say so, propose the two that matter.

## Step 3 — re-snapshot and report

Run the script again so the cache includes what you just filed, then report in this shape
and nothing longer:

```
filed:    DAR-2xx <title>, DAR-2xx <title>   (or: nothing was conversation-only)
proposed: <one line each, awaiting your yes>  (omit the line when there are none)
asking:   <a question you asked that never got answered>  (omit when there are none)
board:    N open · M pending feedback
git:      N dirty · N unpushed  (name them if unpushed > 0)
procs:    any DOWN, or "all up"
safe to compact
```

`proposed` and `asking` are why the sweep no longer needs to guess. Anything you were
tempted to file onto a shared board goes on those two lines instead, and a one-line
proposal Raj can say no to costs him a second; a ticket he has to find and cancel costs him
the rest of the afternoon.

If something is genuinely unresolved and cannot be filed, say so in one line instead of
`safe to compact`, and say what would resolve it. A handoff that hides an open question is
worse than no handoff, because the next session trusts it.

## After compaction

**State comes back on its own; doctrine does not.** The `SessionStart` hook on
`matcher: "compact"` prints the snapshot into the fresh context automatically, because
SessionStart stdout enters context and PreCompact stdout does not. That covers the board,
git and processes. It does not cover how the project is run: the operating manual was a
skill body, and a skill body is exactly what a summary drops.

So the other half of the pair is `darbar-resume`, and the hook tells the fresh session to
invoke it. It re-reads the charter and the event log from the API and re-loads Part 0 and
Part C from `darbar-project-init`, which is the authority for both skills and is
deliberately restated in neither. Running THIS skill after a compaction is harmless but
pointless; it just reprints state.

If the block did not appear, the hook is gated on the API answering on 4899 — start the
server, or run Step 1 by hand.
