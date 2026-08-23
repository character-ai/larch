use crate::support;

use std::fs;

use predicates::prelude::*;
use support::TempRepo;

const EXTERNAL: &str = "Style requirements: `<READABILITY_STYLE>`.\n";
const PLAN_REVIEW: &str =
    "Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`.\n";
const PUBLIC: &str = "**MANDATORY: READ ENTIRE FILE before composing fixture text: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**\n";
const DEV: &str = "**MANDATORY: READ ENTIRE FILE before composing fixture text: `$PWD/skills/shared/readability-style.md`.**\n";
const EXEMPTIONS: &str = "skills/design/SKILL.md\tskill-exempt\t0\tfixture\t\nskills/review/SKILL.md\tskill-exempt\t0\tfixture\t\n";

#[test]
fn readability_preamble_counts_external_and_orchestrator_directives() {
    let repository = TempRepo::new();
    write_manifest(
        &repository,
        concat!(
            "__metadata__\tmetadata-min-count\t3\t\n",
            "skills/design/references/a.md\texternal-prompt\t1\tstandard\t\n",
            "skills/design/references/plan.md\texternal-prompt\t1\tplan-review\t\n",
            "skills/design/SKILL.md\torchestrator-inline\t2\t\t2b,3b\n",
            "skills/review/SKILL.md\tskill-exempt\t0\tfixture\t\n"
        ),
    );
    repository.write("skills/design/references/a.md", EXTERNAL.as_bytes());
    repository.write("skills/design/references/plan.md", PLAN_REVIEW.as_bytes());
    repository.write(
        "skills/design/SKILL.md",
        format!("<!-- step:2b fixture -->\n{PUBLIC}<!-- step:3b fixture -->\n{PUBLIC}").as_bytes(),
    );
    repository.commit_all();

    run_rule(&repository)
        .success()
        .stdout(predicate::str::is_empty());

    repository.write(
        "skills/design/SKILL.md",
        format!("<!-- step:2b fixture -->\n{PUBLIC}<!-- step:3b fixture -->\nmissing\n").as_bytes(),
    );
    run_rule(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            "skills/design/SKILL.md:1: expected 2 orchestrator-inline readability-style directives, found 1\n",
        ));

    write_manifest(
        &repository,
        concat!(
            "__metadata__\tmetadata-min-count\t2\t\n",
            "skills/design/references/a.md\texternal-prompt\t1\tstandard\t\n",
            "skills/design/references/plan.md\texternal-prompt\t1\tplan-review\t\n",
            "skills/design/SKILL.md\torchestrator-inline\t1\t\t2b,3b\n",
            "skills/review/SKILL.md\tskill-exempt\t0\tfixture\t\n"
        ),
    );
    run_rule(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            "skills/design/SKILL.md:1: step \"3b\": expected >=1 orchestrator-inline readability-style directive in step body, found 0\n",
        ));
}

#[test]
fn readability_preamble_reports_count_missing_and_path_form_failures() {
    let repository = TempRepo::new();
    write_manifest(
        &repository,
        concat!(
            "__metadata__\tmetadata-min-count\t1\t\n",
            "prompt.md\texternal-prompt\t2\tstandard\t\n",
            "missing.md\texternal-prompt\t1\tstandard\t\n",
            "skills/foo/SKILL.md\torchestrator-inline\t1\t\t\n",
            ".claude/skills/bar/SKILL.md\torchestrator-inline\t1\t\t\n",
            "skills/design/SKILL.md\tskill-exempt\t0\tfixture\t\n",
            "skills/review/SKILL.md\tskill-exempt\t0\tfixture\t\n"
        ),
    );
    repository.write("prompt.md", EXTERNAL.as_bytes());
    repository.write("skills/foo/SKILL.md", DEV.as_bytes());
    repository.write(".claude/skills/bar/SKILL.md", PUBLIC.as_bytes());
    repository.commit_all();

    run_rule(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            "prompt.md:1: expected 2 external-prompt readability-style directives, found 1\n",
        ))
        .stdout(predicate::str::contains(
            "missing.md:1: missing external-prompt readability-style directive\n",
        ))
        .stdout(predicate::str::contains(
            "skills/foo/SKILL.md:1: missing per-skill readability directive for ${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md\n",
        ))
        .stdout(predicate::str::contains(
            "skills/foo/SKILL.md:1: uses wrong readability directive path form\n",
        ))
        .stdout(predicate::str::contains(
            ".claude/skills/bar/SKILL.md:1: missing per-skill readability directive for $PWD/skills/shared/readability-style.md\n",
        ))
        .stdout(predicate::str::contains(
            ".claude/skills/bar/SKILL.md:1: uses wrong readability directive path form\n",
        ));
}

#[test]
fn readability_preamble_checks_agents_and_ignores_external_prompts() {
    let repository = TempRepo::new();
    repository.write("agents/reviewer-fixture.md", DEV.as_bytes());
    repository.write(
        "skills/implement/prompts/codex-implementer.md",
        b"# no directive\n",
    );
    repository.commit_all();

    run_rule(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            "agents/reviewer-fixture.md:1: missing reviewer readability directive for ${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md\n",
        ))
        .stdout(predicate::str::contains(
            "agents/reviewer-fixture.md:1: uses wrong readability directive path form\n",
        ))
        .stdout(predicate::str::contains("skills/implement/prompts/codex-implementer.md").not());
}

#[test]
fn readability_preamble_accepts_exemptions_and_rejects_malformed_manifest_rows() {
    let valid = TempRepo::new();
    write_manifest(
        &valid,
        &format!("skills/foo/SKILL.md\tskill-exempt\t0\tpure pass-through\t\n{EXEMPTIONS}"),
    );
    valid.write("skills/foo/SKILL.md", b"# Foo\n");
    valid.commit_all();
    run_rule(&valid)
        .success()
        .stdout(predicate::str::is_empty());

    let missing = TempRepo::new();
    fs::remove_file(missing.path().join("scripts/lint-readability-preamble.tsv"))
        .expect("remove manifest");
    missing.commit_all();
    run_rule(&missing).code(2).stderr(predicate::str::contains(
        "manifest not found: scripts/lint-readability-preamble.tsv",
    ));

    let invalid = TempRepo::new();
    write_manifest(&invalid, "broken.md\texternal-prompt\t\tstandard\t\n");
    invalid.commit_all();
    run_rule(&invalid).code(2).stderr(predicate::str::contains(
        "invalid expected_count in scripts/lint-readability-preamble.tsv for row broken.md",
    ));

    let bad_exemption = TempRepo::new();
    write_manifest(&bad_exemption, "skills/foo/SKILL.md\tskill-exempt\t1\t\t\n");
    bad_exemption.commit_all();
    run_rule(&bad_exemption)
        .code(2)
        .stderr(predicate::str::contains(
            "invalid skill exemption row for skills/foo/SKILL.md",
        ));

    let duplicate_floor = TempRepo::new();
    write_manifest(
        &duplicate_floor,
        &format!("a\tmetadata-min-count\t0\t\nb\tmetadata-min-count\t0\t\n{EXEMPTIONS}"),
    );
    duplicate_floor.commit_all();
    run_rule(&duplicate_floor)
        .code(1)
        .stdout(predicate::str::contains(
            "scripts/lint-readability-preamble.tsv:1: duplicate metadata-min-count rows\n",
        ));
}

#[test]
fn readability_preamble_rejects_invalid_directives_and_manifest_variants() {
    let repository = TempRepo::new();
    write_manifest(
        &repository,
        concat!(
            "__metadata__\tmetadata-min-count\t2\t\n",
            "skills/foo/SKILL.md\torchestrator-inline\t1\t\t\n",
            "skills/design/SKILL.md\tskill-exempt\t0\tfixture\t\n",
            "skills/review/SKILL.md\tskill-exempt\t0\tfixture\t\n"
        ),
    );
    repository.write(
        "skills/foo/SKILL.md",
        b"See `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.\n**MANDATORY \xe2\x80\x94 READ ENTIRE FILE before composing fixture text: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**\n",
    );
    repository.commit_all();
    run_rule(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            "scripts/lint-readability-preamble.tsv:1: expected_count floor 2 exceeds manifest total 1\n",
        ))
        .stdout(predicate::str::contains(
            "skills/foo/SKILL.md:1: expected 1 orchestrator-inline readability-style directives, found 0\n",
        ))
        .stdout(predicate::str::contains(
            "skills/foo/SKILL.md:1: missing per-skill readability directive for ${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md\n",
        ));

    write_manifest(&repository, "\texternal-prompt\t1\tstandard\t\n");
    run_rule(&repository)
        .code(2)
        .stderr(predicate::str::contains(
            "invalid manifest row 1 in scripts/lint-readability-preamble.tsv: path and variant are required",
        ));

    write_manifest(&repository, "prompt.md\tunsupported\t1\t\t\n");
    run_rule(&repository)
        .code(2)
        .stderr(predicate::str::contains(
            "scripts/lint-readability-preamble.tsv: unknown manifest variant: unsupported",
        ));
}

fn write_manifest(repository: &TempRepo, rows: &str) {
    repository.write("scripts/lint-readability-preamble.tsv", rows.as_bytes());
}

fn run_rule(repository: &TempRepo) -> assert_cmd::assert::Assert {
    TempRepo::command_from(repository.path())
        .args(["rule", "readability-preamble"])
        .assert()
}
