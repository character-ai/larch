//! Rust owners for the small developer-tooling command selectors.
//!
//! These commands deliberately keep their compatibility parsing at the
//! command boundary.  Their repository reads go through `GixRepository`; no
//! invocation depends on an installed `git` or `grep` binary.

use std::{
    collections::BTreeSet,
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    io::{self, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
};

#[cfg(unix)]
use std::os::unix::ffi::OsStringExt as _;

use clap::{Args, Subcommand};
use larch_adapters::GixRepository;
use larch_core::{Head, RepositoryRead, Revision, StatusOptions};
use larch_harness_mark::{
    RESIDUAL_BASH_MANIFEST, has_shell_suffix_bytes, read_residual_bash_paths,
};
use regex::bytes::RegexBuilder;

const MAX_U64_DECIMAL: &str = "18446744073709551615";
const PUBLIC_STYLE_LINE: &str = "**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**";
const DEV_STYLE_LINE: &str = "**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `$PWD/skills/shared/readability-style.md`.**";
const VERIFY_SKILL_USAGE: &str = "Usage: verify skill-called (--sentinel-file PATH | --stdout-line RE --stdout-file PATH | --commit-delta N --before-count N)";

/// Alias-generation helpers used by `/alias`.
#[derive(Subcommand)]
pub enum AliasCommand {
    /// Render one generated alias SKILL.md document to stdout.
    #[command(disable_help_flag = true)]
    Generate(RawArguments),
    /// Resolve an alias target directory from the current repository.
    #[command(name = "resolve-target", disable_help_flag = true)]
    ResolveTarget(RawArguments),
}

/// Residual Bash manifest helpers.
#[derive(Subcommand)]
pub enum ResidualBashCommand {
    /// List the residual Bash paths retained by the manifest.
    #[command(disable_help_flag = true)]
    Paths(RawArguments),
}

/// Small post-skill verification helpers.
#[derive(Subcommand)]
pub enum VerifyCommand {
    /// Verify an observable child-skill side effect.
    #[command(name = "skill-called", disable_help_flag = true)]
    SkillCalled(RawArguments),
}

/// Preserve the legacy command-specific parser boundary.
#[derive(Args)]
#[command(trailing_var_arg = true)]
pub struct RawArguments {
    #[arg(allow_hyphen_values = true)]
    arguments: Vec<OsString>,
}

/// Dispatch one `alias` command.
pub fn run_alias(command: AliasCommand) -> ExitCode {
    let code = match command {
        AliasCommand::Generate(arguments) => alias_generate(&arguments.arguments),
        AliasCommand::ResolveTarget(arguments) => alias_resolve_target(&arguments.arguments),
    };
    ExitCode::from(code)
}

/// Dispatch one `residual-bash` command.
pub fn run_residual_bash(command: ResidualBashCommand) -> ExitCode {
    let code = match command {
        ResidualBashCommand::Paths(arguments) => residual_bash_paths(&arguments.arguments),
    };
    ExitCode::from(code)
}

/// Dispatch one `verify` command.
pub fn run_verify(command: VerifyCommand) -> ExitCode {
    let code = match command {
        VerifyCommand::SkillCalled(arguments) => verify_skill_called(&arguments.arguments),
    };
    ExitCode::from(code)
}

fn argument_text(arguments: &[OsString]) -> Vec<String> {
    arguments
        .iter()
        .map(|argument| argument.to_string_lossy().into_owned())
        .collect()
}

fn alias_generate(arguments: &[OsString]) -> u8 {
    let arguments = argument_text(arguments);
    let mut name = String::new();
    let mut target = String::new();
    let mut flags = String::new();
    let mut version = String::new();
    let mut target_dir = String::new();
    let mut index = 0;
    while index < arguments.len() {
        let argument = &arguments[index];
        let Some(value) = arguments.get(index + 1) else {
            eprintln!("ERROR: Unknown argument: {argument}");
            return 1;
        };
        match argument.as_str() {
            "--name" => name.clone_from(value),
            "--target" => target.clone_from(value),
            "--flags" => flags.clone_from(value),
            "--version" => version.clone_from(value),
            "--target-dir" => target_dir.clone_from(value),
            _ => {
                eprintln!("ERROR: Unknown argument: {argument}");
                return 1;
            }
        }
        index += 2;
    }
    if name.is_empty() || target.is_empty() {
        eprintln!("ERROR: --name and --target are required");
        return 1;
    }

    let escaped_flags = flags.replace('"', r#"\""#);
    let description = if flags.is_empty() {
        format!("Alias for /{target} (created by /alias)")
    } else {
        format!("Alias for /{target} {escaped_flags} (created by /alias)")
    };
    let usage = if flags.is_empty() {
        format!("/{name} <arguments> is equivalent to /{target} <arguments>")
    } else {
        format!("/{name} <arguments> is equivalent to /{target} {flags} <arguments>")
    };
    let behavior_args = if flags.is_empty() {
        r#"--lifecycle-parent-context "$CONTEXT_FILE" $ARGUMENTS"#.to_owned()
    } else {
        format!(r#"--lifecycle-parent-context "$CONTEXT_FILE" {flags} $ARGUMENTS"#)
    };
    let version_line = if version.is_empty() {
        "Generated by larch /alias".to_owned()
    } else {
        format!("Generated by larch /alias v{version}")
    };
    let style_line = if target_dir.contains("/.claude/skills/") {
        DEV_STYLE_LINE
    } else {
        PUBLIC_STYLE_LINE
    };

    let mut output = String::new();
    let _ = writeln!(output, "---");
    let _ = writeln!(output, "# larch-run-lifecycle: shared-v1 skill={name}");
    let _ = writeln!(output, "name: {name}");
    let _ = writeln!(output, "description: \"{description}\"");
    let _ = writeln!(output, "argument-hint: \"<arguments>\"");
    let _ = writeln!(output, "allowed-tools: Bash(python3:*), Read, Skill");
    let _ = writeln!(output, "---");
    let _ = writeln!(output);
    let _ = writeln!(
        output,
        "**MANDATORY: Follow the complete shared lifecycle contract in `${{CLAUDE_PLUGIN_ROOT}}/skills/shared/run-lifecycle.md` with declared skill `{name}`.**"
    );
    let _ = writeln!(output);
    let _ = writeln!(output, "{style_line}");
    let _ = writeln!(output);
    let _ = writeln!(
        output,
        "Auto-generated alias created by larch /alias. Invokes /{target} with preset flags."
    );
    let _ = writeln!(output);
    let _ = writeln!(output, "## Usage");
    let _ = writeln!(output);
    let _ = writeln!(output, "{usage}");
    let _ = writeln!(output);
    let _ = writeln!(output, "## Behavior");
    let _ = writeln!(output);
    let _ = writeln!(output, "Invoke the Skill tool:");
    let _ = writeln!(
        output,
        "- Try skill: \"{target}\" first (bare name). If no skill matches, try skill: \"larch:{target}\" (fully-qualified plugin name)."
    );
    let _ = writeln!(output, "- args: {behavior_args}");
    if target == "implement" {
        let _ = writeln!(output);
        let _ = writeln!(
            output,
            "After the Skill tool loads /implement, the child skill MUST begin execution at its Step 0 (session setup). Do not investigate the codebase, plan, or implement anything before Step 0 completes."
        );
    }
    let _ = writeln!(output);
    let _ = writeln!(output, "{version_line}");
    print!("{output}");
    0
}

fn alias_resolve_target(arguments: &[OsString]) -> u8 {
    let arguments = argument_text(arguments);
    let mut name = String::new();
    let mut private = false;
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--alias-name" => {
                let Some(value) = arguments.get(index + 1) else {
                    eprintln!("ERROR: --alias-name requires a value");
                    return 1;
                };
                name.clone_from(value);
                index += 2;
            }
            "--private" => {
                private = true;
                index += 1;
            }
            argument => {
                eprintln!("ERROR: Unknown argument: {argument}");
                return 1;
            }
        }
    }
    if name.is_empty() {
        eprintln!("ERROR: --alias-name is required");
        return 1;
    }
    if !is_alias_name(&name) {
        eprintln!("ERROR: alias-name '{name}' is invalid (must match ^[a-z][a-z0-9-]*$)");
        return 1;
    }

    let root = env::current_dir()
        .ok()
        .and_then(|cwd| GixRepository::discover(cwd).ok())
        .and_then(|repository| repository.location().work_dir)
        .and_then(|path| path_from_git_bytes(path.as_bytes()).ok())
        .map(|path| fs::canonicalize(&path).unwrap_or(path));
    let Some(root) = root else {
        eprintln!("ERROR: not in a git repository");
        return 1;
    };
    let plugin_repo = root.join(".claude-plugin/plugin.json").is_file()
        && root.join("skills/implement/SKILL.md").is_file();
    let target_dir = if plugin_repo && !private {
        root.join("skills").join(&name)
    } else {
        root.join(".claude").join("skills").join(&name)
    };
    println!("REPO_ROOT={}", root.display());
    println!("PLUGIN_REPO={}", if plugin_repo { "true" } else { "false" });
    println!("TARGET_DIR={}", target_dir.display());
    0
}

fn is_alias_name(name: &str) -> bool {
    let bytes = name.as_bytes();
    matches!(bytes.first(), Some(b'a'..=b'z'))
        && bytes
            .iter()
            .skip(1)
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || *byte == b'-')
}

#[cfg(unix)]
fn path_from_git_bytes(bytes: &[u8]) -> Result<PathBuf, ()> {
    if bytes.contains(&0) {
        return Err(());
    }
    Ok(PathBuf::from(OsString::from_vec(bytes.to_vec())))
}

#[cfg(not(unix))]
fn path_from_git_bytes(bytes: &[u8]) -> Result<PathBuf, ()> {
    let text = std::str::from_utf8(bytes).map_err(|_| ())?;
    Ok(PathBuf::from(text))
}

#[derive(Default)]
struct ResidualBashOptions {
    root: Option<PathBuf>,
    null_delimited: bool,
    check_exists: bool,
    intersect_git: bool,
}

fn residual_bash_paths(arguments: &[OsString]) -> u8 {
    let options = match parse_residual_bash_options(&argument_text(arguments)) {
        Ok(Some(options)) => options,
        Ok(None) => return 0,
        Err(error) => {
            eprintln!("ERROR: {error}");
            return 2;
        }
    };
    let root = options
        .root
        .as_deref()
        .map_or_else(residual_root_from_cwd, absolute_path);
    let paths = if options.intersect_git {
        match intersect_git_shell_paths(&root) {
            Ok(paths) => paths,
            Err(error) => {
                eprintln!("ERROR: {error}");
                return 2;
            }
        }
    } else {
        match read_residual_bash_paths(&root, options.check_exists) {
            Ok(paths) => paths,
            Err(error) => {
                eprintln!("ERROR: {error}");
                return 2;
            }
        }
    };
    if options.intersect_git
        && options.check_exists
        && let Err(error) = read_residual_bash_paths(&root, true)
    {
        eprintln!("ERROR: {error}");
        return 2;
    }
    if !paths.is_empty() {
        let separator = if options.null_delimited { "\0" } else { "\n" };
        let mut stdout = io::stdout().lock();
        if stdout
            .write_all(paths.join(separator).as_bytes())
            .and_then(|()| stdout.write_all(separator.as_bytes()))
            .is_err()
        {
            return 1;
        }
    }
    0
}

fn parse_residual_bash_options(
    arguments: &[String],
) -> Result<Option<ResidualBashOptions>, String> {
    let mut options = ResidualBashOptions::default();
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--root" => {
                let Some(root) = arguments.get(index + 1) else {
                    return Err("--root requires a value".to_owned());
                };
                options.root = Some(PathBuf::from(root));
                index += 2;
            }
            "--null-delimited" => {
                options.null_delimited = true;
                index += 1;
            }
            "--check-exists" => {
                options.check_exists = true;
                index += 1;
            }
            "--intersect-git" => {
                options.intersect_git = true;
                index += 1;
            }
            "-h" | "--help" => {
                println!(
                    "Usage: residual-bash paths [--root PATH] [--null-delimited] [--check-exists] [--intersect-git]"
                );
                return Ok(None);
            }
            argument => return Err(format!("Unknown argument: {argument}")),
        }
    }
    Ok(Some(options))
}

fn residual_root_from_cwd() -> PathBuf {
    let start = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let start = fs::canonicalize(&start).unwrap_or(start);
    for candidate in start.ancestors() {
        if candidate.join(RESIDUAL_BASH_MANIFEST).is_file() {
            return candidate.to_owned();
        }
    }
    if let Some(root) = env::var_os("CLAUDE_PLUGIN_ROOT")
        .map(PathBuf::from)
        .map(|path| absolute_path(&path))
        && root.join(RESIDUAL_BASH_MANIFEST).is_file()
    {
        return root;
    }
    start
}

fn absolute_path(path: &Path) -> PathBuf {
    let absolute = if path.is_absolute() {
        path.to_owned()
    } else {
        env::current_dir()
            .unwrap_or_else(|_| PathBuf::from("."))
            .join(path)
    };
    fs::canonicalize(&absolute).unwrap_or(absolute)
}

fn intersect_git_shell_paths(root: &Path) -> Result<Vec<String>, String> {
    let manifest_paths = read_residual_bash_paths(root, false)?;
    let paths = git_shell_paths(root);
    Ok(manifest_paths
        .into_iter()
        .filter(|path| paths.contains(path.as_bytes()))
        .collect())
}

fn git_shell_paths(root: &Path) -> BTreeSet<Vec<u8>> {
    let Ok(repository) = GixRepository::discover(root) else {
        return BTreeSet::new();
    };
    let mut paths = repository
        .tracked_paths()
        .into_iter()
        .flatten()
        .map(|path| path.as_bytes().to_vec())
        .filter(|path| is_shell_path(path))
        .collect::<BTreeSet<_>>();
    if let Ok(status) = repository.local_status(&StatusOptions::default()) {
        paths.extend(
            status
                .untracked
                .into_iter()
                .map(|path| path.as_bytes().to_vec())
                .filter(|path| is_shell_path(path)),
        );
    }
    paths
}

fn is_shell_path(path: &[u8]) -> bool {
    has_shell_suffix_bytes(path)
}

#[derive(Default)]
struct VerifySkillOptions {
    sentinel_file: Option<String>,
    stdout_line: Option<String>,
    stdout_file: Option<String>,
    commit_delta: Option<String>,
    before_count: Option<String>,
}

fn verify_skill_called(arguments: &[OsString]) -> u8 {
    let arguments = argument_text(arguments);
    let options = match parse_verify_skill_options(&arguments) {
        Ok(Some(options)) => options,
        Ok(None) => return 0,
        Err(()) => return 1,
    };
    let sentinel_mode = options.sentinel_file.is_some();
    let stdout_mode = options.stdout_line.is_some() || options.stdout_file.is_some();
    let commit_mode = options.commit_delta.is_some() || options.before_count.is_some();
    if [sentinel_mode, stdout_mode, commit_mode]
        .into_iter()
        .filter(|selected| *selected)
        .count()
        != 1
    {
        eprintln!("ERROR: pass exactly one verification mode");
        return 1;
    }
    if sentinel_mode {
        return verify_sentinel(options.sentinel_file.as_deref().unwrap_or_default());
    }
    if stdout_mode {
        return verify_stdout_line(
            options.stdout_line.as_deref().unwrap_or_default(),
            options.stdout_file.as_deref().unwrap_or_default(),
        );
    }
    verify_commit_delta(
        options.commit_delta.as_deref().unwrap_or_default(),
        options.before_count.as_deref().unwrap_or_default(),
    )
}

fn parse_verify_skill_options(arguments: &[String]) -> Result<Option<VerifySkillOptions>, ()> {
    let mut options = VerifySkillOptions::default();
    let mut index = 0;
    while index < arguments.len() {
        let argument = &arguments[index];
        if matches!(argument.as_str(), "-h" | "--help") {
            eprintln!("{VERIFY_SKILL_USAGE}");
            return Ok(None);
        }
        if !matches!(
            argument.as_str(),
            "--sentinel-file"
                | "--stdout-line"
                | "--stdout-file"
                | "--commit-delta"
                | "--before-count"
        ) {
            eprintln!("ERROR: Unknown argument: {argument}");
            eprintln!("{VERIFY_SKILL_USAGE}");
            return Err(());
        }
        let Some(value) = arguments.get(index + 1) else {
            eprintln!("{VERIFY_SKILL_USAGE}");
            return Err(());
        };
        match argument.as_str() {
            "--sentinel-file" => options.sentinel_file = Some(value.clone()),
            "--stdout-line" => options.stdout_line = Some(value.clone()),
            "--stdout-file" => options.stdout_file = Some(value.clone()),
            "--commit-delta" => options.commit_delta = Some(value.clone()),
            "--before-count" => options.before_count = Some(value.clone()),
            _ => unreachable!("the selector was checked before reading its value"),
        }
        index += 2;
    }
    Ok(Some(options))
}

fn verify_sentinel(raw: &str) -> u8 {
    if raw.is_empty() {
        eprintln!("ERROR: --sentinel-file requires a non-empty path");
        return 1;
    }
    let path = Path::new(raw);
    if !path.exists() {
        return emit_verification(false, "missing_path");
    }
    if !path.is_file() {
        return emit_verification(false, "not_regular_file");
    }
    if fs::metadata(path).map_or(true, |metadata| metadata.len() == 0) {
        return emit_verification(false, "empty_file");
    }
    emit_verification(true, "ok")
}

fn verify_stdout_line(regex: &str, stdout_file: &str) -> u8 {
    if regex.is_empty() {
        eprintln!(
            "ERROR: --stdout-line requires a non-empty regex (empty would match any non-empty line)"
        );
        return 1;
    }
    if stdout_file.is_empty() {
        eprintln!("ERROR: --stdout-line requires --stdout-file");
        return 1;
    }
    let path = Path::new(stdout_file);
    if !path.is_file() {
        return emit_verification(false, "missing_stdout_file");
    }
    let expression = RegexBuilder::new(regex)
        .multi_line(true)
        .unicode(false)
        .build();
    let contents = fs::read(path);
    let (Ok(expression), Ok(contents)) = (expression, contents) else {
        eprintln!("ERROR: grep failed (exit 2) - regex may be malformed or file unreadable");
        return 1;
    };
    let matches = expression.is_match(&contents);
    emit_verification(matches, if matches { "ok" } else { "no_match" })
}

fn verify_commit_delta(expected: &str, before: &str) -> u8 {
    if !is_nonnegative(expected) {
        eprintln!("ERROR: --commit-delta value must be a non-negative integer");
        return 1;
    }
    if !is_nonnegative(before) {
        eprintln!("ERROR: --before-count value must be a non-negative integer");
        return 1;
    }
    let (count, status) = commit_count();
    if status != "ok" {
        return emit_verification(false, status);
    }
    let matches = decimal_to_u64(before)
        .and_then(|before| count.checked_sub(before))
        .is_some_and(|delta| decimal_equals_u64(expected, delta));
    emit_verification(
        matches,
        if matches {
            "ok"
        } else {
            "commit_delta_mismatch"
        },
    )
}

fn is_nonnegative(value: &str) -> bool {
    !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit())
}

fn decimal_to_u64(value: &str) -> Option<u64> {
    let normalized = value.trim_start_matches('0');
    if normalized.is_empty() {
        return Some(0);
    }
    if normalized.len() > MAX_U64_DECIMAL.len()
        || (normalized.len() == MAX_U64_DECIMAL.len() && normalized > MAX_U64_DECIMAL)
    {
        return None;
    }
    normalized.parse().ok()
}

fn decimal_equals_u64(value: &str, number: u64) -> bool {
    let normalized = value.trim_start_matches('0');
    let normalized = if normalized.is_empty() {
        "0"
    } else {
        normalized
    };
    normalized == number.to_string()
}

fn commit_count() -> (u64, &'static str) {
    let Ok(cwd) = env::current_dir() else {
        return (0, "missing_main_ref");
    };
    let Ok(repository) = GixRepository::discover(cwd) else {
        return (0, "missing_main_ref");
    };
    let base = repository
        .resolve_revision(&Revision::new(b"origin/main".to_vec()))
        .or_else(|_| repository.resolve_revision(&Revision::new(b"main".to_vec())));
    let Ok(base) = base else {
        return (0, "missing_main_ref");
    };
    let head = match repository.head() {
        Ok(Head::Symbolic { target, .. } | Head::Detached { target }) => target,
        Ok(Head::Unborn { .. }) | Err(_) => return (0, "git_error"),
    };
    repository
        .commit_count_range(&base, &head)
        .map_or((0, "git_error"), |count| (count, "ok"))
}

fn emit_verification(verified: bool, reason: &str) -> u8 {
    println!("VERIFIED={}", if verified { "true" } else { "false" });
    println!("REASON={reason}");
    0
}
