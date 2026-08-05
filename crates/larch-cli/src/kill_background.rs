//! `session kill-background-processes` command boundary.

use larch_adapters::SystemProcessIdentityHost;
use larch_core::{cleanup_cache_sessions_root, kill_session_background_processes};
use std::{
    env,
    ffi::{OsStr, OsString},
    fs,
    io::Write as _,
    path::{Component, Path, PathBuf},
    process::ExitCode,
};

/// Run the Rust-owned `session kill-background-processes` command.
pub fn kill_background_processes(arguments: &[OsString]) -> ExitCode {
    match parse_arguments(arguments) {
        ParseOutcome::Help => {
            println!(
                "Usage: session kill-background-processes (--design-tmpdir PATH | --implement-tmpdir PATH)"
            );
            ExitCode::SUCCESS
        }
        ParseOutcome::Error(message) => error(&message),
        ParseOutcome::Ok { kind, value } => {
            let resolved = match validate_kill_tmpdir_path(&value, kind) {
                Ok(path) => path,
                Err(message) => return error(&message),
            };
            if kind == TmpdirKind::Design {
                if !resolved
                    .file_name()
                    .and_then(OsStr::to_str)
                    .is_some_and(|name| name.starts_with("claude-design-"))
                {
                    return error("design-tmpdir basename must start with claude-design-");
                }
                let marker = resolved.join("source-env.sh");
                match fs::symlink_metadata(&marker) {
                    Ok(metadata) if metadata.is_file() && !metadata.file_type().is_symlink() => {}
                    _ => return error("design-tmpdir missing regular source-env.sh marker"),
                }
            }
            let host = SystemProcessIdentityHost::new();
            let killed = kill_session_background_processes(&host, &resolved.display().to_string());
            if writeln!(
                std::io::stdout(),
                "KILLED={}",
                if killed { "true" } else { "false" }
            )
            .is_err()
            {
                return ExitCode::FAILURE;
            }
            ExitCode::SUCCESS
        }
    }
}

#[derive(Clone, Copy, Eq, PartialEq)]
enum TmpdirKind {
    Design,
    Implement,
}

enum ParseOutcome {
    Help,
    Error(String),
    Ok { kind: TmpdirKind, value: String },
}

fn parse_arguments(arguments: &[OsString]) -> ParseOutcome {
    let mut design_tmpdir = String::new();
    let mut implement_tmpdir = String::new();
    let mut index = 0;
    while index < arguments.len() {
        let Some(arg) = arguments[index].to_str() else {
            return ParseOutcome::Error(format!(
                "unknown argument: {}",
                arguments[index].to_string_lossy()
            ));
        };
        match arg {
            "--design-tmpdir" => {
                index += 1;
                let Some(value) = arguments.get(index).and_then(|value| value.to_str()) else {
                    return ParseOutcome::Error("--design-tmpdir requires a value".to_owned());
                };
                value.clone_into(&mut design_tmpdir);
            }
            "--implement-tmpdir" => {
                index += 1;
                let Some(value) = arguments.get(index).and_then(|value| value.to_str()) else {
                    return ParseOutcome::Error("--implement-tmpdir requires a value".to_owned());
                };
                value.clone_into(&mut implement_tmpdir);
            }
            "-h" | "--help" => return ParseOutcome::Help,
            other => return ParseOutcome::Error(format!("unknown argument: {other}")),
        }
        index += 1;
    }
    if !design_tmpdir.is_empty() && !implement_tmpdir.is_empty() {
        return ParseOutcome::Error(
            "pass only one of --design-tmpdir or --implement-tmpdir".to_owned(),
        );
    }
    if !implement_tmpdir.is_empty() {
        return ParseOutcome::Ok {
            kind: TmpdirKind::Implement,
            value: implement_tmpdir,
        };
    }
    ParseOutcome::Ok {
        kind: TmpdirKind::Design,
        value: design_tmpdir,
    }
}

fn validate_kill_tmpdir_path(raw: &str, kind: TmpdirKind) -> Result<PathBuf, String> {
    let label = match kind {
        TmpdirKind::Design => "design-tmpdir",
        TmpdirKind::Implement => "implement-tmpdir",
    };
    if raw.is_empty() {
        return Err(format!("--{label} is required"));
    }
    if raw.contains('\n') || raw.contains('\r') {
        return Err(format!(
            "{label}: path must not contain newline or carriage return"
        ));
    }
    let path = PathBuf::from(raw);
    if !path.is_absolute() {
        return Err(format!("--{label} must be an absolute path"));
    }
    if path
        .components()
        .any(|component| matches!(component, Component::ParentDir))
    {
        return Err(format!("--{label} must not contain '..' segments"));
    }
    validate_design_tmpdir_allowlist(raw, label)?;
    match fs::symlink_metadata(&path) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            return Err(format!("{label} must not be a symlink"));
        }
        Ok(metadata) if metadata.is_dir() => {}
        Ok(_) => return Err(format!("{label} must be a directory")),
        Err(_) => return Err(format!("{label} must exist and be a directory")),
    }
    let resolved = path
        .canonicalize()
        .map_err(|_| format!("{label} resolution failed"))?;
    if !resolved.is_dir() {
        return Err(format!("{label} must exist and be a directory"));
    }
    Ok(resolved)
}

fn validate_design_tmpdir_allowlist(candidate: &str, label: &str) -> Result<(), String> {
    if candidate.contains('\n') || candidate.contains('\r') {
        return Err(format!(
            "{label}: path must not contain newline or carriage return"
        ));
    }
    if !candidate.starts_with('/') {
        return Err(format!("Invalid --{label}: must be an absolute path"));
    }
    let segments = candidate
        .split('/')
        .filter(|segment| !segment.is_empty())
        .collect::<Vec<_>>();
    if segments
        .iter()
        .any(|segment| *segment == "." || *segment == "..")
    {
        return Err(format!(
            "{label}: path must not contain '.' or '..' segments"
        ));
    }
    let path = Path::new(candidate);
    let resolved = if path.exists() {
        if path
            .symlink_metadata()
            .is_ok_and(|metadata| metadata.file_type().is_symlink())
            && !path.is_dir()
        {
            return Err(format!("{label}: leaf symlink must resolve to a directory"));
        }
        if !path.is_dir() {
            return Err(format!("{label}: path must name a directory"));
        }
        path.canonicalize().map_err(|_| {
            if path
                .symlink_metadata()
                .is_ok_and(|metadata| metadata.file_type().is_symlink())
            {
                format!("{label}: leaf symlink must resolve to a directory")
            } else {
                format!("{label}: parent resolution failed")
            }
        })?
    } else {
        let (ancestor, tail) = split_ancestor_tail(candidate);
        let resolved_ancestor = Path::new(&ancestor)
            .canonicalize()
            .map_err(|_| format!("{label}: parent resolution failed"))?;
        if tail.is_empty() {
            resolved_ancestor
        } else {
            resolved_ancestor.join(tail)
        }
    };
    let allow = [
        canonical_prefix(&cleanup_cache_sessions_root(
            env::var_os("XDG_CACHE_HOME").as_deref(),
            env::var_os("HOME").as_deref(),
        )),
        env::var_os("TMPDIR")
            .map(|value| canonical_prefix(Path::new(&value)))
            .unwrap_or_default(),
        canonical_prefix(Path::new("/tmp")),
    ];
    let resolved_cmp = format!("{}/", resolved.display().to_string().trim_end_matches('/'));
    if !allow
        .iter()
        .any(|prefix| !prefix.is_empty() && resolved_cmp.starts_with(prefix))
    {
        return Err(format!(
            "{label}: path not under allowlist after resolution: {}",
            resolved.display()
        ));
    }
    Ok(())
}

fn split_ancestor_tail(candidate: &str) -> (String, String) {
    let path = Path::new(candidate);
    match path.parent() {
        Some(parent) if !parent.as_os_str().is_empty() => (
            parent.display().to_string(),
            path.file_name()
                .map(|name| name.to_string_lossy().into_owned())
                .unwrap_or_default(),
        ),
        _ => (candidate.to_owned(), String::new()),
    }
}

fn canonical_prefix(path: &Path) -> String {
    let resolved = path.canonicalize().unwrap_or_else(|_| path.to_path_buf());
    format!("{}/", resolved.display().to_string().trim_end_matches('/'))
}

fn error(message: &str) -> ExitCode {
    let _ = writeln!(std::io::stderr(), "ERROR={message}");
    ExitCode::from(2)
}
