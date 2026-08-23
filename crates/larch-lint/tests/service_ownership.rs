use crate::support;

use predicates::prelude::*;
use support::TempRepo;

fn ownership_matrix(adapter: &str) -> String {
    let rows = [
        "actions",
        "attestations",
        "comments",
        "issue-dependencies",
        "issue-sub-issues",
        "issues",
        "labels",
        "pull-requests",
        "releases",
        "repository-metadata",
    ]
    .map(|operation| {
        format!("{operation}\t{adapter}\tpython\t#7661\tpending\tpending\tpending\tfixture run")
    })
    .join("\n");
    format!(
        "Owner: {adapter}\n<!-- github-service-ownership:start -->\n```text\noperation\tadapter_owner\tcurrent_owner\tplanning_issues\timplementation_parity\tconsumer_cutover\tpython_removal\tcommands\n{rows}\n```\n<!-- github-service-ownership:end -->\n"
    )
}

#[test]
fn rejects_concrete_clients_and_request_surfaces_outside_the_adapter() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-core/src/leak.rs",
        br#"use octocrab::Octocrab;
use reqwest::Client;

const ENDPOINT: &str = "https://api.github.com/repos";
const NAMED_QUERY: &str = "query GetRepo($owner:String!){repository(owner:$owner){name}}";

fn fetch() {
    let _ = google_cloud_auth::credentials::Builder::default();
    let _ = format!("https://oauth2.googleapis.com/token");
    let _ = "query($id:ID!){node(id:$id){id}}";
    let _ = make!(octocrab::Client);
}
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "crates/larch-core/src/leak.rs:1: concrete service client `octocrab` is used outside crates/larch-adapters/",
        ))
        .stdout(predicate::str::contains(
            "crates/larch-core/src/leak.rs:2: concrete service client `reqwest` is used outside crates/larch-adapters/",
        ))
        .stdout(predicate::str::contains(
            "crates/larch-core/src/leak.rs:4: service request host `api.github.com` appears outside crates/larch-adapters/",
        ))
        .stdout(predicate::str::contains(
            "crates/larch-core/src/leak.rs:5: GraphQL document appears outside crates/larch-adapters",
        ))
        .stdout(predicate::str::contains(
            "crates/larch-core/src/leak.rs:8: concrete service client `google-cloud-auth` is used outside crates/larch-adapters/",
        ))
        .stdout(predicate::str::contains(
            "crates/larch-core/src/leak.rs:9: service request host `googleapis.com` appears outside crates/larch-adapters/",
        ))
        .stdout(predicate::str::contains(
            "crates/larch-core/src/leak.rs:11: concrete service client `octocrab` is used outside crates/larch-adapters/",
        ))
        .stderr("");
}

#[test]
fn finds_nested_client_imports_and_macro_request_surfaces() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-core/src/nested.rs",
        br#"use {octocrab, reqwest as Http};
use hyper::*;

macro_rules! audit_request {
    () => {
        tracing::debug!(endpoint = "https://api.github.com/repos", client = octocrab::Octocrab);
    };
}

fn request() {
    audit_request!();
}
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "crates/larch-core/src/nested.rs:1: concrete service client `octocrab` is used outside crates/larch-adapters/",
        ))
        .stdout(predicate::str::contains(
            "crates/larch-core/src/nested.rs:1: concrete service client `reqwest` is used outside crates/larch-adapters/",
        ))
        .stdout(predicate::str::contains(
            "crates/larch-core/src/nested.rs:2: concrete service client `hyper` is used outside crates/larch-adapters/",
        ))
        .stdout(predicate::str::contains(
            "crates/larch-core/src/nested.rs:6: concrete service client `octocrab` is used outside crates/larch-adapters/",
        ))
        .stdout(predicate::str::contains(
            "crates/larch-core/src/nested.rs:6: service request host `api.github.com` appears outside crates/larch-adapters/",
        ))
        .stderr("");
}

#[test]
fn counts_one_live_adapter_owner_and_ignores_test_only_construction() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-adapters/src/github/mod.rs",
        br"use octocrab::Octocrab;

pub fn build() {
    let _ = Octocrab::builder();
}

#[cfg(test)]
mod tests {
    use octocrab::Octocrab;

    fn fake() {
        let _ = Octocrab::builder();
    }
}
",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn allows_a_single_owner_adapter_named_by_the_inventories() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-adapters/src/github/mod.rs",
        br#"use octocrab::Octocrab;

pub fn build() -> Octocrab {
    Octocrab::builder().build().expect("client")
}
"#,
    );
    repository.write(
        "crates/larch-adapters/src/google_auth.rs",
        br"use google_cloud_auth::credentials::Builder;

pub fn load() {
    let _ = Builder::default();
}
",
    );
    repository.write(
        "crates/larch-core/src/clean.rs",
        b"pub fn ok() -> u32 { 0 }\n",
    );
    let inventory = ownership_matrix("crates/larch-adapters/src/github/mod.rs");
    repository.write("docs/github-service-inventory.md", inventory.as_bytes());
    repository.write(
        "docs/google-service-inventory.md",
        b"Owner: crates/larch-adapters/src/google_auth.rs\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn rejects_inventory_omissions_duplicate_rows_and_false_cutover_claims() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-adapters/src/github/mod.rs",
        b"pub fn owner() {}\n",
    );
    let inventory = ownership_matrix("crates/larch-adapters/src/github/mod.rs")
        .replace(
            "labels\tcrates/larch-adapters/src/github/mod.rs\tpython\t#7661\tpending\tpending\tpending\tfixture run\n",
            "",
        )
        .replace(
            "issues\tcrates/larch-adapters/src/github/mod.rs\tpython\t#7661\tpending\tpending\tpending\tfixture run",
            "issues\tcrates/larch-adapters/src/github/mod.rs\trust\t#7661\tcomplete\tcomplete\tcomplete\tfixture run,missing command\nissues\tcrates/larch-adapters/src/github/mod.rs\tpython\t#7661\tpending\tpending\tpending\tfixture run",
        );
    repository.write("docs/github-service-inventory.md", inventory.as_bytes());
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "GitHub service operation `labels` is missing from the ownership matrix",
        ))
        .stdout(predicate::str::contains(
            "duplicate GitHub service operation owner `issues`",
        ))
        .stdout(predicate::str::contains(
            "falsely claims migration state for fixture run",
        ))
        .stdout(predicate::str::contains(
            "unknown command selector `missing command`",
        ))
        .stderr("");
}

#[test]
fn rejects_every_untrustworthy_field_in_a_github_service_ownership_row() {
    let repository = TempRepo::new();
    let inventory = ownership_matrix("crates/larch-adapters/src/github/mod.rs").replace(
        "actions\tcrates/larch-adapters/src/github/mod.rs\tpython\t#7661\tpending\tpending\tpending\tfixture run",
        "Actions\tnot-an-adapter\tunknown\t#7687\tinvalid\tinvalid\tinvalid\tmissing *",
    );
    repository.write("docs/github-service-inventory.md", inventory.as_bytes());
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "GitHub service operation key is invalid",
        ))
        .stdout(predicate::str::contains(
            "GitHub service adapter owner `not-an-adapter` is not a tracked adapter path",
        ))
        .stdout(predicate::str::contains(
            "GitHub service current owner is invalid",
        ))
        .stdout(predicate::str::contains(
            "GitHub service planning owner must name concrete issues and must not delegate to #7687",
        ))
        .stdout(predicate::str::contains(
            "GitHub service migration state is invalid",
        ))
        .stdout(predicate::str::contains(
            "GitHub service ownership row names unknown command selector `missing *`",
        ))
        .stdout(predicate::str::contains(
            "GitHub service ownership row names no production command",
        ))
        .stderr("");
}

#[test]
fn reports_structurally_incomplete_service_ownership_matrices() {
    for (contents, message) in [
        (
            "GitHub service inventory without a matrix\n",
            "GitHub service ownership matrix is missing",
        ),
        (
            "<!-- github-service-ownership:start -->\n",
            "GitHub service ownership matrix is unterminated",
        ),
        (
            "<!-- github-service-ownership:start -->\nwrong header\n<!-- github-service-ownership:end -->\n",
            "GitHub service ownership matrix has an invalid header",
        ),
        (
            "<!-- github-service-ownership:start -->\noperation\tadapter_owner\tcurrent_owner\tplanning_issues\timplementation_parity\tconsumer_cutover\tpython_removal\tcommands\nshort\n<!-- github-service-ownership:end -->\n",
            "GitHub service ownership row must contain exactly eight tab-separated fields",
        ),
        (
            "<!-- github-service-ownership:start -->\n<!-- github-service-ownership:end -->\n",
            "GitHub service ownership matrix is empty",
        ),
    ] {
        let repository = TempRepo::new();
        repository.write("docs/github-service-inventory.md", contents.as_bytes());
        repository.commit_all();

        TempRepo::command_from(repository.path())
            .args(["rule", "service-ownership"])
            .assert()
            .code(1)
            .stdout(predicate::str::contains(message))
            .stderr("");
    }
}

#[test]
fn rejects_generic_github_credential_fallback_in_the_adapter() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-adapters/src/github/mod.rs",
        b"pub fn load() { let _ = env::GH_TOKEN; }\n",
    );
    let inventory = ownership_matrix("crates/larch-adapters/src/github/mod.rs");
    repository.write("docs/github-service-inventory.md", inventory.as_bytes());
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "GitHub service must not read caller-supplied GH_TOKEN or GITHUB_TOKEN",
        ))
        .stderr("");
}

#[test]
fn rejects_a_second_client_owner_and_excludes_test_module_construction() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-adapters/src/github/mod.rs",
        br#"use octocrab::Octocrab;

pub fn build() -> Octocrab {
    Octocrab::builder().build().expect("client")
}
"#,
    );
    repository.write(
        "crates/larch-adapters/src/github/extra.rs",
        br#"use octocrab::Octocrab;

pub fn also() -> Octocrab {
    Octocrab::builder().build().expect("client")
}
"#,
    );
    repository.write(
        "crates/larch-adapters/src/github/tested.rs",
        br"#[cfg(test)]
mod tests {
    fn make() {
        let _ = octocrab::Octocrab::builder();
    }
}
",
    );
    repository.write(
        "docs/github-service-inventory.md",
        b"Owners: crates/larch-adapters/src/github/mod.rs crates/larch-adapters/src/github/extra.rs\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "crates/larch-adapters/src/github/mod.rs:4: duplicate concrete GitHub client owner; Octocrab must be constructed by one adapter module",
        ))
        .stdout(predicate::str::contains(
            "crates/larch-adapters/src/github/extra.rs:4: duplicate concrete GitHub client owner; Octocrab must be constructed by one adapter module",
        ))
        .stdout(predicate::str::contains("tested.rs").not())
        .stderr("");
}

#[test]
fn rejects_inventory_drift_for_a_detected_owner() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-adapters/src/github/mod.rs",
        br#"use octocrab::Octocrab;

pub fn build() -> Octocrab {
    Octocrab::builder().build().expect("client")
}
"#,
    );
    repository.write(
        "crates/larch-adapters/src/google_auth.rs",
        br"use google_cloud_auth::credentials::Builder;

pub fn load() {
    let _ = Builder::default();
}
",
    );
    repository.write(
        "docs/github-service-inventory.md",
        b"This inventory names no owner.\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "docs/github-service-inventory.md:1: docs/github-service-inventory.md does not name the concrete service client owner crates/larch-adapters/src/github/mod.rs",
        ))
        .stdout(predicate::str::contains(
            "docs/google-service-inventory.md:1: docs/google-service-inventory.md is missing but a concrete service client owner exists",
        ))
        .stderr("");
}

#[test]
fn rejects_gcloud_and_credential_child_environments_in_production_shell() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/deploy.sh",
        b"#!/usr/bin/env bash\ngcloud auth login\nLARCH_GH_TOKEN=\"$SECRET\" ./do-thing\nGH_TOKEN=\"$SECRET\" ./do-thing\nCLOUDSDK_CONFIG=/tmp/adc ./do-thing\nDISCOVERED_ACCESS_TOKEN=secret ./unrelated-child\nsudo gcloud components update\ncommand gcloud storage ls\nenv FOO=bar gcloud auth print-access-token\n",
    );
    repository.write(
        "skills/example/SKILL.md",
        b"```bash\n/usr/local/bin/gcloud storage ls\nenv GITHUB_TOKEN=abc gh api\n```\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "scripts/deploy.sh:2: production runtime must not invoke the gcloud CLI; use the Rust Google adapter",
        ))
        .stdout(predicate::str::contains(
            "scripts/deploy.sh:3: service credential LARCH_GH_TOKEN must not enter a child environment",
        ))
        .stdout(predicate::str::contains(
            "scripts/deploy.sh:4: service credential GH_TOKEN must not enter a child environment",
        ))
        .stdout(predicate::str::contains(
            "scripts/deploy.sh:5: service credential CLOUDSDK_CONFIG must not enter a child environment",
        ))
        .stdout(predicate::str::contains(
            "scripts/deploy.sh:6: service credential DISCOVERED_ACCESS_TOKEN must not enter a child environment",
        ))
        .stdout(predicate::str::contains(
            "scripts/deploy.sh:7: production runtime must not invoke the gcloud CLI; use the Rust Google adapter",
        ))
        .stdout(predicate::str::contains(
            "scripts/deploy.sh:8: production runtime must not invoke the gcloud CLI; use the Rust Google adapter",
        ))
        .stdout(predicate::str::contains(
            "scripts/deploy.sh:9: production runtime must not invoke the gcloud CLI; use the Rust Google adapter",
        ))
        .stdout(predicate::str::contains(
            "skills/example/SKILL.md:2: production runtime must not invoke the gcloud CLI; use the Rust Google adapter",
        ))
        .stdout(predicate::str::contains(
            "skills/example/SKILL.md:3: service credential GITHUB_TOKEN must not enter a child environment",
        ))
        .stderr("");
}

#[test]
fn honors_reasoned_suppressions_across_rust_and_shell() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-core/src/allowed.rs",
        b"use octocrab::Octocrab; // lint-service-ownership: ok reviewed migration shim\n",
    );
    repository.write(
        "scripts/allowed.sh",
        b"#!/usr/bin/env bash\ngcloud version # lint-service-ownership: ok reviewed operator probe\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn rejects_a_suppression_without_a_reason() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/bad.sh",
        b"#!/usr/bin/env bash\ngcloud version # lint-service-ownership: ok\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::contains(
            "suppression lint-service-ownership lacks a reason",
        ));
}

#[test]
fn allows_documentation_comments_that_mention_service_hosts() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-core/src/doc.rs",
        br"//! Notes on api.github.com and googleapis.com endpoints.

/// Retries requests against api.github.com when rate-limited.
pub fn retry() -> u32 {
    0
}
",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn counts_feature_gated_owners_but_not_test_functions() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-adapters/src/github/mod.rs",
        br#"use octocrab::Octocrab;

pub fn build() -> Octocrab {
    Octocrab::builder().build().expect("client")
}
"#,
    );
    // A `#[cfg(test)]` free function builds a fake client, so it is not an owner.
    repository.write(
        "crates/larch-adapters/src/github/faked.rs",
        br"#[cfg(test)]
fn fake() {
    let _ = octocrab::Octocrab::builder();
}
",
    );
    // A feature-gated ("latest" contains the substring "test") second owner is
    // production code and must be flagged as a duplicate.
    repository.write(
        "crates/larch-adapters/src/github/latest.rs",
        br#"use octocrab::Octocrab;

#[cfg(feature = "latest")]
pub fn build_latest() -> Octocrab {
    Octocrab::builder().build().expect("client")
}
"#,
    );
    repository.write(
        "docs/github-service-inventory.md",
        b"Owners: crates/larch-adapters/src/github/mod.rs crates/larch-adapters/src/github/latest.rs\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "service-ownership"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "crates/larch-adapters/src/github/mod.rs:4: duplicate concrete GitHub client owner",
        ))
        .stdout(predicate::str::contains(
            "crates/larch-adapters/src/github/latest.rs:5: duplicate concrete GitHub client owner",
        ))
        .stdout(predicate::str::contains("faked.rs").not())
        .stderr("");
}
