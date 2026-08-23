use crate::support;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn unreachable_branch_reports_only_same_value_return_proofs() {
    let repository = TempRepo::new();
    repository.write(
        "crates/demo/src/lib.rs",
        br"fn repeated(flag: bool) -> u8 {
    if flag {
        return 1;
    }
    if flag {
        return 1;
    }
    2
}

fn different_return(flag: bool) -> u8 {
    if flag {
        return 1;
    }
    if flag {
        return 2;
    }
    3
}

fn different_condition(first: bool, second: bool) -> u8 {
    if first {
        return 1;
    }
    if second {
        return 1;
    }
    3
}

fn changed_by_call(flag: bool) -> u8 {
    if flag {
        return 1;
    }
    may_change_flag();
    if flag {
        return 1;
    }
    3
}
",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "unreachable-branch"])
        .assert()
        .code(1)
        .stdout("crates/demo/src/lib.rs:5: branch is contradicted by an earlier return of the same value\n")
        .stderr(predicate::str::is_empty());
}

#[test]
fn unreachable_branch_covers_nested_else_if_match_and_direct_returns() {
    let repository = TempRepo::new();
    repository.write(
        "crates/demo/src/lib.rs",
        br"fn nested(outer: bool, inner: bool) -> u8 {
    if outer {
        if inner {
            return 1;
        }
        if inner {
            return 1;
        }
    }
    2
}

fn chained(flag: bool) -> u8 {
    if flag {
        return 1;
    } else if flag {
        return 1;
    }
    2
}

fn matched(flag: bool) -> u8 {
    match flag {
        true => return 1,
        false => {}
    }
    if flag {
        return 1;
    }
    2
}

fn tail(flag: bool) -> u8 {
    return 1;
    if flag {
        return 1;
    }
}
",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "unreachable-branch"])
        .assert()
        .code(1)
        .stdout(concat!(
            "crates/demo/src/lib.rs:6: branch is contradicted by an earlier return of the same value\n",
            "crates/demo/src/lib.rs:16: branch is contradicted by an earlier return of the same value\n",
            "crates/demo/src/lib.rs:27: branch is contradicted by an earlier return of the same value\n",
            "crates/demo/src/lib.rs:35: branch is contradicted by an earlier return of the same value\n",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn unreachable_branch_respects_reasoned_suppressions_and_rejects_empty_ones() {
    let suppressed = TempRepo::new();
    suppressed.write(
        "crates/demo/src/lib.rs",
        br"fn repeated(flag: bool) -> u8 {
    if flag {
        return 1;
    }
    if flag { // lint-unreachable-branch: ok fixture documents intentional duplicate
        return 1;
    }
    2
}
",
    );
    suppressed.commit_all();
    TempRepo::command_from(suppressed.path())
        .args(["rule", "unreachable-branch"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());

    let missing_reason = TempRepo::new();
    missing_reason.write(
        "crates/demo/src/lib.rs",
        br"fn repeated(flag: bool) -> u8 {
    if flag {
        return 1;
    }
    if flag { // lint-unreachable-branch: ok
        return 1;
    }
    2
}
",
    );
    missing_reason.commit_all();
    TempRepo::command_from(missing_reason.path())
        .args(["rule", "unreachable-branch"])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr("larch-lint: error: suppression lint-unreachable-branch lacks a reason\n");
}
