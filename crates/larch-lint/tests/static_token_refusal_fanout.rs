use crate::support;

use predicates::prelude::*;
use support::TempRepo;

const LEDGER: &str =
    "crates/larch-lint/migration-ledger/static-token-refusal-fanout.toml";

const fn refusal_definitions() -> &'static [u8] {
    br#"pub struct Refusal(&'static str);
pub const BAD: Refusal = Refusal("bad");
"#
}

#[test]
fn reports_direct_and_closure_return_sites() {
    let repository = TempRepo::new();
    repository.write("crates/demo/src/errors.rs", refusal_definitions());
    repository.write(
        "crates/demo/src/lib.rs",
        br"fn direct(first: Option<u8>, flag: bool) -> Result<u8, Refusal> {
    if flag {
        return Err(BAD);
    }
    let value = first.ok_or(BAD)?;
    if value == 1 {
        Err(BAD)
    } else {
        Ok(value)
    }
}

fn closures(first: Option<u8>, second: Result<u8, ()>, third: Result<u8, ()>) -> Result<u8, Refusal> {
    let _ = first.ok_or_else(|| BAD)?;
    let _ = second.map_err(|_| BAD)?;
    third.map_err(|_error| BAD)
}
",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "static-token-refusal-fanout"])
        .assert()
        .code(1)
        .stdout(concat!(
            "crates/demo/src/lib.rs:1: direct returns BAD from 3 distinct branches; give each branch its own reason or name the offending element\n",
            "crates/demo/src/lib.rs:13: closures returns BAD from 3 distinct branches; give each branch its own reason or name the offending element\n",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn scans_impl_methods_and_trait_defaults() {
    let repository = TempRepo::new();
    let mut source = refusal_definitions().to_vec();
    source.extend_from_slice(
        br"
struct Worker;

impl Worker {
    fn method(first: Option<u8>, flag: bool) -> Result<u8, Refusal> {
        if flag { return Err(BAD); }
        let value = first.ok_or(BAD)?;
        Err(BAD)
    }
}

trait Check {
    fn default(first: Option<u8>, flag: bool) -> Result<u8, Refusal> {
        if flag { return Err(BAD); }
        let value = first.ok_or(BAD)?;
        Err(BAD)
    }
}
",
    );
    repository.write("crates/demo/src/lib.rs", &source);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "static-token-refusal-fanout"])
        .assert()
        .code(1)
        .stdout(
            predicate::str::contains("method returns BAD from 3 distinct branches").and(
                predicate::str::contains("default returns BAD from 3 distinct branches"),
            ),
        )
        .stderr(predicate::str::is_empty());
}

#[test]
fn two_sites_do_not_trigger() {
    let repository = TempRepo::new();
    let mut source = refusal_definitions().to_vec();
    source.extend_from_slice(
        br"
fn only_two(first: Option<u8>) -> Result<u8, Refusal> {
    let value = first.ok_or(BAD)?;
    Err(BAD)
}
",
    );
    repository.write("crates/demo/src/lib.rs", &source);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "static-token-refusal-fanout"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn plain_strings_and_enum_variants_do_not_trigger() {
    let repository = TempRepo::new();
    repository.write(
        "crates/demo/src/lib.rs",
        br#"pub const BAD: &str = "bad";
enum Failure { Bad }

fn string_error(first: Option<u8>, flag: bool) -> Result<u8, &'static str> {
    if flag { return Err(BAD); }
    let value = first.ok_or(BAD)?;
    Err(BAD)
}

fn enum_error(first: Option<u8>, flag: bool) -> Result<u8, Failure> {
    if flag { return Err(Failure::Bad); }
    let value = first.ok_or(Failure::Bad)?;
    Err(Failure::Bad)
}
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "static-token-refusal-fanout"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn reasoned_site_suppression_reduces_the_count() {
    let repository = TempRepo::new();
    let mut source = refusal_definitions().to_vec();
    source.extend_from_slice(
        br"
fn suppressed(first: Option<u8>, flag: bool) -> Result<u8, Refusal> {
    if flag { return Err(BAD); } // lint-static-token-refusal-fanout: ok all branches are malformed JSON
    let value = first.ok_or(BAD)?;
    Err(BAD)
}
",
    );
    repository.write("crates/demo/src/lib.rs", &source);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "static-token-refusal-fanout"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());

    let text = String::from_utf8(source)
        .expect("UTF-8 fixture")
        .replace(": ok all branches are malformed JSON", ": ok");
    repository.write("crates/demo/src/lib.rs", text.as_bytes());
    TempRepo::command_from(repository.path())
        .args(["rule", "static-token-refusal-fanout"])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr("larch-lint: error: suppression lint-static-token-refusal-fanout lacks a reason\n");
}

#[test]
fn cfg_test_modules_are_not_scanned() {
    let repository = TempRepo::new();
    let mut source = refusal_definitions().to_vec();
    source.extend_from_slice(
        br"
#[cfg(test)]
mod tests {
    use super::*;

    fn fixture(first: Option<u8>, flag: bool) -> Result<u8, Refusal> {
        if flag { return Err(BAD); }
        let value = first.ok_or(BAD)?;
        Err(BAD)
    }
}

#[cfg(all(test, unix))]
mod external_tests;
",
    );
    repository.write(
        "crates/demo/src/external_tests.rs",
        br"fn fixture(first: Option<u8>, flag: bool) -> Result<u8, Refusal> {
    if flag { return Err(BAD); }
    let value = first.ok_or(BAD)?;
    Err(BAD)
}
",
    );
    repository.write("crates/demo/src/lib.rs", &source);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "static-token-refusal-fanout"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn live_ledger_rows_silence_findings_and_stale_rows_fail() {
    let repository = TempRepo::new();
    let mut source = refusal_definitions().to_vec();
    source.extend_from_slice(
        br"
fn legacy(first: Option<u8>, flag: bool) -> Result<u8, Refusal> {
    if flag { return Err(BAD); }
    let value = first.ok_or(BAD)?;
    Err(BAD)
}
",
    );
    repository.write("crates/demo/src/lib.rs", &source);
    repository.write(
        LEDGER,
        br#"rule = "static-token-refusal-fanout"

[[grandfathered]]
path = "crates/demo/src/lib.rs"
function = "legacy"
constant = "BAD"
reason = "legacy parser reports one malformed-input category"
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "static-token-refusal-fanout"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());

    let stale = String::from_utf8(source)
        .expect("UTF-8 fixture")
        .replace("    Err(BAD)\n", "    Ok(value)\n");
    repository.write("crates/demo/src/lib.rs", stale.as_bytes());
    TempRepo::command_from(repository.path())
        .args(["rule", "static-token-refusal-fanout"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "stale grandfathered row for crates/demo/src/lib.rs::legacy BAD",
        ))
        .stderr(predicate::str::is_empty());

    repository.write(
        LEDGER,
        br#"rule = "static-token-refusal-fanout"

[[grandfathered]]
path = "crates/demo/src/lib.rs"
function = "legacy"
constant = "BAD"
reason = ""
"#,
    );
    TempRepo::command_from(repository.path())
        .args(["rule", "static-token-refusal-fanout"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains(
            "grandfathered rows need single-line path, function, constant, and reason",
        ));
}
