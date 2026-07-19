# Google Service Inventory

This ledger records the production Google and `gcloud` caller inventory for
issue #7727. It separates adapter parity, consumer cutover, and Python removal
for every operation found by the scan.

## Checked scope

The inventory was checked against main commit `5ad844c03` and the issue branch.
The scan covered production Rust, Python, skills, agents, hooks, scripts, and CI
configuration. It excluded documentation, fixtures, historical run logs, and
the generated `plugin/` projection from caller classification.

The scan found no production Google API request and no production `gcloud`
process launch. Current matches are controls or setup prose:

- `crates/larch-core/src/config.rs` owns the
  `GOOGLE_APPLICATION_CREDENTIALS` environment name.
- `crates/larch-adapters/src/process.rs` removes Google credential variables
  from child environments and verifies that neither `gh` nor `gcloud` is an
  inherited executable.
- Redaction code recognizes Google API key shapes.
- Installation documentation shows operator-run ADC setup checks. Those
  commands are not larch production callers.

## Operation ledger

| Service category | Current production operations | Production callers | Adapter parity | Consumer cutover | Python removal |
| --- | --- | --- | --- | --- | --- |
| Google Cloud service APIs | None | None | Not applicable | Not applicable | Not applicable |
| `gcloud` CLI | None | None | Not applicable | Not applicable | Not applicable |

The Rust adapter now owns hardened ADC construction through
`google-cloud-auth`. It is a credential boundary, not a service operation, and
has no production consumer to cut over. No `google-cloud-*` service client or
larch-owned service trait is present because the operation inventory is empty.

Before adding a Google operation, update this ledger with its production caller,
service, exact OAuth scopes, minimum IAM permissions, larch-owned port and DTOs,
official client crate, adapter parity evidence, consumer cutover state, and
Python removal state. Add offline fake-credential and fake-transport coverage
before cutover. Keep any live test ignored by default, explicit opt-in, and
credential-free in its output.
