//! Rust owner for `implement step-2-post-dispatch` (#8623).
//!
//! Runs the phantom untracked probe, reports the checked-out branch and short
//! commit, persists the ship-seed context Step 8 later reads, and emits the
//! routing token. Every refusal is routed on stdout as
//! `POST_DISPATCH_NEXT=bail`; the orchestrator routes on that token, not on the
//! exit code, so a branch that fails its expectation is not an error here.

use std::{
    env,
    ffi::OsString,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::GixRepository;
use larch_core::{ChildEnvironment, Head, RepositoryRead as _, emit_kv};

use crate::{argparse_compat::parse_required_with_help, python_verb::publish_session_environment};

const PROG: &str = "cli.py implement step-2-post-dispatch";
const USAGE: &str = "usage: cli.py implement step-2-post-dispatch [-h] --expected-branch\n                                             EXPECTED_BRANCH\n";
const HELP: &str = "usage: cli.py implement step-2-post-dispatch [-h] --expected-branch\n                                             EXPECTED_BRANCH\n\noptions:\n  -h, --help            show this help message and exit\n  --expected-branch EXPECTED_BRANCH\n";

const SEED_FILE: &str = "ship-seed-input.env";
const BAIL_REASON: &str = "main-branch-post-dispatch";
const SHORT_SHA_LENGTH: usize = 7;

/// `implement step-2-post-dispatch` compatibility command.
pub fn step_2_post_dispatch(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        PROG,
        USAGE,
        HELP,
        &["--expected-branch"],
        &[],
        &["--expected-branch"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let expected_branch = parsed
        .value("--expected-branch")
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default();
    let Some(tmpdir) = implement_tmpdir() else {
        eprintln!("IMPLEMENT_TMPDIR required");
        return ExitCode::from(2);
    };
    rehydrate_plugin_root(&tmpdir);
    for line in crate::phantom_probe_lines("2-post-dispatch", None, true) {
        println!("{line}");
    }
    let Some(branch) = current_branch() else {
        eprintln!("step-2-post-dispatch: not on a named branch (detached HEAD or not a git repo)");
        emit_kv("POST_DISPATCH_NEXT", "bail");
        emit_kv("BAIL_REASON", BAIL_REASON);
        return ExitCode::SUCCESS;
    };
    emit_kv("BRANCH", &branch);
    if let Some(sha) = head_short_sha() {
        emit_kv("COMMIT_SHA", &sha);
    }
    persist_ship_seed_context(&tmpdir);
    if expected_branch.is_empty() || branch != expected_branch {
        emit_kv("POST_DISPATCH_NEXT", "bail");
        emit_kv("BAIL_REASON", BAIL_REASON);
        return ExitCode::SUCCESS;
    }
    upsert_seed_keys(&tmpdir, &[("DISPATCHER_COMMITTED", "true".to_owned())]);
    emit_kv("POST_DISPATCH_NEXT", "continue");
    ExitCode::SUCCESS
}

fn implement_tmpdir() -> Option<PathBuf> {
    env::var_os("IMPLEMENT_TMPDIR")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

/// Publish `CLAUDE_PLUGIN_ROOT` for later children from the session's record.
///
/// The workspace forbids mutating this process's own environment, so the value
/// travels as a child-environment row instead.
fn rehydrate_plugin_root(tmpdir: &Path) {
    if env::var_os("CLAUDE_PLUGIN_ROOT").is_some_and(|value| !value.is_empty()) {
        return;
    }
    let resolved = read_session_key(&tmpdir.join("plugin-root.env"), "CLAUDE_PLUGIN_ROOT")
        .or_else(|| read_session_key(&tmpdir.join("session-env.sh"), "LARCH_CLAUDE_PLUGIN_ROOT"))
        .or_else(|| {
            crate::implement_child_seam::resolve_plugin_root()
                .ok()
                .map(|root| root.display().to_string())
        });
    if let Some(root) = resolved.filter(|value| !value.is_empty()) {
        publish_session_environment(vec![(
            ChildEnvironment::ClaudePluginRoot,
            OsString::from(root),
        )]);
    }
}

fn read_session_key(path: &Path, key: &str) -> Option<String> {
    let text = std::fs::read_to_string(path).ok()?;
    let prefix = format!("{key}=");
    for line in text.lines() {
        let trimmed = line.trim_start().trim_start_matches("export ");
        if let Some(rest) = trimmed.strip_prefix(&prefix) {
            let value = rest.trim().trim_matches('"').trim_matches('\'');
            if !value.is_empty() {
                return Some(value.to_owned());
            }
        }
    }
    None
}

/// The checked-out branch, or `None` for a detached HEAD or a non-repository.
fn current_branch() -> Option<String> {
    let repository = GixRepository::discover(env::current_dir().ok()?).ok()?;
    let name = match repository.head().ok()? {
        Head::Symbolic { name, .. } | Head::Unborn { name } => name,
        Head::Detached { .. } => return None,
    };
    let raw = name.as_bytes();
    let stripped = raw.strip_prefix(b"refs/heads/").unwrap_or(raw);
    let text = std::str::from_utf8(stripped).ok()?;
    (!text.is_empty()).then(|| text.to_owned())
}

/// The abbreviated HEAD commit, or `None` when HEAD resolves to no commit.
fn head_short_sha() -> Option<String> {
    let repository = GixRepository::discover(env::current_dir().ok()?).ok()?;
    let target = match repository.head().ok()? {
        Head::Symbolic { target, .. } | Head::Detached { target } => target,
        Head::Unborn { .. } => return None,
    };
    let mut hex = String::with_capacity(SHORT_SHA_LENGTH);
    for byte in target.digest() {
        use std::fmt::Write as _;
        if hex.len() >= SHORT_SHA_LENGTH {
            break;
        }
        let _written = write!(hex, "{byte:02x}");
    }
    hex.truncate(SHORT_SHA_LENGTH);
    (!hex.is_empty()).then_some(hex)
}

/// Fill in the ship-seed keys Step 8 needs, without disturbing existing values.
///
/// Step 0 owns run flags in the same file, so only absent-or-empty keys are
/// written.
fn persist_ship_seed_context(tmpdir: &Path) {
    let lines = read_seed_lines(tmpdir);
    let mut updates = Vec::new();
    if !seed_value_nonempty(&lines, "MANIFEST_PATH") {
        updates.push(("MANIFEST_PATH", resolved_manifest_path(tmpdir)));
    }
    if !seed_value_nonempty(&lines, "TOOL_LABEL") {
        updates.push(("TOOL_LABEL", tool_label(tmpdir)));
    }
    upsert_seed_keys(tmpdir, &updates);
}

/// The manifest the external coder wrote, preferring the Codex out-directory.
fn resolved_manifest_path(tmpdir: &Path) -> String {
    for candidate in [
        tmpdir.join("codex-step2-out").join("manifest.json"),
        tmpdir.join("manifest.json"),
    ] {
        if candidate.is_file() {
            return candidate.display().to_string();
        }
    }
    String::new()
}

fn tool_label(tmpdir: &Path) -> String {
    match read_session_key(&tmpdir.join("bootstrap-routing.env"), "coder")
        .unwrap_or_default()
        .as_str()
    {
        "codex" => "Codex",
        "cursor" => "Cursor",
        _ => "claude",
    }
    .to_owned()
}

fn read_seed_lines(tmpdir: &Path) -> Vec<String> {
    let path = tmpdir.join(SEED_FILE);
    let Ok(metadata) = std::fs::symlink_metadata(&path) else {
        return Vec::new();
    };
    if metadata.is_symlink() || !metadata.is_file() {
        return Vec::new();
    }
    let bytes = std::fs::read(&path).unwrap_or_default();
    String::from_utf8_lossy(&bytes)
        .lines()
        .map(str::to_owned)
        .collect()
}

fn seed_value_nonempty(lines: &[String], key: &str) -> bool {
    let prefix = format!("{key}=");
    lines
        .iter()
        .find_map(|line| line.strip_prefix(&prefix))
        .is_some_and(|value| !value.trim().is_empty())
}

/// Replace or append each `key=value` row, preserving every other line.
fn upsert_seed_keys(tmpdir: &Path, updates: &[(&str, String)]) {
    if updates.is_empty() {
        return;
    }
    let mut lines = read_seed_lines(tmpdir);
    for (key, value) in updates {
        let prefix = format!("{key}=");
        let row = format!("{prefix}{value}");
        match lines.iter().position(|line| line.starts_with(&prefix)) {
            Some(index) => lines[index] = row,
            None => lines.push(row),
        }
    }
    let mut text = lines.join("\n");
    if !text.is_empty() {
        text.push('\n');
    }
    let path = tmpdir.join(SEED_FILE);
    if larch_core::write_bytes_atomic(&path, text.as_bytes()).is_err() {
        eprintln!(
            "step-2-post-dispatch: could not persist ship-seed context: {}",
            path.display()
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn a_malformed_command_line_refuses_with_the_python_exit_codes() {
        assert_eq!(
            format!("{:?}", step_2_post_dispatch(&arguments(&[]))),
            format!("{:?}", ExitCode::from(2))
        );
        assert_eq!(
            format!("{:?}", step_2_post_dispatch(&arguments(&["--help"]))),
            format!("{:?}", ExitCode::SUCCESS)
        );
    }

    #[test]
    fn seed_rows_are_upserted_without_disturbing_other_keys() {
        let temporary = tempfile::tempdir().expect("temporary dir");
        fs::write(
            temporary.path().join(SEED_FILE),
            "RUN_FLAG=keep\nMANIFEST_PATH=\n",
        )
        .expect("seed file");
        upsert_seed_keys(
            temporary.path(),
            &[
                ("MANIFEST_PATH", "/tmp/m.json".to_owned()),
                ("DISPATCHER_COMMITTED", "true".to_owned()),
            ],
        );
        let text = fs::read_to_string(temporary.path().join(SEED_FILE)).expect("read seed");
        assert_eq!(
            text,
            "RUN_FLAG=keep\nMANIFEST_PATH=/tmp/m.json\nDISPATCHER_COMMITTED=true\n"
        );
    }

    #[test]
    fn existing_nonempty_seed_values_are_preserved() {
        let temporary = tempfile::tempdir().expect("temporary dir");
        fs::write(
            temporary.path().join(SEED_FILE),
            "MANIFEST_PATH=/keep/me.json\nTOOL_LABEL=Codex\n",
        )
        .expect("seed file");
        fs::write(temporary.path().join("manifest.json"), "{}").expect("manifest");
        persist_ship_seed_context(temporary.path());
        let text = fs::read_to_string(temporary.path().join(SEED_FILE)).expect("read seed");
        assert_eq!(text, "MANIFEST_PATH=/keep/me.json\nTOOL_LABEL=Codex\n");
    }

    #[test]
    fn an_absent_seed_file_is_created_with_the_resolved_context() {
        let temporary = tempfile::tempdir().expect("temporary dir");
        let out = temporary.path().join("codex-step2-out");
        fs::create_dir_all(&out).expect("out dir");
        fs::write(out.join("manifest.json"), "{}").expect("manifest");
        fs::write(temporary.path().join("manifest.json"), "{}").expect("fallback manifest");
        fs::write(
            temporary.path().join("bootstrap-routing.env"),
            "coder=codex\n",
        )
        .expect("routing");
        persist_ship_seed_context(temporary.path());
        let text = fs::read_to_string(temporary.path().join(SEED_FILE)).expect("read seed");
        assert!(
            text.contains(&format!(
                "MANIFEST_PATH={}\n",
                out.join("manifest.json").display()
            )),
            "the Codex out-directory manifest wins: {text}"
        );
        assert!(text.contains("TOOL_LABEL=Codex\n"), "{text}");
    }

    #[test]
    fn tool_labels_map_every_routed_coder() {
        let temporary = tempfile::tempdir().expect("temporary dir");
        assert_eq!(tool_label(temporary.path()), "claude");
        for (coder, label) in [
            ("codex", "Codex"),
            ("cursor", "Cursor"),
            ("claude", "claude"),
            ("bogus", "claude"),
        ] {
            fs::write(
                temporary.path().join("bootstrap-routing.env"),
                format!("coder={coder}\n"),
            )
            .expect("routing");
            assert_eq!(tool_label(temporary.path()), label, "coder={coder}");
        }
    }

    #[test]
    fn a_symlinked_seed_file_is_not_read() {
        let temporary = tempfile::tempdir().expect("temporary dir");
        let target = temporary.path().join("elsewhere.env");
        fs::write(&target, "MANIFEST_PATH=/attacker\n").expect("target");
        #[cfg(unix)]
        std::os::unix::fs::symlink(&target, temporary.path().join(SEED_FILE)).expect("symlink");
        #[cfg(unix)]
        assert!(read_seed_lines(temporary.path()).is_empty());
    }
}
