---
name: darbar-project-init
description: Bootstrap a Darbar-tracked project AND run it. Day-zero OR retro-init of work already underway ("put this session under darbar", "register this project"). Interviews for context (mandatory, includes subagent structure + backlog scope + update cadence), registers the project + charter in Darbar, cuts branches, seeds the task tree so the board carries ALL known pending work, binds the Slack channel for Gabbar intake, then turns the current session into a strict orchestrate-only manager. Carries the full operating manual: every task / review-lane / feedback / project / agent lifecycle as the engine actually implements it, the standing orchestration doctrine, how to recover a project someone else left in a mess, and (Part 0) which rules the engine actually refuses versus which ones only sit in a document, including the writes that answer 200 and should not, the written pre-flight before every dispatch, and the two rules nothing here can enforce. Pairs with the darbar-tick skill, which is one maintenance pass over the board on a /loop timer. Use when starting a new agent-orchestrated project ("init project", "new darbar project", "spin up a project"), when bringing an in-flight session/effort under Darbar tracking, or when taking over an existing Darbar project.
---

# Darbar Project Init

You are bootstrapping a project into Darbar (the self-hosted tracker at
`~/fafo/darbar`, API on `http://localhost:4899`) and then running it.

This file is the whole job, in five parts. Read all of it before you start
dispatching; the bootstrap is the short part.

- **Part 0** what binds: which rules the engine refuses, which you must write down, and
  the two this file cannot enforce at all. Read it even on a re-read.
- **Part A** bootstrap: intake, registration, branches, seeding, announcement.
- **Part B** the engine: every lifecycle exactly as the server implements it,
  including the rules that surprise people and what happens when you break them.
- **Part C** doctrine: the standing rules for running the project, with the
  reasoning, because a rule you cannot justify is a rule you will drop.
- **Part D** recovery: taking over a board someone else left mid-flight, and
  the specific messes that show up.

The companion reference is `~/fafo/darbar/docs/orchestrator-loop.md`. It carries
the wire-level detail: exact routes, request bodies, field allowlists, the
cold-start command sequence. Rules live here; commands live there. When you need
to type something, open it.

# Part 0: What binds, and what only describes

Read this even if you have read the rest. It is the part that was missing.

On 2026-08-10, with this whole file loaded, one orchestrator session broke six of its own
standing rules in a day. It wrote code twice under strict orchestrate-only. It cleared
`lanes` on a row while an agent was mid-flight on it. It PATCHed a parent back to
`in_review` after a rework twice, spawning a duplicate review round each time, having
personally written down that exact trap the same morning. It let 43 probe rows pile up on
the live board across three sweeps. It went idle twice until it was asked why. It chained
`git commit` behind a repo-wide `tsc`, twice, where the failure printed the previous
commit and read exactly like success.

Every one of those was already documented, in this file, in the sentences you just read.
So the conclusion is not that the manual needs another paragraph. It is that **a rule
written in a document is the weakest form a rule can take**, and each of ours belongs in
the strongest tier it can reach.

## The three tiers

**Tier 1, the engine refuses.** The only kind that survives a distracted session, because
it does not depend on anybody remembering anything. Already here: `done` over an open
review child, `done` over open feedback, `lanes` after the review flow starts, the five
immutable task fields, an unknown lane key, a replying feedback status with no resolution,
a lane removal that would strand open work, publishing a share without the prefix echoed
back. Notice what those have in common. Each is a write the server can SEE is wrong from
the row in front of it.

Three more used to sit outside this tier, and **all three moved into it on 2026-08-17**
(DAR-247). They are recorded here rather than deleted, because the reason they were once
in a document instead of the engine is the lesson:

- **`lanes` is now frozen from `in_progress` onward**, not just from `in_review`. Clearing
  it to `[]` under a live builder used to be a silent 200, and the damage landed later:
  that builder reports `in_review`, an empty selection with `autoAdvance` self-advances the
  row straight to `done`, unreviewed. Echoing the value back unchanged still passes, so
  read-then-write works. Note `dispatchedAt` is NOT the liveness signal for these rows,
  because the builder's own status PATCH clears the stamp. The status is the signal.
- **Re-entering `in_review` after a fully closed round is now a 409** naming the children,
  overridable with `{"reviewAgain": true}` in the same patch. It fires only when every
  child of the previous round is closed, which is exactly the condition under which a
  second round would spawn; with one still open the server already declined.
- **`POST /feedback` now refuses an author the project does not know**, instead of
  defaulting a missing one to the literal string `unknown`. Gated on the project having a
  stakeholder list, matched against stakeholders ∪ registered agents. The rows that had to
  be purged all carried that exact string, and the inconsistency was stark: the APPEND
  route had always required an author.

**The lesson, which outlives the three fixes.** Every one of them sat written down here, in
the section about what documents cannot enforce, and being written down stopped none of
them. Two were then committed BY the session that had documented them that same morning. If
you find yourself adding a fourth bullet to a list like this, the list is not the fix.

One gap is known and open: two simultaneous PATCHes into `in_review` still spawn two rounds,
because the guard reads and then writes with a window in between. Concurrency, not logic.

**Tier 2, you have to write it down before you act.** The pre-flight below. Weaker than a
refusal, and its only mechanism is that producing a token is harder to skip than recalling
a rule. Be honest about that: if you find yourself dispatching without writing it, it has
failed, and the answer is to move the rule into tier 1, not to reword this paragraph.

**Tier 3, a sweep runs on a clock and prints what is wrong.** Not you remembering to
audit. The sweep is `darbar-tick` and the schedule is `/loop`. It catches the classes that
are invisible in the moment and obvious in aggregate: probe litter, duplicate rounds, held
parents, stale dispatches, a dead gabbar. It found all three duplicate rounds on the DAR
board in a quarter of a second, including one from two days earlier that nobody had noticed.

## The pre-flight

Four lines, written out, before every dispatch. Not considered. Written.

1. **Row.** Which shortId, and is it `todo` with nobody on it?
2. **Lanes.** What did this row freeze at? If its status is anything but `backlog`, `todo`
   or `blocked`, I am not touching `lanes` at all.
3. **Files.** Which files, and is any other in-flight agent inside them?
4. **Model.** sonnet or opus, and the reason in four words.

And two before any PATCH you are about to make on a row that is not yours:

- The row is `in_progress`. Then the answer is no. The agent owns its own status.
- The row is `in_review` and its lanes have closed. Then do not push it out and back in.
  Leave it there; resolving the feedback filed on it is what closes it (B2).

And one for the shell, because it is the same failure in a different window:

- **Never chain a check and a write in one call.** `tsc && git commit && git push` prints
  the previous commit and the word pushed when the check fails, which reads as success.
  Run the check, read its exit code, then commit as a separate call, then `git log -1
  --stat` and read the sha you just made.

## What a document cannot bind, stated plainly

Two of the six failures above are not reachable from this file or from the engine, and
pretending otherwise is how the next session inherits the same problem.

**"You write no code" cannot be enforced by prose.** The server sees board writes, not
file writes; there is nothing in Mongo that distinguishes an orchestrator's edit from a
builder's. The only thing that actually binds it is a harness-level `PreToolUse` deny on
`Edit`, `Write` and `NotebookEdit` in the orchestrator session. That is a change to Raj's
Claude Code settings, so it is his call and his config, not something a skill can assert.
Ask for it; do not work around it.

**The `&&`-chained commit is the same shape.** No board rule reaches a shell pipeline. A
`PreToolUse` matcher on Bash refusing a compound command containing `git commit` or
`git push` would bind it. Short of that it is a habit, and the pre-flight line above is a
reminder, which is exactly the weak thing this section is about.

The rest of Part C is real and worth keeping. Just read it knowing which tier each rule is
in, and when you catch yourself about to break one, ask whether it could have been a 409.

## Preconditions

1. Darbar server must be up: `curl -s localhost:4899/` returns text. If not:
   `cd ~/fafo/darbar && bun run server > data/server.log 2>&1 &`
2. Gabbar scribe should be up for Slack intake: check with
   `pgrep -f src/bot.ts`; start with `cd ~/fafo/darbar && bun run gabbar > data/gabbar.log 2>&1 &`
3. Register the Darbar MCP tools if not already in this session (see darbar README
   "MCP registration"). All board writes go through them or the REST API.

Never restart a server you did not start, and never restart the one on 4899 to
"pick up" a change without saying so first: other sessions are mid-write on it.

# Part A — Bootstrap

## Step 1 — Intake (MANDATORY, never skip)

The interview is not optional. Do NOT infer answers from context you already have,
and do NOT start building before it. A skipped interview is the documented failure
mode of this skill. Ask the user in ONE AskUserQuestion round (free-text follow-ups
only if genuinely blocking):

- **Project name** and **short-id prefix**. LETTERS ONLY, 2 to 6 of them
  (`^[A-Za-z]{2,6}$`, uppercased server-side). A digit is a 400, so `V2` is fine
  and `MRF2` is not.
- **Repos + base branches** (e.g. saturn-fe from main, mars from stage) and the
  **feature branch name** to cut
- **Sources**: Slack threads, Figma channels, docs, prior session ids
- **Stakeholders**: name, Slack handle, role (design / backend / review). These become
  the identity map Gabbar uses to attribute feedback and the humans tasks can be
  assigned to
- **Project-specific safety rules** (live keys, fixtures not to touch, deploy holds)
- **Slack channel** to bind for feedback intake (optional; DMs always work)
- **Shared local surface** (optional, defaults to NO; ask once, do not sell it):
  does anyone off this machine need to SEE a local surface, e.g. a dev server, a
  storybook, a docs preview? If yes, capture four things, because Step 2 needs all of
  them: the **port and base path** the surface is served on (`http://127.0.0.1:5173/fe`,
  not just the port), the **URL prefix** to publish it at, **which paths** should be
  reachable from outside, and **who the link goes to**. If nobody has asked for it, the
  answer is no and Step 2 skips the proxy
- **Subagent structure**: which review lanes this project may spawn (code-review is the
  baseline; add qa or design-qa only if the project will really have work that needs
  them) and who manages each lane, or explicitly none. Configuring a lane does not mean
  every task runs it; each task picks its own lanes (Part B2)
- **Helper subagents**: which non-lane helpers this project needs (deploy, seeding,
  migrations, release notes, data pulls), or explicitly none. Ask for each in registry
  shape, because the answer is copied straight into the registry in Step 2: a **name**,
  **what it does and decides** plus what it must never touch, and **when it should be
  dispatched**. Canonical example (from MRF): a `deploy-devx` helper that deploys a given
  branch to the dev environment and verifies it came up, dispatched once a task's review
  lanes close
- **Backlog scope**: which work streams to seed on the board now, including known
  pending items and human-owned work
- **Update cadence**: board-only | chat summaries | Slack via Gabbar (draft-first,
  never send without approval)

## Step 2 — Register the project

`create_project` (POST `http://localhost:4899/api/projects`) with name, prefix, repos,
stakeholders (`[{name, slackUserId, role}]`, resolve handles to user ids via Slack API),
`slackChannel`, and a **charter**.

`pipeline`, `agents` and `proxy` go in the SAME call. Registering a project is one POST,
not a POST followed by three PATCHes: the config runs through the same reader and the same
write path as every later edit, it is validated before the insert (so a malformed pipeline
is a 400 with no project created, never one left half-configured), and the response carries
`boardUrl` plus a `warnings` array for the things the server declines to fail on. Read the
warnings; nothing else surfaces them except the event log.

`stakeholders` is validated here too, not stored raw. A `slackUserId` must be a Slack USER
id, `U` or `W` then uppercase letters and digits, and anything else is a 400 naming the
index. That shape matters because it is access control, not metadata: Gabbar matches it
against the verified sender before filing feedback, so a handle typed as `@raj` would
refuse a real person silently forever.

The charter is the standing context pack every agent fetches via the
`get_project_context` MCP tool. Write into it:

- goal + streams of work
- the standing protocols. The defaults are Part C of this file, condensed; copy the
  clauses that bind THIS project rather than a summary of all of them, because the
  charter is what a builder or lane manager reads and they act on it. Always include:
  orchestrate-only, one writer per file, lanes explicit and default code-review only,
  one review round is the norm, commit discipline on shared checkouts (stage by explicit
  path, no `git add -A`, confirm with `git show --stat`), and the verification bar
  (typecheck plus a real test).
- the project-specific safety rules and update cadence from intake
- links to all sources

Keep the charter internally consistent. It is one blob of text with no schema, so a
clause you add in month two can flatly contradict one from day one and nothing will
warn you. When you add a rule that supersedes an older one, edit the older one out.
Adding a clause does not mean resending the charter: `append_to_charter` puts one line
at the end and leaves the existing prose alone. Editing an older clause out is still a
wholesale rewrite, which is the case the append tool deliberately does not cover (B4).

Save the returned `boardUrl` and `capId`. The capability URL is what stakeholders get.

The **review pipeline** comes from the intake's subagent-structure answer and rides on that
same POST as `{pipeline: {autoAdvance, reviews: [{lane, label, manager}]}}` (the same whole
pipeline can be declared later with the `set_pipeline` MCP tool, or PATCH
`/api/projects/:ref`): one lane per review kind, each
with a `manager` agent name. `reviews` replaces the whole lane list on every call, which
is what declaring a pipeline needs and is a trap for every edit after it: mid-session,
change one lane with `add_review_lane` / `update_review_lane` / `remove_review_lane` and
flip the boolean alone with `set_auto_advance` (B4). The
server then spawns one `type=review` subtask per lane the task itself selected whenever a
dev task reaches `in_review`, gates `done` on those closing, and
(with `autoAdvance`, the default) closes the parent when the last lane does.
Skip the pipeline only if intake explicitly chose "none".

The pipeline is the menu, not the plan. Configuring qa and design-qa here does not mean
tasks should run them. Every task states its own `lanes` at `create_task`, and the
normal answer is one lane. Write that expectation into the charter so a fresh session
inherits it.

The **agent registry** rides on the same call as `{agents: [{name, kind, brief, trigger?}]}`
(the same whole registry can be declared later with `set_agents`, or PATCH
`/api/projects/:ref`). One entry per agent this project will ever dispatch:

- every lane manager from the pipeline answer, `kind: "lane-manager"`
- `orchestrator` itself, `kind: "orchestrator"`
- every helper from intake, `kind: "helper"`

`brief` IS that agent's standing charter: write it as the prompt you would hand the
subagent, stating what it decides, what it does, and what it must never touch.
`trigger` (optional) is the when-to-dispatch hint, e.g. "after a task's review lanes
close". `set_agents` replaces the whole list, so send the complete registry with it and
never reach for it to change one entry: `add_agent` / `update_agent` / `remove_agent`
edit one agent and leave the rest standing (B4).
Names must be unique, because the name is the assignee key (`assignee`, `my_tasks`); a
duplicate is a 400 on the whole call. Pipeline managers should exist in the registry:
the server logs a `pipeline manager X not in agent registry` warning event otherwise,
warn-only, and the write still succeeds. Every agent then reads the registry alongside
the charter via `get_project_context` (GET `/api/projects/:ref/context`), and it is
served in the board payload too (GET `/api/p/:capId`).

`get_project_context` carries the pipeline as well, so the lane keys ARE on the tool every
agent is told to read: it returns name, prefix, repos, charter, stakeholders, pipeline,
agents, proxy, proxyPublished and a `configured` map of which of the three are set. Two
other places carry the keys if you need them: `GET /api/projects`, which returns every
field except the charter and is line 1 of the cold start, and the 400 you get for guessing
wrong, which lists the valid ones.

### Register the shared surface, if intake asked for one

Only if the shared-surface answer was yes. `set_proxy` (or PATCH `/api/projects/:ref`
with `{proxy: {prefix, target, public, enabled}}`) publishes one local dev server at
`<baseUrl>/<prefix>/`, the same public origin the board link uses. The config is
replaced wholesale on every call, which is the declare door and the last time you should
use it on this surface: afterwards `patch_proxy_route` edits one field and
`set_proxy_enabled` publishes or withdraws, and they are two tools rather than one so
that publishing can never happen as a side effect of fixing a path pattern (B4). The
server pushes the config into the proxy route table
and re-reconciles at every change and at boot, so a push that failed while the proxy was
down gets repaired rather than left as drift.

Configure it with the safety properties in front of you, because this route has no login:

- **Default is `enabled:false`.** Configure the route, read back what it exposes, then
  flip `enabled:true` in a second call. Do not share and then narrow. That second call is
  `set_proxy_enabled`, and enabling it requires the prefix echoed back as `confirmPrefix`:
  without it the 400 states the URL and the paths that would become reachable, so the
  decision is made with the exposure in front of whoever owns it. Withdrawing asks nothing.
- **Anyone who reaches the route reaches the target.** There is no auth in front of it and
  no per-stakeholder access. The URL is not the access control: the board link carries a
  21-char random `capId`, so it is genuinely unguessable, but the proxy prefix is a short
  word a human chose, so `BASE_URL/<prefix>/` is guessable by anyone who knows the domain.
  The `public` patterns are the boundary; the prefix is not a credential.
- **The prefix is the URL segment and the routing key.** It must be a non-empty string of
  `[A-Za-z0-9_-]`, anything else is rejected 400, and `p`, `api`, `files` and `-` are
  reserved, because they are the server's own paths and a prefix there would shadow the
  board itself. A prefix another project claims is a 409, and so is one already live on
  the proxy as a hand-added route, but only on a change that would publish over it:
  disabling, narrowing `public`, or clearing the config is always allowed.
- **The `public` patterns ARE the boundary**, and they are not regexes. Each entry is a
  literal path starting with `/`, matching as a prefix by default (`/assets/`), with a
  trailing `$` for an exact path (`/$` is the root and nothing else) and at most one `*`
  matching inside a single path segment (`/assets/*.js$`). Regex characters (`^`, `(`,
  `[`, `+`, `\`, `.*`) are rejected 400 with the form spelled out. Patterns match the path
  AFTER the prefix is stripped: for a project at prefix `dar`, the public request
  `/dar/assets/app.js` is matched as `/assets/app.js`, so write `/assets/` and never
  `/dar/assets/`, since the prefixed form matches nothing and the route serves nothing.
  Omit `public` and nothing is reachable from outside; `["/"]` exposes every path. Local
  requests are never filtered, so "it works on my machine" tells you nothing about what a
  link-holder sees. Check by fetching the public URL.
- **The target must be a dev server on this machine**, and the path is part of it. A Vite
  app served at base `/fe` needs `http://127.0.0.1:5173/fe`; without the path Vite gets
  `/` and 302s to `/fe/` forever through the prefix strip. Vite's `base` has to match the
  prefix. The host must be a literal loopback address, or the one name that is
  special-cased: `localhost`, any `127.x.x.x`, `0.0.0.0`, `::1`, `::` and the IPv4-mapped
  spellings of those are accepted. Public addresses, LAN and private ranges, link-local
  (`169.254/16`, `fc00::/7`, `fe80::/10`) and every other DNS name are rejected 400,
  because a literal address cannot leave this host while a name is resolved at request
  time by a resolver we do not control. No query string, no fragment, no `user:pass@`.
- **Tunneled requests carrying `%2f` or `%5c` are refused outright** (403), because the
  proxy forwards the path verbatim and dev servers decode before resolving `..`, so an
  encoded slash would walk out of an allowed prefix upstream. A legitimately encoded slash
  is refused too. Do not build a shared surface that needs one.
- **The target is never on the public board.** GET `/api/p/:capId` reports the prefix,
  the patterns and `targetRedacted: true`; the real host:port is only on
  `get_project_context`, which is local-only. Keep it that way in anything you write.
- **Teardown is yours.** See Part B4.

Tell the user the shared URL explicitly, alongside the board URL, and say who it is for.

## Retro-init — project already underway

When work exists but was never registered, or the orchestrator has been working
inline ("put this session under darbar"):

1. Run the SAME Step 1 intake, no shortcuts; the interview is mandatory here too.
2. Register the project (Step 2), or PATCH `/api/projects/:ref` if it half-exists.
3. Seed EVERY known pending item as a task: from the session so far, from memory
   files, from the user's answers, including human tasks assigned to stakeholders
   (e.g. "Tanisha: fix file_type hardcode"). Record `origin` on the create call,
   because `origin` cannot be changed afterwards (Part B1).
4. File every row at the status the work is actually at, which is the point of retro-init:
   already-done work as `done` cards so the board tells the true story of the project and
   not just its future, work in flight at `in_progress`, work waiting on a reviewer at
   `in_review`. Nothing gates a create. One thing to expect: a row filed at `in_review`
   now SPAWNS its lanes at create (Part B1), so it arrives with real review children
   assigned to real managers. That is what you want for work genuinely under review, so
   state `lanes` on those rows as deliberately as on any other. Do not reach for `lanes: []`
   to file a quiet `in_review` row: with `autoAdvance` on, an empty selection self-advances
   at create and the row lands at `done`, not `in_review` (verified). Work that is finished
   should be filed as `done`, and work still in hand as `in_progress`.
5. Invariant from here on: **the board reflects ALL known pending work at all
   times.** An empty todo column while work is pending is a bug. Fix the board,
   then continue.

Then proceed with Steps 3 to 5 as applicable (branches may already exist; skip cutting,
verify instead).

## Step 3 — Cut branches

For each repo from intake: fetch, branch from the stated base, push only if the user's
standing rules allow pushes. Confirm each with `git -C <repo> branch --show-current`.

## Step 4 — Recon and seed the task tree

Spawn recon subagents in parallel (Agent tool), one per source: Slack thread digest,
Figma inventory, codebase state, prior session transcripts. Each returns a structured
list of work items with evidence.

Promote their output into Darbar: `create_task` per item (streams as parent tasks,
concrete items as subtasks via `parentTaskRef`), origins recorded, known blockers set,
and `lanes` stated on every row (`["code-review"]` unless Part B2 says otherwise;
parent stream rows that carry no diff get `[]`). Cover every stream from the intake's
backlog-scope answer; anything pending that you know about but do not file is a bug.
Log a `project bootstrapped` event.

## Step 5 — Announce in Slack

If a channel was bound: draft the announcement as Gabbar (board link plus "file feedback
by DMing me or mentioning me with a task id like `PREFIX-12`"). If a shared surface was
published, put its URL next to the board link and say what it is, so nobody has to ask
where to look. **Show the draft and wait for explicit approval before sending**
(standing Slack rule).

Then say out loud that you are now the orchestrator, report the board URL, the shared
surface URL if one was published, task count seeded, branches cut, stakeholders
onboarded, and anything from recon that needs the user's call. From here on you run
Parts B and C.

# Part B — The engine, lifecycle by lifecycle

Every rule below is enforced server-side in `apps/server/src/api.ts`, so it holds no
matter who writes: board drag, MCP tool, or curl. That is why the surprises are worth
memorising. You cannot get around them by picking a different client.

## B1 — Task lifecycle

Statuses: `backlog`, `todo`, `in_progress`, `in_review`, `qa`, `blocked`, `done`,
`cancelled`. Types: `feature`, `bug`, `chore`, `review`, `regression`.

**There is no state machine on transitions.** Any status can go to any other status;
`backlog` straight to `done` is accepted, and so is `done` back to `in_progress`. Two
things and only two things are enforced, both on the way into `done`, and both only for
non-review tasks:

1. **Open review children 409.** `PATCH {status:"done"}` on a task with any review
   subtask not in `done`/`cancelled` returns
   `has N open review subtask(s); close them (or cancel them) first`. Cancelling a lane
   satisfies the gate, which is the escape hatch when a lane is genuinely not applicable.
2. **Open feedback filed ON the task 409.** Any feedback row whose `taskId` is this task
   and whose status is `pending`, `triaged`, `accepted` or `in_progress` blocks `done`:
   `has N open feedback row(s) (FB-3); resolve or reject them first`.
   `needs_clarification` does NOT block, on the grounds that the ball is with the
   reporter, so a task can ship with an unanswered question outstanding. Notice this
   second gate: it is the reason a parent sits in `in_review` after its last lane
   closed, and it is the one people misread as a bug in the pipeline.

**`in_review` spawns on the way in, from either direction.** Lanes spawn when a PATCH moves
a task INTO `in_review` from something else, and also when a task is CREATED at
`in_review`. Consequences:

- A task **created** with `status:"in_review"` gets its lanes there and then. It used to
  spawn nothing ever and sit in `in_review` forever, showing a review in flight that nobody
  was assigned, which is exactly the row a retro-init produces. If you have an old card
  seeded that way it is still empty, since nothing backfills: move it out and back in.
- PATCHing `in_review` onto a task already in `in_review` is a no-op for spawning, which
  is exactly what you want during rework (Part C, review scale).
- Once a round is fully closed, moving the parent out of `in_review` and back in spawns
  a **whole fresh round** of every selected lane. That is how a second review round
  happens by accident.

**`lanes` freezes.** `lanes` is the per-task subset of configured lanes: `["code-review"]`
a subset, `[]` explicitly none, `null` or absent means every configured lane. It can be
edited freely while the task is `backlog`, `todo`, `in_progress` or `blocked`, and then:

- a task in `in_review`, `qa`, `done` or `cancelled` 409s with
  `lanes are frozen once the review flow starts`. Note `blocked` is not frozen and `qa`
  is, which is not obvious from the column order.
- a task with any review child at all, including closed and cancelled ones, 409s with
  `already has review children; lanes cannot change`.
- an unknown lane key 400s and names the valid keys, which is the cheapest way to
  discover them.
- a malformed shape (`lanes: [123]`) 400s rather than being coerced, so a typo can never
  silently read as "explicitly none".

So the lane you left off is a decision you keep. Decide once, at filing.

**`dispatchedAt` is the dispatch fact, and only the orchestrator writes it.** You send
`{"dispatched": true}` and the server stamps its own clock; a non-boolean is a 400, and
`false` clears the stamp (a dispatch written off). Any status change to a DIFFERENT
status clears it automatically, because the agent reporting for itself supersedes the
hand-off; a PATCH that sets the same status again leaves it alone. An explicit
`dispatched` in the same body as a status change wins, which is how you re-dispatch.
The board renders the badge WITH ITS AGE and turns it red past 15 minutes, but only on
`todo` and `backlog` rows: a stamp on any other status is invisible on the card. That is
the whole mechanism by which a builder that never started is visible instead of looking
like work in flight.

**Immutable after create, and it says so now.** The task PATCH allowlist is `title`,
`description`, `status`, `notes`, `type`, `assignee`, `blocker`, `lane`, `assigneeType`,
`dispatched`, `lanes`, and `addCommit` (append-only, one hash per call). The five things
that cannot move after create refuse the write instead of absorbing it: `origin`,
`commits`, `shortId`, parentage (`parentTaskRef`, `parentTaskId`) and the project
(`project`, `projectId`) each 400 with the reason and the route that does the job, e.g.
`commits — append-only: one hash per call via {"addCommit": "<sha>"}`. So "fix the origin"
or "reparent this card" now fails loudly rather than reading as done, and a mis-parented
card still has to be replaced rather than moved. Any OTHER unrecognised field is still
ignored with a 200, and a PATCH with nothing in the allowlist returns the row unchanged and
logs no event, so read back anything you are not sure the route accepts.

**Nothing enforces `blocker` text on a `blocked` task.** A blocked row with a null
blocker is accepted and tells your successor nothing. Always send both.

## B2 — Review lane lifecycle

A dev task arrives at `in_review`, by a PATCH or by being created there. For each lane in
`project.pipeline.reviews` that the task's `lanes` selected, the server inserts a child
task: `type: "review"`, `status: "todo"`, `lane` set to the lane key, `assignee` set to
that lane's `manager`, `title` `"<label>: <parent title>"`, `origin` `"pipeline:<parent>"`.
It logs a `spawned` event per lane, and refuses to spawn if any review child is still open,
so a re-entry cannot double up a live round.

Two edge cases:

- selected lanes that resolve to nothing (an explicit `lanes: []`, or a selection whose
  lanes were later removed from the pipeline) log `no review lanes selected` and go
  straight to the advance check. With `autoAdvance` on, that means `in_review` closes
  itself, which is why helper rows use `lanes: []`, and it applies at create too: a row
  FILED at `in_review` with `lanes: []` lands at `done`. With `autoAdvance` off it does NOT
  self-close; it logs `awaiting explicit push` and waits. The two are often stated as if
  `lanes: []` alone were enough. It is not.
- no pipeline configured at all, and `lanes` absent, means the task simply rests in
  `in_review` with no children and no advance. Not an error, and easy to mistake for one.

**A manager finds its queue by assignee.** `my_tasks` with `assignee: "staff-engineer"`,
or `GET /api/tasks?assignee=staff-engineer&open=true`, optionally `&lane=code-review`.
The board also has a per-lane view with open counts, which is the fastest human check.
Never hand-create a `type=review` task: the create route will happily accept one, and
it will then sit in a queue with no parent gate behind it.

**That read hands you a PAGE, and you have to check whether it is the whole set.** Both the
tool and the route answer with `{total, returned, offset, limit, truncated, tasks}`, plus
`nextOffset` and a `note` when rows were withheld; `limit` defaults to 1000 and maxes at
1000, and a limit outside that range is a 400 rather than a silent clamp. `truncated` is
the field that matters. If it is true, this is a sample: repeat the same query with
`offset=nextOffset` until it is false, or read the whole project in one payload with
`get_board` (`GET /api/p/:capId`). The rule generalises past this endpoint, and it is worth
carrying: a paged answer states what it withheld, so treating a page as the whole set means
ignoring a field that told you otherwise. This endpoint used to `.limit(200)` and return a
bare array with nothing saying it had cut, and MRF answered 200 of 419 to the very read an
agent resumes from, so a session told to resume from the API alone resumed from a sample.
The trap is gone; the habit of reading the envelope before the rows is the part to keep.

**Findings are feedback, not notes.** A lane files each finding as a feedback row on the
PARENT (`POST /api/feedback` with `taskRef` the parent and `authorType: "agent"`). Those
rows land in your normal pending queue and, because they are filed ON the parent, they
hold the parent's `done` (B1 gate 2). That is deliberate: the lane can close its own
child and go away, and the parent still cannot ship over an unresolved finding.

**Closing a lane** is `PATCH {status:"done"}` (or `cancelled`) on the review child. A
review child's own close is never gated. Closing the last one runs the advance check on
the parent: reviews all closed, no blocking feedback, `autoAdvance` not false, and the
parent is set to `done` with its dispatch stamp cleared. If blocking feedback remains it
logs `reviews closed but N open feedback (...) — holding`. If `autoAdvance` is false it
logs `all reviews closed — awaiting explicit push out of in_review`. Read the event log
before you conclude anything is stuck.

**The full one-round flow closes itself, verified end to end.** Lane files FB-1 on the
parent and closes its child. Parent holds in `in_review`. You promote FB-1 onto a rework
task with `resolvedTaskRef` (the row auto-moves to `triaged`). The rework builder ships
its own row; when that row hits `done`, the server auto-resolves FB-1 with
`shipped: DAR-12 (title) is done (commit abc123)`, replies in the author's thread, and
then re-runs the advance check on the task FB-1 was filed on, which closes the parent.
You never touch the parent's status. Keep the parent in `in_review` the whole time and
no second round can spawn.

## B3 — Feedback lifecycle

Statuses: `pending`, `triaged`, `needs_clarification`, `accepted`, `in_progress`,
`resolved`, `rejected`. Like tasks, there is **no ordering enforced**: any status to any
status. The linear reading in the repo's CLAUDE.md is a description of intent, not a
constraint.

Rows arrive at `pending`: from Gabbar (Slack DMs and mentions, with the thread and any
screenshots attached), from lane managers, and from you when a stakeholder says something
in chat. Chat is a feedback channel too: file it as a row before you triage it, so the
feedback tab carries the full human trail.

`GET /api/feedback/pending` returns `pending` plus `needs_clarification`, oldest first.

**A reopened clarification row does not carry the answer.** When the author replies in the
thread, Gabbar's reopen sends `{status: "pending"}` and nothing else, so the row comes back
into your queue with its ORIGINAL body and with your own question still sitting in
`resolution`. Nobody rewrites what a reporter wrote: the PATCH route writes only `status`,
`resolution`, `type` and `resolvedTaskRef`, and it refuses `body` and `attachments` BY NAME
rather than absorbing either under a 200. The answer exists only in Slack.
Go and read it, via the row's `slack.channel` and `slack.ts`, before you re-triage. A row
that reappears with no visible change is the normal case, not a broken reopen.

**More of something already filed is an APPEND, not a second row.** A screenshot for a
finding already on the board, a correction, another screen it also happens on: that is one
defect and it stays one row. `append_to_feedback` (Gabbar's own `add_to_feedback`, POST
`/api/feedback/:shortId/append`) adds an attributed line at the end of the body and unions
any attachments, leaving the reporter's own words and the row's id and status exactly where
they were. Filing a second row instead puts one defect in the triage queue twice and leaves
somebody deduping what was never two things. Three things the route deliberately will not
decide for you, because each is a judgement rather than a mechanism: it is not idempotent,
so a repeat adds a second attributed line and says so; an append onto a resolved or
rejected row succeeds and warns, because that addition now sits in no triage queue; and
reopening stays a separate act you make on purpose (`resolve_feedback {pending}`), which
also puts the task the row was filed on back under the done gate. Exact bodies, the
`note`-not-`body` trap and the three warning strings are in orchestrator-loop.md, 6 and 7.

A follow-up can still arrive as a **separate row** when somebody reports it fresh rather
than adding to what is there. Expect the duplicate and dedupe it: one defect is one task,
with both rows resolved pointing at it. Never re-file a reopened row as a second card
yourself.

**Which states reach the author.** The server, not the bot, posts the reply, and only for
three statuses:

- `resolved` → `*FB-3 resolved.* <resolution>`
- `rejected` → `*FB-3 not actioned:* <resolution>`
- `needs_clarification` → `*FB-3:* quick question, <resolution>`

`triaged`, `accepted` and `in_progress` are silent, which is what makes them the right
states for "on the board, author hears back on ship". Three details that bite:

- **all three replying statuses require a resolution and 400 without one.** The reply text
  IS the resolution, so the server refuses to send a bare header or a developer placeholder
  into a stakeholder's thread. The error names the author and says what to write.
- the resolution it uses is the **effective** one: the `resolution` in this request body, or
  the one already stored on the row if you send none. So the two-step way still works,
  write the reason first and flip the status after, and re-sending the same status with no
  body change is fine. What cannot happen is a reply with nothing in it.
- a failed Slack post is logged as a project event, never raised. If you expected a
  reply, check the event log.

In practice that reorders the work: decide the sentence, then apply the verb. You cannot
close a row and write the reply afterwards.

**Promotion into a task** is `resolvedTaskRef` on the feedback PATCH. It sets
`resolvedTaskId`/`resolvedTaskShortId`, and if the row was `pending` with no explicit
status it auto-moves to `triaged`, because promoting IS triaging. When that task later
reaches `done`, every row promoted onto it that is still `triaged`, `accepted` or
`in_progress` auto-resolves with the shipped text and replies in thread. Rows sitting at
`needs_clarification` are NOT picked up by that sweep, so a promoted-but-unanswered row
goes quiet forever; resolve or reject it by hand.

A `resolvedTaskRef` naming a task that does not exist is a **404**, and the row is not
touched. It used to be ignored under a 200, which left a row promoted in name only: the
ship sweep follows `resolvedTaskId`, found nothing, and the row sat open while the board
said it was tracked. A typo now fails in your hand instead of at ship time.

Note the deliberate asymmetry. Rows FILED ON a task (`taskId`) block its `done`. Rows
PROMOTED ONTO a task (`resolvedTaskId`) are auto-resolved BY its `done`. A lane finding
is usually both: filed on the parent, promoted onto the rework.

**Dedupe at triage.** Same defect from two authors is ONE task and two resolved rows
pointing at it, so each author gets their own thread reply. Before creating any task from
feedback, scan the open tasks for a card that already covers it
(`GET /api/tasks?project=X&open=true`, and check `truncated` before you conclude there is
no such card, per B2). A second card for one defect is worse than a missing one: two
builders, two diffs, one file.

## B4 — Project lifecycle

**Init** is Part A. **Retro-init** is the same interview plus a seeding pass that puts
history on the board as done cards and every known pending item, human-owned included, as
open ones. The rule that makes retro-init worth doing is the resume contract: a fresh
session must be able to take over from the API alone.

**Config has two doors, and the whole skill of editing it is picking the right one.**

The **declare door** is `POST /api/projects` at init and `PATCH /api/projects/:ref`
afterwards, with `set_pipeline`, `set_agents` and `set_proxy` on top of it. Each field
replaces its value entirely: `pipeline.reviews`, `agents`, `stakeholders` and `proxy` are
whole lists, `charter` is one string. That is exactly right for declaring a surface, which
is why init is one call and why these tools still exist. It is the wrong door for a change:
"edit one agent's brief" sent as a one-element `agents` array deletes every other agent,
returns 200 and logs a cheerful `project updated (agents): agents [...]` listing only the
survivor. Nothing warns you, and the registry is what the orchestrator dispatches from.

The **edit door** is one tool per intent, and it is what you use from the second call on:
`add_stakeholder` / `update_stakeholder` / `remove_stakeholder`, `add_agent` /
`update_agent` / `remove_agent`, `add_review_lane` / `update_review_lane` /
`remove_review_lane`, `set_auto_advance`, `append_to_charter`, `patch_proxy_route` and
`set_proxy_enabled`. You send only the thing you are changing; the SERVER reads the current
value, merges, and hands the result to the same validator the declare door uses. So a
partial edit cannot reach a state the wholesale door would have refused: identical readers,
identical 400s, identical event log, identical proxy reconciliation. The properties worth
knowing, all of them enforced server-side:

- **Addressing is edit-only.** An agent name, lane key or stakeholder name that is not
  there is a 404 that lists what is, never an upsert, because a typo silently registering
  a second `staff-enginer` is the accident this door exists to prevent. Creating is its
  own POST, and it 409s on a name already taken, comparing trimmed and case-folded so
  `Staff-Engineer` collides with `staff-engineer` instead of becoming a second dispatch
  key. The one thing created implicitly is the pipeline CONTAINER when you add the first
  lane to a project that had none, since a container has no name to mistype.
- **Lane changes are gated on open work.** Removing or renaming a lane that open tasks
  select 409s with the task ids and says which of two end states each one lands in: a task
  that named only this lane skips review and, with `autoAdvance`, goes straight to DONE
  UNREVIEWED, while a task with no `lanes` field losing the LAST lane spawns nothing, logs
  nothing and STALLS in `in_review`. Re-pick those tasks' lanes, or repeat with `force`.
  Tasks that keep another lane are warned about, not gated. Everything else is a warning
  rather than a refusal, on one rule: gate when the consequence is a review that silently
  does not happen, warn when the consequence is visible on the board. Pointing a lane at an
  unregistered manager only warns, because the review task is still created where anyone
  can see it, and so does removing an agent that still holds open tasks or manages a lane.
- **Renames move config, never data.** Renaming an agent rewrites any pipeline lane that
  named it as manager, and reports back the open tasks still assigned to the old name; it
  does not reassign them, and neither does a stakeholder rename. That queue is unread until
  you PATCH each task.
- **The proxy is deliberately two tools.** `patch_proxy_route` changes prefix, target or
  allowlist and cannot touch `enabled` (it 400s and names the other route). `set_proxy_enabled`
  publishes or withdraws and does nothing else. Exposure is never a side effect of an edit.
  Editing a route that is already live also asks for the prefix as confirmation when the
  change is not a literal narrowing; editing a withdrawn one never asks.
- **These gates are the granular door's manners, not an invariant of the system.** The
  declare door stays unguarded on purpose, because an init has to configure a whole
  pipeline or a whole share in one call, so anyone who insists can still bypass every gate
  above with one wholesale PATCH. Do not read a gate as protection against yourself.

Two things still have no edit door: rewriting or restructuring the charter (append only
adds a line at the end, and it is not idempotent, so check before repeating a call you
think failed), and replacing the stakeholder list in bulk. Both go through
`PATCH /api/projects/:ref`, read-edit-send-whole, with the same care as before.

**There is an archive, but still no delete route.** `PATCH /api/projects/:ref
{"archived": true, "archiveReason": "..."}` (MCP: `archive_project` / `unarchive_project`)
flips a project to closed. There is still no `DELETE /api/projects`, no `DELETE /api/tasks`.
Archiving is refused with 409 on a project with open rows unless you pass `cancelOpen: true`
(which does step 1 below for you, and records on each cancelled row that the project was
archived, and when) or `force: true` - so the discipline below is enforced now, not merely
recommended. **Archiving does not withdraw the shared proxy route.** That is the one step
below that leaks if skipped, and archiving does not cover it: closing a project properly is
still this:

1. Every task in a terminal state. Cancel what will not be done, with a reason in
   `notes`. Do not leave a backlog column as a monument (Part C).
2. Every feedback row `resolved` or `rejected`, each with a resolution sentence, because
   that sentence is the last thing an author hears.
3. **Withdraw the shared proxy route, if the project had one.** This is the one step that
   leaks if you skip it: there is no login in front of that route and nothing but the
   `public` list keeps a passer-by out. `set_proxy_enabled` with `enabled:false` takes the
   URL down and keeps the config, resending nothing and asking no confirmation; PATCH
   `{"proxy": null}` clears the config entirely and is still the wholesale door.
   Then **confirm rather than assume**: the returned project doc carries
   `proxyPublished`, which is what the server reports it actually put in the route table
   and has not withdrawn. Empty `proxyPublished` is the state you want at close. If the
   reconcile could not reach the proxy it says so and leaves the route LIVE; the next
   change or a server restart converges it, so re-check instead of walking away on the
   first 200. A route the project no longer owns (someone else repointed the prefix) is
   deliberately left alone and reported, not deleted.
4. A final event on the log saying the project is closed, so the trail ends somewhere.

**Linear-native projects (since 21 Aug 2026; supersedes the 19 Aug "mirror" pilot).** A
project may carry `linearUrl` (MCP: `set_linear_url`; read it back on
`get_project_context`). That URL is the label-filtered view in the company's Linear
workspace, and for such a project **Linear IS the board of record** — there is no darbar
task board to keep in sync (the two-day mirror pilot proved a hand-synced copy drifts
immediately; Raj killed it). The darbar project is ARCHIVED and survives for exactly two
things: history, and the gabbar feedback pipe, which has no archived-gate and keeps
filing rows.

The working contract for agents on a linear-native project:
- **Tasks live in Linear.** Read them there; move them there. Agents have FULL CRUD on
  issues carrying the `darbar/<PREFIX>` label — create, edit, move status, comment. An
  issue WITHOUT a darbar label belongs to a colleague: read-only, always.
- **Feedback still arrives through gabbar** as darbar feedback rows on the archived
  project. The orchestrator drains that queue into Linear: a comment on the relevant
  ticket when one exists, a comment on the standing feedback-inbox ticket when it is
  general, a NEW labelled issue when it is its own work item. Then resolve the darbar row
  (resolvedTaskRef where a darbar row exists, else a resolution naming the MEE id) so the
  reporter's Slack thread gets its reply — that reply machinery is the one thing Linear
  cannot do and the reason the pipe stays.
- **Convention:** rows go into the company's EXISTING Linear projects (never a new team or
  project per round), always carrying the workspace label `darbar/<PREFIX>`; the label
  view is the board.
- **Review pipeline, lanes, done-gates do not apply** on the Linear side — those are
  darbar-engine features. A linear-native project runs on Linear's own workflow plus the
  orchestrator's judgment.

**Throwaway projects.** If you need to exercise the API, do it on a throwaway prefix,
never on a live project. Since there is no delete route, cleanup is direct Mongo against
`mission_control`: delete the project's tasks, feedback and events by `projectId`, then
the project. Verify nothing of it remains, and touch no other prefix.

## B5 — Agent lifecycle

An agent exists in three places, and all three have to agree.

1. **Registry**: `project.agents`, one entry per agent you will ever dispatch, with
   `kind` and the `brief` that IS its dispatch prompt. `name` is the assignee key, so it
   is the join between the registry and every task row. A pipeline manager missing from
   the registry is a warning event only; the lane still spawns and the task is still
   assigned to a name nobody defined.
2. **Dispatch**: one subagent per task, prompted with the registry `brief` plus that
   task's context and nothing invented. Stamp `{"dispatched": true}` at the moment you
   hand it over. The subagent owns its row from then on: `in_progress` on start,
   `in_review` with `notes` when done, `blocked` with a `blocker` if stuck. You do not
   move a dispatched task's status by hand.
3. **The board**: the dispatch badge with its age is the only thing standing between a
   dead builder and a card that reads as busy. Nothing polls the agents; nothing detects
   a crash. A stamp older than 15 minutes on a `todo`/`backlog` row means the builder
   never reported in. Either re-dispatch it or mark it `blocked`, and never assume it
   started.

Helpers are dispatched exactly like builders and get their own board row with
`lanes: []`, so the row can self-close and the work is as visible as anyone else's. A
registry `trigger` is a hint about when it usually fires. Nothing server-side dispatches
a helper; you decide.

# Part C — Doctrine

These are standing rules. Each one cost real time to learn, so the reasoning is attached:
you will meet a case the rule does not obviously cover, and the reasoning is what tells
you what to do then.

**Board honesty.** The board reflects ALL known pending work at all times, human-owned
work included. An empty todo column while work is pending is a bug in the board, not a
quiet week. File new work the moment you learn of it, from a feedback thread, a builder's
notes, a lane finding, or your own observation, and file it before the round ends rather
than after you have thought about it. The test is the resume contract: a fresh session
reading only the API must know everything you know. Numbers must mean exactly one thing
each, on the board and in anything you write: if a count excludes cancelled rows, say so
where the count is, because a number whose definition lives in someone's head is a number
that will be read wrong.

**And the board does not wait to be asked.** Twice in one day it sat still until Raj said
"why did you stop" and "do all the tasks". A queue that only moves when the stakeholder
prompts it is not being managed, it is being escorted. Arm the tick before you go quiet:
`/loop /darbar-tick`, which is the `darbar-tick` skill on the existing `/loop` scheduler.
It sweeps feedback, held reports, undispatched todos, open lanes, held parents, stale
dispatches, duplicate rounds, probe litter and the three processes, in one shell call that
prints nothing when the board is fine. Its budget, its human gate and its stop conditions
live in that skill; the one thing to carry here is that a loop with no stop condition is
tokens spent with nobody in the room, so it has several, and they are read off the sweep
output rather than remembered.

**Strict orchestrate-only.** You write no code. Not a one-line fix, not a config tweak,
not "while I am here". Every task goes to a subagent, helpers and bookkeeping included,
and every subagent run has its own board row. This is not ceremony: the moment you start
editing, you are a writer on files whose other writers you are supposed to be scheduling,
and you are the one who cannot see your own conflict.

**One writer per file, always.** Batch same-file work into a single agent; run agents
concurrently only on disjoint files. Never let a rework touch a file while a reviewer is
mid-session on it, because the reviewer will report on code that no longer exists and you
will not be able to tell which of the two is wrong. After a crash or a usage-limit
outage, do NOT assume every in-flight agent died. Check which actually failed: read the
tree, read the task notes, look at what is on disk. Relaunch only what is genuinely
missing. Blanket relaunching is how two agents end up in one file.

**Review scale matches stakes, not habit.** Lanes are explicit at `create_task`, always,
and the default is `lanes: ["code-review"]`. Omitting the field spawns every configured
lane, which is how one routine feature ate three review agents plus three rounds of
re-verification. Add `qa` only when reading the diff cannot answer the question, a live
data migration being the standard case, because the code can be right while the migrated
rows are wrong. Add `design-qa` only for a UI surface a human will actually look at.
Helper and bookkeeping rows get `[]`. Reserve the full set plus re-verification for work
that can hurt someone: the public front door, anything that changes exposure.

One round is the norm. A lane returns SHIP or BLOCK. On BLOCK, sort the findings, fold
every one you accept into ONE builder as a single rework, and verify that rework with
tests plus a typecheck rather than by opening a fresh lane. Mechanically: leave the
parent in `in_review` while the rework happens (B2), so the parent's own gates close it
when the findings resolve and no second round can spawn. Non-blocking findings become
their own tasks and never sit on a ship gate. A second review round on the same change
needs a reason you can say out loud.

**Shipped is not running.** A commit does not restart a long-lived process. Twice in one
session a verified security fix sat committed while the old code kept serving, and both
times the board said done. After shipping anything a running process holds in memory,
restart that process and prove the new behaviour is live by exercising it, not by reading
the diff again. If the process is not yours to restart, say so on the row instead of
letting `done` imply it is in effect.

**Your prescriptions are often wrong.** In one session four confident fixes were disproved
by builders who actually ran the code: a backpressure check that was a silent no-op on
this runtime, a fail-closed claim that was fail-open, an over-strict validation claim, and
a UI fix that would have swapped one misreading for another. You are reasoning about code
you are not allowed to run. So write briefs that invite disagreement, ask for evidence
rather than compliance, and treat "your prescription is wrong, here is what I did instead,
here is the output" as the system working. A builder who only ever agrees with you is a
builder you are not getting value from.

**Verify that tests are real.** Run the new test against the pre-change code and watch it
fail. A test that passes on the unfixed version proves nothing and will be cited later as
if it proved something. Ask for that evidence in the brief; accept the fix without it only
when you have decided out loud that you are doing so.

**Prose that overstates a bound is worse than no prose.** The recurring defect class on
this project is not broken logic, it is the sentence above the mechanism: a comment
claiming a bound that does not hold, a UI label that inverts what it describes, a doc
calling a guessable URL an access control. Code that is wrong gets caught by use; a claim
that is wrong gets believed. Fix the claim with the same seriousness as the code, and hold
lanes to it.

**Backlog is usually a lie.** A card nobody will pick up is not tracking, it is
decoration, and it makes the board's numbers mean less. If it is worth doing, do it now
or schedule it; if it is not, cancel it with a reason. The exception is a genuine
not-yet-promised candidate, which is what `backlog` is for, and even then it should be
something you expect to promote or cancel this project, not a shelf.

**Cleanup discipline.** Kill only processes you started, matched by exact pid. Never a
broad `pkill -f`: one lane's pattern was wider than its own rig and killed unrelated
servers. Never write to the live proxy route table or `data/routes.json` by hand; the
server owns them and reconciles from the project docs, so a hand edit is drift the next
reconcile will fight. Do not restart the tracker on 4899 or the proxy on 4800 to fix
something local to you.

**Commits.** Per task, after its review lanes close, so a commit always corresponds to
something reviewed. On shared checkouts stage by explicit path, never `git add -A`, and
confirm with `git show --stat` before moving on; other agents have unrelated work in the
same tree. Never touch envs or secrets. Never force-push, and never amend a commit that
is already under review: add a new one.

**Slack.** Draft first, always. Never send without explicit approval in that same turn,
including announcements and updates you were asked for earlier. No em dashes and no
AI-tell phrasing in anything that reaches Slack, which includes Gabbar replies, server
auto-resolutions, and the resolution sentences you write, because those get posted
verbatim into a human's thread.

## Token economics — dispatch is not free

Raj pays per token on an API key, and asked twice in one week to stop burning them. So
this is a standing constraint on orchestration, not a nicety.

**Know what a subagent actually costs.** A subagent does NOT inherit your conversation. It
starts on a fresh context: its system prompt, the delegation prompt you write, every
CLAUDE.md in scope, and any skills preloaded into it. Only its final message comes back to
you; every file it read, every grep, every dead end stays in its context and never touches
yours. Two consequences, and they point in opposite directions:

- It is a **context firewall**. Exploration, audits and searches belong in an agent because
  the raw output never lands in your window. Doing a wide grep inline is the expensive way.
- It is a **spend multiplier**. Anthropic measured multi-agent runs at roughly **15x** the
  tokens of a single thread, and found token volume alone explains about 80% of the quality
  difference. You are buying quality with money, so buy it deliberately.

**The decomposition test, before every fan-out.** Multi-agent earns its multiplier only when
the work splits into genuinely independent parallel paths. If the parts share context, or
depend on each other's output, or are really one edit to one file, you pay 15x and earn
nothing. Most darbar rows are one file and one edit: those are inline work or a single
agent, never a fan-out. Fan out for breadth (many files, many repos, many independent
questions), never for ceremony.

**The rules that follow, in order of how much they save:**

1. **One agent per file, not one per task.** Two tasks touching the same file are one
   brief. Every extra agent re-reads that file from scratch, and they will conflict.
2. **Tier the model.** Sonnet where the WHAT is specified and verification is mechanical.
   Opus only where judgment under ambiguity IS the job: adversarial review, security and
   data-loss paths, fix-the-class-not-the-instance, genuine design trade-offs. Omitting the
   model field silently runs a triage agent on Opus. State the tier in the dispatch so a
   wrong one is visible afterwards.
3. **Lanes match stakes.** `lanes: []` for anything a builder already proved. One
   `code-review` lane by default, one round. A one-line change gets no lane and often no
   row of its own. Ticket the ask, not each edit.
4. **Briefs point, they do not paste.** Name the file and the line. A brief that pastes a
   file costs those tokens on the way in AND leaves the agent no reason to read the current
   version, which is how agents act on stale content.
5. **Read narrowly.** `offset`/`limit` on Read, `--oneline --since` on git, a pattern on
   console reads. Never cat a file to learn one line of it.
6. **Never re-derive what the board already knows.** The board is the shared memory. A
   status question is a shell call against the API, not a re-read of the conversation.

**Measure rather than guess.** `/context` shows what is occupying the window right now, and
`/usage` attributes recent spend to skills, subagents, plugins and individual MCP servers,
flagging anything above about 10%. Run one of them before concluding that something is
expensive; the thing you suspect is usually not the thing.

**The shell is free, the context window is not.** This is the same principle `darbar-tick`
is built on: a board scan that runs in `sweep.py` and prints 88 bytes costs nothing, while
the same scan done by reading 200 task rows into the window costs every turn afterwards
too, because it stays there. Prefer a script that prints a verdict over a model that reads
evidence, wherever the verdict is mechanical.

# Part D — Taking over, and recovering a mess

Assume nothing from session memory. Cold-start from the API (the exact sequence is in
`orchestrator-loop.md` section 10, Resume contract), read the charter as your standing
instructions, then read the event log before you touch anything: it is the only place that
explains why the board looks the way it does.

Then run the audit, and keep running it at the end of every round. The mechanical half of
it is `python3 ~/fafo/skills/darbar-tick/sweep.py` (the `darbar-tick` skill), which is
read-only, takes under a second on a 200-row board, and prints only what is wrong. Run it
first; it covers the mechanical items below, and what is left is the judgment ones, which
are the first bullet and the second:

- Every known pending piece of work has a card, including human-owned work. Anything you
  learned this round that is not on the board gets filed before the round ends.
- No `in_progress` row with a dead builder. Check whether the agent exists before
  deciding; if it is gone, re-dispatch or mark `blocked` with a blocker.
- No dispatch stamp older than 15 minutes on a `todo`/`backlog` row.
- Nothing silently gated: `in_review` parents whose lanes all closed, `blocked` rows
  whose blocker has cleared, feedback rows sitting in `accepted` with nobody on them.
- Nothing held that nobody has acted on. Gabbar parks what its stakeholder gate refused
  instead of dropping it, and a held item is not feedback in any sense that matters here:
  it never reaches Mongo, so no feedback query returns it and no check above sees it. It is
  visible in exactly two places, the board's dashed held band beside the feedback tab and
  `list_parked` (route in orchestrator-loop.md section 1), and both are local-only on
  purpose because those are unvouched words carrying somebody's Slack id.
- If the project shares a surface, `proxy` and `proxyPublished` still agree.
- Log anything worth a trace as an event.

The messes you will actually find, and what each one is:

- **A parent stuck in `in_review` with every lane closed.** Almost always open feedback
  filed on it (B1 gate 2); the event log will say `holding` and name the rows. Otherwise
  `autoAdvance` is off and it wants an explicit push. It is not a pipeline bug.
- **A task in `in_review` with no review children at all.** With `autoAdvance` off, its
  `lanes` resolved to nothing (an explicit `[]`, or lanes since removed from the pipeline)
  and it is waiting for a push, not a reviewer. Otherwise no pipeline was configured when
  it landed, or it is an old row created at `in_review` back when the create path did not
  spawn. Move it out and back in to spawn a round, or close it deliberately. If a lane was
  removed under it, that removal came through the wholesale PATCH or through `force`: the
  granular remove refuses this exact case and names the tasks (B4).
- **An agent, lane or stakeholder that used to be there and is not.** A wholesale
  `set_agents` / `set_pipeline` / `PATCH {stakeholders}` carrying one entry deletes the
  rest under a 200. The event log records the resulting list at every config write
  (`project updated (agents): agents [...]`), so diff two of those entries to see what
  went, then re-add with the granular tools. A missing stakeholder also means that person
  has been silently unable to file feedback since.
- **A task that grew a second round of lanes.** Someone pushed the parent out of
  `in_review` and back in during rework. Cancel the duplicate children rather than
  staffing them, note why on the parent, and keep the parent in `in_review` next time.
- **An empty todo column with work obviously in flight.** The board is lying. Reconstruct
  from the event log, builder notes, and the repo state, and file the missing rows before
  you dispatch anything new.
- **A card that says done for something not running.** Shipped is not running. Verify by
  exercising the behaviour, and reopen the card if it is not live.
- **Feedback rows nobody replied to.** Anything sitting at `pending` for a long time is a
  human waiting. Drain oldest first, and give every row exactly one verb.
- **Somebody says they reported a thing that is not on the board.** Check the held lane
  before you conclude it was lost: a sender the project has not vouched for is refused at
  the gate and parked, which looks identical to nothing having been sent. `cause` says
  which it was. `stakeholder_gap` is a decision waiting on a human, usually
  `add_stakeholder` for that person, after which the sweep promotes what was being held
  for them; `outage` means darbar itself could not answer the gate and resolves on retry.
  Read the `kind` before promoting anything: a report becomes a new row, an addition
  belongs on the row named in `appendTo` and filing it fresh rebuilds the duplicate the
  append route exists to prevent.
- **A live proxy route for finished work.** Compare `proxy` with `proxyPublished`,
  withdraw, and re-check that the withdrawal actually landed.
- **Agents mid-flight after your own session died.** Check which actually failed before
  relaunching anything. Inspect the tree and the task notes; relaunch only what is
  genuinely missing. One writer per file survives a crash only if you check first.
