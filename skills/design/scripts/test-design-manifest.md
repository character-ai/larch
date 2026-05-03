`skills/design/scripts/test-design-manifest.sh` is the offline regression harness for the `/design` to `/implement` manifest handoff. It covers writer atomic output, missing required artifacts, safe KV grammar parsing, source/eval injection resistance, path traversal, symlink rejection, control-character rejection, malformed-key rejection, and the reader's end-to-end success path. It is wired into `make lint` via the `test-design-manifest` target.

When editing `write-design-manifest.sh` or `read-design-manifest.sh`, update this harness and the sibling script contracts in the same change.
