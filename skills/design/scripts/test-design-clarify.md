# test-design-clarify.sh

Offline harness for `design-clarify.sh`.

## Coverage

- Fetch happy path writes `clarify-request.md` and emits durable handoff paths.
- Publish happy path writes the plan, publishes logs, posts the response,
  removes the label, and renames with `--state designing`.
- Plan-write failure stops before publish, response post, label removal, and
  rename.
- Non-zero publish forces `PUBLISH_OK=false`, appends a warning, and still posts
  the response plus removes the label.
- Empty `SESSION_ID` skips publish and rename while preserving response and
  label cleanup.

## Invocation

```bash
bash skills/design/scripts/test-design-clarify.sh
```

Wired through `make test-design-clarify`.
