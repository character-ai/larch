//! Rust command boundary for review context gathering.

use std::{
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Component, Path, PathBuf},
    process::ExitCode,
};

use clap::Subcommand;
use larch_adapters::{GixRepository, atomic_write_utf8_in, ensure_directory_chain};
use larch_core::{
    GitPath, RepositoryRead, StatusOptions, emit_kv,
    review::{
        GATHER_CONTEXT_USAGE, GatherContextArguments, GatherContextMode, GatherContextParse,
        description_path_matches, description_tokens, parse_gather_context_arguments,
        valid_relative_review_path,
    },
};

use crate::{agent_commands::AgentRawArguments, argparse_compat::absolute_path};

/// Review-domain commands now owned by Rust.
#[derive(Subcommand)]
pub enum ReviewCommand {
    /// Gather branch or description context for one review round.
    #[command(name = "gather-context", disable_help_flag = true)]
    #[allow(clippy::struct_field_names)]
    // raw compatibility arguments name the legacy boundary.
    GatherContext(AgentRawArguments),
}

/// Dispatch one Rust-owned review command.
pub fn run(command: ReviewCommand) -> ExitCode {
    match command {
        ReviewCommand::GatherContext(arguments) => gather_context(&arguments.arguments),
    }
}

fn gather_context(arguments: &[OsString]) -> ExitCode {
    let arguments = arguments
        .iter()
        .map(|argument| argument.to_string_lossy().into_owned())
        .collect::<Vec<_>>();
    match parse_gather_context_arguments(&arguments) {
        Ok(GatherContextParse::Help) => {
            eprintln!("{GATHER_CONTEXT_USAGE}");
            ExitCode::SUCCESS
        }
        Ok(GatherContextParse::Arguments(arguments)) => run_gather_context(&arguments),
        Err(error) => {
            eprint!("{}", error.prefix());
            if error.includes_usage() {
                eprintln!("{GATHER_CONTEXT_USAGE}");
            } else {
                eprintln!();
            }
            ExitCode::from(2)
        }
    }
}

fn run_gather_context(arguments: &GatherContextArguments) -> ExitCode {
    if let Err(error) = validate_output_arguments(arguments) {
        eprintln!("review gather-context: {error}");
        return ExitCode::from(1);
    }
    let output_dir = output_directory(&arguments.output_dir);
    let absolute_output = match absolute_path(&output_dir) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("review gather-context: cannot resolve output directory: {error}");
            return ExitCode::from(1);
        }
    };
    if let Err(error) = ensure_directory_chain(&absolute_output) {
        eprintln!("review gather-context: cannot create output directory: {error}");
        return ExitCode::from(1);
    }
    match arguments.mode {
        GatherContextMode::Diff => gather_diff_context(&output_dir),
        GatherContextMode::Description => gather_description_context(arguments, &output_dir),
    }
}

fn validate_output_arguments(arguments: &GatherContextArguments) -> Result<(), String> {
    for (name, value) in [
        ("--output-dir", arguments.output_dir.as_str()),
        ("--scope-files", arguments.scope_files.as_str()),
    ] {
        if value.contains(['\n', '\r']) {
            return Err(format!(
                "{name} must not contain a newline or carriage return"
            ));
        }
    }
    Ok(())
}

fn output_directory(value: &str) -> PathBuf {
    if value.is_empty() {
        PathBuf::from(".")
    } else {
        PathBuf::from(value)
    }
}

fn gather_diff_context(output_dir: &Path) -> ExitCode {
    let result = crate::agent_commands::gather_branch_context_for_review(output_dir);
    let rows = result
        .as_ref()
        .map_or_else(|_| Vec::new(), crate::agent_commands::branch_context_rows);
    if let Err(error) = write_rows(output_dir, &rows) {
        eprintln!("review gather-context: cannot write branch context: {error}");
        return ExitCode::from(1);
    }
    let exit_code = match &result {
        Ok(_) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("gather-branch-context.sh: {error}");
            ExitCode::from(1)
        }
    };
    for (key, value) in rows {
        emit_kv(&key, &value);
    }
    emit_kv("SCOPE_FILES_COUNT", "0");
    emit_kv("MODE", "diff");
    exit_code
}

fn gather_description_context(arguments: &GatherContextArguments, output_dir: &Path) -> ExitCode {
    let file_list = if arguments.scope_files.is_empty() {
        output_dir.join("scope-files.txt")
    } else {
        PathBuf::from(&arguments.scope_files)
    };
    let matches = description_scope_matches(&arguments.description_text).unwrap_or_default();
    let mut content = String::new();
    for path in &matches {
        writeln!(&mut content, "{path}").expect("writing to String cannot fail");
    }
    if let Err(error) = write_scope_file(&file_list, &content) {
        eprintln!("review gather-context: cannot write scope files: {error}");
        return ExitCode::from(1);
    }
    emit_kv("DIFF_FILE", "");
    emit_kv("FILE_LIST_FILE", &file_list.display().to_string());
    emit_kv("COMMIT_LOG_FILE", "");
    emit_kv("COMMIT_COUNT", "0");
    emit_kv("SCOPE_FILES_COUNT", &matches.len().to_string());
    emit_kv("MODE", "description");
    ExitCode::SUCCESS
}

fn description_scope_matches(description: &str) -> Result<Vec<String>, String> {
    let cwd = env::current_dir().map_err(|error| error.to_string())?;
    let repository = GixRepository::discover(cwd.as_path()).map_err(|error| error.to_string())?;
    let repository_root = repository
        .location()
        .work_dir
        .map(|path| PathBuf::from(String::from_utf8_lossy(path.as_bytes()).into_owned()))
        .ok_or_else(|| "repository has no working directory".to_owned())?;
    let tracked = repository
        .tracked_paths()
        .map_err(|error| error.to_string())?;
    let mut tracked_paths = paths_from_current_directory(&repository_root, &cwd, tracked);
    tracked_paths.sort();
    tracked_paths.dedup();
    let mut content_paths = tracked_paths.clone();
    if let Ok(status) = repository.local_status(&StatusOptions::default()) {
        content_paths.extend(paths_from_current_directory(
            &repository_root,
            &cwd,
            status.untracked,
        ));
    }
    content_paths.sort();
    content_paths.dedup();
    let tokens = description_tokens(description);
    let eligible = |path: &str| eligible_review_file(&cwd, path);
    let mut matches =
        description_path_matches(&tokens, tracked_paths.iter().map(String::as_str), eligible);
    // Preserve the legacy availability gate without adding an untyped `rg`
    // process path beside the in-process repository owner.
    if matches.is_empty() && !description.is_empty() && ripgrep_available() {
        let lowercase_description = description.to_lowercase();
        for path in &content_paths {
            if !eligible_review_file(&cwd, path) {
                continue;
            }
            let Ok(contents) = fs::read(cwd.join(path)) else {
                continue;
            };
            let text = String::from_utf8_lossy(&contents);
            if text.to_lowercase().contains(&lowercase_description) {
                matches.insert(path.clone());
            }
        }
    }
    Ok(matches.into_iter().collect())
}

fn ripgrep_available() -> bool {
    let executable = if cfg!(windows) { "rg.exe" } else { "rg" };
    env::var_os("PATH").is_some_and(|path| {
        env::split_paths(&path).any(|directory| {
            let candidate = directory.join(executable);
            candidate.is_file() && executable_file(&candidate)
        })
    })
}

#[cfg(unix)]
fn executable_file(path: &Path) -> bool {
    use std::os::unix::fs::PermissionsExt as _;

    fs::metadata(path).is_ok_and(|metadata| metadata.permissions().mode() & 0o111 != 0)
}

#[cfg(not(unix))]
fn executable_file(_path: &Path) -> bool {
    true
}

fn paths_from_current_directory(
    repository_root: &Path,
    cwd: &Path,
    paths: impl IntoIterator<Item = GitPath>,
) -> Vec<String> {
    paths
        .into_iter()
        .filter_map(|path| {
            let path = PathBuf::from(String::from_utf8_lossy(path.as_bytes()).into_owned());
            repository_root
                .join(path)
                .strip_prefix(cwd)
                .ok()
                .and_then(git_wire_path)
        })
        .collect()
}

fn git_wire_path(path: &Path) -> Option<String> {
    let mut parts = Vec::new();
    for component in path.components() {
        match component {
            Component::Normal(part) => parts.push(part.to_str()?.to_owned()),
            Component::CurDir => {}
            Component::ParentDir | Component::RootDir | Component::Prefix(_) => return None,
        }
    }
    (!parts.is_empty()).then(|| parts.join("/"))
}

fn eligible_review_file(cwd: &Path, path: &str) -> bool {
    if !valid_relative_review_path(path) {
        return false;
    }
    fs::symlink_metadata(cwd.join(path))
        .is_ok_and(|metadata| metadata.file_type().is_file() && !metadata.file_type().is_symlink())
}

fn write_scope_file(path: &Path, content: &str) -> Result<(), String> {
    let absolute = absolute_path(path).map_err(|error| error.to_string())?;
    let (root, target) = crate::launcher_support::confined_target(&absolute)
        .ok_or_else(|| "scope-files path is not a confinable file".to_owned())?;
    atomic_write_utf8_in(&root, &target, content, true, 0o600).map_err(|error| error.to_string())
}

fn write_rows(output_dir: &Path, rows: &[(String, String)]) -> Result<(), String> {
    if rows
        .iter()
        .any(|(key, value)| key.contains(['\n', '\r']) || value.contains(['\n', '\r']))
    {
        return Err("branch context contains a newline or carriage return".to_owned());
    }
    let absolute_output = absolute_path(output_dir).map_err(|error| error.to_string())?;
    let path = absolute_output.join("gather-branch-context.env");
    let (root, target) = crate::launcher_support::confined_target(&path)
        .ok_or_else(|| "branch-context path is not confinable".to_owned())?;
    let mut content = String::new();
    for (key, value) in rows {
        writeln!(&mut content, "{key}={value}").expect("writing to String cannot fail");
    }
    atomic_write_utf8_in(&root, &target, &content, true, 0o600).map_err(|error| error.to_string())
}
