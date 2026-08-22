//! Rust owner for architectural guideline and invariant runtime commands
//! (#8794, #8795).
//!
//! The two domains share argparse-compatible preparation and assessment-write
//! verbs. Core owns knowledge parsing, durable-state invalidation, diff and
//! note persistence, and compose materialization. This command layer owns
//! legacy argv and `KEY=value` stdout compatibility.

#![allow(clippy::too_many_lines)]

use std::{
    env,
    ffi::{OsStr, OsString},
    fmt::Write as _,
    fs,
    io::Read as _,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::GixRepository;
use larch_core::{
    ArchitecturalKind, ArchitecturalKnowledge, ArchitecturalStatus, AssessmentGit, AssessmentKind,
    AssessmentWriteError, ComposePreparation, RepositoryRead, append_deviation_note,
    diff_fingerprint, invalidate_implement_note, materialize_preparation_diff,
    persist_preparation_diff, pin_note_from_staged, prepare_compose, read_architectural_knowledge,
    untrusted_content_block, write_compose_assessment, write_staged_assessment,
};

use crate::{
    architectural_assessment_commands::LiveAssessmentGit,
    argparse_compat::{
        ParsedCommandLine, finish_parse, parse_with_flags, usage_error, write_stdout,
    },
};

const EXIT_OK: u8 = 0;
const EXIT_FAILED: u8 = 1;
const EXIT_USAGE: u8 = 2;
const EXIT_REAUTHOR_REQUIRED: u8 = 7;
const REAUTHOR_REQUIRED_STATUS: &str = "re-author-required";

const fn domain(kind: AssessmentKind) -> &'static str {
    match kind {
        AssessmentKind::Guidelines => "architectural-guidelines",
        AssessmentKind::Invariants => "architectural-invariants",
    }
}

const fn env_prefix(kind: AssessmentKind) -> &'static str {
    match kind {
        AssessmentKind::Guidelines => "ARCHITECTURAL_GUIDELINES",
        AssessmentKind::Invariants => "ARCHITECTURAL_INVARIANTS",
    }
}

const fn knowledge_kind(kind: AssessmentKind) -> ArchitecturalKind {
    match kind {
        AssessmentKind::Guidelines => ArchitecturalKind::Guidelines,
        AssessmentKind::Invariants => ArchitecturalKind::Invariants,
    }
}

const fn status_token(status: ArchitecturalStatus) -> &'static str {
    match status {
        ArchitecturalStatus::Present => "present",
        ArchitecturalStatus::Absent => "absent",
        ArchitecturalStatus::Invalid => "invalid",
    }
}

fn program(kind: AssessmentKind, verb: &str) -> String {
    format!("{} {verb}", domain(kind))
}

fn usage(kind: AssessmentKind, verb: &str) -> String {
    let command = program(kind, verb);
    let indent = " ".repeat(format!("usage: {command} ").len());
    match verb {
        "prepare-compose" => format!(
            "usage: {command} [-h] [--repo-root REPO_ROOT]\n\
             {indent}[--forked-target FORKED_TARGET]\n\
             {indent}[--implement-tmpdir IMPLEMENT_TMPDIR]\n\
             {indent}[--expected-head-sha EXPECTED_HEAD_SHA]"
        ),
        _ => format!(
            "usage: {command} [-h] [--repo-root REPO_ROOT]\n\
             {indent}[--forked-target FORKED_TARGET]\n\
             {indent}[--output OUTPUT]\n\
             {indent}[--implement-tmpdir IMPLEMENT_TMPDIR]"
        ),
    }
}

fn help(kind: AssessmentKind, verb: &str) -> String {
    let usage = usage(kind, verb);
    if verb == "prepare-compose" {
        format!(
            "{usage}\n\noptions:\n  -h, --help            show this help message and exit\n  --repo-root REPO_ROOT\n  --forked-target FORKED_TARGET\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --expected-head-sha EXPECTED_HEAD_SHA\n"
        )
    } else {
        format!(
            "{usage}\n\noptions:\n  -h, --help            show this help message and exit\n  --repo-root REPO_ROOT\n  --forked-target FORKED_TARGET\n  --output OUTPUT\n  --implement-tmpdir IMPLEMENT_TMPDIR\n"
        )
    }
}

fn parse(
    arguments: &[OsString],
    kind: AssessmentKind,
    verb: &str,
) -> Result<ParsedCommandLine, ExitCode> {
    let options: &[&str] = if verb == "prepare-compose" {
        &[
            "--repo-root",
            "--forked-target",
            "--implement-tmpdir",
            "--expected-head-sha",
        ]
    } else {
        &[
            "--repo-root",
            "--forked-target",
            "--output",
            "--implement-tmpdir",
        ]
    };
    let parsed = parse_with_flags(arguments, options, &["-h", "--help"], 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        return Err(write_stdout(&help(kind, verb)));
    }
    finish_parse(parsed, &usage(kind, verb), &program(kind, verb), &[])
}

fn option_text(parsed: &ParsedCommandLine, option: &str) -> String {
    parsed
        .value(option)
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default()
}

fn option_or_environment(parsed: &ParsedCommandLine, option: &str, variable: &str) -> String {
    parsed.value(option).map_or_else(
        || env::var(variable).unwrap_or_default(),
        |value| value.to_string_lossy().into_owned(),
    )
}

fn bool_arg(value: &str) -> bool {
    matches!(
        value.trim().to_ascii_lowercase().as_str(),
        "1" | "true" | "yes" | "on"
    )
}

fn assessment_usage(kind: AssessmentKind, verb: &str) -> String {
    let command = program(kind, verb);
    let indent = " ".repeat(format!("usage: {command} ").len());
    match verb {
        "write-compose-assessment" => format!(
            "usage: {command} [-h]\n\
             {indent}[--outcome OUTCOME]\n\
             {indent}[--implement-tmpdir IMPLEMENT_TMPDIR]\n\
             {indent}[--repo-root REPO_ROOT]\n\
             {indent}(--assessment-file ASSESSMENT_FILE | --assessment-text ASSESSMENT_TEXT)"
        ),
        "write-staged-assessment" => format!(
            "usage: {command} [-h]\n\
             {indent}[--outcome OUTCOME]\n\
             {indent}[--implement-tmpdir IMPLEMENT_TMPDIR]\n\
             {indent}(--assessment-file ASSESSMENT_FILE | --assessment-text ASSESSMENT_TEXT)\n\
             {indent}[--assessed-head-sha ASSESSED_HEAD_SHA]\n\
             {indent}[--diff-fingerprint DIFF_FINGERPRINT]\n\
             {indent}[--base-ref BASE_REF]\n\
             {indent}[--diff-file DIFF_FILE]"
        ),
        "append-deviation-note" => format!(
            "usage: {command} [-h]\n\
             {indent}[--implement-tmpdir IMPLEMENT_TMPDIR]\n\
             {indent}--note-file NOTE_FILE"
        ),
        "pin-note-from-staged" => format!(
            "usage: {command} [-h]\n\
             {indent}[--implement-tmpdir IMPLEMENT_TMPDIR]\n\
             {indent}[--head-sha HEAD_SHA]\n\
             {indent}[--base-ref BASE_REF]\n\
             {indent}[--repo-root REPO_ROOT]"
        ),
        "invalidate" => format!(
            "usage: {command} [-h]\n\
             {indent}[--implement-tmpdir IMPLEMENT_TMPDIR]"
        ),
        _ => unreachable!("known architectural assessment verb"),
    }
}

fn assessment_help(kind: AssessmentKind, verb: &str) -> String {
    let usage = assessment_usage(kind, verb);
    let options = match verb {
        "write-compose-assessment" => {
            "  --outcome OUTCOME\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --repo-root REPO_ROOT\n  --assessment-file ASSESSMENT_FILE\n  --assessment-text ASSESSMENT_TEXT\n"
        }
        "write-staged-assessment" => {
            "  --outcome OUTCOME\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --assessment-file ASSESSMENT_FILE\n  --assessment-text ASSESSMENT_TEXT\n  --assessed-head-sha ASSESSED_HEAD_SHA\n  --diff-fingerprint DIFF_FINGERPRINT\n  --base-ref BASE_REF\n  --diff-file DIFF_FILE\n"
        }
        "append-deviation-note" => {
            "  --implement-tmpdir IMPLEMENT_TMPDIR\n  --note-file NOTE_FILE\n"
        }
        "pin-note-from-staged" => {
            "  --implement-tmpdir IMPLEMENT_TMPDIR\n  --head-sha HEAD_SHA\n  --base-ref BASE_REF\n  --repo-root REPO_ROOT\n"
        }
        "invalidate" => "  --implement-tmpdir IMPLEMENT_TMPDIR\n",
        _ => unreachable!("known architectural assessment verb"),
    };
    format!(
        "{usage}\n\noptions:\n  -h, --help            show this help message and exit\n{options}"
    )
}

fn assessment_options(verb: &str) -> &'static [&'static str] {
    match verb {
        "write-compose-assessment" => &[
            "--outcome",
            "--implement-tmpdir",
            "--repo-root",
            "--assessment-file",
            "--assessment-text",
        ],
        "write-staged-assessment" => &[
            "--outcome",
            "--implement-tmpdir",
            "--assessment-file",
            "--assessment-text",
            "--assessed-head-sha",
            "--diff-fingerprint",
            "--base-ref",
            "--diff-file",
        ],
        "append-deviation-note" => &["--implement-tmpdir", "--note-file"],
        "pin-note-from-staged" => &[
            "--implement-tmpdir",
            "--head-sha",
            "--base-ref",
            "--repo-root",
        ],
        "invalidate" => &["--implement-tmpdir"],
        _ => unreachable!("known architectural assessment verb"),
    }
}

fn parse_assessment(
    arguments: &[OsString],
    kind: AssessmentKind,
    verb: &str,
) -> Result<ParsedCommandLine, ExitCode> {
    let usage = assessment_usage(kind, verb);
    let program = program(kind, verb);
    let parsed = parse_with_flags(arguments, assessment_options(verb), &["-h", "--help"], 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        return Err(write_stdout(&assessment_help(kind, verb)));
    }
    if let Some(error) = parsed.value_error() {
        return Err(usage_error(&usage, &program, error, EXIT_USAGE));
    }
    if matches!(verb, "write-compose-assessment" | "write-staged-assessment") {
        let file = parsed.value("--assessment-file").is_some();
        let text = parsed.value("--assessment-text").is_some();
        if file && text {
            let first = parsed
                .entries()
                .iter()
                .find(|(name, _)| matches!(*name, "--assessment-file" | "--assessment-text"))
                .map_or("--assessment-file", |(name, _)| *name);
            let second = if first == "--assessment-file" {
                "--assessment-text"
            } else {
                "--assessment-file"
            };
            return Err(usage_error(
                &usage,
                &program,
                &format!("argument {second}: not allowed with argument {first}"),
                EXIT_USAGE,
            ));
        }
        if !file && !text {
            return Err(usage_error(
                &usage,
                &program,
                "one of the arguments --assessment-file --assessment-text is required",
                EXIT_USAGE,
            ));
        }
    }
    let required = if verb == "append-deviation-note" {
        &["--note-file"][..]
    } else {
        &[]
    };
    finish_parse(parsed, &usage, &program, required)
}

fn current_head() -> String {
    let Some(root) = env::current_dir()
        .ok()
        .and_then(|cwd| discovered_root(&cwd))
    else {
        return String::new();
    };
    LiveAssessmentGit::default()
        .git_read(&root, &["rev-parse", "HEAD"])
        .unwrap_or_default()
}

fn read_regular_no_follow(path: &Path) -> Result<String, String> {
    let metadata = path
        .symlink_metadata()
        .map_err(|_| "assessment file must be a regular non-symlink file".to_owned())?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err("assessment file must be a regular non-symlink file".to_owned());
    }
    #[cfg(unix)]
    let mut file = {
        use std::os::unix::fs::OpenOptionsExt as _;

        fs::File::options()
            .read(true)
            .custom_flags(nix::libc::O_NOFOLLOW | nix::libc::O_NONBLOCK)
            .open(path)
    }
    .map_err(|error| error.to_string())?;
    #[cfg(not(unix))]
    let mut file = fs::File::open(path).map_err(|error| error.to_string())?;
    if !file
        .metadata()
        .is_ok_and(|opened_metadata| opened_metadata.is_file())
    {
        return Err("assessment file must be a regular file".to_owned());
    }
    let mut text = String::new();
    file.read_to_string(&mut text)
        .map_err(|error| error.to_string())?;
    Ok(text)
}

fn emit_action_status(
    kind: AssessmentKind,
    action: &str,
    status: &str,
    warning: &str,
    code: u8,
) -> ExitCode {
    let prefix = env_prefix(kind);
    let mut output = format!("{prefix}_{action}_STATUS={status}\n");
    if !warning.is_empty() {
        writeln!(output, "{prefix}_WARNING={}", flattened(warning))
            .expect("writing to a String cannot fail");
    }
    let write = write_stdout(&output);
    if write == ExitCode::SUCCESS {
        ExitCode::from(code)
    } else {
        write
    }
}

fn missing_tmpdir(kind: AssessmentKind, action: &str) -> ExitCode {
    emit_action_status(
        kind,
        action,
        "failed",
        "missing implement tmpdir",
        EXIT_USAGE,
    )
}

fn discovered_root(start: &Path) -> Option<PathBuf> {
    let repository = GixRepository::discover(start).ok()?;
    repository
        .location()
        .work_dir
        .map(|path| PathBuf::from(String::from_utf8_lossy(path.as_bytes()).into_owned()))
}

fn resolve_repo_root(explicit: Option<&OsStr>) -> Option<PathBuf> {
    if let Some(explicit) = explicit {
        let path = PathBuf::from(explicit);
        return fs::canonicalize(&path)
            .or_else(|_| std::path::absolute(path))
            .ok();
    }
    if let Ok(project) = env::var("CLAUDE_PROJECT_DIR") {
        let project = project.trim();
        if !project.is_empty()
            && let Some(root) = discovered_root(Path::new(project))
        {
            return Some(root);
        }
    }
    env::current_dir()
        .ok()
        .and_then(|cwd| discovered_root(&cwd))
}

fn read_knowledge(repo_root: Option<&Path>, kind: AssessmentKind) -> ArchitecturalKnowledge {
    repo_root.map_or_else(ArchitecturalKnowledge::absent, |root| {
        read_architectural_knowledge(root, knowledge_kind(kind))
    })
}

fn append_knowledge(
    output: &mut String,
    repo_root: Option<&Path>,
    kind: AssessmentKind,
) -> ArchitecturalKnowledge {
    let knowledge = read_knowledge(repo_root, kind);
    let prefix = env_prefix(kind);
    writeln!(output, "{prefix}_STATUS={}", status_token(knowledge.status))
        .expect("writing to a String cannot fail");
    match knowledge.status {
        ArchitecturalStatus::Present => {
            if let Some(root) = repo_root {
                writeln!(
                    output,
                    "{prefix}_PATH={}",
                    root.join(kind.knowledge_filename()).display()
                )
                .expect("writing to a String cannot fail");
            }
            if !knowledge.content.is_empty() {
                output.push_str(&untrusted_content_block(
                    knowledge_kind(kind).tag(),
                    &knowledge.content,
                ));
            }
        }
        ArchitecturalStatus::Invalid => {
            writeln!(output, "{prefix}_WARNING={}", knowledge.warning)
                .expect("writing to a String cannot fail");
        }
        ArchitecturalStatus::Absent => {}
    }
    knowledge
}

fn flattened(value: &str) -> String {
    value.replace(['\n', '\r'], " ")
}

fn diff_output(
    repo_root: &Path,
    forked_target: bool,
    output_path: &str,
    implement_tmpdir: &str,
    kind: AssessmentKind,
) -> (u8, String) {
    let prefix = env_prefix(kind);
    let git = if forked_target {
        LiveAssessmentGit::for_base_remote("upstream")
    } else {
        LiveAssessmentGit::default()
    };
    let prepared = match materialize_preparation_diff(repo_root, &git) {
        Ok(prepared) => prepared,
        Err(error) => {
            return (
                EXIT_FAILED,
                format!(
                    "{prefix}_DIFF_STATUS=failed\n{prefix}_WARNING={}\n",
                    flattened(&error)
                ),
            );
        }
    };
    let output = (!output_path.is_empty()).then(|| Path::new(output_path));
    let tmpdir = (!implement_tmpdir.is_empty()).then(|| Path::new(implement_tmpdir));
    if let Err(error) = persist_preparation_diff(kind, &prepared, output, tmpdir) {
        return (
            EXIT_FAILED,
            format!(
                "{prefix}_DIFF_STATUS=failed\n{prefix}_WARNING={}\n",
                flattened(&error)
            ),
        );
    }
    let mut rendered = format!(
        "{prefix}_DIFF_STATUS=ok\n{prefix}_BASE_REF={}\n{prefix}_DIFF_FINGERPRINT={}\n",
        prepared.base_ref, prepared.fingerprint
    );
    rendered.push_str(&untrusted_content_block(
        &format!("architectural_{}_diff", kind.key()),
        &prepared.text,
    ));
    (EXIT_OK, rendered)
}

/// Run `architectural-{guidelines,invariants} materialize-diff`.
pub fn materialize_diff_command(kind: AssessmentKind, arguments: &[OsString]) -> ExitCode {
    let parsed = match parse(arguments, kind, "materialize-diff") {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let Some(repo_root) = resolve_repo_root(parsed.value("--repo-root")) else {
        return write_stdout(&format!("{}_DIFF_STATUS=absent\n", env_prefix(kind)));
    };
    let forked = bool_arg(&option_text(&parsed, "--forked-target"));
    let output = option_text(&parsed, "--output");
    let tmpdir = option_or_environment(&parsed, "--implement-tmpdir", "IMPLEMENT_TMPDIR");
    let (code, rendered) = diff_output(&repo_root, forked, &output, &tmpdir, kind);
    let write = write_stdout(&rendered);
    if write == ExitCode::SUCCESS {
        ExitCode::from(code)
    } else {
        write
    }
}

/// Run `architectural-{guidelines,invariants} prepare`.
pub fn prepare_command(kind: AssessmentKind, arguments: &[OsString]) -> ExitCode {
    let parsed = match parse(arguments, kind, "prepare") {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let prefix = env_prefix(kind);
    let tmpdir = option_or_environment(&parsed, "--implement-tmpdir", "IMPLEMENT_TMPDIR");
    if !tmpdir.is_empty()
        && let Err(error) = invalidate_implement_note(Path::new(&tmpdir), kind)
    {
        let write = write_stdout(&format!(
            "{prefix}_INVALIDATE_STATUS=failed\n{prefix}_WARNING={error}\n"
        ));
        return if write == ExitCode::SUCCESS {
            ExitCode::from(EXIT_USAGE)
        } else {
            write
        };
    }
    let repo_root = resolve_repo_root(parsed.value("--repo-root"));
    let mut rendered = String::new();
    let knowledge = append_knowledge(&mut rendered, repo_root.as_deref(), kind);
    if knowledge.status != ArchitecturalStatus::Present
        || (kind.is_invariant() && knowledge.content.trim().is_empty())
    {
        return write_stdout(&rendered);
    }
    let forked = bool_arg(&option_text(&parsed, "--forked-target"));
    let output = option_text(&parsed, "--output");
    let (code, diff) = diff_output(
        repo_root.as_deref().expect("present knowledge has a root"),
        forked,
        &output,
        &tmpdir,
        kind,
    );
    rendered.push_str(&diff);
    let write = write_stdout(&rendered);
    if write == ExitCode::SUCCESS {
        ExitCode::from(code)
    } else {
        write
    }
}

fn append_compose_result(
    output: &mut String,
    result: &ComposePreparation,
    repo_root: Option<&Path>,
    implement_tmpdir: &Path,
    kind: AssessmentKind,
) {
    let prefix = env_prefix(kind);
    writeln!(output, "{prefix}_COMPOSE_STATUS={}", result.status)
        .expect("writing to a String cannot fail");
    let diff_path = result
        .diff_path
        .as_ref()
        .map(|path| path.to_string_lossy().into_owned())
        .unwrap_or_default();
    for (key, value) in [
        ("HEAD_SHA", result.head_sha.as_str()),
        ("BASE_REF", result.base_ref.as_str()),
        ("DIFF_FINGERPRINT", result.diff_fingerprint.as_str()),
        ("DIFF_PATH", diff_path.as_str()),
        ("WARNING", result.warning.as_str()),
    ] {
        if !value.is_empty() {
            writeln!(output, "{prefix}_{key}={value}").expect("writing to a String cannot fail");
        }
    }
    let knowledge = append_knowledge(output, repo_root, kind);
    if knowledge.status != ArchitecturalStatus::Present {
        return;
    }
    let fallback = implement_tmpdir.join(kind.materialized_diff_filename());
    let diff_path = result.diff_path.as_deref().unwrap_or(&fallback);
    let Ok(metadata) = diff_path.symlink_metadata() else {
        return;
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return;
    }
    let Ok(bytes) = fs::read(diff_path) else {
        return;
    };
    let diff = String::from_utf8_lossy(&bytes);
    if !diff.is_empty() {
        output.push_str(&untrusted_content_block(
            &format!("architectural_{}_diff", kind.key()),
            &diff,
        ));
    }
}

/// Run `architectural-{guidelines,invariants} prepare-compose`.
pub fn prepare_compose_command(kind: AssessmentKind, arguments: &[OsString]) -> ExitCode {
    let parsed = match parse(arguments, kind, "prepare-compose") {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let prefix = env_prefix(kind);
    let tmpdir = option_or_environment(&parsed, "--implement-tmpdir", "IMPLEMENT_TMPDIR");
    if tmpdir.is_empty() {
        let write = write_stdout(&format!(
            "{prefix}_COMPOSE_STATUS=failed\n{prefix}_WARNING=missing implement tmpdir\n"
        ));
        return if write == ExitCode::SUCCESS {
            ExitCode::from(EXIT_USAGE)
        } else {
            write
        };
    }
    let repo_root = resolve_repo_root(parsed.value("--repo-root"));
    let forked = bool_arg(&option_text(&parsed, "--forked-target"));
    let expected_head = option_text(&parsed, "--expected-head-sha");
    let git = if forked {
        LiveAssessmentGit::for_base_remote("upstream")
    } else {
        LiveAssessmentGit::default()
    };
    let tmpdir = PathBuf::from(tmpdir);
    let result = prepare_compose(kind, &tmpdir, repo_root.as_deref(), &expected_head, &git)
        .unwrap_or_else(|error| ComposePreparation {
            status: "failed".to_owned(),
            warning: flattened(&error),
            ..ComposePreparation::default()
        });
    let mut rendered = String::new();
    append_compose_result(&mut rendered, &result, repo_root.as_deref(), &tmpdir, kind);
    let write = write_stdout(&rendered);
    if write != ExitCode::SUCCESS {
        return write;
    }
    ExitCode::from(if result.status == "failed" {
        EXIT_FAILED
    } else {
        EXIT_OK
    })
}

/// Run `architectural-{guidelines,invariants} write-compose-assessment`.
pub fn write_compose_assessment_command(kind: AssessmentKind, arguments: &[OsString]) -> ExitCode {
    let verb = "write-compose-assessment";
    let parsed = match parse_assessment(arguments, kind, verb) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = option_or_environment(&parsed, "--implement-tmpdir", "IMPLEMENT_TMPDIR");
    if tmpdir.is_empty() {
        return missing_tmpdir(kind, "WRITE");
    }
    let tmpdir = PathBuf::from(tmpdir);
    let assessment_file = option_text(&parsed, "--assessment-file");
    let assessment_text = if assessment_file.is_empty() {
        option_text(&parsed, "--assessment-text")
    } else {
        let path = PathBuf::from(assessment_file);
        let path = if path.is_absolute() {
            path
        } else {
            tmpdir.join(path)
        };
        match read_regular_no_follow(&path) {
            Ok(text) => text,
            Err(error) => {
                return emit_action_status(kind, "WRITE", "failed", &error, EXIT_FAILED);
            }
        }
    };
    let repo_root = resolve_repo_root(parsed.value("--repo-root"))
        .or_else(|| env::current_dir().ok())
        .unwrap_or_else(|| PathBuf::from("."));
    let git = LiveAssessmentGit::default();
    match write_compose_assessment(
        &tmpdir,
        &assessment_text,
        &option_text(&parsed, "--outcome"),
        kind,
        &repo_root,
        &git,
    ) {
        Ok(()) => emit_action_status(kind, "WRITE", "ok", "", EXIT_OK),
        Err(AssessmentWriteError::Reauthor(reason)) => emit_action_status(
            kind,
            "WRITE",
            REAUTHOR_REQUIRED_STATUS,
            &reason,
            EXIT_REAUTHOR_REQUIRED,
        ),
        Err(AssessmentWriteError::Other(error)) => {
            emit_action_status(kind, "WRITE", "failed", &error, EXIT_FAILED)
        }
    }
}

/// Run `architectural-{guidelines,invariants} write-staged-assessment`.
pub fn write_staged_assessment_command(kind: AssessmentKind, arguments: &[OsString]) -> ExitCode {
    let verb = "write-staged-assessment";
    let parsed = match parse_assessment(arguments, kind, verb) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = option_or_environment(&parsed, "--implement-tmpdir", "IMPLEMENT_TMPDIR");
    if tmpdir.is_empty() {
        return missing_tmpdir(kind, "WRITE");
    }
    let assessment_file = option_text(&parsed, "--assessment-file");
    let assessment_text = if assessment_file.is_empty() {
        option_text(&parsed, "--assessment-text")
    } else {
        match fs::read_to_string(&assessment_file) {
            Ok(text) => text,
            Err(error) => {
                return emit_action_status(
                    kind,
                    "WRITE",
                    "failed",
                    &error.to_string(),
                    EXIT_FAILED,
                );
            }
        }
    };
    let diff_file = option_text(&parsed, "--diff-file");
    let diff_text = if diff_file.is_empty() {
        String::new()
    } else {
        let path = Path::new(&diff_file);
        let valid = path
            .symlink_metadata()
            .is_ok_and(|metadata| metadata.is_file() && !metadata.file_type().is_symlink());
        if !valid {
            return emit_action_status(kind, "WRITE", "failed", "missing diff file", EXIT_FAILED);
        }
        match fs::read(path) {
            Ok(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
            Err(error) => {
                return emit_action_status(
                    kind,
                    "WRITE",
                    "failed",
                    &format!("unreadable diff file ({error})"),
                    EXIT_FAILED,
                );
            }
        }
    };
    let fingerprint = {
        let supplied = option_text(&parsed, "--diff-fingerprint");
        if supplied.is_empty() {
            diff_fingerprint(&diff_text)
        } else {
            supplied
        }
    };
    let head = {
        let supplied = option_text(&parsed, "--assessed-head-sha");
        if supplied.is_empty() {
            current_head()
        } else {
            supplied
        }
    };
    match write_staged_assessment(
        Path::new(&tmpdir),
        &assessment_text,
        &head,
        &fingerprint,
        &option_text(&parsed, "--base-ref"),
        &option_text(&parsed, "--outcome"),
        kind,
        &diff_text,
    ) {
        Ok(()) => emit_action_status(kind, "WRITE", "ok", "", EXIT_OK),
        Err(AssessmentWriteError::Reauthor(reason)) => emit_action_status(
            kind,
            "WRITE",
            REAUTHOR_REQUIRED_STATUS,
            &reason,
            EXIT_REAUTHOR_REQUIRED,
        ),
        Err(AssessmentWriteError::Other(error)) => {
            emit_action_status(kind, "WRITE", "failed", &error, EXIT_FAILED)
        }
    }
}

/// Run `architectural-{guidelines,invariants} append-deviation-note`.
pub fn append_deviation_note_command(kind: AssessmentKind, arguments: &[OsString]) -> ExitCode {
    let verb = "append-deviation-note";
    let parsed = match parse_assessment(arguments, kind, verb) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = option_or_environment(&parsed, "--implement-tmpdir", "IMPLEMENT_TMPDIR");
    if tmpdir.is_empty() {
        return missing_tmpdir(kind, "APPEND");
    }
    let note_file = PathBuf::from(option_text(&parsed, "--note-file"));
    let note = match read_regular_no_follow(&note_file) {
        Ok(note) => note,
        Err(error) => {
            return emit_action_status(kind, "APPEND", "failed", &error, EXIT_FAILED);
        }
    };
    if note.lines().all(|line| line.trim().is_empty()) {
        return emit_action_status(
            kind,
            "APPEND",
            "failed",
            "note-file: content must not be empty",
            EXIT_FAILED,
        );
    }
    let status = append_deviation_note(Path::new(&tmpdir), &note);
    emit_action_status(
        kind,
        "APPEND",
        status,
        "",
        if status == "failed" {
            EXIT_FAILED
        } else {
            EXIT_OK
        },
    )
}

/// Run `architectural-{guidelines,invariants} pin-note-from-staged`.
pub fn pin_note_from_staged_command(kind: AssessmentKind, arguments: &[OsString]) -> ExitCode {
    let verb = "pin-note-from-staged";
    let parsed = match parse_assessment(arguments, kind, verb) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = option_or_environment(&parsed, "--implement-tmpdir", "IMPLEMENT_TMPDIR");
    if tmpdir.is_empty() {
        return missing_tmpdir(kind, "PIN");
    }
    let head = {
        let supplied = option_text(&parsed, "--head-sha");
        if supplied.is_empty() {
            current_head()
        } else {
            supplied
        }
    };
    let repo_root = parsed
        .value("--repo-root")
        .and_then(|root| resolve_repo_root(Some(root)));
    let git = LiveAssessmentGit::default();
    let result = pin_note_from_staged(
        Path::new(&tmpdir),
        &head,
        &option_text(&parsed, "--base-ref"),
        kind,
        repo_root.as_deref(),
        repo_root.as_ref().map(|_| &git as &dyn AssessmentGit),
    );
    if !result.warning.is_empty() {
        eprintln!(
            "ARCHITECTURAL_GUIDELINES_WARNING={}",
            flattened(&result.warning)
        );
    }
    emit_action_status(
        kind,
        "PIN",
        if result.pinned { "ok" } else { "skipped" },
        "",
        EXIT_OK,
    )
}

/// Run `architectural-{guidelines,invariants} invalidate`.
pub fn invalidate_command(kind: AssessmentKind, arguments: &[OsString]) -> ExitCode {
    let verb = "invalidate";
    let parsed = match parse_assessment(arguments, kind, verb) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tmpdir = option_or_environment(&parsed, "--implement-tmpdir", "IMPLEMENT_TMPDIR");
    if tmpdir.is_empty() {
        return missing_tmpdir(kind, "INVALIDATE");
    }
    match invalidate_implement_note(Path::new(&tmpdir), kind) {
        Ok(()) => emit_action_status(kind, "INVALIDATE", "ok", "", EXIT_OK),
        Err(error) => emit_action_status(kind, "INVALIDATE", "failed", &error, EXIT_USAGE),
    }
}
