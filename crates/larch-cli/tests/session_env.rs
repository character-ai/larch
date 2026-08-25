//! Native session-environment writer and confinement coverage.

use std::{fs, path::PathBuf, process::Command};
use tempfile::TempDir;

const SESSION: &str = "writer-session";
const SANDBOX_TOKEN: &str = "%SANDBOX%";

struct Sandbox {
    _directory: TempDir,
    root: PathBuf,
}

impl Sandbox {
    fn new() -> Self {
        let directory = tempfile::Builder::new()
            .prefix("larch-session-env-")
            .tempdir_in(real_temporary_root())
            .expect("session-env sandbox");
        let root = directory.path().to_path_buf();
        fs::create_dir_all(root.join(SESSION)).expect("session directory");
        fs::create_dir_all(root.join(".home/.cache/larch/sessions")).expect("home sessions");
        Self {
            _directory: directory,
            root,
        }
    }

    fn path(&self, relative: &str) -> PathBuf {
        self.root.join(relative)
    }

    fn text(&self, relative: &str) -> String {
        fs::read_to_string(self.path(relative)).unwrap_or_default()
    }

    fn seed(&self, relative: &str, contents: &str) {
        let path = self.path(relative);
        fs::create_dir_all(path.parent().expect("seed parent")).expect("seed directories");
        fs::write(path, contents).expect("seed file");
    }

    fn run(&self, arguments: &[&str]) -> (i32, String, String) {
        let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
        command.arg("session");
        for argument in arguments {
            command.arg(argument.replace(SANDBOX_TOKEN, &self.root.to_string_lossy()));
        }
        let output = command
            .current_dir(&self.root)
            .env("HOME", self.path(".home"))
            .env("TMPDIR", &self.root)
            .env("CLAUDE_PLUGIN_ROOT", "/opt/larch")
            .env_remove("XDG_CACHE_HOME")
            .env_remove("CLAUDE_PROJECT_DIR")
            .env_remove("REPO_ROOT")
            .env_remove("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT")
            .output()
            .expect("run session verb");
        (
            output.status.code().unwrap_or(-1),
            self.normalize(&String::from_utf8_lossy(&output.stdout)),
            self.normalize(&String::from_utf8_lossy(&output.stderr)),
        )
    }

    fn normalize(&self, text: &str) -> String {
        text.replace(&*self.root.to_string_lossy(), "<SANDBOX>")
    }
}

fn real_temporary_root() -> PathBuf {
    std::env::temp_dir()
        .canonicalize()
        .unwrap_or_else(|_error| std::env::temp_dir())
}

#[cfg(unix)]
fn file_mode(metadata: &fs::Metadata) -> u32 {
    use std::os::unix::fs::PermissionsExt as _;
    metadata.permissions().mode() & 0o777
}

#[cfg(not(unix))]
const fn file_mode(_metadata: &fs::Metadata) -> u32 {
    0
}

#[test]
fn design_run_publishes_and_resolves_the_pid_keyed_pointer() {
    let sandbox = Sandbox::new();
    let (code, _stdout, stderr) = sandbox.run(&[
        "write-design-env",
        "--output",
        "%SANDBOX%/writer-session/source-env.sh",
        "--design-tmpdir",
        "%SANDBOX%/writer-session",
        "--session-id",
        "sid.1",
        "--run-id",
        "run-7",
        "--claude-pid",
        "4242",
        "--repo",
        "character-ai/larch",
        "--repo-root",
        "/repo/root",
        "--issue-number",
        "8058",
        "--codex-binary-found",
        "true",
        "--live-mutation-ok",
        "true",
    ]);
    assert_eq!(code, 0, "publish failed: {stderr}");

    let (code, stdout, stderr) = sandbox.run(&[
        "resolve-trusted-design-env",
        "--session-env-path",
        "%SANDBOX%/.home/.cache/larch/sessions/current-design-env-4242.sh",
        "--claude-pid",
        "4242",
    ]);
    assert_eq!(code, 0, "resolve failed: {stderr}");
    assert_eq!(
        stdout,
        "TRUSTED_SOURCE=<SANDBOX>/writer-session/source-env.sh\n"
    );
}

#[test]
fn session_env_writes_outside_the_session_roots_are_refused() {
    let sandbox = Sandbox::new();
    let (code, stdout, stderr) = sandbox.run(&[
        "write-env",
        "--output",
        "/larch-not-a-session-root/session-env.sh",
        "--repo-unavailable",
        "false",
    ]);

    assert_eq!(code, 1);
    assert_eq!(stdout, "");
    assert_eq!(
        stderr,
        "ERROR=output path not under allowed session root: /larch-not-a-session-root/session-env.sh\n"
    );
    assert!(!PathBuf::from("/larch-not-a-session-root").exists());
}

#[test]
fn a_refused_publication_leaves_the_prior_env_file_intact() {
    let sandbox = Sandbox::new();
    sandbox.seed("writer-session/session-env.sh", "REPO=prior/repo\n");
    let target = sandbox.path("writer-session/session-env.sh");
    let mode_before = file_mode(&fs::metadata(&target).expect("prior metadata"));

    let (code, _stdout, stderr) = sandbox.run(&[
        "write-env",
        "--output",
        "%SANDBOX%/writer-session/session-env.sh",
        "--repo-unavailable",
        "false",
        "--token-session-id",
        "not a valid id",
    ]);

    assert_eq!(code, 1);
    assert!(
        stderr.starts_with("ERROR=Invalid --token-session-id"),
        "{stderr}"
    );
    assert_eq!(
        sandbox.text("writer-session/session-env.sh"),
        "REPO=prior/repo\n"
    );
    assert_eq!(
        file_mode(&fs::metadata(&target).expect("surviving metadata")),
        mode_before
    );
    assert!(!sandbox.path("writer-session/session-env.sh.tmp").exists());
}
