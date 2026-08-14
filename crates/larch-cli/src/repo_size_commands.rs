//! `repo size` composition over the typed repository-read owner.

use std::{
    env, fs,
    io::Write as _,
    path::{Component, Path, PathBuf},
    process::ExitCode,
};

#[cfg(unix)]
use std::ffi::OsString;

use clap::Subcommand;
use larch_adapters::{GixRepository, RepositoryRoot};
use larch_core::{
    GitPath, RepoSizeReport, RepositoryRead, count_newlines, is_rust_line_count_path,
    line_count_category, rust_line_split,
};

/// Repository-scoped developer commands.
#[derive(Clone, Copy, Subcommand)]
pub enum RepoCommand {
    /// Report tracked source lines and run-log byte totals.
    Size,
}

/// Dispatch one repository developer command.
pub fn run(command: RepoCommand) -> ExitCode {
    match command {
        RepoCommand::Size => match render_size() {
            Ok(report) => {
                let mut stdout = std::io::stdout().lock();
                if let Err(error) = stdout.write_all(report.as_bytes()) {
                    eprintln!("repo size: cannot write output: {error}");
                    return ExitCode::FAILURE;
                }
                if let Err(error) = stdout.write_all(b"\n") {
                    eprintln!("repo size: cannot write output: {error}");
                    return ExitCode::FAILURE;
                }
                ExitCode::SUCCESS
            }
            Err(error) => {
                eprintln!("{error}");
                ExitCode::FAILURE
            }
        },
    }
}

fn render_size() -> Result<String, String> {
    let (root, repository) = open_repository()?;
    let tracked_paths = repository
        .tracked_paths()
        .map_err(|_| "repo size: cannot read git index".to_owned())?;
    let mut report = RepoSizeReport::default();

    for path in &tracked_paths {
        let path_bytes = path.as_bytes();
        let category = line_count_category(path_bytes);
        if category.is_none() && !is_rust_line_count_path(path_bytes) {
            continue;
        }
        let content = fs::read(path_at_root(root.path(), path)?).map_err(|_| display_path(path))?;
        if let Some(category) = category {
            report.add_line_count(category, count_newlines(&content));
        } else {
            let (code_lines, test_lines) = rust_line_split(path_bytes, &content);
            report.add_rust_line_split(code_lines, test_lines);
        }
    }
    for path in &tracked_paths {
        let metadata =
            fs::metadata(path_at_root(root.path(), path)?).map_err(|_| display_path(path))?;
        report.add_size(path.as_bytes(), metadata.len());
    }
    Ok(report.render())
}

fn open_repository() -> Result<(RepositoryRoot, GixRepository), String> {
    let current = env::current_dir()
        .map_err(|error| format!("repo size: cannot resolve current directory: {error}"))?;
    let repository = GixRepository::discover(&current)
        .map_err(|_| "repo size: not inside a git work tree".to_owned())?;
    let work_dir = repository
        .location()
        .work_dir
        .ok_or_else(|| "repo size: not inside a git work tree".to_owned())?;
    let work_dir = path_from_git_bytes(work_dir.as_bytes())?;
    let root = RepositoryRoot::resolve(Some(&work_dir))
        .map_err(|_| "repo size: not inside a git work tree".to_owned())?;
    Ok((root, repository))
}

fn path_at_root(root: &Path, path: &GitPath) -> Result<PathBuf, String> {
    let relative = path_from_git_bytes(path.as_bytes())?;
    if relative.as_os_str().is_empty()
        || relative.is_absolute()
        || relative.components().any(|component| {
            matches!(
                component,
                Component::CurDir
                    | Component::ParentDir
                    | Component::RootDir
                    | Component::Prefix(_)
            )
        })
    {
        return Err("repo size: git index contains an unsafe path".to_owned());
    }
    Ok(root.join(relative))
}

#[cfg(unix)]
fn path_from_git_bytes(bytes: &[u8]) -> Result<PathBuf, String> {
    use std::os::unix::ffi::OsStringExt as _;

    if bytes.contains(&0) {
        return Err("repo size: git index contains an unsafe path".to_owned());
    }
    Ok(PathBuf::from(OsString::from_vec(bytes.to_vec())))
}

#[cfg(not(unix))]
fn path_from_git_bytes(bytes: &[u8]) -> Result<PathBuf, String> {
    let text = std::str::from_utf8(bytes)
        .map_err(|_| "repo size: git index path is not valid UTF-8".to_owned())?;
    Ok(PathBuf::from(text))
}

fn display_path(path: &GitPath) -> String {
    String::from_utf8_lossy(path.as_bytes()).into_owned()
}
