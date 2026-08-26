# skills

Personal Claude Code skills, installable via [skills.sh](https://skills.sh):

```
npx skills add RajVarsani/skills            # pick skills interactively
npx skills add RajVarsani/skills -s gabbar  # one skill
```

| skill | what it does |
|---|---|
| `gabbar` | Send Slack messages as Gabbar Singh, Raj's bot (draft-first, never auto-send) |
| `darbar-project-init` | Day-zero bootstrap for a Darbar-tracked project: charter, branches, recon-seeded task tree, Slack binding, orchestrator mode |
| `darbar-tick` | One maintenance pass over a Darbar board, armed on a timer with `/loop` so the queue keeps draining. Clean pass is one line |
| `darbar-handoff` | Run BEFORE `/compact`: files everything that exists only in the conversation onto the board, then writes the snapshot the SessionStart hook prints back |
| `darbar-resume` | Run AFTER a compaction, `/clear` or `--resume`: re-reads state from the API and re-loads the doctrine, because state survives compaction and doctrine does not |

`darbar-project-init` is the authority the other three point at; none of them restate its
rules, so a doctrine change lands in one file.

Skills reference tokens from env vars only; no secrets live in this repo.
Darbar itself (tracker app: API, board, Gabbar bot, MCP tools): `RajVarsani/darbar`.
