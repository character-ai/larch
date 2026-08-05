//! Statusline rendering, session reset, and clone-local installation effects.
//!
//! `render` runs on a Claude Code hot path, so it reads at most one breadcrumb
//! log and probes background-job liveness only once a log is already stale.
//! Every entry point is fail silent: any unsafe, missing, or corrupt input
//! renders an empty line rather than failing the session.

use crate::{
    PathIntent, SystemProcessIdentityHost, TemporaryRoot, atomic_write_utf8, bgjob_registry,
    ensure_directory_chain,
    progress_state::{self, ProgressPaths},
};
use chrono::{DateTime, Local};
use larch_core::{
    DEFAULT_HIDE_AFTER_S, DEFAULT_STALE_AFTER_S, MAX_STATUSLINE_LINES, RUN_BREADCRUMB_FILENAME,
    StalenessDecision, apply_statusline, chained_user_command, classify_staleness,
    is_breadcrumb_row, is_larch_statusline_command, positive_int, render_statusline_body,
    resets_active_run, settings_statusline_command, stale_suffix, statusline_launcher_text,
    statusline_payload_directory,
};
use serde_json::Value;
use std::{
    fs,
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};

/// Ambient inputs one statusline invocation reads, captured by the caller.
#[derive(Clone, Debug)]
pub struct StatuslineEnvironment {
    /// Resolved larch cache home holding progress state.
    pub cache_home: PathBuf,
    /// Background-job registry root, when overridden.
    pub bgjob_registry_root: Option<PathBuf>,
    /// Rendered line budget from `LARCH_STATUSLINE_LINES`.
    pub lines: Option<String>,
    /// Stale threshold override in seconds.
    pub stale_after_s: Option<String>,
    /// Hide threshold override in seconds.
    pub hide_after_s: Option<String>,
    /// Terminal width from `COLUMNS`; zero disables truncation.
    pub columns: Option<String>,
    /// Frozen clock in Unix seconds used by offline harnesses.
    pub now_override: Option<String>,
}

/// Why an installation attempt did not publish a larch statusline.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InstallRefusal {
    /// A path on the write route was unsafe or a write failed.
    UnsafePath,
    /// The clone-local settings file was not a JSON object.
    InvalidSettings,
    /// A non-larch clone-local statusline already owns the slot.
    CustomStatusline,
}

/// Outcome of one clone-local statusline installation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InstallOutcome {
    /// The launcher and settings entry are published.
    Installed {
        /// Whether this call introduced the clone's first larch statusline.
        first_install: bool,
    },
    /// Nothing was published, for the stated reason.
    Refused(InstallRefusal),
}

/// Render the larch statusline for one Claude Code payload.
///
/// Returns an empty string whenever nothing should be shown.
#[must_use]
pub fn render(payload: &str, environment: &StatuslineEnvironment) -> String {
    let Some(directory) = statusline_payload_directory(payload) else {
        return String::new();
    };
    let paths = progress_state::progress_paths(&environment.cache_home, Path::new(&directory));
    let Some(run_id) = progress_state::read_active_run_id(&paths) else {
        return String::new();
    };
    let line_count = positive_int(environment.lines.as_deref(), 1, Some(MAX_STATUSLINE_LINES));
    let log = paths.run_breadcrumbs(&run_id);
    let Some(text) = read_breadcrumb_log(&paths, &run_id) else {
        return String::new();
    };
    let rows: Vec<&str> = text
        .lines()
        .filter(|line| is_breadcrumb_row(line))
        .collect();
    let usize_count = usize::try_from(line_count).unwrap_or(usize::MAX);
    let rows = &rows[rows.len().saturating_sub(usize_count)..];
    if rows.is_empty() {
        return String::new();
    }
    let now = environment
        .now_override
        .as_deref()
        .and_then(|value| value.parse::<f64>().ok())
        .unwrap_or_else(unix_now);
    let Some(modified) = modified_seconds(&log) else {
        return String::new();
    };
    let Some(suffix) = age_suffix(&paths, &run_id, environment, now - modified) else {
        return String::new();
    };
    let stamp = local_stamp(modified.max(0.0));
    let columns = usize::try_from(positive_int(environment.columns.as_deref(), 0, None))
        .unwrap_or(usize::MAX);
    render_statusline_body(rows, &stamp, &suffix, columns)
}

/// Clear a stale active-run pointer when a fresh session starts.
///
/// Returns whether the pointer was cleared.
#[must_use]
pub fn session_reset(payload: &str, environment: &StatuslineEnvironment) -> bool {
    if !resets_active_run(payload) {
        return false;
    }
    let Some(directory) = statusline_payload_directory(payload) else {
        return false;
    };
    let paths = progress_state::progress_paths(&environment.cache_home, Path::new(&directory));
    let Some(run_id) = progress_state::read_active_run_id(&paths) else {
        return false;
    };
    if has_live_bgjob(&paths, &run_id, environment) {
        return false;
    }
    progress_state::deactivate_run(&paths, &run_id)
}

/// Idempotently merge the larch statusline into one clone's local settings.
///
/// `launcher` is the stable `~/.cache/larch/statusline.sh` path, and
/// `larch_entrypoint` is the verified bootstrap script the launcher executes.
#[must_use]
pub fn install(
    repo_root: &Path,
    plugin_root: &Path,
    launcher: &Path,
    larch_entrypoint: &Path,
    user_settings: Option<&Path>,
) -> InstallOutcome {
    let settings_path = repo_root.join(larch_core::STATUSLINE_LOCAL_SETTINGS);
    if !safe_existing_file(&settings_path) || !safe_existing_file(launcher) {
        return InstallOutcome::Refused(InstallRefusal::UnsafePath);
    }
    let chained = match user_settings.map(read_json_object) {
        Some(SettingsRead::Object(settings)) => chained_user_command(&settings),
        _other => String::new(),
    };
    let launcher_text = statusline_launcher_text(
        &plugin_root.to_string_lossy(),
        &larch_entrypoint.to_string_lossy(),
        &chained,
    );
    if write_confined(launcher, &launcher_text, 0o755).is_err() {
        return InstallOutcome::Refused(InstallRefusal::UnsafePath);
    }
    let mut settings = match read_json_object(&settings_path) {
        SettingsRead::Absent => Value::Object(serde_json::Map::new()),
        SettingsRead::Object(value) => value,
        SettingsRead::Unusable => {
            return InstallOutcome::Refused(InstallRefusal::InvalidSettings);
        }
    };
    let current = settings_statusline_command(&settings).to_owned();
    if !current.is_empty() && !is_larch_statusline_command(&current) {
        return InstallOutcome::Refused(InstallRefusal::CustomStatusline);
    }
    apply_statusline(&mut settings, &launcher.to_string_lossy());
    let Ok(rendered) = serde_json::to_string_pretty(&settings) else {
        return InstallOutcome::Refused(InstallRefusal::InvalidSettings);
    };
    if write_confined(&settings_path, &format!("{rendered}\n"), 0o600).is_err() {
        return InstallOutcome::Refused(InstallRefusal::UnsafePath);
    }
    InstallOutcome::Installed {
        first_install: current.is_empty(),
    }
}

/// Publish the one-time first-install notice sentinel.
///
/// Returns whether this call created it, so the caller announces the notice
/// exactly once. An existing entry of any type, including a symlink, is left
/// alone: the sentinel is written through the same confinement as every other
/// installer target and never follows a link.
#[must_use]
pub fn publish_notice_sentinel(sentinel: &Path) -> bool {
    if fs::symlink_metadata(sentinel).is_ok() {
        return false;
    }
    write_confined(sentinel, "installed\n", 0o600).is_ok()
}

fn read_breadcrumb_log(paths: &ProgressPaths, run_id: &str) -> Option<String> {
    let root = TemporaryRoot::resolve(Some(paths.clone_dir())).ok()?;
    let target = root.path().join(run_id).join(RUN_BREADCRUMB_FILENAME);
    let confined = root.confine(target, PathIntent::Read).ok()?;
    fs::read(confined.path())
        .ok()
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
}

fn age_suffix(
    paths: &ProgressPaths,
    run_id: &str,
    environment: &StatuslineEnvironment,
    age: f64,
) -> Option<String> {
    #[expect(
        clippy::cast_possible_truncation,
        clippy::cast_sign_loss,
        reason = "the age is clamped to a non-negative whole-second count first"
    )]
    let age_s = age.max(0.0).trunc() as u64;
    let decision = classify_staleness(
        age_s,
        positive_int(
            environment.stale_after_s.as_deref(),
            DEFAULT_STALE_AFTER_S,
            None,
        ),
        positive_int(
            environment.hide_after_s.as_deref(),
            DEFAULT_HIDE_AFTER_S,
            None,
        ),
    );
    match decision {
        StalenessDecision::Fresh => Some(String::new()),
        // A live background job keeps a long-running step visible without a
        // staleness marker, so liveness is probed only past the threshold.
        _ if has_live_bgjob(paths, run_id, environment) => Some(String::new()),
        StalenessDecision::Stale(minutes) => Some(stale_suffix(minutes)),
        StalenessDecision::Hidden => None,
    }
}

fn has_live_bgjob(
    paths: &ProgressPaths,
    run_id: &str,
    environment: &StatuslineEnvironment,
) -> bool {
    let Some(root) = environment.bgjob_registry_root.clone().or_else(|| {
        paths
            .clone_dir()
            .parent()
            .and_then(Path::parent)
            .map(|larch| larch.join(bgjob_registry::REGISTRY_DIRNAME))
    }) else {
        return false;
    };
    let host = SystemProcessIdentityHost::new();
    bgjob_registry::has_live_entry(
        &root,
        paths.clone_identity(),
        run_id,
        &bgjob_registry::HostLiveness(&host),
        unix_now(),
    )
}

fn modified_seconds(path: &Path) -> Option<f64> {
    let modified = fs::metadata(path).ok()?.modified().ok()?;
    modified
        .duration_since(UNIX_EPOCH)
        .ok()
        .map(|elapsed| elapsed.as_secs_f64())
}

fn unix_now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0.0, |elapsed| elapsed.as_secs_f64())
}

fn local_stamp(seconds: f64) -> String {
    #[expect(
        clippy::cast_possible_truncation,
        reason = "Unix seconds fit an i64 for every representable statusline stamp"
    )]
    let stamp =
        DateTime::from_timestamp(seconds.trunc() as i64, 0).map(|utc| utc.with_timezone(&Local));
    stamp.map_or_else(String::new, |local| local.format("%H:%M").to_string())
}

fn safe_existing_file(path: &Path) -> bool {
    match fs::symlink_metadata(path) {
        Ok(metadata) => metadata.file_type().is_file(),
        Err(_error) => true,
    }
}

/// What one settings file read found.
enum SettingsRead {
    /// The file does not exist, so an empty document is the starting point.
    Absent,
    /// The file holds a JSON object.
    Object(Value),
    /// The file is unreadable, symlinked, or not a JSON object.
    Unusable,
}

fn read_json_object(path: &Path) -> SettingsRead {
    match fs::symlink_metadata(path) {
        Err(_error) => SettingsRead::Absent,
        Ok(metadata) if !metadata.file_type().is_file() => SettingsRead::Unusable,
        Ok(_) => match fs::read_to_string(path).map(|text| serde_json::from_str::<Value>(&text)) {
            Ok(Ok(value @ Value::Object(_))) => SettingsRead::Object(value),
            _other => SettingsRead::Unusable,
        },
    }
}

fn write_confined(path: &Path, text: &str, mode: u32) -> Result<(), String> {
    let parent = path
        .parent()
        .ok_or_else(|| "statusline target has no parent".to_owned())?;
    ensure_directory_chain(parent)
        .map_err(|error| format!("statusline parent creation failed: {error}"))?;
    let root = TemporaryRoot::resolve(Some(parent))
        .map_err(|error| format!("unsafe statusline parent: {error}"))?;
    let Some(name) = path.file_name() else {
        return Err("statusline target has no basename".to_owned());
    };
    let confined = root
        .confine(root.path().join(name), PathIntent::Write)
        .map_err(|error| format!("unsafe statusline target: {error}"))?;
    atomic_write_utf8(&confined, text, mode)
        .map_err(|error| format!("statusline write failed: {error}"))
}

#[cfg(test)]
mod tests {
    use super::{
        InstallOutcome, InstallRefusal, StatuslineEnvironment, install, render, session_reset,
    };
    use crate::progress_state::{self, activate_run};
    use std::{fs, path::PathBuf};
    use tempfile::TempDir;

    fn environment(cache_home: &std::path::Path, now: &str) -> StatuslineEnvironment {
        StatuslineEnvironment {
            cache_home: cache_home.to_path_buf(),
            bgjob_registry_root: Some(cache_home.join("missing-registry")),
            lines: None,
            stale_after_s: None,
            hide_after_s: None,
            columns: None,
            now_override: Some(now.to_owned()),
        }
    }

    fn payload(directory: &std::path::Path) -> String {
        sourced_payload(directory, None)
    }

    fn sourced_payload(directory: &std::path::Path, source: Option<&str>) -> String {
        let mut document = serde_json::json!({
            "workspace": {"current_dir": directory.to_string_lossy()},
        });
        if let (Some(source), Some(object)) = (source, document.as_object_mut()) {
            let _replaced = object.insert("source".to_owned(), serde_json::json!(source));
        }
        document.to_string()
    }

    #[test]
    fn an_active_run_renders_its_last_breadcrumb() {
        let sandbox = TempDir::new().expect("sandbox");
        let clone = sandbox.path().join("clone");
        fs::create_dir_all(&clone).expect("clone");
        let paths = progress_state::progress_paths(sandbox.path(), &clone);
        activate_run(&paths, "run-1").expect("activate");
        assert!(progress_state::append_breadcrumb(
            &paths,
            "implement",
            "5",
            "code review started"
        ));
        let log = paths.run_breadcrumbs("run-1");
        let modified = fs::metadata(&log)
            .expect("metadata")
            .modified()
            .expect("mtime")
            .duration_since(std::time::UNIX_EPOCH)
            .expect("epoch")
            .as_secs();

        let fresh = render(
            &payload(&clone),
            &environment(sandbox.path(), &modified.to_string()),
        );

        assert!(fresh.contains("[implement 5] code review started"));
        assert!(!fresh.contains("stale"));

        let stale = render(
            &payload(&clone),
            &environment(sandbox.path(), &(modified + 400).to_string()),
        );

        assert!(stale.contains("(stale 6m)"));

        let hidden = render(
            &payload(&clone),
            &environment(sandbox.path(), &(modified + 4000).to_string()),
        );

        assert_eq!(hidden, "");
    }

    #[test]
    fn missing_torn_and_unparsable_state_render_nothing() {
        let sandbox = TempDir::new().expect("sandbox");
        let clone = sandbox.path().join("clone");
        fs::create_dir_all(&clone).expect("clone");
        let paths = progress_state::progress_paths(sandbox.path(), &clone);
        let environment = environment(sandbox.path(), "1000");

        assert_eq!(render(&payload(&clone), &environment), "");
        assert_eq!(render("not json", &environment), "");
        assert_eq!(render("{}", &environment), "");

        activate_run(&paths, "run-1").expect("activate");

        assert_eq!(render(&payload(&clone), &environment), "");

        let log = paths.run_breadcrumbs("run-1");
        fs::write(&log, b"[implement 5] partial line without a newline").expect("torn log");

        assert!(render(&payload(&clone), &environment).contains("partial line"));

        fs::write(&log, b"\xff\xfe not a breadcrumb\n").expect("binary log");

        assert_eq!(render(&payload(&clone), &environment), "");
    }

    #[test]
    fn session_reset_clears_only_a_startup_payload() {
        let sandbox = TempDir::new().expect("sandbox");
        let clone = sandbox.path().join("clone");
        fs::create_dir_all(&clone).expect("clone");
        let paths = progress_state::progress_paths(sandbox.path(), &clone);
        activate_run(&paths, "run-1").expect("activate");
        let environment = environment(sandbox.path(), "1000");
        let with_source = |source: &str| sourced_payload(&clone, Some(source));

        assert!(!session_reset(&payload(&clone), &environment));
        assert!(!session_reset(&with_source("resume"), &environment));
        assert_eq!(
            progress_state::read_active_run_id(&paths).as_deref(),
            Some("run-1")
        );
        assert!(session_reset(&with_source("startup"), &environment));
        assert_eq!(progress_state::read_active_run_id(&paths), None);
    }

    #[test]
    fn the_notice_sentinel_is_written_once_and_never_through_a_symlink() {
        let sandbox = TempDir::new().expect("sandbox");
        let sentinel = sandbox.path().join("cache/.statusline-install-notice");
        let decoy = sandbox.path().join("decoy");

        assert!(super::publish_notice_sentinel(&sentinel));
        assert_eq!(
            fs::read_to_string(&sentinel).expect("sentinel"),
            "installed\n"
        );
        assert!(!super::publish_notice_sentinel(&sentinel));

        let planted = sandbox.path().join("cache/planted-notice");
        std::os::unix::fs::symlink(&decoy, &planted).expect("dangling symlink");

        assert!(!super::publish_notice_sentinel(&planted));
        assert!(!decoy.exists(), "a dangling symlink must not be followed");
    }

    #[test]
    fn installation_is_idempotent_and_never_overwrites_a_custom_statusline() {
        let sandbox = TempDir::new().expect("sandbox");
        let clone = sandbox.path().join("clone/.claude");
        fs::create_dir_all(&clone).expect("clone");
        let repo_root = sandbox.path().join("clone");
        let plugin_root = sandbox.path().join("plugin");
        fs::create_dir_all(plugin_root.join("scripts")).expect("plugin");
        let entrypoint = plugin_root.join("scripts/larch.sh");
        fs::write(&entrypoint, "#!/bin/sh\n").expect("entrypoint");
        let launcher = sandbox.path().join(".cache/larch/statusline.sh");
        fs::create_dir_all(launcher.parent().expect("parent")).expect("cache");
        let settings = repo_root.join(".claude/settings.local.json");
        let user_settings: Option<PathBuf> = None;

        let first = install(
            &repo_root,
            &plugin_root,
            &launcher,
            &entrypoint,
            user_settings.as_deref(),
        );

        assert_eq!(
            first,
            InstallOutcome::Installed {
                first_install: true
            }
        );
        let published = fs::read_to_string(&settings).expect("settings");
        assert!(published.contains("statusLine"));
        assert!(
            fs::read_to_string(&launcher)
                .expect("launcher")
                .contains("progress statusline")
        );

        let second = install(
            &repo_root,
            &plugin_root,
            &launcher,
            &entrypoint,
            user_settings.as_deref(),
        );

        assert_eq!(
            second,
            InstallOutcome::Installed {
                first_install: false
            }
        );
        assert_eq!(fs::read_to_string(&settings).expect("settings"), published);

        fs::write(
            &settings,
            r#"{"statusLine": {"type": "command", "command": "/usr/bin/mine"}}"#,
        )
        .expect("custom");

        assert_eq!(
            install(
                &repo_root,
                &plugin_root,
                &launcher,
                &entrypoint,
                user_settings.as_deref()
            ),
            InstallOutcome::Refused(InstallRefusal::CustomStatusline)
        );

        fs::write(&settings, "{ not json").expect("invalid");

        assert_eq!(
            install(
                &repo_root,
                &plugin_root,
                &launcher,
                &entrypoint,
                user_settings.as_deref()
            ),
            InstallOutcome::Refused(InstallRefusal::InvalidSettings)
        );
    }
}
