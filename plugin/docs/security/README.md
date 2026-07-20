# Security Reference Index

This index owns larch's security document taxonomy and ownership map. It does
not duplicate behavioral guarantees. The root [`SECURITY.md`](../../SECURITY.md)
owns the public policy, supported versions, responsible disclosure, scope, and
high-level trust statement.

## Ownership Rules

- Give each security guarantee one canonical document.
- Link to the canonical document instead of copying its normative text.
- Keep a compatibility pointer under an old root heading until its callers use
  the focused reference.
- Keep disclosure and security-sensitive triage instructions useful without
  opening a secondary link.
- Record implementation owners and migration status. Do not treat a planned
  document as authoritative before its extraction lands.

## Document Taxonomy

| Area | Canonical owner now | Focused owner | Status |
|------|---------------------|---------------|--------|
| Public policy, supported versions, disclosure, scope, and high-level trust | [`SECURITY.md`](../../SECURITY.md) | Root policy | Current |
| Release provenance, bootstrap, dependencies, credentials, and external service boundaries | [`docs/security/supply-chain-credentials-and-services.md`](supply-chain-credentials-and-services.md) | Focused reference | Current; root headings are compatibility pointers |
| Workflow trust, untrusted input, agent access, authorization, and mutation controls | Named sections in [`SECURITY.md`](../../SECURITY.md) | `docs/security/workflow-trust-and-mutations.md` | Planned in #7855; root sections remain canonical |
| Temporary and committed artifacts, redaction, retention, and public publication | Named sections in [`SECURITY.md`](../../SECURITY.md) | `docs/security/artifacts-redaction-and-publication.md` | Planned in #7856; root sections remain canonical |

The final reference cleanup in #7857 will remove obsolete detail only after all
live callers point to the correct canonical owner. Root compatibility headings
remain until that cleanup.

## Runtime Packaging Contract

The runtime-only `plugin/` projection must contain the root `SECURITY.md`, this
index, and every tracked Markdown file under `docs/security/`. Projection
generation also scans shipped skill Markdown for `docs/security/*.md`
references and fails if a target is absent. The same validation runs when CI
generates the projection and checks it for byte-for-byte drift.

The projection also includes `ARCHITECTURE.md` and the Git, GitHub, and Google
service inventories linked by the focused supply-chain reference. Those links
therefore resolve in both a source checkout and an installed plugin.

`crates/larch-cli/src/release_plugin_runtime.rs` is the single implementation
owner. The old Python projection command is retired, and no Bash projection
implementation remains.

## Live Reference Audit

Use these stable entry points when editing security references. Do not rely on
a fixed repository-wide count.

| Concern | Live entry points | Required destination |
|---------|-------------------|----------------------|
| Vulnerability disclosure | `skills/bug/SKILL.md`, `skills/triage/SKILL.md` | Root `SECURITY.md`; keep the no-public-issue instruction inline |
| Installation and runtime loading | `docs/installation-and-setup.md`, `.claude-plugin/marketplace.json`, `crates/larch-cli/src/release_plugin_runtime.rs` | Root policy and all focused references ship in `plugin/` |
| Runtime security decisions | Shipped Markdown under `skills/` | Root policy or an existing focused reference in the installed plugin |
| Contributor policy | `AGENTS.md`, `docs/preparing-your-repo.md` | Root policy for behavior; this index for taxonomy and ownership |

When a focused document becomes authoritative, audit the relevant entry points
and preserve self-contained safety instructions at public-disclosure and
security-sensitive triage boundaries.
