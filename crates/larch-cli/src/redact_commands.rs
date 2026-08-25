//! Rust-owned redaction command boundaries.

use crate::argparse_compat::{absolute_path, python_io_error, read_stdin, write_stdout};
use larch_adapters::{
    FileIoErrorKind, GitCli, GitCliPolicy, GitPath as GitCliPath, GitToken, PathIntent,
    RepositoryRoot, SubmoduleRequest, TemporaryRoot, TokioProcessRunner, atomic_write_utf8_in,
    ensure_directory_chain, read_utf8, read_utf8_lossy,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    ParseOptions, WhitespacePolicy, parse_single_kv_row, redact_secrets, redact_secrets_only,
    redact_secrets_streaming, redact_sensitive_paths, scrub_submodule_findings,
};
use std::{
    collections::BTreeSet,
    env,
    ffi::{OsStr, OsString},
    fs, io,
    os::unix::{
        ffi::{OsStrExt as _, OsStringExt as _},
        fs::PermissionsExt as _,
    },
    path::{Path, PathBuf},
    process::ExitCode,
};

const STREAMING_PEM_WARNING: &str = "WARN: redact secrets: unterminated PEM block (streaming)";

pub fn secrets(arguments: &[OsString]) -> ExitCode {
    let mut streaming = false;
    let mut state_file: Option<PathBuf> = None;
    let mut index = 0;
    while index < arguments.len() {
        let argument = &arguments[index];
        if argument == "--streaming" {
            streaming = true;
            index += 1;
        } else if argument == "--state-file" {
            let Some(value) = arguments.get(index + 1) else {
                eprintln!("redact secrets: --state-file requires a value");
                return ExitCode::from(2);
            };
            state_file = Some(PathBuf::from(value));
            index += 2;
        } else if let Some(value) = strip_os_prefix(argument, b"--state-file=") {
            state_file = Some(PathBuf::from(value));
            index += 1;
        } else {
            eprintln!(
                "redact secrets: unknown option: {}",
                argument.to_string_lossy()
            );
            return ExitCode::from(2);
        }
    }
    let input = read_stdin();
    if !streaming {
        return write_stdout(&redact_secrets_only(&input));
    }
    let Some(state_file) = state_file.filter(|path| !path.as_os_str().is_empty()) else {
        eprintln!("redact secrets: --streaming requires --state-file");
        return ExitCode::from(2);
    };
    let in_pem = match read_stream_state(&state_file) {
        Ok(in_pem) => in_pem,
        Err(error) => {
            eprintln!("redact secrets: {error}");
            return ExitCode::FAILURE;
        }
    };
    let result = redact_secrets_streaming(&input, in_pem);
    if let Err(error) = write_private_text(
        &state_file,
        if result.in_pem() {
            "in_pem=1\n"
        } else {
            "in_pem=0\n"
        },
        0o600,
    ) {
        eprintln!("redact secrets: {error}");
        return ExitCode::FAILURE;
    }
    if result.in_pem() {
        eprintln!("{STREAMING_PEM_WARNING}");
    }
    write_stdout(result.text())
}

pub fn tmpdir_paths(arguments: &[OsString]) -> ExitCode {
    if let Some(argument) = arguments.first() {
        eprintln!(
            "redact tmpdir-paths: unknown option: {}",
            argument.to_string_lossy()
        );
        return ExitCode::from(2);
    }
    write_stdout(&redact_sensitive_paths(&read_stdin()))
}

pub fn scrub_log_secrets(arguments: &[OsString]) -> ExitCode {
    let directory = match parse_log_directory(arguments) {
        Ok(directory) => directory,
        Err(code) => return code,
    };
    if !directory.exists() {
        eprintln!(
            "redact scrub-log-secrets: directory not found: {}",
            directory.display()
        );
        return ExitCode::from(2);
    }
    match scrub_log_directory(&directory) {
        Ok((violations, files)) => {
            println!("LARCH_SECRET_SCRUB_VIOLATIONS={violations}");
            println!("LARCH_SECRET_SCRUB_FILES={files}");
            ExitCode::SUCCESS
        }
        Err(LogScrubError::Survived(path)) => {
            eprintln!("secret survived scrubbing in {}", path.display());
            ExitCode::from(3)
        }
        Err(LogScrubError::Io(error)) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}

pub fn scrub_submodule_paths(arguments: &[OsString]) -> ExitCode {
    let (input, output, log) = match parse_submodule_arguments(arguments) {
        Ok(paths) => paths,
        Err(code) => return code,
    };
    let result = (|| {
        let text = read_confined_text(&input, true)?;
        let cwd = env::current_dir().map_err(|error| RedactIoError::io(Path::new("."), &error))?;
        let submodules = discover_submodule_paths(&cwd)?;
        let scrubbed = scrub_submodule_findings(&text, &submodules);
        write_private_text(&output, scrubbed.text(), 0o600)?;
        write_private_text(&log, scrubbed.audit(), 0o600)?;
        Ok::<usize, RedactIoError>(scrubbed.count())
    })();
    match result {
        Ok(count) => {
            println!("SCRUB_COUNT={count}");
            println!("SCRUB_OK=true");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("scrub-submodule-paths.sh: {error}");
            println!("SCRUB_COUNT=0");
            println!("SCRUB_OK=false");
            ExitCode::from(2)
        }
    }
}

fn parse_log_directory(arguments: &[OsString]) -> Result<PathBuf, ExitCode> {
    let mut directory: Option<PathBuf> = None;
    let mut index = 0;
    while index < arguments.len() {
        let argument = &arguments[index];
        if matches!(argument.to_str(), Some("--dir" | "--log-root" | "--path")) {
            let Some(value) = arguments.get(index + 1) else {
                eprintln!(
                    "redact scrub-log-secrets: {} requires a value",
                    argument.to_string_lossy()
                );
                return Err(ExitCode::from(2));
            };
            directory = Some(PathBuf::from(value));
            index += 2;
        } else if directory.is_some() {
            eprintln!(
                "redact scrub-log-secrets: unknown option: {}",
                argument.to_string_lossy()
            );
            return Err(ExitCode::from(2));
        } else {
            directory = Some(PathBuf::from(argument));
            index += 1;
        }
    }
    directory
        .filter(|path| !path.as_os_str().is_empty())
        .ok_or_else(|| {
            eprintln!("redact scrub-log-secrets: directory is required");
            ExitCode::from(2)
        })
}

fn parse_submodule_arguments(
    arguments: &[OsString],
) -> Result<(PathBuf, PathBuf, PathBuf), ExitCode> {
    let mut input: Option<PathBuf> = None;
    let mut output: Option<PathBuf> = None;
    let mut log: Option<PathBuf> = None;
    let mut index = 0;
    while index < arguments.len() {
        let argument = &arguments[index];
        let target = if argument == "--input" {
            &mut input
        } else if argument == "--output" {
            &mut output
        } else if argument == "--log" {
            &mut log
        } else {
            eprintln!(
                "scrub-submodule-paths.sh: unknown or incomplete option: {}",
                argument.to_string_lossy()
            );
            return Err(ExitCode::from(2));
        };
        let Some(value) = arguments.get(index + 1) else {
            eprintln!(
                "scrub-submodule-paths.sh: unknown or incomplete option: {}",
                argument.to_string_lossy()
            );
            return Err(ExitCode::from(2));
        };
        *target = Some(PathBuf::from(value));
        index += 2;
    }
    if let (Some(input), Some(output), Some(log)) =
        (nonempty(input), nonempty(output), nonempty(log))
    {
        Ok((input, output, log))
    } else {
        eprintln!("scrub-submodule-paths.sh: --input, --output, and --log are required");
        Err(ExitCode::from(2))
    }
}

fn nonempty(path: Option<PathBuf>) -> Option<PathBuf> {
    path.filter(|value| !value.as_os_str().is_empty())
}

fn scrub_log_directory(directory: &Path) -> Result<(usize, usize), LogScrubError> {
    let metadata = fs::symlink_metadata(directory)
        .map_err(|error| LogScrubError::Io(RedactIoError::io(directory, &error)))?;
    if metadata.file_type().is_symlink() {
        return Err(LogScrubError::Io(RedactIoError::other(
            directory,
            "symbolic links are not allowed",
        )));
    }
    if !metadata.is_dir() {
        return Ok((0, 0));
    }
    let absolute = absolute_path(directory)
        .map_err(|error| LogScrubError::Io(RedactIoError::io(directory, &error)))?;
    let root = TemporaryRoot::resolve(Some(&absolute))
        .map_err(|error| LogScrubError::Io(RedactIoError::other(directory, error)))?;
    let mut paths = Vec::new();
    collect_regular_files(root.path(), &mut paths)
        .map_err(|error| LogScrubError::Io(RedactIoError::io(directory, &error)))?;
    paths.sort();
    let mut violations = 0;
    let mut files = 0;
    for path in paths {
        let confined = root
            .confine(&path, PathIntent::Read)
            .map_err(|error| LogScrubError::Io(RedactIoError::other(&path, error)))?;
        let text = match read_utf8(&confined) {
            Ok(text) => text,
            Err(error)
                if matches!(
                    error.kind(),
                    FileIoErrorKind::InvalidUtf8 | FileIoErrorKind::Io
                ) =>
            {
                continue;
            }
            Err(error) => {
                return Err(LogScrubError::Io(RedactIoError::other(&path, error)));
            }
        };
        let first = redact_secrets(&text);
        if first.findings().is_empty() {
            continue;
        }
        if !redact_secrets(first.text()).findings().is_empty() {
            return Err(LogScrubError::Survived(path));
        }
        let mode = fs::symlink_metadata(&path)
            .map_err(|error| LogScrubError::Io(RedactIoError::io(&path, &error)))?
            .permissions()
            .mode()
            & 0o777;
        let destination = root
            .confine(&path, PathIntent::Write)
            .map_err(|error| LogScrubError::Io(RedactIoError::other(&path, error)))?;
        larch_adapters::atomic_write_utf8(&destination, first.text(), mode)
            .map_err(|error| LogScrubError::Io(RedactIoError::other(&path, error)))?;
        violations += first.findings().values().sum::<usize>();
        files += 1;
    }
    Ok((violations, files))
}

fn collect_regular_files(directory: &Path, paths: &mut Vec<PathBuf>) -> io::Result<()> {
    for entry in fs::read_dir(directory)? {
        let path = entry?.path();
        let Ok(metadata) = fs::symlink_metadata(&path) else {
            continue;
        };
        if metadata.file_type().is_symlink() {
            continue;
        }
        if metadata.is_dir() {
            collect_regular_files(&path, paths)?;
        } else if metadata.is_file() {
            paths.push(path);
        }
    }
    Ok(())
}

fn discover_submodule_paths(cwd: &Path) -> Result<Vec<String>, RedactIoError> {
    let repository =
        RepositoryRoot::resolve(Some(cwd)).map_err(|error| RedactIoError::other(cwd, error))?;
    let mut paths = BTreeSet::new();
    let gitmodules = repository.path().join(".gitmodules");
    match fs::symlink_metadata(&gitmodules) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            return Err(RedactIoError::other(
                &gitmodules,
                "symbolic links are not allowed",
            ));
        }
        Ok(metadata) if metadata.is_file() => {
            let confined = repository
                .confine(&gitmodules, PathIntent::Read)
                .map_err(|error| RedactIoError::other(&gitmodules, error))?;
            let text = read_utf8_lossy(&confined)
                .map_err(|error| RedactIoError::other(&gitmodules, error))?;
            add_gitmodule_paths(&text, &mut paths);
        }
        Ok(_) | Err(_) => {}
    }
    let policy = GitCliPolicy::new(repository.path().to_path_buf())
        .map_err(|error| RedactIoError::other(repository.path(), error))?;
    let runtime = LarchRuntime::current_thread()
        .map_err(|error| RedactIoError::other(repository.path(), error))?;
    let command = GitToken::new("printf '%s\\n' \"$sm_path\"")
        .map_err(|error| RedactIoError::other(repository.path(), error))?;
    let runner = TokioProcessRunner::default();
    let cancellation = Cancellation::new();
    if let Ok(result) = runtime.block_on(GitCli::new(&runner, policy).submodule(
        SubmoduleRequest::Foreach {
            quiet: true,
            recursive: false,
            command: vec![command],
        },
        &cancellation,
    )) {
        let stdout = std::str::from_utf8(result.output().stdout())
            .map_err(|error| RedactIoError::other(repository.path(), error))?;
        add_command_paths(stdout, &mut paths);
    }
    Ok(paths.into_iter().collect())
}

fn add_gitmodule_paths(text: &str, paths: &mut BTreeSet<String>) {
    let options = ParseOptions {
        key_whitespace: WhitespacePolicy::Trim,
        value_whitespace: WhitespacePolicy::Trim,
        ..ParseOptions::legacy()
    };
    for line in text.lines() {
        if let Some(row) = parse_single_kv_row(line.trim(), options)
            && row.key() == "path"
            && !row.value().is_empty()
        {
            add_submodule_path(row.value(), paths);
        }
    }
}

fn add_command_paths(text: &str, paths: &mut BTreeSet<String>) {
    for line in text.lines().map(str::trim).filter(|line| !line.is_empty()) {
        add_submodule_path(line, paths);
    }
}

fn add_submodule_path(value: &str, paths: &mut BTreeSet<String>) {
    let normalized = value.trim().trim_matches('/');
    if GitCliPath::new(normalized).is_ok() {
        paths.insert(normalized.to_owned());
    }
}

fn strip_os_prefix(argument: &OsStr, prefix: &[u8]) -> Option<OsString> {
    argument
        .as_bytes()
        .strip_prefix(prefix)
        .map(|value| OsString::from_vec(value.to_vec()))
}

fn read_stream_state(path: &Path) -> Result<bool, RedactIoError> {
    match fs::symlink_metadata(path) {
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(false),
        Err(error) => return Err(RedactIoError::io(path, &error)),
        Ok(metadata) if metadata.file_type().is_symlink() => {
            return Err(RedactIoError::other(path, "symbolic links are not allowed"));
        }
        Ok(metadata) if !metadata.is_file() => return Ok(false),
        Ok(_) => {}
    }
    read_confined_text(path, false).map(|text| text.contains("in_pem=1"))
}

fn read_confined_text(path: &Path, lossy: bool) -> Result<String, RedactIoError> {
    let absolute = absolute_path(path).map_err(|error| RedactIoError::io(path, &error))?;
    match fs::symlink_metadata(&absolute) {
        Err(error) => return Err(RedactIoError::io(path, &error)),
        Ok(metadata) if metadata.file_type().is_symlink() => {
            return Err(RedactIoError::other(path, "symbolic links are not allowed"));
        }
        Ok(_) => {}
    }
    let parent = absolute
        .parent()
        .ok_or_else(|| RedactIoError::other(path, "path has no parent"))?;
    let relative = absolute
        .strip_prefix(parent)
        .map_err(|error| RedactIoError::other(path, error))?;
    let root =
        TemporaryRoot::resolve(Some(parent)).map_err(|error| RedactIoError::other(path, error))?;
    let confined = root
        .confine(relative, PathIntent::Read)
        .map_err(|error| RedactIoError::other(path, error))?;
    if lossy {
        read_utf8_lossy(&confined).map_err(|error| RedactIoError::other(path, error))
    } else {
        read_utf8(&confined).map_err(|error| RedactIoError::other(path, error))
    }
}

fn write_private_text(path: &Path, text: &str, mode: u32) -> Result<(), RedactIoError> {
    let absolute = absolute_path(path).map_err(|error| RedactIoError::io(path, &error))?;
    let parent = absolute
        .parent()
        .ok_or_else(|| RedactIoError::other(path, "path has no parent"))?;
    let relative = absolute
        .strip_prefix(parent)
        .map_err(|error| RedactIoError::other(path, error))?;
    ensure_directory_chain(parent).map_err(|error| RedactIoError::other(path, error))?;
    let root =
        TemporaryRoot::resolve(Some(parent)).map_err(|error| RedactIoError::other(path, error))?;
    atomic_write_utf8_in(&root, relative, text, false, mode)
        .map_err(|error| RedactIoError::other(path, error))
}

enum LogScrubError {
    Survived(PathBuf),
    Io(RedactIoError),
}

#[derive(Debug)]
struct RedactIoError(String);

impl RedactIoError {
    fn io(path: &Path, error: &io::Error) -> Self {
        Self(python_io_error(error, path))
    }

    fn other(path: &Path, error: impl std::fmt::Display) -> Self {
        Self(format!("{}: {error}", path.display()))
    }
}

impl std::fmt::Display for RedactIoError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

#[cfg(test)]
mod tests {
    use super::{
        add_command_paths, add_gitmodule_paths, parse_submodule_arguments, read_stream_state,
        write_private_text,
    };
    use std::{
        collections::BTreeSet,
        ffi::OsString,
        fs,
        os::unix::fs::{PermissionsExt as _, symlink},
    };

    #[test]
    fn gitmodule_and_foreach_paths_match_python_normalization() {
        let mut paths = BTreeSet::new();
        add_gitmodule_paths(
            "[submodule \"a\"]\n path = /vendor/a/\n path = /\nignored = value\n",
            &mut paths,
        );
        add_command_paths(" vendor/b/ \n../escape\n\n", &mut paths);
        assert_eq!(
            paths.into_iter().collect::<Vec<_>>(),
            vec![String::from("vendor/a"), String::from("vendor/b")]
        );
    }

    #[test]
    fn submodule_parser_rejects_inline_and_incomplete_options() {
        assert!(parse_submodule_arguments(&[OsString::from("--input=a")]).is_err());
        assert!(parse_submodule_arguments(&[OsString::from("--input")]).is_err());
    }

    #[test]
    fn streaming_state_rejects_invalid_utf8() {
        let temporary = tempfile::tempdir().expect("temporary directory");
        let state = temporary.path().join("state.env");
        fs::write(&state, [0xff]).expect("write invalid state");

        assert!(read_stream_state(&state).is_err());
    }

    #[test]
    fn streaming_state_rejects_symlinks() {
        let temporary = tempfile::tempdir().expect("temporary directory");
        let target = temporary.path().join("target.env");
        let state = temporary.path().join("state.env");
        fs::write(&target, b"in_pem=1\n").expect("write state target");
        symlink(&target, &state).expect("create state symlink");

        assert!(read_stream_state(&state).is_err());
    }

    #[test]
    fn private_writer_sets_mode_and_rejects_multiply_linked_targets() {
        let temporary = tempfile::tempdir().expect("temporary directory");
        let output = temporary.path().join("nested/output.txt");
        write_private_text(&output, "safe\n", 0o600).expect("write private output");
        assert_eq!(
            fs::metadata(&output)
                .expect("output metadata")
                .permissions()
                .mode()
                & 0o777,
            0o600
        );

        let alias = temporary.path().join("output-alias.txt");
        fs::hard_link(&output, &alias).expect("create hard link");
        assert!(write_private_text(&output, "replacement\n", 0o600).is_err());
        assert_eq!(fs::read_to_string(&alias).expect("read alias"), "safe\n");
    }
}
