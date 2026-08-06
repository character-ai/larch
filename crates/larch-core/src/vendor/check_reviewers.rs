//! Reviewer availability result types and probe-budget helpers for #8108.
//!
//! Live probing lives in the adapters layer over [`ProbeCache`] and the
//! approved process runner. This module owns the result envelope and the
//! timeout/retry budget resolution that every probe path shares.

use crate::{
    CodexGateDetail, ExternalAuthVerdict, PROBE_AUTH_RETRY_RC, ProbeRetryLimits,
    transient_probe_retries,
};
use std::path::{Component, Path, PathBuf};

/// Process exit code Python mapped for a timed-out probe child.
pub const PROBE_TIMEOUT_EXIT_CODE: i32 = 124;

/// Result of `agent check-reviewers`.
#[allow(clippy::struct_excessive_bools)] // mirrors the Python KV presence/binary/timeout hexad
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CheckReviewersResult {
    codex_binary_found: bool,
    cursor_binary_found: bool,
    codex_present: bool,
    cursor_present: bool,
    codex_probe_timed_out: bool,
    cursor_probe_timed_out: bool,
    codex_gate_detail: Option<CodexGateDetail>,
}

impl CheckReviewersResult {
    /// Build a result from resolved probe outcomes.
    #[must_use]
    #[allow(clippy::fn_params_excessive_bools)] // one arg per Python CheckReviewersResult field
    pub const fn new(
        codex_binary_found: bool,
        cursor_binary_found: bool,
        codex_present: bool,
        cursor_present: bool,
        codex_probe_timed_out: bool,
        cursor_probe_timed_out: bool,
        codex_gate_detail: Option<CodexGateDetail>,
    ) -> Self {
        Self {
            codex_binary_found,
            cursor_binary_found,
            codex_present,
            cursor_present,
            codex_probe_timed_out,
            cursor_probe_timed_out,
            codex_gate_detail,
        }
    }

    /// Whether the Codex binary is on PATH.
    #[must_use]
    pub const fn codex_binary_found(&self) -> bool {
        self.codex_binary_found
    }

    /// Whether the Cursor binary is on PATH.
    #[must_use]
    pub const fn cursor_binary_found(&self) -> bool {
        self.cursor_binary_found
    }

    /// Whether Codex answered the health probe successfully.
    #[must_use]
    pub const fn codex_present(&self) -> bool {
        self.codex_present
    }

    /// Whether Cursor answered the health probe successfully.
    #[must_use]
    pub const fn cursor_present(&self) -> bool {
        self.cursor_present
    }

    /// Whether the Codex probe loop exhausted its timeout budget.
    #[must_use]
    pub const fn codex_probe_timed_out(&self) -> bool {
        self.codex_probe_timed_out
    }

    /// Whether the Cursor probe loop exhausted its timeout budget.
    #[must_use]
    pub const fn cursor_probe_timed_out(&self) -> bool {
        self.cursor_probe_timed_out
    }

    /// Optional Codex CLI gate detail from a failing probe.
    #[must_use]
    pub const fn codex_gate_detail(&self) -> Option<&CodexGateDetail> {
        self.codex_gate_detail.as_ref()
    }

    /// Emit the KEY=value envelope lines in the Python-stable order.
    #[must_use]
    pub fn kv_lines(&self) -> Vec<String> {
        vec![
            format!(
                "CODEX_BINARY_FOUND={}",
                if self.codex_binary_found {
                    "true"
                } else {
                    "false"
                }
            ),
            format!(
                "CURSOR_BINARY_FOUND={}",
                if self.cursor_binary_found {
                    "true"
                } else {
                    "false"
                }
            ),
            format!(
                "CODEX_PRESENT={}",
                if self.codex_present { "true" } else { "false" }
            ),
            format!(
                "CURSOR_PRESENT={}",
                if self.cursor_present { "true" } else { "false" }
            ),
            format!(
                "CODEX_PROBE_TIMED_OUT={}",
                if self.codex_probe_timed_out {
                    "true"
                } else {
                    "false"
                }
            ),
            format!(
                "CURSOR_PROBE_TIMED_OUT={}",
                if self.cursor_probe_timed_out {
                    "true"
                } else {
                    "false"
                }
            ),
        ]
    }
}

/// Resolved probe budgets and skip flags for one check-reviewers run.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CheckReviewersConfig {
    /// Positive probe-stamp TTL in seconds.
    pub ttl_seconds: u64,
    /// Negative probe-stamp TTL in seconds.
    pub negative_ttl_seconds: u64,
    /// Per-attempt probe timeout in seconds.
    pub timeout_seconds: u64,
    /// Separated auth / transient / timeout retry budgets.
    pub retry_limits: ProbeRetryLimits,
    /// Skip the Codex probe entirely.
    pub skip_codex_probe: bool,
    /// Skip the Cursor probe entirely.
    pub skip_cursor_probe: bool,
}

impl CheckReviewersConfig {
    /// Resolve budgets from environment-style string values.
    #[must_use]
    #[allow(clippy::too_many_arguments)] // mirrors the Python probe-budget env surface
    pub fn from_env_values(
        ttl: Option<&str>,
        negative_ttl: Option<&str>,
        timeout: Option<&str>,
        auth_retries: Option<&str>,
        probe_retries: Option<&str>,
        timeout_retries: Option<&str>,
        skip_codex_probe: bool,
        skip_cursor_probe: bool,
        probe_timeout_override: Option<u64>,
    ) -> Self {
        let ttl_seconds = parse_u64_default(ttl, 60, true);
        let negative_ttl_seconds = parse_u64_default(negative_ttl, 0, true);
        let timeout_seconds =
            probe_timeout_override.unwrap_or_else(|| parse_u64_default(timeout, 60, false));
        #[allow(clippy::cast_possible_truncation)] // retry budgets stay well below usize::MAX
        let max_auth_retries = parse_u64_default(auth_retries, 5, false) as usize;
        #[allow(clippy::cast_possible_truncation)] // retry budgets stay well below usize::MAX
        let transient_override =
            probe_retries.map(|raw| parse_u64_default(Some(raw), 2, true) as usize);
        let max_transient = transient_probe_retries(transient_override, max_auth_retries);
        #[allow(clippy::cast_possible_truncation)] // retry budgets stay well below usize::MAX
        let max_timeout = parse_u64_default(timeout_retries, 0, true) as usize;
        Self {
            ttl_seconds,
            negative_ttl_seconds,
            timeout_seconds,
            retry_limits: ProbeRetryLimits::new(max_auth_retries, max_transient, max_timeout),
            skip_codex_probe,
            skip_cursor_probe,
        }
    }
}

fn parse_u64_default(raw: Option<&str>, default: u64, zero_allowed: bool) -> u64 {
    let Some(raw) = raw.map(str::trim).filter(|value| !value.is_empty()) else {
        return default;
    };
    match raw.parse::<u64>() {
        Ok(value) if zero_allowed || value > 0 => value,
        _ => default,
    }
}

/// Map an auth verdict and exit code onto the probe retry class exit code.
#[must_use]
pub fn probe_attempt_rc(exit_code: i32, timed_out: bool, auth_verdict: ExternalAuthVerdict) -> i32 {
    if timed_out {
        return PROBE_TIMEOUT_EXIT_CODE;
    }
    if exit_code == 0 {
        return 0;
    }
    if auth_verdict == ExternalAuthVerdict::Auth {
        return PROBE_AUTH_RETRY_RC;
    }
    1
}

/// Return whether `name` appears as an executable on `path_env`.
#[must_use]
pub fn binary_on_path(name: &str, path_env: Option<&str>) -> bool {
    let Some(path_env) = path_env.filter(|value| !value.is_empty()) else {
        return false;
    };
    for entry in std::env::split_paths(path_env) {
        let candidate = entry.join(name);
        if is_executable(&candidate) {
            return true;
        }
    }
    false
}

fn is_executable(path: &Path) -> bool {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::metadata(path)
            .map(|meta| meta.is_file() && meta.permissions().mode() & 0o111 != 0)
            .unwrap_or(false)
    }
    #[cfg(not(unix))]
    {
        path.is_file()
    }
}

/// Resolve a probe working directory, preferring a git toplevel when available.
#[must_use]
pub fn resolve_probe_workdir(
    cwd: &Path,
    project_dir: Option<&Path>,
    git_toplevel: Option<&Path>,
) -> PathBuf {
    if let Some(project) = project_dir
        && let Some(toplevel) = git_toplevel_for(project, git_toplevel)
    {
        return toplevel;
    }
    if let Some(toplevel) = git_toplevel_for(cwd, git_toplevel) {
        return toplevel;
    }
    cwd.to_path_buf()
}

fn git_toplevel_for(start: &Path, discovered: Option<&Path>) -> Option<PathBuf> {
    discovered
        .filter(|path| path_under_or_eq(start, path) || path_under_or_eq(path, start))
        .map(Path::to_path_buf)
        .or_else(|| {
            // Callers that already resolved a toplevel for `start` pass it in;
            // when absent, keep the start path rather than spawning git here.
            let _ = start
                .components()
                .any(|component| component == Component::RootDir);
            None
        })
}

fn path_under_or_eq(path: &Path, root: &Path) -> bool {
    path == root || path.starts_with(root)
}

#[cfg(test)]
mod tests {
    use super::{CheckReviewersConfig, CheckReviewersResult, binary_on_path, probe_attempt_rc};
    use crate::{ExternalAuthVerdict, PROBE_AUTH_RETRY_RC, external_auth_verdict};

    #[test]
    fn kv_order_is_stable() {
        let result = CheckReviewersResult::new(true, false, true, false, false, true, None);
        assert_eq!(
            result.kv_lines(),
            vec![
                "CODEX_BINARY_FOUND=true".to_owned(),
                "CURSOR_BINARY_FOUND=false".to_owned(),
                "CODEX_PRESENT=true".to_owned(),
                "CURSOR_PRESENT=false".to_owned(),
                "CODEX_PROBE_TIMED_OUT=false".to_owned(),
                "CURSOR_PROBE_TIMED_OUT=true".to_owned(),
            ]
        );
    }

    #[test]
    fn auth_verdict_and_attempt_rc() {
        assert_eq!(
            external_auth_verdict("cursor", ["cursor-user keychain not found"]),
            ExternalAuthVerdict::Auth
        );
        assert_eq!(
            external_auth_verdict("codex", ["network unreachable"]),
            ExternalAuthVerdict::NonAuth
        );
        assert_eq!(
            external_auth_verdict("codex", [""]),
            ExternalAuthVerdict::Unclassified
        );
        assert_eq!(probe_attempt_rc(1, true, ExternalAuthVerdict::NonAuth), 124);
        assert_eq!(
            probe_attempt_rc(1, false, ExternalAuthVerdict::Auth),
            PROBE_AUTH_RETRY_RC
        );
        assert_eq!(
            probe_attempt_rc(0, false, ExternalAuthVerdict::Unclassified),
            0
        );
    }

    #[test]
    fn config_defaults_and_binary_lookup() {
        let config = CheckReviewersConfig::from_env_values(
            None, None, None, None, None, None, false, true, None,
        );
        assert_eq!(config.ttl_seconds, 60);
        assert_eq!(config.timeout_seconds, 60);
        assert!(config.skip_cursor_probe);
        assert!(!binary_on_path(
            "definitely-missing-larch-binary",
            Some("/tmp")
        ));
    }
}
