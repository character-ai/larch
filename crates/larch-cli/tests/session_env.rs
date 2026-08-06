//! Session-env writer coverage that the byte-compared parity matrix cannot host.
//!
//! The parity harness refuses a command that creates a symlink, so the `/design`
//! pointer publication is compared here against the same frozen Python reference,
//! tree for tree. The remaining tests pin the confinement guard, the atomic
//! replacement guarantee, and the still-Python run-log delegation.

use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
    process::Command,
};
use tempfile::TempDir;

const REFERENCE: &str = "fixtures/rust-parity/session_env_reference.py";
/// A session directory whose name never matches the tmpdir redaction rules.
const SESSION: &str = "writer-session";
/// Argument placeholder each case expands to its own sandbox root.
const SANDBOX_TOKEN: &str = "%SANDBOX%";

#[derive(Debug, Eq, PartialEq)]
enum Entry {
    Symlink(String),
    File { text: String, mode: u32 },
}

/// One sandbox with the session directory both owners write into.
struct Sandbox {
    _directory: TempDir,
    root: PathBuf,
}

impl Sandbox {
    fn new() -> Self {
        // macOS resolves the default temporary root through `/var -> /private/var`,
        // and every writer refuses a symlinked ancestor, so anchor at a real root.
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

    /// Run one verb and return its exit code, stdout, and stderr.
    fn run(&self, program: &Program, arguments: &[&str]) -> (i32, String, String) {
        let mut command = program.command();
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

    /// Snapshot every file and symlink below the sandbox, root-normalized.
    fn snapshot(&self) -> BTreeMap<String, Entry> {
        let mut entries = BTreeMap::new();
        self.walk(&self.root, &mut entries);
        entries
    }

    fn walk(&self, directory: &Path, entries: &mut BTreeMap<String, Entry>) {
        let Ok(children) = fs::read_dir(directory) else {
            return;
        };
        for child in children.flatten() {
            let path = child.path();
            let key = self.normalize(&path.to_string_lossy());
            let metadata = fs::symlink_metadata(&path).expect("snapshot metadata");
            if metadata.file_type().is_symlink() {
                let target = fs::read_link(&path).expect("snapshot symlink target");
                entries.insert(
                    key,
                    Entry::Symlink(self.normalize(&target.to_string_lossy())),
                );
            } else if metadata.is_dir() {
                self.walk(&path, entries);
            } else {
                entries.insert(
                    key,
                    Entry::File {
                        text: self.normalize(&fs::read_to_string(&path).unwrap_or_default()),
                        mode: file_mode(&metadata),
                    },
                );
            }
        }
    }
}

/// One of the two owners under comparison.
enum Program {
    Python(PathBuf),
    Rust,
}

impl Program {
    fn command(&self) -> Command {
        match self {
            Self::Python(reference) => {
                let mut command = Command::new("python3");
                command.arg(reference);
                command
            }
            Self::Rust => {
                let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
                command.arg("session");
                command
            }
        }
    }
}

fn reference_script() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(REFERENCE)
        .canonicalize()
        .expect("frozen python reference")
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

/// Run one argument list through both owners and assert identical observable state.
fn assert_same(arguments: &[&str], seeds: &[(&str, &str)]) {
    let python = Sandbox::new();
    let rust = Sandbox::new();
    for (relative, contents) in seeds {
        python.seed(relative, contents);
        rust.seed(relative, contents);
    }
    let python_result = python.run(&Program::Python(reference_script()), arguments);
    let rust_result = rust.run(&Program::Rust, arguments);

    assert_eq!(
        python_result, rust_result,
        "streams differ for {arguments:?}"
    );
    assert_eq!(
        python.snapshot(),
        rust.snapshot(),
        "tree differs for {arguments:?}"
    );
}

#[test]
fn design_run_publishes_an_identical_tree_and_pointer() {
    assert_same(
        &[
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
        ],
        &[],
    );
}

#[test]
fn design_refresh_recovers_prior_values_from_the_replaced_env() {
    assert_same(
        &[
            "write-design-env",
            "--output",
            "%SANDBOX%/writer-session/source-env.sh",
            "--design-tmpdir",
            "%SANDBOX%/writer-session",
            "--session-id",
            "sid.2",
            "--claude-pid",
            "777",
        ],
        &[(
            "writer-session/source-env.sh",
            concat!(
                "#!/usr/bin/env bash\n",
                "export REPO_ROOT=/prior/root\n",
                "export LARCH_RUN_ID=prior-run\n",
                "export CODEX_BINARY_FOUND=true\n",
                "export CURSOR_BINARY_FOUND=false\n",
                "export LARCH_LIVE_MUTATION_OK=true\n",
            ),
        )],
    );
}

#[test]
fn design_run_without_a_pid_warns_and_publishes_the_legacy_pointer() {
    assert_same(
        &[
            "write-design-env",
            "--output",
            "%SANDBOX%/writer-session/source-env.sh",
            "--design-tmpdir",
            "%SANDBOX%/writer-session",
            "--session-id",
            "sid.3",
        ],
        &[],
    );
}

#[test]
fn implement_run_publishes_an_identical_pointer_launcher_and_flags() {
    assert_same(
        &[
            "write-implement-env",
            "--claude-pid",
            "4242",
            "--implement-tmpdir",
            "%SANDBOX%/writer-session",
            "--cwd",
            "%SANDBOX%",
        ],
        &[],
    );
    assert_same(
        &[
            "persist-run-flags",
            "--implement-tmpdir",
            "%SANDBOX%/writer-session",
            "--quick-mode",
            "false",
            "--no-issues",
            "false",
            "--force-requested",
            "true",
            "--self-review-requested",
            "true",
            "--self-implement-requested",
            "false",
        ],
        &[],
    );
}

#[test]
fn implement_pointer_clearing_removes_only_the_pid_keyed_file() {
    assert_same(
        &["clear-implement-pointer", "--claude-pid", "4242"],
        &[
            (
                ".home/.cache/larch/sessions/current-implement-env-4242.sh",
                "IMPLEMENT_TMPDIR=/tmp/writer-session\n",
            ),
            (
                ".home/.cache/larch/sessions/current-implement-env-4243.sh",
                "IMPLEMENT_TMPDIR=/tmp/other-session\n",
            ),
        ],
    );
}

#[test]
fn trusted_pointer_resolution_matches_the_published_target() {
    let python = Sandbox::new();
    let rust = Sandbox::new();
    for (sandbox, program) in [
        (&python, Program::Python(reference_script())),
        (&rust, Program::Rust),
    ] {
        let (code, _stdout, stderr) = sandbox.run(
            &program,
            &[
                "write-design-env",
                "--output",
                "%SANDBOX%/writer-session/source-env.sh",
                "--design-tmpdir",
                "%SANDBOX%/writer-session",
                "--session-id",
                "sid.4",
                "--claude-pid",
                "999",
            ],
        );
        assert_eq!(code, 0, "publish failed: {stderr}");
        let (code, stdout, stderr) = sandbox.run(
            &program,
            &[
                "resolve-trusted-design-env",
                "--session-env-path",
                "%SANDBOX%/.home/.cache/larch/sessions/current-design-env-999.sh",
                "--claude-pid",
                "999",
            ],
        );
        assert_eq!(code, 0, "resolve failed: {stderr}");
        assert_eq!(
            stdout,
            "TRUSTED_SOURCE=<SANDBOX>/writer-session/source-env.sh\n"
        );
    }
}

/// `AGENTS.md` forbids prompt-side writes to `$IMPLEMENT_TMPDIR/session-env.sh`.
/// The writer keeps that guard by refusing every target outside the session
/// roots, so no caller can reach the file through an unconfined path.
#[test]
fn session_env_writes_outside_the_session_roots_are_refused() {
    let sandbox = Sandbox::new();
    let (code, stdout, stderr) = sandbox.run(
        &Program::Rust,
        &[
            "write-env",
            "--output",
            "/larch-not-a-session-root/session-env.sh",
            "--repo-unavailable",
            "false",
        ],
    );

    assert_eq!(code, 1);
    assert_eq!(stdout, "");
    assert_eq!(
        stderr,
        "ERROR=output path not under allowed session root: /larch-not-a-session-root/session-env.sh\n"
    );
    assert!(!Path::new("/larch-not-a-session-root").exists());
}

/// A publication that fails after validation must leave the prior file whole,
/// which is what the temporary-file-then-rename discipline buys.
#[test]
fn a_refused_publication_leaves_the_prior_env_file_intact() {
    let sandbox = Sandbox::new();
    sandbox.seed("writer-session/session-env.sh", "REPO=prior/repo\n");
    let target = sandbox.path("writer-session/session-env.sh");
    let mode_before = file_mode(&fs::metadata(&target).expect("prior metadata"));

    let (code, _stdout, stderr) = sandbox.run(
        &Program::Rust,
        &[
            "write-env",
            "--output",
            "%SANDBOX%/writer-session/session-env.sh",
            "--repo-unavailable",
            "false",
            "--token-session-id",
            "not a valid id",
        ],
    );

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
    assert!(
        !sandbox.path("writer-session/session-env.sh.tmp").exists(),
        "a refused publication must not strand its temporary file"
    );
}

/// The durable bail reason still reaches the Python-owned `run-log write`.
///
/// That delegation retires when `run-log write` becomes Rust-owned (#7683).
#[test]
fn restoring_finalize_state_delegates_the_bail_reason_to_the_python_run_log_writer() {
    let sandbox = Sandbox::new();
    let recorded = sandbox.path("recorded-argv.txt");
    sandbox.seed(
        "python/cli.py",
        &format!(
            "import sys\nopen({:?}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n",
            recorded.to_string_lossy()
        ),
    );
    sandbox.seed(
        "writer-session/ship-pr-state.sh",
        "BRANCH_NAME=b1\nRUN_ID=run-abc\nBAIL_REASON=lint-fix-failed\n",
    );

    let output = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(["session", "restore-finalize-state", "--implement-tmpdir"])
        .arg(sandbox.path(SESSION))
        .current_dir(&sandbox.root)
        .env("HOME", sandbox.path(".home"))
        .env("TMPDIR", &sandbox.root)
        .env("CLAUDE_PLUGIN_ROOT", &sandbox.root)
        .output()
        .expect("run restore-finalize-state");

    assert!(
        output.status.success(),
        "restore failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(
        sandbox.text("writer-session/final-bail-reason.txt"),
        "lint-fix-failed"
    );
    let argv = fs::read_to_string(&recorded).expect("delegation must run");
    assert_eq!(
        sandbox.normalize(argv.trim_end()),
        format!(
            "run-log write --log-root <SANDBOX>/{SESSION}/larch-logs --skill implement --run-id run-abc --batch final-bail-reason --input-file <SANDBOX>/{SESSION}/final-bail-reason.txt"
        )
    );
}
