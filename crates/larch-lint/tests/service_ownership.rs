mod support;

use predicates::prelude::*;
use support::TempRepo;

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
    repository.write(
        "docs/github-service-inventory.md",
        b"Owner: crates/larch-adapters/src/github/mod.rs\n",
    );
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
        b"#!/usr/bin/env bash\ngcloud auth login\nLARCH_GH_TOKEN=\"$SECRET\" ./do-thing\nGH_TOKEN=\"$SECRET\" ./do-thing\nsudo gcloud components update\ncommand gcloud storage ls\nenv FOO=bar gcloud auth print-access-token\n",
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
            "scripts/deploy.sh:5: production runtime must not invoke the gcloud CLI; use the Rust Google adapter",
        ))
        .stdout(predicate::str::contains(
            "scripts/deploy.sh:6: production runtime must not invoke the gcloud CLI; use the Rust Google adapter",
        ))
        .stdout(predicate::str::contains(
            "scripts/deploy.sh:7: production runtime must not invoke the gcloud CLI; use the Rust Google adapter",
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
