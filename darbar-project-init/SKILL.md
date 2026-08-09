---
name: darbar-project-init
description: Bootstrap a Darbar-tracked project — day-zero OR retro-init of work already underway ("put this session under darbar", "register this project"). Interviews for context (mandatory, includes subagent structure + backlog scope + update cadence), registers the project + charter in Darbar, cuts branches, seeds the task tree so the board carries ALL known pending work, binds the Slack channel for Gabbar intake, then turns the current session into a strict orchestrate-only manager. Use when starting a new agent-orchestrated project ("init project", "new darbar project", "spin up a project") or when bringing an in-flight session/effort under Darbar tracking.
---

# Darbar Project Init

You are bootstrapping a project into Darbar (the self-hosted tracker at
`~/fafo/darbar`, API on `http://localhost:4899`) and becoming its orchestrator.

## Preconditions

1. Darbar server must be up: `curl -s localhost:4899/` returns text. If not:
   `cd ~/fafo/darbar && bun run server > data/server.log 2>&1 &`
2. Gabbar scribe should be up for Slack intake: check with
   `pgrep -f src/bot.ts`; start with `cd ~/fafo/darbar && bun run gabbar > data/gabbar.log 2>&1 &`
3. Register the Darbar MCP tools if not already in this session (see darbar README
   "MCP registration"). All board writes go through them or the REST API.

## Step 1 — Intake (MANDATORY — never skip)

The interview is not optional. Do NOT infer answers from context you already have,
and do NOT start building before it — a skipped interview is the documented failure
mode of this skill. Ask the user in ONE AskUserQuestion round (free-text follow-ups
only if genuinely blocking):

- **Project name** and **short-id prefix** (2 to 6 caps, e.g. MRF, VAR)
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
  every task runs it; each task picks its own lanes (Step 6)
- **Helper subagents**: which non-lane helpers this project needs (deploy, seeding,
  migrations, release notes, data pulls) — or explicitly none. Ask for each in registry
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

POST `http://localhost:4899/api/projects` with name, prefix, repos, stakeholders
(`[{name, slackUserId, role}]` — resolve handles to user ids via Slack API if needed),
`slackChannel`, and a **charter**.

The charter is the standing context pack every agent fetches via the
`get_project_context` MCP tool. Write into it:
- goal + streams of work
- the standing protocols (defaults, adapt as needed): orchestrate-only (builders do the
  work, orchestrator writes no code), builders verify build-only (tsc / go build),
  commit discipline on shared checkouts (stage by explicit path, no `git add -A`,
  `--no-verify`, confirm with `git show --stat`), concurrency cap 3 to 4 agents,
  design QA reads live design-tool values not memory, QA asserts outcomes against DB
  truth not UI interactions
- the project-specific safety rules and update cadence from intake
- links to all sources

Save the returned `boardUrl` and `capId` — the capability URL is what stakeholders get.

Then configure the **review pipeline** from the intake's subagent-structure answer
(`set_pipeline` MCP tool, or PATCH `/api/projects/:ref` with
`{pipeline: {autoAdvance, reviews: [{lane, label, manager}]}}`): one lane per review
kind, each with a `manager` agent name. The server then auto-spawns one `type=review`
subtask per lane the task itself selected whenever a dev task moves to `in_review`, gates
`done` on the lanes closing, and (with `autoAdvance`, the default) closes the parent when the last
lane does. Skip the pipeline only if intake explicitly chose "none".

The pipeline is the menu, not the plan. Configuring qa and design-qa here does not mean
tasks should run them — every task states its own `lanes` at `create_task`, and the
normal answer is one lane. Write that expectation into the charter so a fresh session
inherits it (the wording in Step 6 is the version to copy).

Next, register the **agent registry** (`set_agents` MCP tool, or PATCH
`/api/projects/:ref` with `{agents: [{name, kind, brief, trigger?}]}`). One entry per
agent this project will ever dispatch:

- every lane manager from the pipeline answer — `kind: "lane-manager"`
- `orchestrator` itself — `kind: "orchestrator"`
- every helper from intake — `kind: "helper"`

`brief` IS that agent's standing charter: write it as the prompt you would hand the
subagent — what it decides, what it does, what it must never touch. `trigger` (optional)
is the when-to-dispatch hint, e.g. "after a task's review lanes close". `set_agents`
replaces the whole list, so always send the complete registry. Names must be unique —
the name is the assignee key (`assignee`, `my_tasks`). Pipeline managers should exist in
the registry: the server logs a `pipeline manager X not in agent registry` warning event
otherwise (warn-only, the write still succeeds). Every agent then reads the registry
alongside the charter via `get_project_context` (GET `/api/projects/:ref/context`), and
it is served in the board payload too (GET `/api/p/:capId`).

### Register the shared surface, if intake asked for one

Only if the shared-surface answer was yes. `set_proxy` (or PATCH `/api/projects/:ref`
with `{proxy: {prefix, target, public, enabled}}`) publishes one local dev server at
`<baseUrl>/<prefix>/`, the same public origin the board link uses. The config is
replaced wholesale on every call, and the server pushes it into the proxy route table
and re-reconciles at every change and at boot, so a push that failed while the proxy was
down gets repaired rather than left as drift.

Configure it with the safety properties in front of you, because this route has no login:

- **Default is `enabled:false`.** Configure the route, read back what it exposes, then
  flip `enabled:true` in a second call. Do not share and then narrow.
- **Anyone who reaches the route reaches the target.** There is no auth in front of it and
  no per-stakeholder access. The URL is not the access control: the board link carries a
  21-char random `capId`, so it is genuinely unguessable, but the proxy prefix is a short
  word a human chose, so `BASE_URL/<prefix>/` is guessable by anyone who knows the domain.
  The `public` patterns are the boundary; the prefix is not a credential.
- **The prefix is the URL segment and the routing key.** It must be a non-empty string of
  `[A-Za-z0-9_-]` — anything else is rejected 400 — and `p`, `api`, `files` and `-` are
  reserved, because they are the server's own paths and a prefix there would shadow the
  board itself.
- **The `public` patterns ARE the boundary**, and they are not regexes. Each entry is a
  literal path starting with `/`, matching as a prefix by default (`/assets/`), with a
  trailing `$` for an exact path (`/$` is the root and nothing else) and at most one `*`
  matching inside a single path segment (`/assets/*.js$`). Regex characters (`^`, `(`,
  `[`, `+`, `\`, `.*`) are rejected 400 with the form spelled out. Patterns match the path
  AFTER the prefix is stripped: for a project at prefix `dar`, the public request
  `/dar/assets/app.js` is matched as `/assets/app.js`, so write `/assets/` and never
  `/dar/assets/` — the prefixed form matches nothing and the route serves nothing. Omit
  `public` and nothing is reachable from outside; `["/"]` exposes every path. Local
  requests are never filtered, so "it works on my machine" tells you nothing about what a
  link-holder sees. Check by fetching the public URL.
- **The target must be a dev server on this machine**, and the path is part of it. A Vite
  app served at base `/fe` needs `http://127.0.0.1:5173/fe`; without the path Vite gets
  `/` and 302s to `/fe/` forever through the prefix strip. Vite's `base` has to match the
  prefix. The host must be a literal loopback address, or the one name that is special-cased:
  `localhost`, any `127.x.x.x`, `0.0.0.0`, `::1`, `::` and the IPv4-mapped spellings of those
  are accepted. Public addresses, LAN and private ranges, link-local (`169.254/16`,
  `fc00::/7`, `fe80::/10`) and every other DNS name are rejected 400 — a literal address
  cannot leave this host, while a name is resolved at request time by a resolver we do not
  control.
- **Tunneled requests carrying `%2f` or `%5c` are refused outright** (403), because the
  proxy forwards the path verbatim and dev servers decode before resolving `..`, so an
  encoded slash would walk out of an allowed prefix upstream. A legitimately encoded slash
  is refused too. Do not build a shared surface that needs one.
- **The target is never on the public board.** GET `/api/p/:capId` reports the prefix,
  the patterns and `targetRedacted: true`; the real host:port is only on
  `get_project_context`, which is local-only. Keep it that way in anything you write.
- **Teardown is yours.** When the project closes, withdraw the route: `set_proxy` with
  `enabled:false` keeps the config and takes the URL down, and PATCH
  `/api/projects/:ref` with `{"proxy": null}` clears it entirely. A finished project
  leaving a live route is a leak with nobody watching it.

Tell the user the shared URL explicitly, alongside the board URL, and say who it is for.

## Retro-init — project already underway

When work exists but was never registered, or the orchestrator has been working
inline ("put this session under darbar"):

1. Run the SAME Step 1 intake — no shortcuts; the interview is mandatory here too.
2. Register the project (Step 2), or PATCH `/api/projects/:ref` if it half-exists.
3. Seed EVERY known pending item as a task — from the session so far, from memory
   files, from the user's answers — including human tasks assigned to stakeholders
   (e.g. "Tanisha: fix file_type hardcode"). Record origins.
4. Record already-done work as done cards so the board tells the true story of the
   project, not just the future.
5. Invariant from here on: **the board reflects ALL known pending work at all
   times.** An empty todo column while work is pending is a bug — fix the board,
   then continue.

Then proceed with Steps 3–6 as applicable (branches may already exist; skip cutting,
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
and `lanes` stated on every row (`["code-review"]` unless the rules in Step 6 say
otherwise; parent stream rows that carry no diff get `[]`). Cover every stream from the
intake's backlog-scope answer; anything pending that you know about but don't file is a
bug. Log a `project bootstrapped` event.

## Step 5 — Announce in Slack

If a channel was bound: draft the announcement as Gabbar (board link + "file feedback
by DMing me or mentioning me with a task id like `PREFIX-12`"). If a shared surface was
published, put its URL next to the board link and say what it is, so nobody has to ask
where to look. **Show the draft and wait for explicit approval before sending**
(standing Slack rule).

## Step 6 — Become the orchestrator (strict orchestrate-only)

Adopt the manager loop for the rest of the session (and say so). Default is strict
orchestrate-only — the orchestrator writes NO code, ever; relax only if the user
explicitly says so:

- **Dispatch**: one builder subagent per task via the Agent tool, each scoped to
  exactly one task. Builders PATCH their own rows via REST
  (`PATCH /api/tasks/:shortId` — `in_progress` on start, `in_review` with notes when
  done, `blocked` with blocker if stuck). When the agent is in the registry, its
  `brief` is the prompt — hand it the brief plus that task's context, nothing invented.
- **Helpers**: dispatched exactly like builders. Every helper run gets its own task row
  on the board; the subagent prompt is the helper's registry `brief` plus the task
  context, and the helper PATCHes its own row (`in_progress` → `in_review`/`done`) so
  its work is as visible as anyone else's. Create that row with `lanes: []`
  (`create_task` / `POST /api/tasks` with `"lanes": []`) — that is what makes
  `in_review` → `done` self-closing; omit `lanes` and the `in_review` PATCH spawns the
  full pipeline (code-review/qa/design-qa on a deploy) and the row cannot close until
  those lanes do. `trigger` is a hint, not a rule — you decide
  when to fire (e.g. deploy-devx after a task's lanes close, and only if the change is
  worth a deploy).
- **Reviews**: the server auto-spawns review-lane subtasks on `in_review`, so the lanes
  are decided when you file the task, not when it lands. **Always state `lanes`
  explicitly at `create_task`.** Omitting the field spawns every configured lane, which
  is how one routine feature ate three review agents and three re-verification rounds.
  Spawn lane-manager subagents to drain their queues
  (`GET /api/tasks?assignee=<manager>&open=true`), review the work, file findings via
  `POST /api/feedback` (authorType `agent`), and close their lanes. The done-gate +
  `autoAdvance` handle parents. Picking the lanes:
  - Default is `lanes: ["code-review"]`. One lane is the normal answer for ordinary work.
  - Add `qa` only when reading the diff cannot answer the question: a live data
    migration is the standard case, because the code can look right while the migrated
    rows are wrong.
  - Add `design-qa` only for a UI surface a human will actually look at.
  - Helper and bookkeeping rows get `lanes: []`, which makes `in_review` self-closing.
  - The full set plus re-verification is for work that can hurt someone: the public
    front door, anything that changes exposure. Reserve it for that, not for habit.
  - Unknown lane keys 400, and the selection freezes once the review flow starts, so a
    lane you skipped is a decision you keep.
- **One review round is the norm.** A lane comes back SHIP or BLOCK. On BLOCK, fold
  every finding you accept into ONE builder, and verify that rework with tests plus a
  typecheck rather than a fresh lane. Sending the same change through another review
  round needs a reason beyond wanting to be thorough. Findings that are real but not
  blocking go on a polish backlog as their own tasks; they never sit on a ship gate.
- **Feedback**: drain `next_pending_feedback` on a self-paced loop; triage every item:
  rework an existing task, `create_task` a new one, reject with a reason, or ask for
  clarification (all via `resolve_feedback`, which auto-replies in the author's
  thread). Dedupe at triage: same defect from two authors = one task, both notified.
- **Commits**: orchestrator commits per task only after its review lanes close,
  following the charter's commit discipline.
- **Board honesty**: the board is the single source of truth and must reflect ALL
  known pending work at all times — file new work the moment you learn of it,
  including human tasks. A fresh session must be able to resume from the API alone.
- **Updates**: follow the cadence chosen at intake; Slack updates always draft-first
  via Gabbar.
- **Shared surface**: if one is published, it is yours for the life of the project. Keep
  the `public` list as narrow as the surface actually needs, and withdraw the route when
  the project closes (`set_proxy` `enabled:false`, or `{"proxy": null}` to clear it).

Finish the bootstrap by reporting: board URL, the shared surface URL if one was
published, task count seeded, branches cut, stakeholders onboarded, and anything from
recon that needs the user's call.
