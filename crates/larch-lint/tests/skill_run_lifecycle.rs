mod support;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn skill_run_lifecycle_rejects_missing_bash_handoff_and_direct_publication() {
    let repository = TempRepo::new();
    repository.write(
        "skills/demo/SKILL.md",
        b"# larch-run-lifecycle: shared-v1 skill=demo\nallowed-tools: Read\n**MANDATORY: Follow the complete shared lifecycle contract in `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-lifecycle.md` with declared skill `demo`.**\nInvoke the Skill tool:\n- description: fixture child\n- args: --fixture\npublish_log_run(\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "skill-run-lifecycle"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "skills/demo/SKILL.md:1: shared lifecycle declaration requires Bash permission",
        ))
        .stdout(predicate::str::contains(
            "skills/demo/SKILL.md:6: child Skill call omits leading lifecycle parent-context handoff",
        ))
        .stdout(predicate::str::contains(
            "skills/demo/SKILL.md:1: direct terminal publisher bypasses lifecycle ownership",
        ));
}

#[test]
fn skill_run_lifecycle_accepts_the_seeded_shared_contract() {
    let repository = TempRepo::new();
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "skill-run-lifecycle"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}
