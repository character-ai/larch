mod support;

use predicates::prelude::*;
use support::TempRepo;

const OWNER_GUIDANCE: &str = "use larch.issue.issue_mutation";

#[test]
fn rejects_raw_python_helpers_aliases_multiline_calls_and_wrappers() {
    let repository = TempRepo::new();
    repository.write(
        "python/larch/issue/direct.py",
        br#"from larch.git import gh
from larch.git.gh import issue_edit as rename
from larch.git import gh as github

def wrapper() -> None:
    gh.issue_edit(
        runner,
        "7",
        repo="owner/repo",
        title="new",
    )
    rename(runner, "7", repo="owner/repo", body="new")
    github.issue_label_add(runner, "7", "bug", repo="owner/repo")
    gh.issue_label_remove(runner, "7", "old", repo="owner/repo")
    gh.issue_edit_body_file(runner, "7", path, repo="owner/repo")
    gh.issue_edit_body_with_retry(runner, "7", "body", repo="owner/repo")
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-mutation-owner"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(format!(
            "python/larch/issue/direct.py:6: raw issue mutation helper issue_edit; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "python/larch/issue/direct.py:12: raw issue mutation helper issue_edit; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "raw issue mutation helper issue_label_add; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "raw issue mutation helper issue_label_remove; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "raw issue mutation helper issue_edit_body_file; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "raw issue mutation helper issue_edit_body_with_retry; {OWNER_GUIDANCE}"
        )))
        .stderr("");
}

#[test]
fn rejects_python_cli_rest_and_graphql_mutations() {
    let repository = TempRepo::new();
    repository.write(
        "python/larch/issue/direct.py",
        br#"from larch.git import gh
from larch.git.gh import command as invoke

runner.run(["gh", "issue", "edit", "7", "--title", "new"])
gh.command(
    runner,
    ["issue", "edit", "7", "--body", "new"],
)
gh.command(runner, ["api", f"/repos/{repo}/issues/{issue}", "-X", "PATCH", "-f", "title=new"])
runner.run(["curl", "-X", "PATCH", "https://api.github.com/repos/owner/repo/issues/7"])
gh.command(runner, ["api", "graphql", "-f", "query=mutation { updateIssue(input: $input) { issue { id } } }"])
gh.command(runner, ["api", "graphql", "-f", "query=mutation { addLabelsToLabelable(input: $input) { clientMutationId } }"])
gh.command(runner, ["api", "graphql", "-f", "query=mutation { removeLabelsFromLabelable(input: $input) { clientMutationId } }"])
invoke(runner, ["issue", "edit", "7", "--title", "aliased"])
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "issue-mutation-owner"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(format!(
            "python/larch/issue/direct.py:4: raw gh issue edit argv; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "python/larch/issue/direct.py:5: raw gh issue edit argv; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "python/larch/issue/direct.py:14: raw gh issue edit argv; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "raw issue REST PATCH; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "raw issue GraphQL mutation updateIssue; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "raw issue GraphQL mutation addLabelsToLabelable; {OWNER_GUIDANCE}"
        )))
        .stdout(predicate::str::contains(format!(
            "raw issue GraphQL mutation removeLabelsFromLabelable; {OWNER_GUIDANCE}"
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
fn allows_owner_fixture_roots_comments_strings_reads_and_unrelated_mutations() {
    let repository = TempRepo::new();
    let fixture = br#"from larch.git import gh
gh.issue_edit(runner, "7", repo="owner/repo", title="new")
runner.run(["gh", "issue", "edit", "7"])
"#;
    repository.write("python/larch/issue/issue_mutation.py", fixture);
    repository.write("python/tests/issue/test_direct.py", fixture);
    repository.write("python/larch/fixtures/direct.py", fixture);
    repository.write(
        "python/larch/issue/safe.py",
        br#"# gh.issue_edit(runner, "7")
NOTE = "gh issue edit 7"
GRAPHQL_NOTE = "updateIssue(input: $input)"
gh.api_read(runner, [f"/repos/{repo}/issues/{issue}", "--jq", ".title"])
gh.command(runner, ["api", "/repos/owner/repo/issues/comments/7", "-X", "PATCH"])
gh.command(runner, ["pr", "edit", "7", "--title", "new"])
editor.issue_edit(document)
runner.run(["echo", "safe"], env={"QUERY": "updateIssue(input: $input)", "METHOD": "PATCH", "PATH": "/repos/owner/repo/issues/7"})
"#,
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
