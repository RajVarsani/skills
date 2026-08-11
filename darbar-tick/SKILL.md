---
name: darbar-tick
description: One maintenance pass over a Darbar board, designed to be armed on a timer with /loop so the board keeps draining when nobody is asking. Sweeps pending feedback and held reports, undispatched todos, review lanes left open after a manager reported, parents held by the done-gate, stale dispatches, duplicate review rounds, probe litter, and the three darbar processes. A tick that finds nothing prints one line and stops. Use when asked to keep working the board, drain the queue, run the loop, stop the board going idle, or check what is stuck. For bootstrapping or taking over a project, use darbar-project-init instead; that skill is the authority and this one only executes a round of it.
---

# Darbar tick

One tick. Not a session, not a work plan. It answers one question, "is anything on this
board waiting on somebody", and then either acts on a bounded amount of it or stops.

`darbar-project-init` is the authority for every rule referenced here, and it wins on any
overlap. `~/fafo/darbar/docs/orchestrator-loop.md` carries the exact routes and bodies.
This file carries only what a tick does and what stops it.

## The one non-negotiable property

**An idle tick costs a tool call and one line of output.** The board scan runs in the
shell, not in the context window, so the model never reads 200 task rows to learn that
nothing is wrong. Measured on the DAR board at 200 tasks: 0.25s, 88 bytes of output,
four HTTP calls, none of which land in context. A loop whose empty pass costs a full
board read and a paragraph of prose is a loop somebody turns off in a week, and then the
board stops draining again, which is the thing this exists to prevent.

Every design choice below follows from that.

## Step 1 - sweep

```bash
PROJ=DAR LIVE=DAR,MRF,ONCALL python3 ~/fafo/skills/darbar-tick/sweep.py
```

Read-only, never writes to the board. Exit `0` clean, `1` findings, `2` the api is
unreachable or the project does not exist.

**Exit 0: stop here.** Say nothing beyond the one line it printed, or nothing at all.
Do not summarise, do not restate what is fine, do not look for something to do. The
`clean streak N` on that line is the counter the stop conditions below read.

**Exit 2: stop here too.** If the api on 4899 is down, every other check is unreadable
and a retry loop against a dead port is pure spend. Report it once and stop the loop.
Do NOT restart the server: other sessions are mid-write on it, and restarting one you did
not start is a standing prohibition.

**Exit 1: continue to step 2**, with the budget.

The findings the sweep can print, and what each one means, in the order it prints them:

| Finding | What is waiting |
|---|---|
| `DOWN gabbar` / `DOWN proxy 4800` | a process is dead. Slack intake files nothing, or a published surface is a dead link |
| `FEEDBACK pending N` | humans and lane managers waiting on a verb |
| `PARKED held N` | gabbar refused somebody at the stakeholder gate. Not in any feedback query, so nothing else sees it |
| `TODO undispatched N` | the dispatch queue |
| `LANES open N` | review children still open, with the manager each is assigned to |
| `STALE DISPATCH` | handed to a builder over 15 minutes ago that never reported in. Assume it died |
| `HELD IN REVIEW` | lanes all closed, parent still held. It names the feedback holding it, or says to check autoAdvance |
| `NO LANES EVER` | in_review with no children ever spawned |
| `BLOCKED NO REASON` | a blocked row with a null blocker, which tells a successor nothing |
| `FEEDBACK PARKED NO TASK` | triaged or accepted with nobody on it |
| `DUPLICATE ROUND` | a parent was pushed out of in_review and back in, so a second round of the same lane spawned. Cancel the duplicate, do not staff it |
| `UNVOUCHED FEEDBACK AUTHORS` | open rows by a name that is not a stakeholder and not a registered agent. This is what probe litter looks like: the junk rows purged from DAR were all author `unknown` |
| `THROWAWAY PROJECTS LEFT` | a probe project nobody deleted. There is no DELETE route; clean from mongo by projectId |

`SAME AS LAST TICK` on the header means the fingerprint of the findings is unchanged since
the previous tick. See the stop conditions.

Two of those checks deliberately look only at work that is still open: `DUPLICATE ROUND`
skips a parent that has closed with all its children closed, and `UNVOUCHED FEEDBACK
AUTHORS` skips rows that are already resolved or rejected. Both are history at that point,
nothing can clear them, and a finding that can never be cleared would keep the board from
ever reading clean and would trip `SAME AS LAST TICK` forever. A recurring sweep may only
report things somebody can act on. History belongs in a one-off audit; DAR carries three
closed duplicate rounds (DAR-21 with two lanes doubled, DAR-208, DAR-210) that this sweep
found once and then correctly stopped reporting.

## Step 2 - act, in this order, within the budget

Cheapest and most human-facing first, so a tick that runs out of budget has already done
the part somebody is waiting on.

1. **Dead process.** Report it. Restart only a process you started, by exact pid.
2. **Pending feedback and held reports.** Read them. File anything new as a row before
   anything else, because the board carrying all pending work is the invariant every
   later check depends on. Then apply verbs, subject to the human gate below.
3. **Duplicate rounds.** Cancel the extra review children with a reason in `notes`.
   Never staff them.
4. **Silently stuck rows.** A `HELD IN REVIEW` parent needs its named feedback resolved,
   not a status push. A `STALE DISPATCH` gets re-dispatched or marked `blocked` with a
   blocker. A `BLOCKED NO REASON` gets a blocker written on it.
5. **Dispatch todos.** Last, and only under the dispatch gate below.

### The human gate

**A tick never uses `resolved`, `rejected` or `needs_clarification` unattended.** Those
three post into a stakeholder's own Slack thread, with the resolution text as the message
body, and the server sends it, not you. A background loop composing a reply to a human
who is not in the room is the single worst thing this could do. The tick may use the
silent verbs, `triaged`, `accepted`, `in_progress`, and may promote a row onto a task with
`resolvedTaskRef`; when that task ships, the server auto-resolves and replies with a
factual `shipped: X is done`, which is a statement about the board rather than a reply the
loop wrote.

Anything needing one of the three replying verbs is collected and reported to Raj at the
end of the tick, and the loop stops if that is all that is left.

### The dispatch gate

**Do not dispatch while a row is `in_progress`.** A tick that dispatches alongside live
builders is a second orchestrator scheduling writers into files it cannot see, and one
writer per file is the rule that a background loop is least able to honour. The sweep
prints `N in flight` on its header line for exactly this decision. With anything in
flight, the tick does steps 1 to 4 and stops before step 5.

## Budget, and what it costs

- **At most 2 dispatches per tick.** A tick is a maintenance pass. If eight rows are
  waiting, the next tick takes the next two. Nothing is lost, because the board is the
  queue.
- **At most one drain pass over pending feedback.** Do not re-read the queue after acting
  on it; the next tick does that.
- **No subagent for the sweep.** The tick IS the cheap thing. Spawning an agent to run a
  0.25s script costs more than the script.

Cost, stated so a wrong assumption is visible: an idle tick is one Bash call and 88 bytes,
call it under 200 tokens all in. At a 30 minute cadence that is roughly 20 idle ticks a
day, a few thousand tokens, which is the price of the board never going quiet. A tick that
finds something costs whatever the work costs, and that work was going to be done anyway;
the loop changes when it happens, not how much it costs.

## Stop conditions

The loop stops, and says why, on any of these. Most are read off the sweep output rather
than remembered, which is deliberate: a stop condition that depends on the model recalling
how many quiet ticks have passed is not a stop condition.

1. **`clean streak 3`.** Back the interval off, 20m to 60m. Announce it in one line.
2. **`clean streak 6`.** Stop the loop. Six quiet passes means nobody needs it right now,
   and Raj can re-arm it in one command.
3. **`SAME AS LAST TICK`.** The loop is spinning on something it cannot clear. Stop and
   report the finding. Do not try the same thing a third time.
4. **Budget exhausted.** Stop this tick. The next one continues. This is not a loop stop.
5. **Anything needing a human.** A replying verb, a `stakeholder_gap` parked item, a
   blocked row whose blocker is a person. Report and stop.
6. **Exit 2.** The api is unreachable. Stop, do not spin.
7. **Raj says stop, or starts driving the session himself.** A human in the room does not
   need a loop, and two schedulers on one board is worse than none.

## Arming it

Compose with the existing `/loop` skill rather than building a scheduler. `/loop` takes a
slash command and either an interval or nothing:

```
/loop 30m /darbar-tick
```

Fixed cadence. `/loop` arms one background shell loop emitting a sentinel and wakes on it,
runs the prompt once immediately, and tracks the pid so it can be stopped.

```
/loop /darbar-tick
```

Self-paced, which is the better default here: the tick picks its own next delay from what
it just found. Suggested pacing, and it is only a suggestion because the findings are the
real signal: work in flight or findings acted on, 10 to 15 minutes; clean, 30; clean
streak at 3, 60; clean streak at 6, stop.

Do not arm a second loop on a board that already has one. Check for a running sentinel
loop before arming, which `/loop` tells you to do anyway.

## What this tick will never fix

Worth saying plainly, because the sweep is precise about the board and silent about
everything else. It cannot see a file being edited, a commit being made, or an orchestrator
writing code it was told not to write. Those are enforced at the tool layer or not at all,
and `darbar-project-init` says which is which. A green tick means the board is consistent.
It does not mean the round was run properly.
