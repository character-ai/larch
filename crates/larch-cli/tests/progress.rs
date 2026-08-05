//! End-to-end `progress` verb behavior that a parity golden cannot pin.
//!
//! Staleness depends on the breadcrumb log's mtime, and installation writes a
//! launcher whose body changes by design in this cutover, so both are asserted
//! against the real binary here rather than against the frozen Python reference.

use std::{
    fs,
    path::{Path, PathBuf},
    process::{Command, Stdio},
    time::UNIX_EPOCH,
};

use tempfile::TempDir;

struct Clone {
    sandbox: TempDir,
    path: PathBuf,
}

impl Clone {
    fn create() -> Self {
        let sandbox = TempDir::new().expect("sandbox");
        let path = sandbox.path().join("clone");
        fs::create_dir_all(&path).expect("clone directory");
        Self { sandbox, path }
    }

    fn cache_home(&self) -> PathBuf {
        self.sandbox.path().join("cache")
    }

    fn home(&self) -> PathBuf {
        self.sandbox.path().join("home")
    }

    fn payload(&self) -> String {
        format!(
            r#"{{"workspace": {{"current_dir": "{}"}}}}"#,
            self.path.display()
        )
    }

    fn run(&self, arguments: &[&str], now: Option<f64>, stdin: Option<&str>) -> Output {
        let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
        command
            .arg("progress")
            .args(arguments)
            .env("LARCH_TEST_CACHE_HOME", self.cache_home())
            .env("HOME", self.home())
            // No registry root exists, so no background job is ever live.
            .env(
                "LARCH_BGJOB_REGISTRY_ROOT",
                self.sandbox.path().join("no-registry"),
            )
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        if let Some(seconds) = now {
            command.env("LARCH_TEST_STATUSLINE_NOW", format!("{seconds:.6}"));
        }
        let mut child = command.spawn().expect("launch larch");
        {
            use std::io::Write as _;
            let mut pipe = child.stdin.take().expect("stdin pipe");
            pipe.write_all(stdin.unwrap_or_default().as_bytes())
                .expect("write stdin");
        }
        let finished = child.wait_with_output().expect("collect larch output");
        Output {
            code: finished.status.code().unwrap_or(-1),
            stdout: String::from_utf8_lossy(&finished.stdout).into_owned(),
        }
    }

    fn breadcrumb_log(&self) -> PathBuf {
        let digest = larch_core::progress_clone_digest(
            &fs::canonicalize(&self.path)
                .expect("canonical clone")
                .to_string_lossy(),
        );
        self.cache_home()
            .join("larch/progress")
            .join(digest)
            .join("run-1/breadcrumbs.log")
    }

    /// Return the breadcrumb log's mtime with sub-second precision.
    ///
    /// Whole seconds are not enough: an age computed from a truncated mtime
    /// lands just under each threshold and silently reads as fresh.
    fn log_mtime(&self) -> f64 {
        fs::metadata(self.breadcrumb_log())
            .expect("breadcrumb metadata")
            .modified()
            .expect("breadcrumb mtime")
            .duration_since(UNIX_EPOCH)
            .expect("epoch")
            .as_secs_f64()
    }
}

struct Output {
    code: i32,
    stdout: String,
}

#[test]
fn the_statusline_reports_active_stale_and_hidden_state() {
    let clone = Clone::create();
    let repo_root = clone.path.to_string_lossy().into_owned();

    assert_eq!(
        clone
            .run(
                &["activate", "--repo-root", &repo_root, "--run-id", "run-1"],
                None,
                None
            )
            .code,
        0
    );
    assert_eq!(
        clone
            .run(
                &[
                    "note",
                    "--repo-root",
                    &repo_root,
                    "--skill",
                    "implement",
                    "--step",
                    "5",
                    "code",
                    "review",
                    "started",
                ],
                None,
                None,
            )
            .code,
        0
    );
    let modified = clone.log_mtime();
    let payload = clone.payload();
    let render = |offset: f64| {
        clone
            .run(&["statusline"], Some(modified + offset), Some(&payload))
            .stdout
    };

    let active = render(0.0);
    assert!(
        active.contains("[implement 5] code review started"),
        "{active}"
    );
    assert!(!active.contains("stale"), "{active}");
    assert!(
        active.starts_with("\u{1b}[33m") && active.ends_with("\u{1b}[0m\n"),
        "{active}"
    );

    assert!(render(300.0).contains("(stale 5m)"));
    assert!(render(3599.0).contains("(stale 59m)"));
    assert_eq!(render(3600.0), "");

    // A torn final line still renders; a cleared pointer renders nothing.
    fs::write(clone.breadcrumb_log(), b"[implement 6] partial").expect("torn log");
    assert!(render(0.0).contains("[implement 6] partial"));

    assert_eq!(
        clone
            .run(&["clear", "--repo-root", &repo_root], None, None)
            .code,
        0
    );
    assert_eq!(render(0.0), "");
}

#[test]
fn installation_publishes_a_bootstrap_launcher_and_stays_idempotent() {
    let clone = Clone::create();
    let plugin_root = clone.sandbox.path().join("plugin");
    fs::create_dir_all(plugin_root.join("scripts")).expect("plugin scripts");
    fs::write(plugin_root.join("scripts/larch.sh"), "#!/bin/sh\n").expect("entrypoint");
    fs::create_dir_all(clone.home()).expect("home");
    let install = |extra: &[&str]| {
        let mut arguments = vec![
            "install-statusline",
            "--plugin-root",
            plugin_root.to_str().expect("plugin root text"),
            "--repo-root",
            clone.path.to_str().expect("clone text"),
        ];
        arguments.extend_from_slice(extra);
        clone.run(&arguments, None, None)
    };

    assert_eq!(install(&[]).code, 0);

    let launcher = clone.home().join(".cache/larch/statusline.sh");
    let launcher_text = fs::read_to_string(&launcher).expect("launcher");
    let settings_path = clone.path.join(".claude/settings.local.json");
    let settings = fs::read_to_string(&settings_path).expect("settings");

    assert!(
        launcher_text.contains("scripts/larch.sh progress statusline"),
        "the launcher must enter through the verified bootstrap script"
    );
    assert!(
        !launcher_text.contains("python3") && !launcher_text.contains("bin/larch"),
        "the launcher must not run Python or the installed binary directly"
    );
    assert!(settings.contains("statusLine"));
    assert!(settings.ends_with("}\n"));

    assert_eq!(install(&[]).code, 0);
    assert_eq!(
        fs::read_to_string(&settings_path).expect("settings"),
        settings
    );
    assert_eq!(
        fs::read_to_string(&launcher).expect("launcher"),
        launcher_text
    );

    // A non-larch clone-local statusline is never overwritten.
    fs::write(
        &settings_path,
        "{\n  \"statusLine\": {\n    \"command\": \"/usr/bin/mine\"\n  }\n}\n",
    )
    .expect("custom statusline");

    assert_eq!(install(&[]).code, 0);
    assert!(
        fs::read_to_string(&settings_path)
            .expect("settings")
            .contains("/usr/bin/mine")
    );

    // Invalid JSON is left byte for byte alone.
    fs::write(&settings_path, "{ not json").expect("invalid settings");

    assert_eq!(install(&[]).code, 0);
    assert_eq!(
        fs::read_to_string(&settings_path).expect("settings"),
        "{ not json"
    );
}

#[test]
fn the_disable_switch_keeps_session_reset_from_clearing_the_pointer() {
    let clone = Clone::create();
    let repo_root = clone.path.to_string_lossy().into_owned();
    assert_eq!(
        clone
            .run(
                &["activate", "--repo-root", &repo_root, "--run-id", "run-1"],
                None,
                None
            )
            .code,
        0
    );
    let pointer = clone
        .breadcrumb_log()
        .parent()
        .and_then(Path::parent)
        .expect("clone directory")
        .join("current");
    let payload = format!(
        r#"{{"workspace": {{"current_dir": "{}"}}, "source": "startup"}}"#,
        clone.path.display()
    );

    let disabled = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(["progress", "session-reset"])
        .env("LARCH_TEST_CACHE_HOME", clone.cache_home())
        .env("HOME", clone.home())
        .env("LARCH_STATUSLINE_DISABLE", "1")
        .stdin(Stdio::null())
        .output()
        .expect("run session-reset");

    assert!(disabled.status.success());
    assert!(
        pointer.is_file(),
        "the opt-out must leave the pointer alone"
    );

    assert_eq!(clone.run(&["session-reset"], None, Some(&payload)).code, 0);
    assert!(
        !pointer.exists(),
        "a startup payload must clear the active-run pointer"
    );
}
