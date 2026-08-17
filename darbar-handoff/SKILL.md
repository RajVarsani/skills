---
name: darbar-handoff
description: Run this immediately BEFORE /compact (or before ending a session) so nothing that matters is lost when the conversation is summarised. Sweeps for facts, decisions, gotchas and half-finished work that exist ONLY in this conversation and files them to the Darbar board, then writes the deterministic snapshot the SessionStart hook prints back after compaction. Use when about to compact, about to clear, wrapping up, handing off, or when asked whether everything is in sync with the board.
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
  prose, a "we should also…" nobody ticketed. File it, even as `backlog`.
- **A decision and its reasoning.** Rejected options are the expensive part. A row saying
  what was chosen, without why, gets re-litigated in a week.
- **Gotchas bought with time.** A command whose obvious form is wrong, an env var that
  must be sourced rather than passed, a flag that means something other than it reads.
  These never survive compaction and always cost the same hour twice.
- **State that contradicts the code.** Something running, migrated, deployed or killed
  that no file records.
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

## Step 3 — re-snapshot and report

Run the script again so the cache includes what you just filed, then report in this shape
and nothing longer:

```
filed: DAR-2xx <title>, DAR-2xx <title>      (or: nothing was conversation-only)
board: N open · M pending feedback
git:   N dirty · N unpushed  (name them if unpushed > 0)
procs: any DOWN, or "all up"
safe to compact
```

If something is genuinely unresolved and cannot be filed, say so in one line instead of
`safe to compact`, and say what would resolve it. A handoff that hides an open question is
worse than no handoff, because the next session trusts it.

## After compaction

Nothing to run. The `SessionStart` hook on `matcher: "compact"` prints the snapshot back
into the fresh context automatically, because SessionStart stdout enters context and
PreCompact stdout does not. Running this skill again after a compaction is harmless and
just reprints state.

If the block did not appear, the hook is gated on the API answering on 4899 — start the
server, or run Step 1 by hand.
