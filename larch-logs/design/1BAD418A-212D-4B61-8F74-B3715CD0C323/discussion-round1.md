## Decision 1: Canonical larch repo resolution
- **Question**: Should the upstream larch repo (`character-ai/larch`) be resolved from plugin.json `repository` field or a pinned constant?
- **Resolution**: Parse `$PLUGIN_ROOT/.claude-plugin/plugin.json`, extract the `repository` URL, strip to `OWNER/REPO`. Consistent with existing plugin metadata; handles future repo renames without code change.
- **Source**: user

## Decision 2: Tier B filing path
- **Question**: Should cross-repo filing extend `/larch:issue --repo` or use a thinner direct `gh issue create -R` path?
- **Resolution**: Direct `gh issue create -R <upstream-repo>`. Avoids `/larch:issue` dedup and dependency analysis reading the wrong (consumer) repo. The signature dedup pre-pass replaces generic dedup.
- **Source**: user

## Decision 3: Scope - /design failure reports
- **Question**: Is this issue scoped to `/implement` only, or does it include `/design` failure report porting (#3992 work)?
- **Resolution**: Both `/implement` and `/design` failure reports are in scope. The design plan covers the full three-issue arc (#3991 + #3992) implemented as one plan.
- **Source**: user

## Decision 4: Chat notification on successful cross-repo filing
- **Question**: When Tier B cross-repo filing succeeds, should the operator see the full Tier B body in chat or just a short filed notice?
- **Resolution**: Short filed notice only: `**ℹ /implement stall report filed: <github-url>**` (or "+1 comment: <url>" for dedup hits). No full chat-print body on success. Full chat-print remains the fallback when cross-repo filing fails.
- **Source**: user

## Decision 5: /design terminal failure surface
- **Question**: What events count as /design terminal failures for report filing?
- **Resolution**: Three surfaces in scope: (a) plan-block write failure (`PLAN_WRITE_OK=false`), (b) design log publish failure after multiple retries, (c) external reviewer / judge panel total collapse (all slots failed, `LOOP_STATUS=panel-failed` after cap hit).
- **Source**: user

## Decision 6: /design stall state machinery depth
- **Question**: Should the /design port include full stall-state machinery (state files, classification, attempts, ledger) or just wire existing events to the filing layer?
- **Resolution**: Full machinery mirroring /implement: add `design-failure-tracking.env`, `design-escalation-ledger.tsv`, etc. in `$DESIGN_TMPDIR`.
- **Source**: user
