---
name: houston-project-init
description: Day-zero bootstrap for a Houston-tracked project. Interviews for context, registers the project + charter in Houston, cuts branches, seeds the task tree via recon subagents, binds the Slack channel for Gabbar intake, then turns the current session into the project's orchestrator. Use when starting a new agent-orchestrated project ("init project", "new houston project", "spin up a project").
---

# Houston Project Init

You are bootstrapping a new project into Houston (the self-hosted tracker at
`~/fafo/houston`, API on `http://localhost:4899`) and becoming its orchestrator.

## Preconditions

1. Houston server must be up: `curl -s localhost:4899/` returns text. If not:
   `cd ~/fafo/houston && bun run server > data/server.log 2>&1 &`
2. Gabbar scribe should be up for Slack intake: check with
   `pgrep -f src/bot.ts`; start with `cd ~/fafo/houston && bun run gabbar > data/gabbar.log 2>&1 &`
3. Register the Houston MCP tools if not already in this session (see houston README
   "MCP registration"). All board writes go through them or the REST API.

## Step 1 — Intake (one structured pass)

Ask the user in ONE AskUserQuestion round (plus free-text follow-ups only if
genuinely blocking):

- **Project name** and **short-id prefix** (2 to 6 caps, e.g. MRF, VAR)
- **Repos + base branches** (e.g. saturn-fe from main, mars from stage) and the
  **feature branch name** to cut
- **Sources**: Slack threads, Figma channels, docs, prior session ids
- **Stakeholders**: name, Slack handle, role (design / backend / review). These become
  the identity map Gabbar uses to attribute feedback and the humans tasks can be
  assigned to
- **Project-specific safety rules** (live keys, fixtures not to touch, deploy holds)
- **Slack channel** to bind for feedback intake (optional; DMs always work)

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
- the project-specific safety rules from intake
- links to all sources

Save the returned `boardUrl` and `capId` — the capability URL is what stakeholders get.

## Step 3 — Cut branches

For each repo from intake: fetch, branch from the stated base, push only if the user's
standing rules allow pushes. Confirm each with `git -C <repo> branch --show-current`.

## Step 4 — Recon and seed the task tree

Spawn recon subagents in parallel (Agent tool), one per source: Slack thread digest,
Figma inventory, codebase state, prior session transcripts. Each returns a structured
list of work items with evidence.

Promote their output into Houston: `create_task` per item (streams as parent tasks,
concrete items as subtasks via `parentTaskRef`), origins recorded, known blockers set.
Log a `project bootstrapped` event.

## Step 5 — Announce in Slack

If a channel was bound: draft the announcement as Gabbar (board link + "file feedback
by DMing me or mentioning me with a task id like `PREFIX-12`"). **Show the draft and
wait for explicit approval before sending** (standing Slack rule).

## Step 6 — Become the orchestrator

Adopt the manager loop for the rest of the session (and say so):
- drain `next_pending_feedback` on a self-paced loop; triage every item: rework an
  existing task, `create_task` a new one, reject with a reason, or ask for
  clarification (all via `resolve_feedback`, which auto-replies in the author's thread)
- dedupe at triage: same defect from two authors = one task, both notified
- dispatch builders one scoped task each; they update their own rows via MCP
- never write code yourself; keep the board the single source of truth — a fresh
  session must be able to resume from the API alone

Finish the bootstrap by reporting: board URL, task count seeded, branches cut,
stakeholders onboarded, and anything from recon that needs the user's call.
