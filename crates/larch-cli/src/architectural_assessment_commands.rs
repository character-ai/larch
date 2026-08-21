//! Rust owner for the `architectural-assessment` command surface (#8615).
//!
//! Four verbs matching `larch.implement.architectural_assessment`:
//! `materialize`, `submit`, `final-report-sections`, and `sanitize-detail`.
//! Library logic lives in [`larch_core::architectural_assessment`]; this module
//! owns argparse-compatible argv, live Git via the typed repository and
//! `ExactDiff` ports, and KEY=value stdout contracts.

#![allow(clippy::too_many_lines)]
use std::{
    env,
    ffi::{OsStr, OsString},
    io::{self, Read as _, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{
    ExactDiffRequest, GitPath, GitRef, GixRepository, is_regular_file, path_under,
};
use larch_core::{
    AssessmentGit, AssessmentResult, EXIT_HEAD_DRIFT, MAX_SANITIZE_DETAIL_BYTES, RepositoryRead,
    Revision, SubmitError, durable_note_path, final_report_sections, materialize, normalize_kinds,
    read_regular, sanitize_detail, sanitize_diagnostic_line, submit,
};

use crate::{
    argparse_compat::{finish_parse, parse_with_flags, write_stdout},
    git_command_runtime::GitCommandRuntime,
};

const EXIT_OK: u8 = 0;
const EXIT_INTERNAL: u8 = 1;
const EXIT_USAGE: u8 = 2;

const MATERIALIZE_PROGRAM: &str = "cli.py architectural-assessment materialize";
const MATERIALIZE_USAGE: &str = "usage: cli.py architectural-assessment materialize [-h] [--kind KIND] [--repo-root REPO_ROOT] [--implement-tmpdir IMPLEMENT_TMPDIR]";
const SUBMIT_PROGRAM: &str = "cli.py architectural-assessment submit";
const SUBMIT_USAGE: &str = "usage: cli.py architectural-assessment submit [-h] --kind KIND --state STATE --note-file NOTE_FILE [--allow-exception] [--repo-root REPO_ROOT] [--implement-tmpdir IMPLEMENT_TMPDIR]";
const SANITIZE_PROGRAM: &str = "cli.py architectural-assessment sanitize-detail";
const SANITIZE_USAGE: &str = "usage: cli.py architectural-assessment sanitize-detail [-h] --implement-tmpdir IMPLEMENT_TMPDIR";
const FINAL_PROGRAM: &str = "cli.py architectural-assessment final-report-sections";
const FINAL_USAGE: &str = "usage: cli.py architectural-assessment final-report-sections [-h] --implement-tmpdir IMPLEMENT_TMPDIR";

/// Live Git adapter for assessment identity and diff materialization.
///
/// Peel (`^{commit}`), merge-base, exclude pathspecs, and rename-aware path
/// listings are expressed through [`GixRepository`] and typed `exact_diff`.
#[derive(Debug)]
pub struct LiveAssessmentGit {
    base_remote: &'static str,
}

impl LiveAssessmentGit {
    pub const fn for_base_remote(base_remote: &'static str) -> Self {
        Self { base_remote }
    }
}

impl Default for LiveAssessmentGit {
    fn default() -> Self {
        Self::for_base_remote("origin")
    }
}

impl AssessmentGit for LiveAssessmentGit {
    fn compose_base(&self) -> (&str, &str) {
        (self.base_remote, "main")
    }

    fn git_read(&self, repo_root: &Path, argv: &[&str]) -> Result<String, String> {
        git_read(repo_root, argv)
    }

    fn implementation_diff_for_head(
        &self,
        repo_root: &Path,
        head_sha: &str,
        base_remote: &str,
        base_ref: &str,
    ) -> Result<String, String> {
        implementation_diff_for_head(repo_root, head_sha, base_remote, base_ref)
    }

    fn incremental_paths(
        &self,
        repo_root: &Path,
        old_head: &str,
        new_head: &str,
    ) -> Result<Vec<String>, String> {
        incremental_paths(repo_root, old_head, new_head)
    }
}

fn open_repository(repo_root: &Path) -> Result<GixRepository, String> {
    GixRepository::open(repo_root).map_err(|error| sanitize_diagnostic_line(&error.to_string()))
}

fn resolve_revision(repository: &GixRepository, revision: &str) -> Result<String, String> {
    repository
        .resolve_revision(&Revision::new(revision.as_bytes()))
        .map(|id| id.to_hex())
        .map_err(|error| sanitize_diagnostic_line(&error.to_string()))
}

fn git_read(repo_root: &Path, argv: &[&str]) -> Result<String, String> {
    let revision = match argv {
        ["rev-parse", revision] | ["rev-parse", "--verify", revision] => *revision,
        _ => {
            return Err(sanitize_diagnostic_line(&format!(
                "unsupported assessment git_read argv: {argv:?}"
            )));
        }
    };
    let repository = open_repository(repo_root)?;
    resolve_revision(&repository, revision)
}

fn implementation_diff_for_head(
    repo_root: &Path,
    head_sha: &str,
    base_remote: &str,
    base_ref: &str,
) -> Result<String, String> {
    let repository = open_repository(repo_root)?;
    let target = format!("{base_remote}/{base_ref}");
    let head = repository
        .resolve_revision(&Revision::new(head_sha.as_bytes()))
        .map_err(|error| error.to_string())?;
    let base = repository
        .resolve_revision(&Revision::new(target.as_bytes()))
        .map_err(|_error| format!("could not resolve merge base for {target}"))?;
    let merge_base = repository
        .merge_base(&head, &base)
        .map_err(|_error| format!("could not resolve merge base for {target}"))?;
    let base_ref = GitRef::new(merge_base.to_hex()).map_err(|error| error.to_string())?;
    let head_ref = GitRef::new(head_sha).map_err(|error| error.to_string())?;
    // Keep the exclude pathspec explicit beside the ExactDiff call so this
    // surface stays distinct from the agent branch-context helper.
    let paths = vec![
        GitPath::new(".").map_err(|error| error.to_string())?,
        GitPath::new(":(exclude)larch-logs/**").map_err(|error| error.to_string())?,
    ];
    let runtime = GitCommandRuntime::for_repository(repo_root)?;
    let result = runtime
        .runtime
        .block_on(runtime.git_cli().exact_diff(
            ExactDiffRequest {
                cached: false,
                binary: false,
                no_ext_diff: false,
                numstat_z_rename_50: false,
                unified_context: None,
                name_only: false,
                name_status: false,
                quiet: false,
                exit_code: false,
                base: Some(base_ref),
                head: Some(head_ref),
                paths,
            },
            &runtime.cancellation,
        ))
        .map_err(|error| error.to_string())?;
    if result.truncated() {
        return Err("git diff output exceeded the capture limit".to_owned());
    }
    Ok(String::from_utf8_lossy(result.output().stdout()).into_owned())
}

fn incremental_paths(
    repo_root: &Path,
    old_head: &str,
    new_head: &str,
) -> Result<Vec<String>, String> {
    let repository = open_repository(repo_root)?;
    let old_id = repository
        .resolve_revision(&Revision::new(old_head.as_bytes()))
        .map_err(|_error| "incremental path listing failed".to_owned())?;
    let new_id = repository
        .resolve_revision(&Revision::new(new_head.as_bytes()))
        .map_err(|_error| "incremental path listing failed".to_owned())?;
    let old_tree = repository
        .resolve_revision(&Revision::new(
            format!("{}^{{tree}}", old_id.to_hex()).into_bytes(),
        ))
        .map_err(|_error| "incremental path listing failed".to_owned())?;
    let new_tree = repository
        .resolve_revision(&Revision::new(
            format!("{}^{{tree}}", new_id.to_hex()).into_bytes(),
        ))
        .map_err(|_error| "incremental path listing failed".to_owned())?;
    let changes = repository
        .tree_changes(&old_tree, &new_tree)
        .map_err(|_error| "incremental path listing failed".to_owned())?;
    let mut paths = Vec::new();
    for change in changes.entries() {
        if let Some(source) = &change.source_path {
            let source = String::from_utf8(source.as_bytes().to_vec())
                .map_err(|_error| "incremental path listing is not UTF-8".to_owned())?;
            if source.is_empty() {
                return Err("incremental path listing contains an empty path".to_owned());
            }
            paths.push(source);
        }
        let path = String::from_utf8(change.path.as_bytes().to_vec())
            .map_err(|_error| "incremental path listing is not UTF-8".to_owned())?;
        if path.is_empty() {
            return Err("incremental path listing contains an empty path".to_owned());
        }
        paths.push(path);
    }
    if paths.is_empty() {
        return Err("incremental path listing empty".to_owned());
    }
    Ok(paths)
}

fn option_or_env(
    parsed: &crate::argparse_compat::ParsedCommandLine,
    option: &str,
    variable: &str,
) -> String {
    match parsed.value(option) {
        Some(value) if !value.is_empty() => value.to_string_lossy().into_owned(),
        _ => env::var(variable).unwrap_or_default(),
    }
}

fn os_to_string(value: &OsStr) -> String {
    value.to_string_lossy().into_owned()
}

fn current_head_sha() -> String {
    env::current_dir()
        .ok()
        .and_then(|cwd| GixRepository::discover(cwd).ok())
        .and_then(|repository| {
            repository
                .resolve_revision(&Revision::new(b"HEAD"))
                .ok()
                .map(|id| id.to_hex())
        })
        .unwrap_or_default()
}

fn print_lines(lines: &[String]) {
    for line in lines {
        println!("{line}");
    }
}

fn materialize_usage_error(detail: &str) -> ExitCode {
    print_lines(&[
        "ASSESSMENT_MATERIALIZE_STATUS=usage-error".to_owned(),
        format!("ASSESSMENT_DETAIL={detail}"),
    ]);
    ExitCode::from(EXIT_USAGE)
}

fn submit_status(status: &str, detail: &str, code: u8) -> ExitCode {
    print_lines(&[
        format!("ASSESSMENT_STATUS={status}"),
        format!("ASSESSMENT_DETAIL={detail}"),
    ]);
    ExitCode::from(code)
}

/// Run `architectural-assessment materialize`.
pub fn materialize_command(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &["--kind", "--repo-root", "--implement-tmpdir"],
        &["-h", "--help"],
        0,
    );
    if parsed.flag("-h") || parsed.flag("--help") {
        let help = format!(
            "{MATERIALIZE_USAGE}\n\noptional arguments:\n  -h, --help            show this help message and exit\n  --kind KIND\n  --repo-root REPO_ROOT\n  --implement-tmpdir IMPLEMENT_TMPDIR\n"
        );
        return write_stdout(&help);
    }
    let parsed = match finish_parse(parsed, MATERIALIZE_USAGE, MATERIALIZE_PROGRAM, &[]) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let kinds: Vec<String> = parsed
        .values("--kind")
        .into_iter()
        .map(os_to_string)
        .collect();
    let normalized = match normalize_kinds(&kinds) {
        Ok(kinds) => kinds,
        Err(error) => {
            return materialize_usage_error(&sanitize_diagnostic_line(&error));
        }
    };
    let repo_root = option_or_env(&parsed, "--repo-root", "REPO");
    let implement_tmpdir = option_or_env(&parsed, "--implement-tmpdir", "IMPLEMENT_TMPDIR");
    if repo_root.is_empty() || implement_tmpdir.is_empty() {
        return materialize_usage_error("repo root and implement tmpdir are required");
    }
    let repo_root = PathBuf::from(repo_root);
    let implement_tmpdir = PathBuf::from(implement_tmpdir);
    let git = LiveAssessmentGit::default();
    let (statuses, pending) = match materialize(&kinds, &repo_root, &implement_tmpdir, &git) {
        Ok(result) => result,
        Err(error) => {
            print_lines(&[
                "ASSESSMENT_MATERIALIZE_STATUS=failed".to_owned(),
                format!(
                    "ASSESSMENT_DETAIL={}",
                    sanitize_detail(&error, &implement_tmpdir)
                ),
            ]);
            return ExitCode::from(EXIT_INTERNAL);
        }
    };
    let pending_kinds: Vec<&str> = pending.iter().map(|evidence| evidence.kind.key()).collect();
    let log_pending_kinds: Vec<&str> = normalized
        .iter()
        .filter(|kind| statuses.get(kind.key()).map(String::as_str) == Some("log-pending"))
        .map(|kind| kind.key())
        .collect();
    let deterministic_kinds: Vec<&str> = normalized
        .iter()
        .filter(|kind| {
            statuses
                .get(kind.key())
                .is_some_and(|status| status != "log-pending")
        })
        .map(|kind| kind.key())
        .collect();
    let mut lines = vec![
        "ASSESSMENT_MATERIALIZE_STATUS=ok".to_owned(),
        format!(
            "ASSESSMENT_REQUESTED_KINDS={}",
            normalized
                .iter()
                .map(|kind| kind.key())
                .collect::<Vec<_>>()
                .join(",")
        ),
        format!("ASSESSMENT_PENDING_KINDS={}", pending_kinds.join(",")),
        format!(
            "ASSESSMENT_DETERMINISTIC_KINDS={}",
            deterministic_kinds.join(",")
        ),
        format!(
            "ASSESSMENT_LOG_PENDING_KINDS={}",
            log_pending_kinds.join(",")
        ),
    ];
    for evidence in &pending {
        let upper = evidence.kind.key().to_ascii_uppercase();
        let prior = durable_note_path(&implement_tmpdir, evidence.kind);
        let prior_value = if is_regular_file(&prior) && path_under(&prior, &implement_tmpdir) {
            prior.display().to_string()
        } else {
            String::new()
        };
        lines.push(format!(
            "ASSESSMENT_KIND_{upper}_DIFF_PATH={}",
            evidence.diff_path.display()
        ));
        lines.push(format!(
            "ASSESSMENT_KIND_{upper}_KNOWLEDGE_PATH={}",
            evidence.knowledge_path.display()
        ));
        lines.push(format!(
            "ASSESSMENT_KIND_{upper}_PRIOR_NOTE_PATH={prior_value}"
        ));
        lines.push(format!(
            "ASSESSMENT_KIND_{upper}_HEAD_SHA={}",
            evidence.head_sha
        ));
        lines.push(format!(
            "ASSESSMENT_KIND_{upper}_BASE_REF={}",
            evidence.base_ref
        ));
        lines.push(format!(
            "ASSESSMENT_KIND_{upper}_DIFF_FINGERPRINT={}",
            evidence.diff_fingerprint
        ));
    }
    print_lines(&lines);
    ExitCode::from(EXIT_OK)
}

/// Run `architectural-assessment submit`.
pub fn submit_command(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(
        arguments,
        &[
            "--kind",
            "--state",
            "--note-file",
            "--repo-root",
            "--implement-tmpdir",
        ],
        &["--allow-exception", "-h", "--help"],
        0,
    );
    if parsed.flag("-h") || parsed.flag("--help") {
        let help = format!(
            "{SUBMIT_USAGE}\n\noptional arguments:\n  -h, --help            show this help message and exit\n  --kind KIND\n  --state STATE\n  --note-file NOTE_FILE\n  --allow-exception     permit a deviation note carrying a documented-exception block (fix-ladder decline re-submission only)\n  --repo-root REPO_ROOT\n  --implement-tmpdir IMPLEMENT_TMPDIR\n"
        );
        return write_stdout(&help);
    }
    let parsed = match finish_parse(
        parsed,
        SUBMIT_USAGE,
        SUBMIT_PROGRAM,
        &["--kind", "--state", "--note-file"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let repo_root = option_or_env(&parsed, "--repo-root", "REPO");
    let implement_tmpdir = option_or_env(&parsed, "--implement-tmpdir", "IMPLEMENT_TMPDIR");
    if repo_root.is_empty() || implement_tmpdir.is_empty() {
        return submit_status(
            "usage-error",
            "repo root and implement tmpdir are required",
            EXIT_USAGE,
        );
    }
    let implement_tmpdir = PathBuf::from(implement_tmpdir);
    let kind = os_to_string(parsed.value("--kind").unwrap_or_default());
    let state = os_to_string(parsed.value("--state").unwrap_or_default());
    let note_file = PathBuf::from(os_to_string(
        parsed.value("--note-file").unwrap_or_default(),
    ));
    let allow_exception = parsed.flag("--allow-exception");
    let note = match normalize_kinds(&[kind.as_str()])
        .and_then(|_kinds| read_regular(&note_file, &implement_tmpdir))
    {
        Ok(note) => note,
        Err(error) => {
            return submit_status(
                "usage-error",
                &sanitize_detail(&error, &implement_tmpdir),
                EXIT_USAGE,
            );
        }
    };
    let git = LiveAssessmentGit::default();
    match submit(
        &kind,
        &state,
        &note,
        Path::new(&repo_root),
        &implement_tmpdir,
        allow_exception,
        &git,
    ) {
        Ok(result) => {
            print_complete(&result);
            ExitCode::from(EXIT_OK)
        }
        Err(SubmitError::HeadDrift(error)) => submit_status(
            "head-drift",
            &sanitize_detail(&error.0, &implement_tmpdir),
            u8::try_from(EXIT_HEAD_DRIFT).unwrap_or(10),
        ),
        Err(SubmitError::Reauthor(error)) => submit_status(
            "invalid-note",
            &sanitize_detail(&error.0, &implement_tmpdir),
            EXIT_INTERNAL,
        ),
        Err(SubmitError::LogPending(error)) => submit_status(
            "log-pending",
            &sanitize_detail(&error.0, &implement_tmpdir),
            EXIT_INTERNAL,
        ),
        Err(error) => submit_status(
            "failed",
            &sanitize_detail(&error.to_string(), &implement_tmpdir),
            EXIT_INTERNAL,
        ),
    }
}

fn print_complete(result: &AssessmentResult) {
    print_lines(&[
        "ASSESSMENT_STATUS=complete".to_owned(),
        format!("ASSESSMENT_KIND={}", result.kind.key()),
        format!("ASSESSMENT_STATE={}", result.state),
        format!("ASSESSMENT_RESULTS={}:{}", result.kind.key(), result.state),
        format!("ASSESSMENT_HEAD_SHA={}", result.head_sha),
        format!("ASSESSMENT_BASE_REF={}", result.base_ref),
        format!("ASSESSMENT_DIFF_FINGERPRINT={}", result.diff_fingerprint),
    ]);
}

/// Run `architectural-assessment sanitize-detail`.
pub fn sanitize_detail_command(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, &["--implement-tmpdir"], &["-h", "--help"], 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        let help = format!(
            "{SANITIZE_USAGE}\n\noptional arguments:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR\n"
        );
        return write_stdout(&help);
    }
    let parsed = match finish_parse(
        parsed,
        SANITIZE_USAGE,
        SANITIZE_PROGRAM,
        &["--implement-tmpdir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let implement_tmpdir = PathBuf::from(os_to_string(
        parsed.value("--implement-tmpdir").unwrap_or_default(),
    ));
    if !implement_tmpdir.is_dir()
        || implement_tmpdir
            .symlink_metadata()
            .is_ok_and(|meta| meta.file_type().is_symlink())
    {
        eprintln!("architectural-assessment sanitize-detail: invalid implement tmpdir");
        return ExitCode::from(EXIT_USAGE);
    }
    let mut buffer = vec![0_u8; MAX_SANITIZE_DETAIL_BYTES];
    let read = io::stdin().lock().read(&mut buffer).unwrap_or_default();
    buffer.truncate(read);
    let diagnostic = String::from_utf8_lossy(&buffer);
    println!("{}", sanitize_detail(&diagnostic, &implement_tmpdir));
    ExitCode::from(EXIT_OK)
}

/// Run `architectural-assessment final-report-sections`.
pub fn final_report_sections_command(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, &["--implement-tmpdir"], &["-h", "--help"], 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        let help = format!(
            "{FINAL_USAGE}\n\noptional arguments:\n  -h, --help            show this help message and exit\n  --implement-tmpdir IMPLEMENT_TMPDIR\n"
        );
        return write_stdout(&help);
    }
    let parsed = match finish_parse(parsed, FINAL_USAGE, FINAL_PROGRAM, &["--implement-tmpdir"]) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let implement_tmpdir = PathBuf::from(os_to_string(
        parsed.value("--implement-tmpdir").unwrap_or_default(),
    ));
    let head_sha = current_head_sha();
    let sections = final_report_sections(&implement_tmpdir, &head_sha);
    if io::stdout().lock().write_all(sections.as_bytes()).is_err() {
        return ExitCode::from(EXIT_INTERNAL);
    }
    ExitCode::from(EXIT_OK)
}

/// Render final-report architectural sections for an in-process caller.
///
/// Fail-soft: an unavailable HEAD or non-consumable note contributes nothing.
#[must_use]
pub fn architectural_sections_for_report(implement_tmpdir: &Path) -> String {
    final_report_sections(implement_tmpdir, &current_head_sha())
}
