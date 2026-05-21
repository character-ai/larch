# clarify-comment-post.sh contract

## Purpose

Posts a single issue comment whose body starts with `<!-- larch:clarify-request id=<N> -->` or `<!-- larch:clarify-response id=<N> -->`, followed by the contents of `--content-file`. Body is redacted through `scripts/redact-secrets.sh` before `gh issue comment --body-file`.

## Interface

```
clarify-comment-post.sh --issue <N> --kind request|response --id <N> \
  --content-file <path> [--repo OWNER/REPO]
```

`id` must be a positive integer (`>= 1`).

## Output Contract

- Success: `POSTED=true`, `COMMENT_ID=`, `COMMENT_URL=`, `MARKER=<exact marker line>`, exit 0.
- Invalid `--kind` / `--id`: `FAILED=true`, `ERROR=invalid-kind` or `ERROR=invalid-id`, exit 1.
- `gh` / redaction failure: `FAILED=true`, `ERROR=…`, exit 2.

## Test Harness

```
bash scripts/test-clarify-comment.sh
```

`make test-clarify-comment` (shard `test-harnesses-16`).

## Edit-in-sync

Update `scripts/test-clarify-comment.sh` and this file when the stdout contract changes.
