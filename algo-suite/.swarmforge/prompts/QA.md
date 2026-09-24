Read swarmforge/constitution.prompt, then read every file it refers to recursively, and obey all of those instructions.
Read swarmforge/roles/QA.prompt, then read every file it refers to recursively, and follow all of those instructions.

## Tool Startup

- Do not search `$HOME` or run `find` for APS tools.
- `gherkin-parser` (APS parsing): `swarm_tool.sh require gherkin-parser`
  If missing, run exactly: `swarm_tool.sh ensure gherkin-parser`
- Parse with the two-arg form: `gherkin-parser <feature> ./tmp/<stem>.json`
- Write scratch files and handoff drafts in `./tmp/` in the assigned worktree.
- Do not use `/tmp` or `.swarmforge/handoffs/outbox/tmp/` as scratch.
- Receive with `ready_for_next.sh`. Send with `swarm_handoff.sh ./tmp/<draft>`.
- Do not search the tree or `$HOME` for those scripts.
- Do not invoke helpers as `./swarmforge/scripts/...`. They are already on PATH.
- Board cards live in `.swarmforge/board/tasks.tsv`. Use that card name as `task:`.
- Operator task documents live in `tasks/<task-name>.md`. Re-read that file as operator intent. The master agent commits it with the task's first git work.
- A retry audit may include remedial comments on named documents. Read those comments as findings.
- Do not search the worktree for `.swarmforge/board/tasks.tsv`. That file is on the project (master).
- Use TASK_NAME from `ready_for_next.sh` or the inbound `task:` header. For a batch, that name is the top item. The helper fills `task:` from the in-process batch, else the sender-lane card.
- Do not invent a name or hunt `sessions.tsv`.
- Constitution tools: `swarm_tool.sh require crap4clj` (also dry4clj, clj-mutate, cloverage, speclj, speclj-structure-check, APS, or the language table). If missing, `swarm_tool.sh ensure <tool>`. Do not invent project `bb` proxies.
- Run constitution tools one at a time. Worker-limited tools use `--max-workers 4` or `--workers 4`. Mutation is differential: no `--mutate-all`, no `--level full`.
- Do not clone those repos into `./tmp`.
- If merge_and_process.sh or ready_for_next reports a merge conflict, resolve the conflicted files, git add, and commit. Do not invent git merge. Parallel cards on one tree will conflict; that is expected.
- Operator follow-ups arrive as `[id] text` in this pane. Answer with `pack_dashboard_request.sh answer <id> ./tmp/answer.txt`.
- Ask the operator with `pack_dashboard_request.sh clarify ./tmp/question.txt`. Do not ask in the pane.
- Do not ask for approval in the pane. Queue `git_handoff`; the operator uses Attention.
- You are the last role in this pack. After this pack step, queue a git_handoff. The helper marks the card Done. Do not list every other role on to: to finish the card.
- One commit is one git_handoff. Do not send two git_handoffs of the same SHA.
