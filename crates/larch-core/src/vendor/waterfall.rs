//! Shared tier-waterfall and token-sidecar planning primitives.

use crate::FailureClass;
use std::{
    collections::{BTreeMap, BTreeSet},
    error::Error,
    ffi::OsString,
    fmt,
    path::{Path, PathBuf},
};

/// Environment entries that must not leak into sidecar ingestion.
pub const TOKEN_SIDECAR_ENV_UNSET: [&str; 5] = [
    "LARCH_TOKEN_LEDGER",
    "LARCH_TOKEN_SESSION_ID",
    "DESIGN_TMPDIR",
    "RESEARCH_TMPDIR",
    "SESSION_ENV_PATH",
];

/// Input shared by each CI tier launcher.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TierLaunchInput<'a> {
    pub role: &'a str,
    pub output: &'a str,
    pub run_id: &'a str,
    pub repo: &'a str,
    pub plan_file: Option<&'a str>,
    pub failure_log: Option<&'a str>,
    pub conflict_files: Option<&'a str>,
    pub timeout_seconds: u64,
}

/// A requested tier does not have a CI launcher.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TierLaunchError {
    tier: String,
}

impl fmt::Display for TierLaunchError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "unknown tier: {}", self.tier)
    }
}

impl Error for TierLaunchError {}

/// Build the command arguments after the runtime entrypoint.
///
/// The caller owns the typed runtime program (`scripts/larch.sh` during Rust
/// ownership, or the temporary Python verb during staged migration).
///
/// # Errors
///
/// Returns [`TierLaunchError`] when `tier` has no registered CI launcher.
pub fn build_launch_argv(
    tier: &str,
    input: TierLaunchInput<'_>,
) -> Result<Vec<OsString>, TierLaunchError> {
    let verb = match tier {
        "cursor" => "launch-cursor-ci",
        "codex" => "launch-codex-ci",
        "claude" => "launch-claude-ci",
        _ => {
            return Err(TierLaunchError {
                tier: tier.to_owned(),
            });
        }
    };
    let mut argv = vec![
        OsString::from("agent"),
        OsString::from(verb),
        OsString::from("--role"),
        OsString::from(input.role),
        OsString::from("--output"),
        OsString::from(input.output),
        OsString::from("--run-id"),
        OsString::from(input.run_id),
        OsString::from("--repo"),
        OsString::from(input.repo),
        OsString::from("--timeout"),
        OsString::from(input.timeout_seconds.to_string()),
    ];
    for (flag, value) in [
        ("--plan-file", input.plan_file),
        ("--failure-log", input.failure_log),
        ("--conflict-files", input.conflict_files),
    ] {
        if let Some(value) = value.filter(|value| !value.is_empty()) {
            argv.extend([OsString::from(flag), OsString::from(value)]);
        }
    }
    Ok(argv)
}

/// Build and launch one tier through the caller's approved process adapter.
///
/// # Errors
///
/// Returns [`TierLaunchError`] when `tier` has no registered CI launcher.
pub fn launch_tier<T>(
    tier: &str,
    input: TierLaunchInput<'_>,
    launch: impl FnOnce(Vec<OsString>) -> T,
) -> Result<T, TierLaunchError> {
    Ok(launch(build_launch_argv(tier, input)?))
}

/// One completed waterfall tier attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TierAttempt {
    pub tier: String,
    pub wrapper_rc: i32,
    pub launcher_exit: i32,
    /// The effective class after any launcher-artifact override.
    pub failure_class: FailureClass,
}

/// Result of selecting a tier through the waterfall.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct WaterfallResult {
    pub winning_tier: Option<String>,
    pub attempts: Vec<TierAttempt>,
    pub short_circuited: bool,
}

/// Rotate the configured order to start with the requested available tier.
#[must_use]
pub fn ordered_tiers(tiers: &[String], first_tier: Option<&str>) -> Vec<String> {
    let Some(first_tier) = first_tier else {
        return tiers.to_vec();
    };
    let Some(start) = tiers.iter().position(|tier| tier == first_tier) else {
        return tiers.to_vec();
    };
    tiers[start..]
        .iter()
        .chain(&tiers[..start])
        .cloned()
        .collect()
}

/// Run ordered tiers, restoring the baseline after each failed attempt.
pub fn run_waterfall(
    tiers: &[String],
    first_tier: Option<&str>,
    mut launch: impl FnMut(&str) -> TierAttempt,
    mut restore_baseline: impl FnMut(),
) -> WaterfallResult {
    let mut attempts = Vec::new();
    for (index, tier) in ordered_tiers(tiers, first_tier).iter().enumerate() {
        let attempt = launch(tier);
        if attempt.wrapper_rc == 0 && attempt.launcher_exit == 0 {
            attempts.push(attempt);
            return WaterfallResult {
                winning_tier: Some(tier.clone()),
                attempts,
                short_circuited: false,
            };
        }
        let short_circuited =
            index == 0 && attempt.wrapper_rc == 0 && attempt.failure_class == FailureClass::Other;
        attempts.push(attempt);
        restore_baseline();
        if short_circuited {
            return WaterfallResult {
                winning_tier: None,
                attempts,
                short_circuited: true,
            };
        }
    }
    WaterfallResult {
        winning_tier: None,
        attempts,
        short_circuited: false,
    }
}

/// Remove stale ledgers and point sidecar ingestion at its active temporary root.
#[must_use]
pub fn token_sidecar_ingest_env(
    mut environment: BTreeMap<String, String>,
    implement_tmpdir: Option<&str>,
    tmpdir: Option<&str>,
    tmpdir_env_key: &str,
) -> BTreeMap<String, String> {
    for key in TOKEN_SIDECAR_ENV_UNSET {
        environment.remove(key);
    }
    if let Some(path) = implement_tmpdir.filter(|path| !path.is_empty()) {
        environment.insert("IMPLEMENT_TMPDIR".to_owned(), path.to_owned());
    } else if let Some(path) = tmpdir.filter(|path| !path.is_empty()) {
        environment.insert(tmpdir_env_key.to_owned(), path.to_owned());
    }
    environment
}

/// The two ledger operations required for one selected sidecar.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TokenSidecarIngest {
    pub token_record: PathBuf,
    /// Present only for the first record observed in an active temporary root.
    pub append_tmpdir: Option<PathBuf>,
}

/// Select a launcher token sidecar and plan its once-only append operation.
#[must_use]
pub fn ingest_launcher_token_sidecar(
    launcher_stdout: &str,
    output_fallback: Option<&Path>,
    output_fallback_nonempty: bool,
    ingest_tmpdir: Option<&Path>,
    seen: &mut BTreeSet<PathBuf>,
) -> Option<TokenSidecarIngest> {
    let stdout_record = launcher_stdout
        .lines()
        .find_map(|line| line.strip_prefix("TOKEN_RECORD="))
        .unwrap_or_default()
        .trim();
    let token_record = if stdout_record.is_empty() {
        output_fallback_nonempty
            .then(|| {
                output_fallback
                    .map(|output| PathBuf::from(format!("{}.token-record", output.display())))
            })
            .flatten()?
    } else {
        PathBuf::from(stdout_record)
    };
    let append_tmpdir = ingest_tmpdir
        .filter(|_| seen.insert(token_record.clone()))
        .map(Path::to_path_buf);
    Some(TokenSidecarIngest {
        token_record,
        append_tmpdir,
    })
}

#[cfg(test)]
mod tests {
    use super::{
        TierAttempt, TierLaunchInput, build_launch_argv, ingest_launcher_token_sidecar,
        ordered_tiers, run_waterfall, token_sidecar_ingest_env,
    };
    use crate::FailureClass;
    use std::{
        collections::{BTreeMap, BTreeSet},
        path::Path,
    };

    #[test]
    fn tier_argv_and_rotation_match_the_legacy_waterfall() {
        let input = TierLaunchInput {
            role: "fix",
            output: "/tmp/result",
            run_id: "run",
            repo: "owner/repo",
            plan_file: Some("/tmp/plan"),
            failure_log: None,
            conflict_files: Some("a,b"),
            timeout_seconds: 90,
        };
        assert_eq!(
            build_launch_argv("claude", input)
                .expect("known tier")
                .iter()
                .map(|value| value.to_string_lossy())
                .collect::<Vec<_>>(),
            [
                "agent",
                "launch-claude-ci",
                "--role",
                "fix",
                "--output",
                "/tmp/result",
                "--run-id",
                "run",
                "--repo",
                "owner/repo",
                "--timeout",
                "90",
                "--plan-file",
                "/tmp/plan",
                "--conflict-files",
                "a,b",
            ]
        );
        assert_eq!(
            ordered_tiers(
                &["codex".to_owned(), "cursor".to_owned(), "claude".to_owned()],
                Some("cursor"),
            ),
            ["cursor", "claude", "codex"]
        );
    }

    #[test]
    fn waterfall_reverts_failures_and_short_circuits_only_first_other() {
        let tiers = vec!["codex".to_owned(), "claude".to_owned()];
        let mut restored = 0;
        let result = run_waterfall(
            &tiers,
            None,
            |tier| TierAttempt {
                tier: tier.to_owned(),
                wrapper_rc: 0,
                launcher_exit: 1,
                failure_class: FailureClass::Other,
            },
            || restored += 1,
        );
        assert!(result.short_circuited);
        assert_eq!(result.attempts.len(), 1);
        assert_eq!(restored, 1);
    }

    #[test]
    fn waterfall_rotates_then_continues_after_later_other_failures() {
        let tiers = vec!["codex".to_owned(), "cursor".to_owned(), "claude".to_owned()];
        let mut launched = Vec::new();
        let mut restored = 0;
        let result = run_waterfall(
            &tiers,
            Some("cursor"),
            |tier| {
                launched.push(tier.to_owned());
                TierAttempt {
                    tier: tier.to_owned(),
                    wrapper_rc: 0,
                    launcher_exit: i32::from(tier != "codex"),
                    failure_class: if tier == "cursor" {
                        FailureClass::Health
                    } else {
                        FailureClass::Other
                    },
                }
            },
            || restored += 1,
        );
        assert_eq!(launched, ["cursor", "claude", "codex"]);
        assert_eq!(restored, 2);
        assert_eq!(result.winning_tier.as_deref(), Some("codex"));
        assert!(!result.short_circuited);
    }

    #[test]
    fn sidecar_ingestion_uses_the_first_wire_value_and_active_environment() {
        let mut seen = BTreeSet::new();
        let first = ingest_launcher_token_sidecar(
            "TOKEN_RECORD=/tmp/one\nTOKEN_RECORD=/tmp/two\n",
            None,
            false,
            Some(Path::new("/tmp/active")),
            &mut seen,
        )
        .expect("sidecar");
        assert_eq!(first.token_record, Path::new("/tmp/one"));
        assert_eq!(first.append_tmpdir, Some("/tmp/active".into()));
        assert!(
            ingest_launcher_token_sidecar(
                "TOKEN_RECORD=/tmp/one\n",
                None,
                false,
                Some(Path::new("/tmp/active")),
                &mut seen,
            )
            .expect("sidecar")
            .append_tmpdir
            .is_none()
        );
        let fallback = ingest_launcher_token_sidecar(
            "",
            Some(Path::new("/tmp/output")),
            true,
            Some(Path::new("/tmp/active")),
            &mut seen,
        )
        .expect("fallback sidecar");
        assert_eq!(fallback.token_record, Path::new("/tmp/output.token-record"));
        assert_eq!(fallback.append_tmpdir, Some("/tmp/active".into()));
        let env = token_sidecar_ingest_env(
            BTreeMap::from([
                ("LARCH_TOKEN_LEDGER".to_owned(), "stale".to_owned()),
                ("SESSION_ENV_PATH".to_owned(), "stale".to_owned()),
            ]),
            None,
            Some("/tmp/active"),
            "REVIEW_TMPDIR",
        );
        assert_eq!(
            env,
            BTreeMap::from([("REVIEW_TMPDIR".to_owned(), "/tmp/active".to_owned())])
        );
    }
}
