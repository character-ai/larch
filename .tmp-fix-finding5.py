from pathlib import Path

sec = Path("/Users/zhupanov/larch1/docs/security/workflow-trust-and-mutations.md")
stext = sec.read_text()
old = (
    "`/audit-umbrella` is a standalone, inline audit that does not implement leaves or alter "
    "umbrella or leaf lifecycle fields. Its Rust owner resolves the repository default branch, "
    "fetches a detached immutable worktree, and records a bounded GitHub source snapshot from "
    "two quoted all-state title and backlink searches. The adapter adds `is:issue`. Audit "
    "validates complete search metadata and fails closed at the search bound."
)
new = (
    "`/audit-umbrella` is a standalone, inline audit that does not implement leaves or alter "
    "umbrella or leaf lifecycle fields. Its Rust owner resolves the repository default branch, "
    "fetches a detached immutable worktree, and records a bounded GitHub source snapshot from "
    "two bounded quoted all-state GitHub searches. The adapter adds `is:issue` and scopes each "
    'query to the audited repository. The title search uses `"[LEAF OF N] " in:title state:all`. '
    'The backlink search uses `"This is a leaf of umbrella #N. Read the umbrella in full before '
    'acting." in:body state:all`. Both predicates include `state:all` so closed historical leaves '
    "remain discoverable. Audit validates complete search metadata and fails closed at the search bound."
)
if old not in stext:
    raise SystemExit("old text not found")
sec.write_text(stext.replace(old, new, 1))
