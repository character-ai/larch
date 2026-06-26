# /implement Step 18a.5 escalation-success filing

**Consumer**: /implement Step 18a.5 after eligibility passes.
**Contract**: Owns the eligible-path escalation-success artifact reads, root-cause artifact writes, Tier A/B filing, and sentinel write.
**When to load**: **MANDATORY — READ ENTIRE FILE** only after Step 18a.5 skip predicates are false and escalation evidence exists.

If eligible, Main Claude reads validated failure detail, `ship-pr-state.sh`, `finalize-state.sh`, `session-env.sh`, attempts, classification, ledger, fallback evidence, record-failure marker, execution issues, run-log pointer when present, and prompt-state values it used. It writes root-cause artifacts for why the script loop needed Main Claude. Then it writes the prompt-state sensitive supplement immediately before `compose-report --report-kind escalation-success`.

Tier A files through `/larch:issue --input-file ... --no-dedup` after full-output secret redaction and exact-signature dedup. Tier B files or comments upstream after composing `stall-recovery-chat-print.md`. Write `stall-recovery-escalation-success.env` atomically after filed, commented, fallback-printed, dry-run, or operator-action skip result.
