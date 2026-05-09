---
paths:
  - "scripts/**"
  - "skills/**"
  - ".github/workflows/**"
---

# Verify External Tool Invocations

When any PR adds or modifies an invocation of an external CLI binary (cursor, codex, claude, gitleaks, actionlint, agent-lint, npm, npx, security, gh, etc.):

1. **Run the exact command** with the exact arguments as they appear in the code, on the development machine, before committing.
2. **Verify the exit code and output** are consistent with the expected behavior (success, expected flags recognized, no "unknown option" or "not available" errors).
3. If the invocation targets a platform-specific feature (sandbox, keychain, OS-level API), **document the platform requirement** in a comment adjacent to the call.
4. If the binary is not available locally for testing, **note this explicitly** in the PR description and request manual CI verification before merge.

This rule exists because flag-unavailability failures (e.g. `--sandbox enabled` on hosts without sandbox support, `--prompt` vs `--print` on different CLI versions) produce silent reviewer failures rather than visible errors, making them disproportionately expensive to diagnose.
