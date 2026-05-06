# scripts/gemini-known-tools.txt — contract

`scripts/gemini-known-tools.txt` is the committed Gemini CLI tool-catalog snapshot consumed by `scripts/lib-gemini-tool-drift.sh` during `scripts/check-reviewers.sh --probe --include-gemini`. It is a known-catalog fixture, not an allowlist: write-style tools must still be present in `scripts/gemini-reviewer-policy.toml` or Gemini is marked unhealthy.

Format invariant: `#`-prefixed header lines appear before the first data line, then one lowercase tool name per line, sorted, with no blank data lines. The `# checksum:` value is the sha256 of the body after excluding all `#` header lines:

```bash
grep -v '^#' scripts/gemini-known-tools.txt | shasum -a 256
```

Refresh this file when `gemini-cli` is upgraded or when adding a tool to `scripts/gemini-reviewer-policy.toml`; update the `Refreshed:` header and recompute the checksum in the same change.
