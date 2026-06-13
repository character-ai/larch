## Decision 1: Request comment body fetch mechanism
- **Question**: Add a new Python CLI verb to fetch the clarify-request comment body, or use inline gh/jq in the Bash wrapper?
- **Resolution**: Add a new Python CLI verb (e.g., `clarify comment-fetch`) to `python/cli.py` that reuses the existing comment-list logic and writes the request comment body to a file.
- **Source**: user

## Decision 2: Response file path convention
- **Question**: Should `--phase publish` accept a `--response-file` flag or use a fixed `$DESIGN_TMPDIR/clarify-response.md` path?
- **Resolution**: Fixed convention — LLM writes to `$DESIGN_TMPDIR/clarify-response.md`; `--phase publish` reads from that path without a flag.
- **Source**: user
