BRANCH=B

Phase 1 cross-agent `@./INCLUDED.md` include test did not satisfy Branch A criteria for Claude (targeted answer was not `SCARLET-FOX-9412`; control transcript listed Claude Code environment bullets only, with no INCLUDED.md alias sentence or paraphrase). Codex `exec` on the fixture hit a rollout-recording error mid-session before a clean transcript completed. Cursor was not reached in the interrupted matrix run.

## Claude — targeted

Warning: no stdin data received in 3s, proceeding without it. If piping from a slow command, redirect stdin explicitly: < /dev/null to skip, or wait longer.

larch1

## Claude — control

(Truncated in log; no bullet contained the INCLUDED.md project-alias sentence or SCARLET-FOX-9412.)

## Codex — targeted

Codex session logged `failed to record rollout items: thread ... not found` after partial output; no reliable token-only answer captured.
