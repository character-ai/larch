use crate::support;

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

#[test]
fn skill_run_lifecycle_rejects_generic_instruction_for_external_owners() {
    let repository = TempRepo::new();
    repository.write(
        "skills/shared/run-lifecycle-ownership.tsv",
        b"skill\tstart_owner\tterminal_owner\tno_archive_exception\n*\tskills/shared/run-lifecycle.md\tskills/shared/run-lifecycle.md\t-\ndesign\tcrates/larch-cli/src/design_step0_commands.rs\tcrates/larch-cli/src/design_log_publish_commands.rs\t-\n",
    );
    repository.write(
        "crates/larch-cli/src/design_step0_commands.rs",
        b"run_lifecycle.start_run(\n",
    );
    repository.write(
        "crates/larch-cli/src/design_log_publish_commands.rs",
        b"run_lifecycle.finish_run(\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "skill-run-lifecycle"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "skills/design/SKILL.md:1: externally owned lifecycle must include its exact specialized mandatory instruction once",
        ));
}

#[test]
fn skill_run_lifecycle_accepts_specialized_instruction_for_external_owners() {
    let repository = TempRepo::new();
    repository.write(
        "skills/shared/run-lifecycle-ownership.tsv",
        b"skill\tstart_owner\tterminal_owner\tno_archive_exception\n*\tskills/shared/run-lifecycle.md\tskills/shared/run-lifecycle.md\t-\ndesign\tcrates/larch-cli/src/design_step0_commands.rs\tcrates/larch-cli/src/design_log_publish_commands.rs\t-\n",
    );
    repository.write(
        "skills/design/SKILL.md",
        b"# larch-run-lifecycle: shared-v1 skill=design\nallowed-tools: Bash\n**MANDATORY: Follow `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-lifecycle.md` with declared skill `design`. The `design` row in `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-lifecycle-ownership.tsv` has specialized owners. Do NOT run the shared contract's generic `run-log lifecycle-start` or terminal commands. Pass a leading `--lifecycle-parent-context` only through Step 0 to the registered start owner.**\ncode-quality / risk-integration / correctness / architecture / security\n",
    );
    repository.write(
        "crates/larch-cli/src/design_step0_commands.rs",
        b"run_lifecycle.start_run(\n",
    );
    repository.write(
        "crates/larch-cli/src/design_log_publish_commands.rs",
        b"run_lifecycle.finish_run(\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "skill-run-lifecycle"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}
