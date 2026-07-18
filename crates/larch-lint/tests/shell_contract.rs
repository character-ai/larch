mod support;

use predicates::prelude::*;
use support::TempRepo;
use tempfile::tempdir;

#[test]
fn raw_stderr_rule_preserves_runtime_scope_and_shell_structure() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/good.sh",
        b"#!/usr/bin/env bash\necho 'larch_quiet_init' >&2\nlarch_quiet_init\nlarch_err 'after init'\ncat <<'TEXT'\necho 'inside heredoc' >&2\nTEXT\n",
    );
    repository.write(
        "scripts/bad.sh",
        b"#!/usr/bin/env bash\nlarch_quiet_init\nif true; then\n  echo 'after init' >&2\nfi\n",
    );
    repository.write(
        "hooks/bad-hook.sh",
        b"#!/usr/bin/env bash\nlarch_quiet_init\ncat \"$0\" >&2\n",
    );
    repository.write(
        "skills/example/scripts/bad-skill.sh",
        b"#!/usr/bin/env bash\nlarch_quiet_init\nprintf 'after init\\n' >&2\n",
    );
    repository.write(
        "other/bad.sh",
        b"#!/usr/bin/env bash\nlarch_quiet_init\necho 'outside scope' >&2\n",
    );
    repository.commit_all();

    run_rule(&repository, "no-raw-stderr-after-quiet-init")
        .code(1)
        .stdout(predicate::str::contains(
            "scripts/bad.sh:4: S041/no-raw-stderr-after-quiet-init",
        ))
        .stdout(predicate::str::contains(
            "hooks/bad-hook.sh:3: S041/no-raw-stderr-after-quiet-init",
        ))
        .stdout(predicate::str::contains(
            "skills/example/scripts/bad-skill.sh:3: S041/no-raw-stderr-after-quiet-init",
        ))
        .stdout(predicate::str::contains("other/bad.sh").not());
}

#[test]
fn raw_stderr_rule_requires_a_prior_quiet_init_and_keeps_same_line_legacy_behavior() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/first-line.sh",
        b"#!/usr/bin/env bash\necho 'before init' >&2\nlarch_quiet_init; echo 'same line' >&2\necho 'after init' >&2 # larch_err in a comment\n",
    );
    repository.commit_all();

    run_rule(&repository, "no-raw-stderr-after-quiet-init")
        .code(1)
        .stdout("scripts/first-line.sh:4: S041/no-raw-stderr-after-quiet-init: raw echo/printf/cat stderr after larch_quiet_init; use larch_err/larch_errf\n");
}

#[test]
fn harness_session_env_rule_enforces_preamble_and_reason_bearing_suppression() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/test-clean.sh",
        b"#!/usr/bin/env bash\nunset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR\nset -euo pipefail\n",
    );
    repository.write(
        "skills/example/scripts/test-suppressed.sh",
        b"#!/usr/bin/env bash\nset -euo pipefail\necho \"$IMPLEMENT_TMPDIR\" # lint-harness-session-env: ok verifies inherited state\n",
    );
    repository.write(
        "scripts/test-late.sh",
        b"#!/usr/bin/env bash\nset -euo pipefail\nunset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR\n",
    );
    repository.write(
        "scripts/test-reasonless.sh",
        b"#!/usr/bin/env bash\necho \"$IMPLEMENT_TMPDIR\" # lint-harness-session-env: ok\n",
    );
    repository.write(
        "scripts/test-late-suppression.sh",
        b"#!/usr/bin/env bash\necho \"$IMPLEMENT_TMPDIR\"\necho \"$DESIGN_TMPDIR\" # lint-harness-session-env: ok later state does not excuse the first use\n",
    );
    repository.write("scripts/runtime.sh", b"echo \"$IMPLEMENT_TMPDIR\"\n");
    repository.commit_all();

    run_rule(&repository, "harness-session-env")
        .code(1)
        .stdout(predicate::str::contains(
            "scripts/test-late.sh:1: missing required session-neutralization preamble before the first command\n",
        ))
        .stdout(predicate::str::contains(
            "scripts/test-reasonless.sh:1: missing required session-neutralization preamble before the first command\n",
        ))
        .stdout(predicate::str::contains(
            "scripts/test-late-suppression.sh:1: missing required session-neutralization preamble before the first command\n",
        ))
        .stdout(predicate::str::contains("scripts/runtime.sh").not());
}

#[test]
fn shell_contract_rules_fail_closed_for_an_invalid_root() {
    let directory = tempdir().expect("tempdir");
    TempRepo::command_from(directory.path())
        .args(["rule", "harness-session-env"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("cannot resolve repository root"));
}

fn run_rule(repository: &TempRepo, name: &str) -> assert_cmd::assert::Assert {
    TempRepo::command_from(repository.path())
        .args(["rule", name])
        .assert()
}
