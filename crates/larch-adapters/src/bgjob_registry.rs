//! Read-only background-job registry liveness used by the larch statusline.
//!
//! This is the shared Rust reader for the `daemons/*.env` rows the bgjob
//! runtime writes. It answers exactly one question: does a heartbeat-fresh,
//! live job exist for this clone and run, so the statusline can
//! keep a long-running step visible without a staleness marker. The bgjob
//! command leaves extend this module rather than adding a second reader.

use crate::{read_first_raw_key, read_kv_raw};
use larch_core::{
    BGJOB_HEARTBEAT_STALE_AFTER_S, ProcessBirthIdentity, ProcessIdentityHost,
    ProcessIdentityValidationPolicy, RecordedProcessIdentity,
    validate_process_identity_with_policy,
};
use std::{
    fs,
    path::{Path, PathBuf},
    time::Duration,
};

/// Directory under the larch cache home that holds registry rows.
pub const REGISTRY_DIRNAME: &str = "daemons";
const BGJOB_TMP_SUBDIR: &str = "bgjob";
const SLUG_MAX_CHARS: usize = 97;
const HOOK_REGISTRY_ENTRY_LIMIT: usize = 4_096;
const HOOK_REGISTRY_ROW_MAX_BYTES: u64 = 65_536;

/// Failure to inspect a background-job registry for a clone-scoped hook.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegistryCloneScanError {
    /// The registry or requested clone root could not be inspected safely.
    UnreadableRoot,
    /// A regular registry row could not be read with the shared wire codec.
    UnreadableEntry,
    /// The registry exceeded the bounded hook scan.
    ScanLimitExceeded,
}

/// Return the first registry row whose canonical clone overlaps `clone_root`.
///
/// The hook needs only the `CLONE_PATH` field. This reader keeps the shared KV
/// codec as the sole owner of registry parsing without applying statusline
/// liveness requirements to an entry that the daemon still owns.
///
/// # Errors
///
/// Returns a stable error when an existing registry directory or regular
/// registry row cannot be read.
pub fn find_entry_for_clone(
    registry_root: &Path,
    clone_root: &Path,
) -> Result<Option<PathBuf>, RegistryCloneScanError> {
    let clone_root =
        fs::canonicalize(clone_root).map_err(|_| RegistryCloneScanError::UnreadableRoot)?;
    if !clone_root.is_dir() {
        return Err(RegistryCloneScanError::UnreadableRoot);
    }
    let entries = match fs::read_dir(registry_root) {
        Ok(entries) => entries,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err(RegistryCloneScanError::UnreadableRoot),
    };
    let mut paths = Vec::new();
    for entry in entries {
        let path = entry
            .map_err(|_| RegistryCloneScanError::UnreadableRoot)?
            .path();
        if path.extension().is_none_or(|value| value != "env") {
            continue;
        }
        if paths.len() >= HOOK_REGISTRY_ENTRY_LIMIT {
            return Err(RegistryCloneScanError::ScanLimitExceeded);
        }
        paths.push(path);
    }
    paths.sort();
    for path in paths {
        let Ok(metadata) = fs::symlink_metadata(&path) else {
            return Err(RegistryCloneScanError::UnreadableEntry);
        };
        if !metadata.file_type().is_file() {
            continue;
        }
        if metadata.len() > HOOK_REGISTRY_ROW_MAX_BYTES {
            return Err(RegistryCloneScanError::UnreadableEntry);
        }
        let raw_clone = read_first_raw_key(&path, "CLONE_PATH")
            .map_err(|_| RegistryCloneScanError::UnreadableEntry)?;
        let Some(raw_clone) = raw_clone.filter(|value| !value.is_empty()) else {
            continue;
        };
        let Ok(entry_clone) = fs::canonicalize(&raw_clone) else {
            continue;
        };
        if !entry_clone.is_dir() {
            continue;
        }
        if entry_clone == clone_root
            || entry_clone.starts_with(&clone_root)
            || clone_root.starts_with(&entry_clone)
        {
            return Ok(Some(path));
        }
    }
    Ok(None)
}

/// Narrow liveness port over one recorded process identity.
///
/// The registry reader needs only this question, so callers and tests are not
/// forced to supply the full process-identity host surface.
pub trait IdentityLiveness {
    /// Return whether the recorded identity still names the same live process.
    fn is_live(
        &self,
        recorded: &RecordedProcessIdentity,
        policy: ProcessIdentityValidationPolicy,
    ) -> bool;
}

/// Liveness answered by the shared process-identity validator.
pub struct HostLiveness<'host>(pub &'host dyn ProcessIdentityHost);

impl IdentityLiveness for HostLiveness<'_> {
    fn is_live(
        &self,
        recorded: &RecordedProcessIdentity,
        policy: ProcessIdentityValidationPolicy,
    ) -> bool {
        validate_process_identity_with_policy(self.0, recorded, policy).ok
    }
}

/// The registry fields that decide whether a row is live for one run.
struct RegistryEntry {
    run_id: String,
    clone_path: PathBuf,
    heartbeat_epoch: i64,
    daemon: RecordedProcessIdentity,
    child: RecordedProcessIdentity,
    child_allows_exec: bool,
}

/// Return whether a heartbeat-fresh, live background job owns `run_id` for a clone.
///
/// Any unreadable, malformed, or expired row is treated as not live, matching
/// the fail-silent Python reader this replaces.
#[must_use]
pub fn has_live_entry(
    registry_root: &Path,
    clone_root: &Path,
    run_id: &str,
    liveness: &dyn IdentityLiveness,
    now: f64,
) -> bool {
    if run_id.is_empty() || clone_root.as_os_str().is_empty() {
        return false;
    }
    let Ok(now_duration) = Duration::try_from_secs_f64(now) else {
        return false;
    };
    let Ok(now_epoch) = i64::try_from(now_duration.as_secs()) else {
        return false;
    };
    let Ok(entries) = fs::read_dir(registry_root) else {
        return false;
    };
    let mut paths: Vec<PathBuf> = entries
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| path.extension().is_some_and(|value| value == "env"))
        .collect();
    paths.sort();
    paths.iter().any(|path| {
        read_entry(path).is_some_and(|entry| {
            entry.run_id == run_id
                && now_epoch.saturating_sub(entry.heartbeat_epoch) <= BGJOB_HEARTBEAT_STALE_AFTER_S
                && entry.clone_path == clone_root
                && (liveness.is_live(
                    &entry.child,
                    if entry.child_allows_exec {
                        ProcessIdentityValidationPolicy::AllowCommandTransition
                    } else {
                        ProcessIdentityValidationPolicy::ExactCommand
                    },
                ) || liveness
                    .is_live(&entry.daemon, ProcessIdentityValidationPolicy::ExactCommand))
        })
    })
}

fn read_entry(path: &Path) -> Option<RegistryEntry> {
    if !fs::symlink_metadata(path).is_ok_and(|data| data.file_type().is_file()) {
        return None;
    }
    let rows = read_kv_raw(path).ok()?;
    validate_slug(field(&rows, "STEP")?)?;
    larch_core::validate_progress_run_id(field(&rows, "RUN_ID")?)?;
    let tmpdir = resolved_directory(field(&rows, "TMPDIR")?)?;
    let log_dir = resolved_directory(field(&rows, "LOG_DIR")?)?;
    // The registry row must still describe a coherent job tree; a row whose
    // logs or result env escaped their directories is not evidence of life.
    validated_child_path(field(&rows, "STDOUT_LOG")?, &log_dir)?;
    validated_child_path(field(&rows, "STDERR_LOG")?, &log_dir)?;
    validated_child_path(field(&rows, "RESULT_ENV")?, &tmpdir.join(BGJOB_TMP_SUBDIR))?;
    let start_epoch = field(&rows, "START_EPOCH")?.parse().ok()?;
    let _budget_s = field(&rows, "BUDGET_S")?.parse::<f64>().ok()?;
    Some(RegistryEntry {
        run_id: field(&rows, "RUN_ID")?.to_owned(),
        clone_path: fs::canonicalize(field(&rows, "CLONE_PATH").unwrap_or(".")).ok()?,
        heartbeat_epoch: field(&rows, "HEARTBEAT_EPOCH")
            .map_or(Some(start_epoch), |value| value.parse().ok())?,
        daemon: identity(&rows, "DAEMON")?,
        child: identity(&rows, "CHILD")?,
        child_allows_exec: field(&rows, "CHILD_ALLOW_COMMAND_TRANSITION")
            .is_none_or(|value| value == "true"),
    })
}

fn field<'a>(rows: &'a [(String, String)], key: &str) -> Option<&'a str> {
    rows.iter()
        .find(|(name, _value)| name == key)
        .map(|(_name, value)| value.as_str())
}

fn identity(rows: &[(String, String)], prefix: &str) -> Option<RecordedProcessIdentity> {
    Some(RecordedProcessIdentity {
        pid: field(rows, &format!("{prefix}_PID"))?.parse().ok()?,
        pgid: field(rows, &format!("{prefix}_PGID"))?.parse().ok()?,
        start_time: field(rows, &format!("{prefix}_START_TIME"))?.to_owned(),
        birth_identity: Some(ProcessBirthIdentity::parse_wire_value(field(
            rows,
            &format!("{prefix}_BIRTH_IDENTITY"),
        )?)?),
        command_signature: field(rows, &format!("{prefix}_COMMAND"))?.to_owned(),
        expected_signature: field(rows, &format!("{prefix}_EXPECTED"))
            .unwrap_or_default()
            .to_owned(),
    })
}

fn validate_slug(value: &str) -> Option<&str> {
    let mut characters = value.chars();
    let first = characters.next()?;
    if !first.is_ascii_lowercase() && !first.is_ascii_digit() {
        return None;
    }
    if value.chars().count() > SLUG_MAX_CHARS {
        return None;
    }
    characters
        .all(|character| {
            character.is_ascii_lowercase() || character.is_ascii_digit() || character == '-'
        })
        .then_some(value)
}

fn resolved_directory(raw: &str) -> Option<PathBuf> {
    let candidate = Path::new(raw);
    if fs::symlink_metadata(candidate).is_ok_and(|data| data.file_type().is_symlink()) {
        return None;
    }
    let resolved = fs::canonicalize(candidate).ok()?;
    resolved.is_dir().then_some(resolved)
}

fn validated_child_path(raw: &str, root: &Path) -> Option<PathBuf> {
    let candidate = Path::new(raw);
    if fs::symlink_metadata(candidate).is_ok_and(|data| data.file_type().is_symlink()) {
        return None;
    }
    let resolved = fs::canonicalize(candidate).ok()?;
    let root_resolved = fs::canonicalize(root).ok()?;
    resolved.starts_with(&root_resolved).then_some(resolved)
}

#[cfg(test)]
mod tests {
    use super::{IdentityLiveness, find_entry_for_clone, has_live_entry, validate_slug};
    use larch_core::{ProcessIdentityValidationPolicy, RecordedProcessIdentity};
    use std::{cell::RefCell, fs, path::Path};
    use tempfile::TempDir;

    struct LiveHost(bool);

    #[derive(Default)]
    struct PolicyHost(RefCell<Vec<ProcessIdentityValidationPolicy>>);

    impl IdentityLiveness for LiveHost {
        fn is_live(
            &self,
            _recorded: &RecordedProcessIdentity,
            _policy: larch_core::ProcessIdentityValidationPolicy,
        ) -> bool {
            self.0
        }
    }

    impl IdentityLiveness for PolicyHost {
        fn is_live(
            &self,
            _recorded: &RecordedProcessIdentity,
            policy: ProcessIdentityValidationPolicy,
        ) -> bool {
            self.0.borrow_mut().push(policy);
            true
        }
    }

    fn seed(sandbox: &Path, run_id: &str) -> std::path::PathBuf {
        let registry = sandbox.join("daemons");
        let tmpdir = sandbox.join("tmp");
        let log_dir = sandbox.join("logs");
        let clone = sandbox.join("clone");
        fs::create_dir_all(&registry).expect("registry");
        fs::create_dir_all(tmpdir.join("bgjob")).expect("bgjob");
        fs::create_dir_all(&log_dir).expect("logs");
        fs::create_dir_all(&clone).expect("clone");
        fs::write(log_dir.join("out.log"), "").expect("stdout");
        fs::write(log_dir.join("err.log"), "").expect("stderr");
        fs::write(tmpdir.join("bgjob/result.env"), "").expect("result");
        let identity = |prefix: &str| {
            format!(
                "{prefix}_PID=101\n{prefix}_PGID=4242\n{prefix}_START_TIME=Mon Aug  4 10:00:00 2026\n{prefix}_BIRTH_IDENTITY=darwin:1:101\n{prefix}_COMMAND=bash daemon\n{prefix}_EXPECTED=\n"
            )
        };
        let rows = format!(
            "STEP=step-5\nRUN_ID={run_id}\nTMPDIR={}\nLOG_DIR={}\nCLONE_PATH={}\nSTART_EPOCH=1000\nHEARTBEAT_EPOCH=1090\nBUDGET_S=600\nSTDOUT_LOG={}\nSTDERR_LOG={}\nRESULT_ENV={}\n{}{}",
            tmpdir.display(),
            log_dir.display(),
            clone.display(),
            log_dir.join("out.log").display(),
            log_dir.join("err.log").display(),
            tmpdir.join("bgjob/result.env").display(),
            identity("DAEMON"),
            identity("CHILD"),
        );
        fs::write(registry.join(format!("{run_id}-step-5.env")), rows).expect("entry");
        registry
    }

    #[test]
    fn a_live_heartbeat_fresh_row_for_this_clone_and_run_counts() {
        let sandbox = TempDir::new().expect("sandbox");
        let registry = seed(sandbox.path(), "run-1");
        let clone = fs::canonicalize(sandbox.path().join("clone")).expect("clone");

        assert!(has_live_entry(
            &registry,
            &clone,
            "run-1",
            &LiveHost(true),
            1100.0
        ));
        assert!(!has_live_entry(
            &registry,
            &clone,
            "run-2",
            &LiveHost(true),
            1100.0
        ));
        assert!(!has_live_entry(
            &registry,
            &clone,
            "run-1",
            &LiveHost(true),
            9000.0
        ));
        assert!(!has_live_entry(
            &registry,
            &clone,
            "run-1",
            &LiveHost(false),
            1100.0
        ));
        assert!(!has_live_entry(
            &registry,
            Path::new("/other/clone"),
            "run-1",
            &LiveHost(true),
            1100.0
        ));
    }

    #[test]
    fn a_fresh_heartbeat_survives_a_wall_jump_and_a_stale_one_expires() {
        let sandbox = TempDir::new().expect("sandbox");
        let registry = seed(sandbox.path(), "run-1");
        let clone = fs::canonicalize(sandbox.path().join("clone")).expect("clone");
        let row = registry.join("run-1-step-5.env");
        let jumped = fs::read_to_string(&row)
            .expect("registry row")
            .replace("HEARTBEAT_EPOCH=1090", "HEARTBEAT_EPOCH=14399");
        fs::write(&row, jumped).expect("fresh heartbeat");

        assert!(has_live_entry(
            &registry,
            &clone,
            "run-1",
            &LiveHost(true),
            14_400.0
        ));
        assert!(has_live_entry(
            &registry,
            &clone,
            "run-1",
            &LiveHost(true),
            14_000.0
        ));
        assert!(!has_live_entry(
            &registry,
            &clone,
            "run-1",
            &LiveHost(true),
            14_431.0
        ));
    }

    #[test]
    fn a_row_whose_directories_vanished_is_never_live() {
        let sandbox = TempDir::new().expect("sandbox");
        let registry = seed(sandbox.path(), "run-1");
        let clone = fs::canonicalize(sandbox.path().join("clone")).expect("clone");
        fs::remove_dir_all(sandbox.path().join("logs")).expect("remove logs");

        assert!(!has_live_entry(
            &registry,
            &clone,
            "run-1",
            &LiveHost(true),
            1100.0
        ));
        assert_eq!(validate_slug("step-5"), Some("step-5"));
        assert_eq!(validate_slug("-bad"), None);
        assert_eq!(validate_slug(""), None);
    }

    #[test]
    fn legacy_rows_without_birth_identity_are_not_live() {
        let sandbox = TempDir::new().expect("sandbox");
        let registry = seed(sandbox.path(), "run-1");
        let clone = fs::canonicalize(sandbox.path().join("clone")).expect("clone");
        let path = registry.join("run-1-step-5.env");
        let legacy = fs::read_to_string(&path)
            .expect("registry row")
            .lines()
            .filter(|line| !line.contains("_BIRTH_IDENTITY="))
            .collect::<Vec<_>>()
            .join("\n");
        fs::write(path, format!("{legacy}\n")).expect("legacy registry row");

        assert!(!has_live_entry(
            &registry,
            &clone,
            "run-1",
            &LiveHost(true),
            1100.0
        ));
    }

    #[test]
    fn markerless_rows_keep_the_exec_transition_policy() {
        let sandbox = TempDir::new().expect("sandbox");
        let registry = seed(sandbox.path(), "run-1");
        let clone = fs::canonicalize(sandbox.path().join("clone")).expect("clone");
        let host = PolicyHost::default();

        assert!(has_live_entry(&registry, &clone, "run-1", &host, 1100.0));
        assert_eq!(
            host.0.borrow().as_slice(),
            [ProcessIdentityValidationPolicy::AllowCommandTransition]
        );

        let row = registry.join("run-1-step-5.env");
        let marked = fs::read_to_string(&row).expect("registry row")
            + "CHILD_ALLOW_COMMAND_TRANSITION=false\n";
        fs::write(&row, marked).expect("explicit policy marker");
        host.0.borrow_mut().clear();
        assert!(has_live_entry(&registry, &clone, "run-1", &host, 1100.0));
        assert_eq!(
            host.0.borrow().as_slice(),
            [ProcessIdentityValidationPolicy::ExactCommand]
        );
    }

    #[test]
    fn clone_scan_uses_the_shared_codec_and_canonical_overlap() {
        let sandbox = TempDir::new().expect("sandbox");
        let registry = sandbox.path().join("registry");
        let clone = sandbox.path().join("clone");
        let child = clone.join("child");
        fs::create_dir_all(&registry).expect("registry");
        fs::create_dir_all(&child).expect("clone child");
        fs::write(
            registry.join("run.env"),
            format!("CLONE_PATH={}\n", clone.display()),
        )
        .expect("registry row");

        assert_eq!(
            find_entry_for_clone(&registry, &child)
                .expect("scan")
                .and_then(|path| path.file_name().map(ToOwned::to_owned)),
            Some("run.env".into())
        );
        assert!(
            find_entry_for_clone(&registry, sandbox.path())
                .expect("parent overlap")
                .is_some()
        );

        let other = sandbox.path().join("other");
        fs::create_dir(&other).expect("other clone");
        fs::write(
            registry.join("run.env"),
            format!(
                "CLONE_PATH={}\nCLONE_PATH={}\n",
                clone.display(),
                other.display()
            ),
        )
        .expect("duplicate registry row");
        assert!(
            find_entry_for_clone(&registry, &clone)
                .expect("first-value scan")
                .is_some()
        );
    }

    #[cfg(unix)]
    #[test]
    fn clone_scan_skips_symlinks_and_rejects_malformed_regular_rows() {
        let sandbox = TempDir::new().expect("sandbox");
        let registry = sandbox.path().join("registry");
        let clone = sandbox.path().join("clone");
        fs::create_dir_all(&registry).expect("registry");
        fs::create_dir_all(&clone).expect("clone");
        let target = sandbox.path().join("target.env");
        fs::write(&target, format!("CLONE_PATH={}\n", clone.display())).expect("target row");
        std::os::unix::fs::symlink(&target, registry.join("linked.env")).expect("registry symlink");
        assert!(
            find_entry_for_clone(&registry, &clone)
                .expect("symlink scan")
                .is_none()
        );

        fs::write(registry.join("broken.env"), "CLONE_PATH=bad\r\n").expect("broken row");
        assert!(find_entry_for_clone(&registry, &clone).is_err());

        fs::remove_file(registry.join("broken.env")).expect("remove broken row");
        fs::write(registry.join("oversized.env"), vec![b'x'; 65_537]).expect("oversized row");
        assert!(find_entry_for_clone(&registry, &clone).is_err());
    }
}
