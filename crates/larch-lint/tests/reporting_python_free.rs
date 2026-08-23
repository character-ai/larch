use crate::support;

use std::fmt::Write as _;

use predicates::prelude::*;
use support::TempRepo;

const COMMANDS: [(&str, &str, u64, &str, &str, &str); 4] = [
    (
        "run-log",
        "init",
        8073,
        "rust",
        "larch.report.run_logs",
        "larch_log_init_main",
    ),
    (
        "run-log",
        "flush",
        7995,
        "retired",
        "larch.report.run_log_flush",
        "larch_log_flush_main",
    ),
    (
        "timing",
        "report",
        8083,
        "rust",
        "larch.report.timing",
        "timing_report_main",
    ),
    (
        "gantt",
        "render",
        8092,
        "rust",
        "larch.rendering.gantt",
        "gantt_render_main",
    ),
];

fn registry() -> String {
    let mut output = String::from("schema_version = 2\n");
    for (domain, verb, issue, owner, python_module, python_function) in COMMANDS {
        let parity = if owner == "retired" {
            "not-applicable"
        } else {
            "complete"
        };
        let _ = write!(
            output,
            r#"
[[commands]]
domain = "{domain}"
verb = "{verb}"
python_module = "{python_module}"
python_function = "{python_function}"
machine_stdout = false
owner = "{owner}"
implementation_parity = "{parity}"
consumer_cutover = "complete"
python_removal = "complete"
planning_issue = 7683
migration_issue = {issue}
"#,
        );
    }
    output
}

fn prepare(repository: &TempRepo) {
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        registry().as_bytes(),
    );
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY = {('other', 'run'): ('other', 'main', False)}\n",
    );
    repository.write(
        "python/larch/report/timing.py",
        b"def helper() -> None:\n    return None\n",
    );
}

/// A sampled fixture carries four of the pinned rows, so the only diagnostic it
/// may raise is the absence of the rest. The complete 55-row boundary is
/// asserted against the live ledger by `make rust-lint`.
#[test]
fn accepts_final_rows_and_reports_only_absent_rows() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "reporting-python-free"])
        .assert()
        .failure()
        .stdout(
            predicate::str::contains("missing final reporting-owned command row: run-log manifest")
                .and(predicate::str::contains("non-final").not())
                .and(predicate::str::contains("drift").not())
                .and(predicate::str::contains("unclosed").not())
                .and(predicate::str::contains("remains registered in Python").not())
                .and(predicate::str::contains("entrypoint remains").not()),
        )
        .stderr("");
}

#[test]
fn rejects_a_restored_python_registration_and_entrypoint() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY = {('timing', 'report'): ('larch.report.timing', 'timing_report_main', False)}\n",
    );
    repository.write(
        "python/larch/report/timing.py",
        b"def timing_report_main(argv: list[str]) -> int:\n    return 0\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "reporting-python-free"])
        .assert()
        .failure()
        .stdout(
            predicate::str::contains(
                "reporting-owned command remains registered in Python: timing report",
            )
            .and(predicate::str::contains(
                "superseded reporting Python entrypoint remains: larch.report.timing.timing_report_main",
            )),
        );
}

#[test]
fn rejects_restored_python_manifest_writer_and_caller() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "python/larch/report/run_log_manifest.py",
        b"def _update_manifest_v2() -> None:\n    return None\n",
    );
    repository.write(
        "python/larch/implement/dispatch_ship.py",
        b"run_log_manifest._update_manifest_v2()\n",
    );
    repository.write(
        "python/larch/implement/ship_recovery.py",
        b"def _write_manifest() -> None:\n    return None\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "reporting-python-free"])
        .assert()
        .failure()
        .stdout(
            predicate::str::contains(
                "production Python run-log manifest writer remains: _update_manifest_v2",
            )
            .and(predicate::str::contains(
                "production Python caller bypasses Rust run-log manifest owner: run_log_manifest._update_manifest_v2",
            ))
            .and(predicate::str::contains(
                "production Python run-log manifest writer remains: _write_manifest",
            )),
        );
}

#[test]
fn rejects_restored_python_progress_writer_caller_and_durable_write() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "python/larch/report/progress_file.py",
        b"def activate_run() -> None:\n    return None\nPath('current').write_text('run-1\\n')\n",
    );
    repository.write(
        "python/larch/implement/ship_state.py",
        b"progress_file.append_breadcrumb_for_run()\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "reporting-python-free"])
        .assert()
        .failure()
        .stdout(
            predicate::str::contains(
                "production Python progress-state writer remains: activate_run",
            )
            .and(predicate::str::contains(
                "production Python caller bypasses Rust progress-state owner: progress_file.append_breadcrumb_for_run",
            ))
            .and(predicate::str::contains(
                "production Python progress compatibility module performs a durable write",
            )),
        );
}

#[test]
fn rejects_restored_python_timing_writer_and_caller() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "python/larch/report/timing.py",
        b"class TimingLedger:\n    def record_round(self) -> None:\n        return None\nopen('timing-ledger.tsv', 'a').write('v1\\n')\n",
    );
    repository.write(
        "python/larch/review/plan_review_loop.py",
        b"from larch.report.timing import TimingLedger\nfrom larch.report.timing import record_round\nTimingLedger().record_round()\nrecord_round()\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "reporting-python-free"])
        .assert()
        .failure()
        .stdout(
            predicate::str::contains(
                "production Python timing-ledger writer remains: TimingLedger",
            )
            .and(predicate::str::contains(
                "production Python timing compatibility module performs a durable write",
            ))
            .and(predicate::str::contains(
                "production Python caller bypasses Rust timing owner: fromlarch.report.timingimportTimingLedger",
            ))
            .and(predicate::str::contains(
                "production Python caller bypasses Rust timing owner: fromlarch.report.timingimportrecord_round",
            )),
        );
}

#[test]
fn rejects_non_final_missing_and_unclosed_rows() {
    let repository = TempRepo::new();
    prepare(&repository);
    let drifted = registry()
        .replacen("owner = \"rust\"", "owner = \"python\"", 1)
        .replacen("migration_issue = 8083", "migration_issue = 8084", 1)
        .replace(
            r#"[[commands]]
domain = "gantt""#,
            r#"[[commands]]
domain = "token"
verb = "cost"
python_module = "larch.report.tokens"
python_function = "token_cost_main"
machine_stdout = false
owner = "python"
implementation_parity = "pending"
consumer_cutover = "pending"
python_removal = "pending"
planning_issue = 7683

[[commands]]
domain = "gantt""#,
        );
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        drifted.as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "reporting-python-free"])
        .assert()
        .failure()
        .stdout(
            predicate::str::contains("non-final reporting command row: run-log init")
                .and(predicate::str::contains(
                    "reporting command migration issue drift: timing report; expected #8083",
                ))
                .and(predicate::str::contains(
                    "unclosed #7683 ledger row: token cost",
                ))
                .and(predicate::str::contains(
                    "missing final reporting-owned command row: run-log manifest",
                )),
        );
}
