//! Shared configuration names that survive the Python migration.

/// Trailer added by the public Git commit command unless explicitly disabled.
pub const GIT_COMMIT_CO_AUTHORED_BY_TRAILER: &str =
    "Co-Authored-By: Claude Code <noreply@anthropic.com>";

/// Environment-variable names read at Rust composition boundaries.
///
/// Core domain code does not read the process environment. The CLI and adapter
/// layers use these names to construct typed configuration and runtime context.
pub mod env {
    /// Anthropic API credential used by Claude subprocesses.
    pub const ANTHROPIC_API_KEY: &str = "ANTHROPIC_API_KEY";
    /// Plugin-provided fallback for the Codex effort setting.
    pub const CLAUDE_PLUGIN_OPTION_CODEX_EFFORT: &str = "CLAUDE_PLUGIN_OPTION_CODEX_EFFORT";
    /// Plugin-provided fallback for the Codex model setting.
    pub const CLAUDE_PLUGIN_OPTION_CODEX_MODEL: &str = "CLAUDE_PLUGIN_OPTION_CODEX_MODEL";
    /// Plugin-provided fallback for the Cursor model setting.
    pub const CLAUDE_PLUGIN_OPTION_CURSOR_MODEL: &str = "CLAUDE_PLUGIN_OPTION_CURSOR_MODEL";
    /// Root of the installed Claude plugin.
    pub const CLAUDE_PLUGIN_ROOT: &str = "CLAUDE_PLUGIN_ROOT";
    /// Persistent data root owned by the installed Claude plugin.
    pub const CLAUDE_PLUGIN_DATA: &str = "CLAUDE_PLUGIN_DATA";
    /// Cursor API credential used by Cursor subprocesses.
    pub const CURSOR_API_KEY: &str = "CURSOR_API_KEY";
    /// Isolated Cursor configuration directory injected into vendor children.
    pub const CURSOR_CONFIG_DIR: &str = "CURSOR_CONFIG_DIR";
    /// Isolated Codex home directory injected into vendor children.
    pub const CODEX_HOME: &str = "CODEX_HOME";
    /// Temporary directory for an active design run.
    pub const DESIGN_TMPDIR: &str = "DESIGN_TMPDIR";
    /// Explicit GitHub CLI configuration directory used by typed `gh` operations.
    pub const GH_CONFIG_DIR: &str = "GH_CONFIG_DIR";
    /// Optional Google Application Default Credentials file.
    pub const GOOGLE_APPLICATION_CREDENTIALS: &str = "GOOGLE_APPLICATION_CREDENTIALS";
    /// Current user's home directory.
    pub const HOME: &str = "HOME";
    /// Temporary directory for an active implementation run.
    pub const IMPLEMENT_TMPDIR: &str = "IMPLEMENT_TMPDIR";
    /// Issue number associated with the current workflow.
    pub const ISSUE_NUMBER: &str = "ISSUE_NUMBER";
    /// Wrapper-invoked absolute path to the real larch binary.
    pub const LARCH_BINARY: &str = "LARCH_BINARY";
    /// Optional Codex effort override.
    pub const LARCH_CODEX_EFFORT: &str = "LARCH_CODEX_EFFORT";
    /// Optional Codex fixer model override.
    pub const LARCH_CODEX_FIX_MODEL: &str = "LARCH_CODEX_FIX_MODEL";
    /// Optional Codex implementation model override.
    pub const LARCH_CODEX_MODEL: &str = "LARCH_CODEX_MODEL";
    /// Optional Codex reviewer model override.
    pub const LARCH_CODEX_REVIEW_MODEL: &str = "LARCH_CODEX_REVIEW_MODEL";
    /// Optional Codex voter model override.
    pub const LARCH_CODEX_VOTE_MODEL: &str = "LARCH_CODEX_VOTE_MODEL";
    /// Optional Cursor model override.
    pub const LARCH_CURSOR_MODEL: &str = "LARCH_CURSOR_MODEL";
    /// Maximum authentication attempts a vendor probe or launch may make.
    pub const LARCH_EXTERNAL_AUTH_RETRIES: &str = "LARCH_EXTERNAL_AUTH_RETRIES";
    /// Lifetime of a cached failing reviewer-probe verdict, in seconds.
    pub const LARCH_PROBE_NEGATIVE_TTL_SECONDS: &str = "LARCH_PROBE_NEGATIVE_TTL_SECONDS";
    /// Transient-failure retry budget override for reviewer probes.
    pub const LARCH_PROBE_RETRIES: &str = "LARCH_PROBE_RETRIES";
    /// Timeout retry budget for reviewer probes.
    pub const LARCH_PROBE_TIMEOUT_RETRIES: &str = "LARCH_PROBE_TIMEOUT_RETRIES";
    /// Per-attempt reviewer-probe timeout, in seconds.
    pub const LARCH_PROBE_TIMEOUT_SECONDS: &str = "LARCH_PROBE_TIMEOUT_SECONDS";
    /// Lifetime of a cached successful reviewer-probe verdict, in seconds.
    pub const LARCH_PROBE_TTL_SECONDS: &str = "LARCH_PROBE_TTL_SECONDS";
    /// Timeout for Cursor model-list health checks used by model-pin resolution.
    pub const LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT: &str = "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT";
    /// Optional tail length for a failed-agent stderr excerpt.
    pub const LARCH_FAILED_AGENT_STDERR_TAIL_LINES: &str = "LARCH_FAILED_AGENT_STDERR_TAIL_LINES";
    /// Release version pinned by the release workflow during a local upgrade.
    pub const LARCH_EXPECTED_STABLE_VERSION: &str = "LARCH_EXPECTED_STABLE_VERSION";
    /// Legacy run-log storage override; no longer supported, rejected with guidance.
    pub const LARCH_LOGS_URI: &str = "LARCH_LOGS_URI";
    /// Disable run-log commits for the current workflow.
    pub const LARCH_NO_LOGS_COMMIT: &str = "LARCH_NO_LOGS_COMMIT";
    /// Cloudflare R2 account identifier used to derive the provider endpoint.
    pub const LARCH_R2_ACCOUNT_ID: &str = "LARCH_R2_ACCOUNT_ID";
    /// Cloudflare R2 endpoint override for object-storage requests.
    pub const LARCH_R2_ENDPOINT: &str = "LARCH_R2_ENDPOINT";
    /// Canonical run identifier.
    pub const LARCH_RUN_ID: &str = "LARCH_RUN_ID";
    /// Base object-storage URI override for run-log publication.
    pub const LARCH_STORAGE_BASE_URI: &str = "LARCH_STORAGE_BASE_URI";
    /// Optional byte ceiling for a composed vendor failure diagnostic.
    pub const LARCH_VENDOR_FAILURE_DIAG_BYTES: &str = "LARCH_VENDOR_FAILURE_DIAG_BYTES";
    /// Optional per-section line budget for a vendor failure diagnostic.
    pub const LARCH_VENDOR_FAILURE_DIAG_SECTION_LINES: &str =
        "LARCH_VENDOR_FAILURE_DIAG_SECTION_LINES";
    /// Current user login name on platforms that provide it.
    pub const LOGNAME: &str = "LOGNAME";
    /// Suppresses cursor-agent's deeplink browser opener in headless lanes.
    pub const NO_OPEN_BROWSER: &str = "NO_OPEN_BROWSER";
    /// `OpenAI` API credential used by Codex subprocesses.
    pub const OPENAI_API_KEY: &str = "OPENAI_API_KEY";
    /// Executable search path inherited by approved child processes.
    pub const PATH: &str = "PATH";
    /// GitHub `OWNER/REPO` associated with the current workflow.
    pub const REPO: &str = "REPO";
    /// Session identifier associated with the current workflow.
    pub const SESSION_ID: &str = "SESSION_ID";
    /// Temporary directory for the current session.
    pub const SESSION_TMPDIR: &str = "SESSION_TMPDIR";
    /// System temporary directory override.
    pub const TMPDIR: &str = "TMPDIR";
    /// Current user name.
    pub const USER: &str = "USER";
    /// XDG configuration root used by external products when configured.
    pub const XDG_CONFIG_HOME: &str = "XDG_CONFIG_HOME";

    /// Shared names maintained by this module.
    pub const ALL: [&str; 45] = [
        ANTHROPIC_API_KEY,
        CLAUDE_PLUGIN_OPTION_CODEX_EFFORT,
        CLAUDE_PLUGIN_OPTION_CODEX_MODEL,
        CLAUDE_PLUGIN_OPTION_CURSOR_MODEL,
        CLAUDE_PLUGIN_DATA,
        CLAUDE_PLUGIN_ROOT,
        CODEX_HOME,
        CURSOR_API_KEY,
        CURSOR_CONFIG_DIR,
        DESIGN_TMPDIR,
        GH_CONFIG_DIR,
        GOOGLE_APPLICATION_CREDENTIALS,
        HOME,
        IMPLEMENT_TMPDIR,
        ISSUE_NUMBER,
        LARCH_BINARY,
        LARCH_CODEX_EFFORT,
        LARCH_CODEX_FIX_MODEL,
        LARCH_CODEX_MODEL,
        LARCH_CODEX_REVIEW_MODEL,
        LARCH_CODEX_VOTE_MODEL,
        LARCH_CURSOR_MODEL,
        LARCH_EXPECTED_STABLE_VERSION,
        LARCH_EXTERNAL_AUTH_RETRIES,
        LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT,
        LARCH_LOGS_URI,
        LARCH_NO_LOGS_COMMIT,
        LARCH_PROBE_NEGATIVE_TTL_SECONDS,
        LARCH_PROBE_RETRIES,
        LARCH_PROBE_TIMEOUT_RETRIES,
        LARCH_PROBE_TIMEOUT_SECONDS,
        LARCH_PROBE_TTL_SECONDS,
        LARCH_R2_ACCOUNT_ID,
        LARCH_R2_ENDPOINT,
        LARCH_RUN_ID,
        LARCH_STORAGE_BASE_URI,
        LOGNAME,
        NO_OPEN_BROWSER,
        OPENAI_API_KEY,
        PATH,
        REPO,
        SESSION_ID,
        SESSION_TMPDIR,
        TMPDIR,
        USER,
        XDG_CONFIG_HOME,
    ];
}

#[cfg(test)]
mod tests {
    use super::env;
    use std::collections::BTreeSet;

    #[test]
    fn environment_names_preserve_live_public_strings() {
        assert_eq!(
            env::GOOGLE_APPLICATION_CREDENTIALS,
            "GOOGLE_APPLICATION_CREDENTIALS"
        );
        assert_eq!(env::LARCH_RUN_ID, "LARCH_RUN_ID");
        assert_eq!(env::DESIGN_TMPDIR, "DESIGN_TMPDIR");
        assert_eq!(env::IMPLEMENT_TMPDIR, "IMPLEMENT_TMPDIR");
        assert_eq!(env::CLAUDE_PLUGIN_ROOT, "CLAUDE_PLUGIN_ROOT");
        assert_eq!(env::REPO, "REPO");
        assert_eq!(env::ISSUE_NUMBER, "ISSUE_NUMBER");
        assert_eq!(env::SESSION_ID, "SESSION_ID");
        assert_eq!(env::SESSION_TMPDIR, "SESSION_TMPDIR");
        assert_eq!(
            env::CLAUDE_PLUGIN_OPTION_CODEX_MODEL,
            "CLAUDE_PLUGIN_OPTION_CODEX_MODEL"
        );
        assert_eq!(env::LARCH_NO_LOGS_COMMIT, "LARCH_NO_LOGS_COMMIT");
        assert_eq!(env::LARCH_BINARY, "LARCH_BINARY");
        assert_eq!(env::LARCH_LOGS_URI, "LARCH_LOGS_URI");
        assert_eq!(env::LARCH_STORAGE_BASE_URI, "LARCH_STORAGE_BASE_URI");
        assert_eq!(env::LARCH_R2_ACCOUNT_ID, "LARCH_R2_ACCOUNT_ID");
        assert_eq!(env::LARCH_R2_ENDPOINT, "LARCH_R2_ENDPOINT");
    }

    #[test]
    fn centralized_environment_names_are_unique() {
        let unique = env::ALL.into_iter().collect::<BTreeSet<_>>();
        assert_eq!(unique.len(), env::ALL.len());
        assert!(unique.iter().all(|name| !name.is_empty()));
    }
}
