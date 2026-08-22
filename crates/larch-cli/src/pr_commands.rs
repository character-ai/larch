//! Rust owner for `pr compose-summary` (#8789).

use crate::{
    argparse_compat::parse_required_with_help,
    git_command_runtime::{GitCommandRuntime, exact_name_only_request},
};
use larch_adapters::{GitRef, GixRepository, path_under, resolve_allow_missing};
use larch_core::{RepositoryRead, Revision, compose_pr_summary};
use std::{env, ffi::OsString, fs, path::Path, process::ExitCode};

const PROGRAM: &str = "cli.py pr compose-summary";
const USAGE: &str = "usage: cli.py pr compose-summary [-h] --plan-goals-file PLAN_GOALS_FILE";
const HELP: &str = "usage: cli.py pr compose-summary [-h] --plan-goals-file PLAN_GOALS_FILE\n\noptions:\n  -h, --help            show this help message and exit\n  --plan-goals-file PLAN_GOALS_FILE\n";

/// Compose the implementation goal and changed-scope bullets for a PR.
pub fn compose_summary(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        PROGRAM,
        USAGE,
        HELP,
        &["--plan-goals-file"],
        &[],
        &["--plan-goals-file"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let supplied = parsed
        .value("--plan-goals-file")
        .expect("required option was checked")
        .to_string_lossy()
        .into_owned();
    match compose_summary_in(&supplied) {
        Ok(summary) => print!("{summary}"),
        Err(error) => {
            eprintln!("ERROR={error}");
            return ExitCode::from(2);
        }
    }
    ExitCode::SUCCESS
}

fn compose_summary_in(supplied: &str) -> Result<String, String> {
    let root = env::current_dir()
        .and_then(fs::canonicalize)
        .map_err(|_| format!("plan-goals path escapes repo root: {supplied}"))?;
    compose_summary_at(&root, supplied)
}

fn compose_summary_at(root: &Path, supplied: &str) -> Result<String, String> {
    let unresolved = if Path::new(supplied).is_absolute() {
        Path::new(supplied).to_path_buf()
    } else {
        root.join(supplied)
    };
    let plan = resolve_allow_missing(&unresolved)
        .map_err(|_| format!("plan-goals path escapes repo root: {supplied}"))?;
    if !path_under(&plan, root) {
        return Err(format!("plan-goals path escapes repo root: {supplied}"));
    }
    let metadata = fs::metadata(&plan).ok();
    if !metadata.is_some_and(|value| value.is_file() && value.len() > 0) {
        return Err(format!("plan-goals file missing or empty: {supplied}"));
    }
    let text =
        fs::read_to_string(&plan).map_err(|error| format!("could not read {supplied}: {error}"))?;
    let changed = changed_paths(root);
    compose_pr_summary(&text, changed.iter().map(String::as_str))
        .map_err(|_| format!("no Goal line found in {supplied}"))
}

fn changed_paths(root: &Path) -> Vec<String> {
    let Some((merge_base, head)) = merge_base_and_head(root) else {
        return Vec::new();
    };
    let Ok(base) = GitRef::new(merge_base) else {
        return Vec::new();
    };
    let Ok(head) = GitRef::new(head) else {
        return Vec::new();
    };
    let Ok(runtime) = GitCommandRuntime::for_repository(root) else {
        return Vec::new();
    };
    let result = runtime.runtime.block_on(runtime.git_cli().exact_diff(
        exact_name_only_request(Some(base), Some(head)),
        &runtime.cancellation,
    ));
    match result {
        Ok(result) if !result.truncated() && result.output().status().success() => {
            String::from_utf8_lossy(result.output().stdout())
                .lines()
                .filter(|line| !line.is_empty())
                .map(ToOwned::to_owned)
                .collect()
        }
        _ => Vec::new(),
    }
}

fn merge_base_and_head(root: &Path) -> Option<(String, String)> {
    let repository = GixRepository::discover(root).ok()?;
    let head = repository.resolve_revision(&Revision::new("HEAD")).ok()?;
    let origin_main = repository
        .resolve_revision(&Revision::new("origin/main"))
        .ok()?;
    let merge_base = repository.merge_base(&head, &origin_main).ok()?;
    Some((merge_base.to_hex(), head.to_hex()))
}

#[cfg(test)]
mod tests {
    use super::compose_summary_at;
    use larch_test_support::{GitFixture, GitRepository};
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn composes_without_git_metadata() {
        let fixture = TempDir::new().expect("fixture");
        fs::write(fixture.path().join("plan.md"), "## Goal\nShip Rust.\n").expect("plan write");
        assert_eq!(
            compose_summary_at(fixture.path(), "plan.md"),
            Ok("- Ship Rust.\n".to_owned())
        );
    }

    #[test]
    fn refuses_escape_missing_empty_and_goalless_inputs() {
        let fixture = TempDir::new().expect("fixture");
        let outside = TempDir::new().expect("outside fixture");
        fs::write(fixture.path().join("empty.md"), "").expect("empty write");
        fs::write(fixture.path().join("scope.md"), "## Scope\nNo goal\n").expect("scope write");
        assert!(
            compose_summary_at(
                fixture.path(),
                outside.path().join("plan.md").to_string_lossy().as_ref()
            )
            .is_err_and(|error| error.contains("path escapes repo root"))
        );
        assert_eq!(
            compose_summary_at(fixture.path(), "missing.md"),
            Err("plan-goals file missing or empty: missing.md".to_owned())
        );
        assert_eq!(
            compose_summary_at(fixture.path(), "empty.md"),
            Err("plan-goals file missing or empty: empty.md".to_owned())
        );
        assert_eq!(
            compose_summary_at(fixture.path(), "scope.md"),
            Err("no Goal line found in scope.md".to_owned())
        );
    }

    #[test]
    fn reads_the_merge_base_diff_through_typed_git() {
        let fixture = GitRepository::builder(GitFixture::Unborn)
            .build()
            .expect("fixture");
        fs::write(fixture.root().join("plan.md"), "## Goal\nShip Rust.\n").expect("plan write");
        fs::write(fixture.root().join("base.txt"), "base\n").expect("base write");
        git(&fixture, &["add", "."]);
        git(&fixture, &["commit", "-q", "-m", "base"]);
        git(
            &fixture,
            &["update-ref", "refs/remotes/origin/main", "HEAD"],
        );
        for (path, contents) in [
            ("crates/owner.rs", "owner\n"),
            ("docs/contract.md", "contract\n"),
            ("scripts/test-owner.sh", "#!/bin/sh\n"),
        ] {
            let target = fixture.root().join(path);
            fs::create_dir_all(target.parent().expect("changed parent")).expect("parent create");
            fs::write(target, contents).expect("changed file write");
        }
        git(&fixture, &["add", "."]);
        git(&fixture, &["commit", "-q", "-m", "change"]);

        assert_eq!(
            compose_summary_at(fixture.root(), "plan.md"),
            Ok(concat!(
                "- Ship Rust.\n",
                "- Added or updated 1 test file(s).\n",
                "- Cross-cutting changes across: crates,docs,scripts.\n"
            )
            .to_owned())
        );
    }

    fn git(repository: &GitRepository, arguments: &[&str]) {
        let output = repository.git(arguments).expect("git fixture command");
        assert!(
            output.success(),
            "git {arguments:?}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
}
