//! Rust owner for architectural guideline and invariant preparation (#8794).
//!
//! The two domains share three argparse-compatible verbs: `materialize-diff`,
//! `prepare`, and `prepare-compose`. Core owns knowledge parsing, durable-state
//! invalidation, diff persistence, and compose materialization. This command
//! layer owns legacy argv and `KEY=value` stdout compatibility.

#![allow(clippy::too_many_lines)]

use std::{
    env,
    ffi::{OsStr, OsString},
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::GixRepository;
use larch_core::{
    ArchitecturalKind, ArchitecturalKnowledge, ArchitecturalStatus, AssessmentKind,
    ComposePreparation, RepositoryRead, invalidate_implement_note, materialize_preparation_diff,
    persist_preparation_diff, prepare_compose, read_architectural_knowledge,
    untrusted_content_block,
};

use crate::{
    architectural_assessment_commands::LiveAssessmentGit,
    argparse_compat::{ParsedCommandLine, finish_parse, parse_with_flags, write_stdout},
};

const EXIT_OK: u8 = 0;
const EXIT_FAILED: u8 = 1;
const EXIT_USAGE: u8 = 2;

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
