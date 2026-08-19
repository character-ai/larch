//! Rust owners for `implement checks-result-identity` and `checks self-edit-log`.
//!
//! The pure identity grammar, fingerprint, and classifiers live in
//! `larch_core::implement`; this module owns only the argparse-compatible
//! surface and the typed Git reads that feed the fingerprint.

use std::{
    ffi::OsString,
    num::NonZeroUsize,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{ExactDiffRequest, GixRepository};
use larch_core::{
    RepositoryRead, Revision, StatusOptions,
    implement::{
        CHECKS_INPUT_FP_SCHEMA_V1, ChecksIdentityError, ChecksInputIdentity, WorktreeFacts,
        classify_completed_result, classify_live_seed, compute_identity, file_sha256,
        identities_match, normalize_path, read_self_edits, session_repo_root,
        validate_repo_root_path, validate_session_tmpdir,
    },
};

use crate::{
    argparse_compat::{choice_error, parse_required_with_help, usage_error},
    git_command_runtime::GitCommandRuntime,
    implement_dispatch_commands::{format_rows, opt_string},
};

/// Fail closed rather than fingerprint a truncated diff capture.
const DIFF_CAPTURE_LIMIT: usize = 64 * 1024 * 1024;

const IDENTITY_PROG: &str = "cli.py implement checks-result-identity";
const IDENTITY_USAGE: &str = "usage: cli.py implement checks-result-identity [-h]\n                                               {compute,classify,validate-child,resolve-repo-root}\n                                               ...\n";
const IDENTITY_HELP: &str = "usage: cli.py implement checks-result-identity [-h]\n                                               {compute,classify,validate-child,resolve-repo-root}\n                                               ...\n\npositional arguments:\n  {compute,classify,validate-child,resolve-repo-root}\n\noptions:\n  -h, --help            show this help message and exit\n";

const COMPUTE_PROG: &str = "cli.py implement checks-result-identity compute";
const COMPUTE_USAGE: &str = "usage: cli.py implement checks-result-identity compute [-h] --repo-root\n                                                       REPO_ROOT\n";
const COMPUTE_HELP: &str = "usage: cli.py implement checks-result-identity compute [-h] --repo-root\n                                                       REPO_ROOT\n\noptions:\n  -h, --help            show this help message and exit\n  --repo-root REPO_ROOT\n";

const CLASSIFY_PROG: &str = "cli.py implement checks-result-identity classify";
const CLASSIFY_USAGE: &str = "usage: cli.py implement checks-result-identity classify [-h] --result-env\n                                                        RESULT_ENV --step STEP\n                                                        --repo-root REPO_ROOT\n                                                        [--terminal-actions TERMINAL_ACTIONS]\n                                                        [--mode {completed,live-seed}]\n                                                        [--merge-env MERGE_ENV]\n";
const CLASSIFY_HELP: &str = "usage: cli.py implement checks-result-identity classify [-h] --result-env\n                                                        RESULT_ENV --step STEP\n                                                        --repo-root REPO_ROOT\n                                                        [--terminal-actions TERMINAL_ACTIONS]\n                                                        [--mode {completed,live-seed}]\n                                                        [--merge-env MERGE_ENV]\n\noptions:\n  -h, --help            show this help message and exit\n  --result-env RESULT_ENV\n  --step STEP\n  --repo-root REPO_ROOT\n  --terminal-actions TERMINAL_ACTIONS\n  --mode {completed,live-seed}\n  --merge-env MERGE_ENV\n";

const VALIDATE_PROG: &str = "cli.py implement checks-result-identity validate-child";
const VALIDATE_USAGE: &str = "usage: cli.py implement checks-result-identity validate-child\n       [-h] --repo-root REPO_ROOT --expected-head EXPECTED_HEAD --expected-fp\n       EXPECTED_FP [--expected-schema EXPECTED_SCHEMA]\n";
const VALIDATE_HELP: &str = "usage: cli.py implement checks-result-identity validate-child\n       [-h] --repo-root REPO_ROOT --expected-head EXPECTED_HEAD --expected-fp\n       EXPECTED_FP [--expected-schema EXPECTED_SCHEMA]\n\noptions:\n  -h, --help            show this help message and exit\n  --repo-root REPO_ROOT\n  --expected-head EXPECTED_HEAD\n  --expected-fp EXPECTED_FP\n  --expected-schema EXPECTED_SCHEMA\n";

const RESOLVE_PROG: &str = "cli.py implement checks-result-identity resolve-repo-root";
const RESOLVE_USAGE: &str = "usage: cli.py implement checks-result-identity resolve-repo-root\n       [-h] --implement-tmpdir IMPLEMENT_TMPDIR\n";
const RESOLVE_HELP: &str = "usage: cli.py implement checks-result-identity resolve-repo-root\n       [-h] --implement-tmpdir IMPLEMENT_TMPDIR\n\noptions:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR\n";

const SELF_EDIT_PROG: &str = "cli.py checks self-edit-log";
const SELF_EDIT_USAGE: &str = "usage: cli.py checks self-edit-log [-h] --tmpdir TMPDIR [--path PATH]\n                                   [--repo-root REPO_ROOT]\n";
const SELF_EDIT_HELP: &str = "usage: cli.py checks self-edit-log [-h] --tmpdir TMPDIR [--path PATH]\n                                   [--repo-root REPO_ROOT]\n\noptions:\n  -h, --help            show this help message and exit\n  --tmpdir TMPDIR\n  --path PATH\n  --repo-root REPO_ROOT\n";

const VERBS: &[&str] = &["compute", "classify", "validate-child", "resolve-repo-root"];

/// Validate a persisted repository root, including its Git toplevel identity.
///
/// # Errors
/// Returns the fail-closed identity error for an unsafe or non-toplevel root.
pub fn validate_repo_root(repo_root: &Path) -> Result<PathBuf, ChecksIdentityError> {
    let resolved = validate_repo_root_path(repo_root)?;
    let repository = GixRepository::discover(&resolved)
        .map_err(|_| ChecksIdentityError::new("repo root is not a git repository"))?;
    let toplevel = repository
        .location()
        .work_dir
        .map(|path| PathBuf::from(String::from_utf8_lossy(path.as_bytes()).into_owned()))
        .and_then(|path| std::fs::canonicalize(path).ok())
        .ok_or_else(|| ChecksIdentityError::new("repo root is not a git repository"))?;
    if toplevel == resolved {
        Ok(resolved)
    } else {
        Err(ChecksIdentityError::new(
            "repo root is not the git toplevel",
        ))
    }
}

/// Compute the live checks identity for a validated repository root.
///
/// # Errors
/// Returns the fail-closed identity error for an unsafe root, an unreadable
/// Git state, or a truncated diff capture.
pub fn live_identity(repo_root: &Path) -> Result<ChecksInputIdentity, ChecksIdentityError> {
    let root = validate_repo_root(repo_root)?;
    let facts = worktree_facts(&root)?;
    compute_identity(root, &facts)
}

fn worktree_facts(root: &Path) -> Result<WorktreeFacts, ChecksIdentityError> {
    let repository = GixRepository::discover(root)
        .map_err(|_| ChecksIdentityError::new("repo root is not a git repository"))?;
    let head = repository
        .resolve_revision(&Revision::new("HEAD"))
        .map_err(|_| ChecksIdentityError::new("git rev-parse HEAD failed"))?
        .to_hex();
    let status = repository
        .local_status(&StatusOptions {
            include_untracked: true,
            ..StatusOptions::default()
        })
        .map_err(|_| ChecksIdentityError::new("git status --porcelain=v1 failed"))?;
    let untracked = status
        .untracked
        .iter()
        .map(|path| String::from_utf8_lossy(path.as_bytes()).into_owned())
        .collect();
    Ok(WorktreeFacts {
        head_sha: head,
        staged_diff: binary_diff(root, true)?,
        unstaged_diff: binary_diff(root, false)?,
        untracked,
    })
}

fn binary_diff(root: &Path, cached: bool) -> Result<Vec<u8>, ChecksIdentityError> {
    let label = if cached {
        "git diff --cached --binary --no-ext-diff"
    } else {
        "git diff --binary --no-ext-diff"
    };
    let mut runtime = GitCommandRuntime::for_repository(root)
        .map_err(|_| ChecksIdentityError::new(format!("{label} failed")))?;
    runtime.policy = runtime.policy.clone().with_output_limit(
        NonZeroUsize::new(DIFF_CAPTURE_LIMIT).expect("non-zero fingerprint capture limit"),
    );
    let result = runtime
        .runtime
        .block_on(runtime.git_cli().exact_diff(
            ExactDiffRequest {
                cached,
                binary: true,
                no_ext_diff: true,
                unified_context: None,
                name_only: false,
                name_status: false,
                quiet: false,
                exit_code: false,
                base: None,
                head: None,
                paths: Vec::new(),
            },
            &runtime.cancellation,
        ))
        .map_err(|_| ChecksIdentityError::new(format!("{label} failed")))?;
    if result.truncated() {
        // A truncated capture would silently change the fingerprint, which is
        // exactly the stale-input confusion this identity exists to prevent.
        return Err(ChecksIdentityError::new(format!(
            "{label} output exceeded the fingerprint capture limit"
        )));
    }
    Ok(result.output().stdout().to_vec())
}

/// `implement checks-result-identity` compatibility command.
pub fn checks_result_identity(arguments: &[OsString]) -> ExitCode {
    let mut verb: Option<String> = None;
    let mut rest: &[OsString] = &[];
    for (index, argument) in arguments.iter().enumerate() {
        let text = argument.to_string_lossy();
        if text == "-h" || text == "--help" {
            println!("{IDENTITY_HELP}");
            return ExitCode::SUCCESS;
        }
        if !text.starts_with('-') {
            verb = Some(text.into_owned());
            rest = &arguments[index + 1..];
            break;
        }
    }
    let Some(verb) = verb else {
        return usage_error(
            IDENTITY_USAGE,
            IDENTITY_PROG,
            "the following arguments are required: verb",
            2,
        );
    };
    if !VERBS.contains(&verb.as_str()) {
        let choices = VERBS
            .iter()
            .map(|choice| format!("'{choice}'"))
            .collect::<Vec<_>>()
            .join(", ");
        return usage_error(
            IDENTITY_USAGE,
            IDENTITY_PROG,
            &format!("argument verb: invalid choice: '{verb}' (choose from {choices})"),
            2,
        );
    }
    match dispatch_verb(&verb, rest) {
        Ok(code) | Err(DispatchFailure::Usage(code)) => code,
        Err(DispatchFailure::Identity(error)) => {
            eprintln!("ERROR={error}");
            ExitCode::from(2)
        }
    }
}

enum DispatchFailure {
    Usage(ExitCode),
    Identity(ChecksIdentityError),
}

impl From<ChecksIdentityError> for DispatchFailure {
    fn from(error: ChecksIdentityError) -> Self {
        Self::Identity(error)
    }
}

impl From<ExitCode> for DispatchFailure {
    fn from(code: ExitCode) -> Self {
        Self::Usage(code)
    }
}

fn dispatch_verb(verb: &str, arguments: &[OsString]) -> Result<ExitCode, DispatchFailure> {
    match verb {
        "resolve-repo-root" => resolve_repo_root(arguments),
        "compute" => compute(arguments),
        "validate-child" => validate_child(arguments),
        _ => classify(arguments),
    }
}

fn resolve_repo_root(arguments: &[OsString]) -> Result<ExitCode, DispatchFailure> {
    let parsed = parse_required_with_help(
        arguments,
        RESOLVE_PROG,
        RESOLVE_USAGE,
        RESOLVE_HELP,
        &["--implement-tmpdir"],
        &[],
        &["--implement-tmpdir"],
    )?;
    let tmpdir = PathBuf::from(opt_string(parsed.value("--implement-tmpdir")));
    let raw = session_repo_root(&tmpdir)?;
    let root = validate_repo_root(Path::new(&raw))?;
    println!("REPO_ROOT={}", root.display());
    Ok(ExitCode::SUCCESS)
}

fn compute(arguments: &[OsString]) -> Result<ExitCode, DispatchFailure> {
    let parsed = parse_required_with_help(
        arguments,
        COMPUTE_PROG,
        COMPUTE_USAGE,
        COMPUTE_HELP,
        &["--repo-root"],
        &[],
        &["--repo-root"],
    )?;
    let identity = live_identity(Path::new(&opt_string(parsed.value("--repo-root"))))?;
    print!("{}", format_rows(&identity.as_rows()));
    Ok(ExitCode::SUCCESS)
}

fn validate_child(arguments: &[OsString]) -> Result<ExitCode, DispatchFailure> {
    let parsed = parse_required_with_help(
        arguments,
        VALIDATE_PROG,
        VALIDATE_USAGE,
        VALIDATE_HELP,
        &[
            "--repo-root",
            "--expected-head",
            "--expected-fp",
            "--expected-schema",
        ],
        &[],
        &["--repo-root", "--expected-head", "--expected-fp"],
    )?;
    let root = validate_repo_root(Path::new(&opt_string(parsed.value("--repo-root"))))?;
    let schema = parsed.value("--expected-schema").map_or_else(
        || CHECKS_INPUT_FP_SCHEMA_V1.to_owned(),
        |value| value.to_string_lossy().into_owned(),
    );
    let expected = ChecksInputIdentity {
        head_sha: opt_string(parsed.value("--expected-head")),
        tree_fingerprint: opt_string(parsed.value("--expected-fp")),
        fingerprint_schema: schema,
        repo_root: root.clone(),
    };
    let current = live_identity(&root)?;
    if !identities_match(&current, &expected) {
        return Err(DispatchFailure::Identity(ChecksIdentityError::new(
            "checks input identity drifted from launch seed",
        )));
    }
    println!("MATCH=true");
    Ok(ExitCode::SUCCESS)
}

fn classify(arguments: &[OsString]) -> Result<ExitCode, DispatchFailure> {
    if let Some(error) = choice_error(
        arguments,
        &[
            "--result-env",
            "--step",
            "--repo-root",
            "--terminal-actions",
            "--mode",
            "--merge-env",
            "-h",
            "--help",
        ],
        &[("--mode", &["completed", "live-seed"])],
    ) {
        return Err(DispatchFailure::Usage(usage_error(
            CLASSIFY_USAGE,
            CLASSIFY_PROG,
            &error,
            2,
        )));
    }
    let parsed = parse_required_with_help(
        arguments,
        CLASSIFY_PROG,
        CLASSIFY_USAGE,
        CLASSIFY_HELP,
        &[
            "--result-env",
            "--step",
            "--repo-root",
            "--terminal-actions",
            "--mode",
            "--merge-env",
        ],
        &[],
        &["--result-env", "--step", "--repo-root"],
    )?;
    let root = validate_repo_root(Path::new(&opt_string(parsed.value("--repo-root"))))?;
    let facts = worktree_facts(&root)?;
    let live = compute_identity(root, &facts)?;
    let raw_actions = opt_string(parsed.value("--terminal-actions"));
    let owned_actions: Vec<String> = if raw_actions.trim().is_empty() {
        larch_core::CHECKS_TERMINAL_ACTIONS
            .iter()
            .map(|action| (*action).to_owned())
            .collect()
    } else {
        raw_actions
            .split(',')
            .filter(|part| !part.is_empty())
            .map(ToOwned::to_owned)
            .collect()
    };
    let actions: Vec<&str> = owned_actions.iter().map(String::as_str).collect();
    let mode = opt_string(parsed.value("--mode"));
    let classification = if mode == "live-seed" {
        let merge_env = opt_string(parsed.value("--merge-env"));
        if merge_env.is_empty() {
            return Err(DispatchFailure::Identity(ChecksIdentityError::new(
                "--merge-env is required for live-seed mode",
            )));
        }
        classify_live_seed(Path::new(&merge_env), &live)
    } else {
        classify_completed_result(
            Path::new(&opt_string(parsed.value("--result-env"))),
            &opt_string(parsed.value("--step")),
            &live,
            &actions,
        )
    };
    let mut rows = vec![
        ("STATE".to_owned(), classification.state.to_owned()),
        ("REASON".to_owned(), classification.reason.clone()),
    ];
    rows.extend(live.as_rows());
    print!("{}", format_rows(&rows));
    Ok(ExitCode::from(match classification.state {
        "unsafe" => 2,
        "matching" => 0,
        _ => 1,
    }))
}

/// `checks self-edit-log` compatibility command.
pub fn self_edit_log(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        SELF_EDIT_PROG,
        SELF_EDIT_USAGE,
        SELF_EDIT_HELP,
        &["--tmpdir", "--path", "--repo-root"],
        &[],
        &["--tmpdir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let raw_tmpdir = opt_string(parsed.value("--tmpdir"));
    let raw_tmpdir = if raw_tmpdir.is_empty() {
        std::env::var("IMPLEMENT_TMPDIR").unwrap_or_default()
    } else {
        raw_tmpdir
    };
    let Some(canonical) = validate_session_tmpdir(&raw_tmpdir) else {
        println!("SELF_EDIT_LOG_STATUS=tmpdir-validation");
        return ExitCode::from(2);
    };
    let records = read_self_edits(&canonical);
    let query = opt_string(parsed.value("--path"));
    let repo_root = opt_string(parsed.value("--repo-root"));
    let shown: Vec<&larch_core::implement::SelfEditRecord> = if query.is_empty() {
        println!("SELF_EDIT_COUNT={}", records.len());
        records.iter().collect()
    } else {
        let normalized = normalize_path(&query);
        let rows: Vec<&larch_core::implement::SelfEditRecord> = records
            .iter()
            .filter(|record| record.path == normalized)
            .collect();
        println!("SELF_EDIT_ATTRIBUTED={}", !rows.is_empty());
        if !repo_root.is_empty() && !rows.is_empty() {
            let current = file_sha256(Path::new(&repo_root), &normalized);
            let fresh = rows.iter().any(|record| record.post_sha256 == current);
            println!("SELF_EDIT_CONTENT_MATCHES={fresh}");
        }
        rows
    };
    for record in shown {
        println!(
            "SELF_EDIT source={} recorded_epoch_s={} post_sha256={} path={}",
            record.source, record.recorded_epoch_s, record.post_sha256, record.path
        );
    }
    println!("SELF_EDIT_LOG_STATUS=ok");
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::{checks_result_identity, self_edit_log};
    use std::{ffi::OsString, process::ExitCode};

    fn args(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn identity_reports_missing_and_invalid_verbs() {
        assert_eq!(checks_result_identity(&[]), ExitCode::from(2));
        assert_eq!(checks_result_identity(&args(&["bogus"])), ExitCode::from(2));
        assert_eq!(
            checks_result_identity(&args(&["--help"])),
            ExitCode::SUCCESS
        );
    }

    #[test]
    fn identity_rejects_an_unsafe_repo_root() {
        assert_eq!(
            checks_result_identity(&args(&["compute", "--repo-root", "relative"])),
            ExitCode::from(2)
        );
    }

    #[test]
    fn self_edit_log_refuses_an_unvalidated_tmpdir() {
        assert_eq!(
            self_edit_log(&args(&["--tmpdir", "/larch-self-edit-missing"])),
            ExitCode::from(2)
        );
        assert_eq!(self_edit_log(&args(&["--help"])), ExitCode::SUCCESS);
    }
}
