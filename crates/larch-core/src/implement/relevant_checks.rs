//! Pure selection and result-rendering for `checks run-relevant` (#8616).
//!
//! The path→check selection ("which changed paths need which validation"),
//! the coverage/phase derivation from log markers, and the `KEY=value` stdout
//! grammar live here; the impure orchestration (pre-commit, git, redaction,
//! telemetry) lives in the CLI owner.

/// Workspace-level Rust inputs that force the bounded Clippy selector.
pub const WORKSPACE_INPUTS: [&str; 4] = [
    "Cargo.lock",
    "Cargo.toml",
    "deny.toml",
    "rust-toolchain.toml",
];

/// Whether a repository-relative path needs the bounded Rust selector.
// Python parity: `str.endswith(".rs")` is a case-sensitive suffix test.
#[allow(clippy::case_sensitive_file_extension_comparisons)]
#[must_use]
pub fn is_rust_relevant_path(path: &str) -> bool {
    WORKSPACE_INPUTS.contains(&path)
        || path.starts_with(".cargo/")
        || (path.starts_with("crates/") && (path.ends_with(".rs") || path.ends_with("/Cargo.toml")))
}

/// Coverage label derived from the run outcome and the log phase markers.
#[must_use]
pub const fn coverage_from_markers(
    ok: bool,
    has_precommit: bool,
    has_agent_lint: bool,
) -> &'static str {
    if !ok {
        return "changed-file-only";
    }
    if has_precommit && has_agent_lint {
        "full"
    } else if !has_precommit && has_agent_lint {
        "post-check-only"
    } else {
        "changed-file-only"
    }
}

/// Phase label derived from the run outcome and the log phase markers.
#[must_use]
pub const fn phase_from_markers(
    ok: bool,
    has_precommit: bool,
    has_agent_lint: bool,
) -> &'static str {
    if ok {
        return "unknown";
    }
    if has_agent_lint {
        "agent-lint"
    } else if has_precommit {
        "pre-commit"
    } else {
        "unknown"
    }
}

/// Stream-scan a checks log's text for the phase and coverage markers.
///
/// Returns `(has_precommit, has_agent_lint, has_agent_lint_warning)`.
#[must_use]
pub fn scan_checks_log_markers(text: &str) -> (bool, bool, bool) {
    let mut has_precommit = false;
    let mut has_agent_lint = false;
    let mut has_warning = false;
    for line in text.lines() {
        if line.contains("=== Running pre-commit") {
            has_precommit = true;
        }
        if line.contains("=== Running agent-lint ===") {
            has_agent_lint = true;
        }
        if line.contains("WARNING: agent-lint not found on PATH") {
            has_warning = true;
        }
    }
    (has_precommit, has_agent_lint, has_warning)
}

/// The relevant-checks outcome, mirroring the Python `ChecksResult` dataclass.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ChecksResult {
    /// Whether the checks passed.
    pub ok: bool,
    /// Process exit code for the command.
    pub exit_code: i32,
    /// Validated site label.
    pub site: String,
    /// Path to the redacted failure log, when one was written.
    pub redacted_log_path: Option<String>,
    /// Derived phase label.
    pub phase: String,
    /// Derived coverage label.
    pub coverage: String,
    /// Whether the run was skipped (never true on this path today).
    pub skipped: bool,
    /// Optional warning token.
    pub warn: Option<String>,
    /// Path to the raw log, when one was captured.
    pub raw_log_path: Option<String>,
    /// Failure reason token, when the run failed.
    pub failure_reason: Option<String>,
    /// Path to the failure digest, when one was written.
    pub digest_file_path: Option<String>,
}

impl ChecksResult {
    /// Build a failure result carrying the supplied reason and diagnostics.
    #[must_use]
    pub fn failure(site: &str, exit_code: i32, reason: &str) -> Self {
        Self {
            ok: false,
            exit_code,
            site: site.to_owned(),
            redacted_log_path: None,
            phase: "unknown".to_owned(),
            coverage: "changed-file-only".to_owned(),
            skipped: false,
            warn: None,
            raw_log_path: None,
            failure_reason: Some(reason.to_owned()),
            digest_file_path: None,
        }
    }

    /// Render the `checks run-relevant` stdout line and its exit code.
    ///
    /// `allow_skip` mirrors the `--allow-skip` flag on the command.
    #[must_use]
    pub fn render(&self, allow_skip: bool) -> (String, i32) {
        if self.skipped && allow_skip {
            return (
                format!("RELEVANT_CHECKS_SKIPPED=true SITE={}", self.site),
                0,
            );
        }
        if self.ok {
            let mut line = format!(
                "RELEVANT_CHECKS_OK=true SITE={} COVERAGE={} PHASE={}",
                self.site, self.coverage, self.phase
            );
            if let Some(warn) = &self.warn {
                line.push_str(" WARN=");
                line.push_str(warn);
            }
            return (line, 0);
        }
        let reason = self.failure_reason.as_deref().unwrap_or("checks-failed");
        let mut parts = vec!["STATUS=fail".to_owned(), format!("FAILURE_REASON={reason}")];
        if let Some(redacted) = &self.redacted_log_path {
            parts.push(format!("EXIT_CODE={}", self.exit_code));
            parts.push(format!("PHASE={}", self.phase));
            if let Some(digest) = &self.digest_file_path {
                parts.push(format!("DIGEST_FILE={digest}"));
            }
            parts.push(format!("REDACTED_LOG_FILE={redacted}"));
        }
        let code = if self.exit_code == 0 {
            1
        } else {
            self.exit_code
        };
        (parts.join(" "), code)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rust_relevance_matches_the_selection_grammar() {
        assert!(is_rust_relevant_path("Cargo.toml"));
        assert!(is_rust_relevant_path(".cargo/config.toml"));
        assert!(is_rust_relevant_path("crates/larch-core/src/lib.rs"));
        assert!(is_rust_relevant_path("crates/larch-core/Cargo.toml"));
        assert!(!is_rust_relevant_path("crates/larch-core/README.md"));
        assert!(!is_rust_relevant_path("python/cli.py"));
        assert!(!is_rust_relevant_path("docs/Cargo.toml"));
    }

    #[test]
    fn coverage_and_phase_track_markers() {
        assert_eq!(coverage_from_markers(true, true, true), "full");
        assert_eq!(coverage_from_markers(true, false, true), "post-check-only");
        assert_eq!(
            coverage_from_markers(true, false, false),
            "changed-file-only"
        );
        assert_eq!(
            coverage_from_markers(false, true, true),
            "changed-file-only"
        );
        assert_eq!(phase_from_markers(true, true, true), "unknown");
        assert_eq!(phase_from_markers(false, false, true), "agent-lint");
        assert_eq!(phase_from_markers(false, true, false), "pre-commit");
        assert_eq!(phase_from_markers(false, false, false), "unknown");
    }

    #[test]
    fn scan_markers_detects_each_banner() {
        let text = "line\n=== Running pre-commit on 2 changed file(s) ===\n=== Running agent-lint ===\nWARNING: agent-lint not found on PATH\n";
        assert_eq!(scan_checks_log_markers(text), (true, true, true));
        assert_eq!(
            scan_checks_log_markers("nothing here"),
            (false, false, false)
        );
    }

    #[test]
    fn render_ok_and_skip_and_failure() {
        let mut result = ChecksResult::failure("step3", 2, "site-validation");
        result.ok = true;
        result.coverage = "full".to_owned();
        result.phase = "unknown".to_owned();
        result.failure_reason = None;
        assert_eq!(
            result.render(false),
            (
                "RELEVANT_CHECKS_OK=true SITE=step3 COVERAGE=full PHASE=unknown".to_owned(),
                0
            )
        );
        result.warn = Some("agent-lint-missing".to_owned());
        assert_eq!(
            result.render(false).0,
            "RELEVANT_CHECKS_OK=true SITE=step3 COVERAGE=full PHASE=unknown WARN=agent-lint-missing"
        );

        let mut skipped = ChecksResult::failure("step6", 0, "x");
        skipped.skipped = true;
        assert_eq!(
            skipped.render(true),
            ("RELEVANT_CHECKS_SKIPPED=true SITE=step6".to_owned(), 0)
        );

        let plain = ChecksResult::failure("step3", 2, "tmpdir-validation");
        assert_eq!(
            plain.render(false),
            ("STATUS=fail FAILURE_REASON=tmpdir-validation".to_owned(), 2)
        );

        let mut detailed = ChecksResult::failure("step3", 1, "checks-failed");
        detailed.redacted_log_path = Some("/t/step3-1.redacted.log".to_owned());
        detailed.phase = "pre-commit".to_owned();
        detailed.digest_file_path = Some("/t/step3-1.digest.txt".to_owned());
        assert_eq!(
            detailed.render(false),
            (
                "STATUS=fail FAILURE_REASON=checks-failed EXIT_CODE=1 PHASE=pre-commit DIGEST_FILE=/t/step3-1.digest.txt REDACTED_LOG_FILE=/t/step3-1.redacted.log".to_owned(),
                1
            )
        );
    }
}
