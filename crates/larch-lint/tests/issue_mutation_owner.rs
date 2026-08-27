use crate::support;

use predicates::prelude::*;
use support::TempRepo;

const OWNER_GUIDANCE: &str = "use larch_adapters::github::IssueMutationOwner";

#[test]
fn rejects_raw_rust_issue_field_mutations_outside_the_owner() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-cli/src/direct.rs",
        br#"fn rewrite(service: &impl GitHubService) {
    service.edit_issue(request, cancellation);
    GitHubService::remove_label(service, repository, 7, "old", cancellation);
}

use larch_core::GitHubService;
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-mutation-owner"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(format!(
            "crates/larch-cli/src/direct.rs:2: raw Rust issue field mutation edit_issue; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "crates/larch-cli/src/direct.rs:3: raw Rust issue field mutation remove_label; {OWNER_GUIDANCE}"
        )))
        .stderr("");
}

#[test]
fn rejects_shell_markdown_and_hook_commands() {
    let repository = TempRepo::new();
    repository.write(
        "scripts/direct.sh",
        b"#!/usr/bin/env bash\ngh issue \\\n  edit 7 --title new\n",
    );
    repository.write(
        "skills/example/SKILL.md",
        b"```bash\ngh api --method PATCH /repos/owner/repo/issues/7 -f body=new\n```\n\nRun: `gh api graphql -f 'query=mutation { updateIssue(input: $input) { issue { id } } }'`.\n",
    );
    repository.write(
        "hooks/hooks.json",
        br#"{"hooks":{"PreToolUse":[{"hooks":[{"type":"command","command":"gh issue edit 7 --add-label bug"}]}]}}
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-mutation-owner"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(format!(
            "scripts/direct.sh:2: raw gh issue edit argv; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "skills/example/SKILL.md:2: raw issue REST PATCH; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "skills/example/SKILL.md:5: raw issue GraphQL mutation updateIssue; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "hooks/hooks.json:1: raw gh issue edit argv; {OWNER_GUIDANCE}"
        )))
        .stderr("");
}

#[test]
fn allows_rust_owner_fixture_roots_comments_strings_reads_and_unrelated_mutations() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-adapters/src/github/issue_mutation.rs",
        b"use larch_core::GitHubService;\n\nfn owner(service: &impl GitHubService) {\n    service.edit_issue(request, cancellation);\n}\n",
    );
    repository.write(
        "skills/example/SKILL.md",
        b"Never run `gh issue edit 7`.\nThe old `gh issue edit` command is forbidden.\n```text\ngh issue edit 7\n```\n",
    );
    repository.write(
        "scripts/safe.sh",
        b"#!/usr/bin/env bash\n# gh issue edit 7\nprintf '%s\\n' 'gh issue edit 7'\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-mutation-owner"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}
