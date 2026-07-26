# Prompt Specs

Numbered prompt/spec files for agents built on top of IronWatch's Gold
layer (e.g. natural-language query agents). Convention:

```
NN-short-slug.md
```

Lower numbers are earlier in the build sequence; a prompt file documents
what the agent is instructed to do, its guardrails, and any approval gate
it must pass before acting.

## Status

**Empty as of 2026-07-26.** No numbered prompt files exist yet anywhere in
this repo. In particular, "Prompt 9" / an "IronWatchQueryAgent" plan-approve
gate was referenced as an existing convention but could not be found in any
doc, ADR, backlog item, or `.claude/` config — confirmed by repo-wide
search. It is **reserved, not defined**: when that spec is written, it
belongs here as e.g. `09-ironwatch-query-agent-gate.md`, and `AGENTS.md`
should be updated to link to it instead of flagging the gap.
