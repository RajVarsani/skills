# skills

Personal Claude Code skills, installable via [skills.sh](https://skills.sh):

```
npx skills add RajVarsani/skills            # pick skills interactively
npx skills add RajVarsani/skills -s gabbar  # one skill
```

| skill | what it does |
|---|---|
| `gabbar` | Send Slack messages as Gabbar Singh, Raj's bot (draft-first, never auto-send) |
| `houston-project-init` | Day-zero bootstrap for a Houston-tracked project: charter, branches, recon-seeded task tree, Slack binding, orchestrator mode |

Skills reference tokens from env vars only; no secrets live in this repo.
Houston itself (tracker app: API, board, Gabbar bot, MCP tools): `RajVarsani/houston`.
