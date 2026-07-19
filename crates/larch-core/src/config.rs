//! Shared configuration names that survive the Python migration.

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
    /// Cursor API credential used by Cursor subprocesses.
    pub const CURSOR_API_KEY: &str = "CURSOR_API_KEY";
    /// Temporary directory for an active design run.
    pub const DESIGN_TMPDIR: &str = "DESIGN_TMPDIR";
    /// Legacy GitHub CLI credential, never read by the Rust GitHub service.
    pub const GH_TOKEN: &str = "GH_TOKEN";
    /// GitHub Actions credential, never read by the Rust GitHub service.
    pub const GITHUB_TOKEN: &str = "GITHUB_TOKEN";
    /// Optional Google Application Default Credentials file.
    pub const GOOGLE_APPLICATION_CREDENTIALS: &str = "GOOGLE_APPLICATION_CREDENTIALS";
    /// Current user's home directory.
    pub const HOME: &str = "HOME";
    /// Temporary directory for an active implementation run.
    pub const IMPLEMENT_TMPDIR: &str = "IMPLEMENT_TMPDIR";
    /// Issue number associated with the current workflow.
    pub const ISSUE_NUMBER: &str = "ISSUE_NUMBER";
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
    /// Sole credential read by the Rust GitHub service.
    pub const LARCH_GH_TOKEN: &str = "LARCH_GH_TOKEN";
    /// Disable run-log commits for the current workflow.
    pub const LARCH_NO_LOGS_COMMIT: &str = "LARCH_NO_LOGS_COMMIT";
    /// Canonical run identifier.
    pub const LARCH_RUN_ID: &str = "LARCH_RUN_ID";
    /// Current user login name on platforms that provide it.
    pub const LOGNAME: &str = "LOGNAME";
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

    /// Shared names maintained by this module.
    pub const ALL: [&str; 30] = [
        ANTHROPIC_API_KEY,
        CLAUDE_PLUGIN_OPTION_CODEX_EFFORT,
        CLAUDE_PLUGIN_OPTION_CODEX_MODEL,
        CLAUDE_PLUGIN_OPTION_CURSOR_MODEL,
        CLAUDE_PLUGIN_ROOT,
        CURSOR_API_KEY,
        DESIGN_TMPDIR,
        GH_TOKEN,
        GITHUB_TOKEN,
        GOOGLE_APPLICATION_CREDENTIALS,
        HOME,
        IMPLEMENT_TMPDIR,
        ISSUE_NUMBER,
        LARCH_CODEX_EFFORT,
        LARCH_CODEX_FIX_MODEL,
        LARCH_CODEX_MODEL,
        LARCH_CODEX_REVIEW_MODEL,
        LARCH_CODEX_VOTE_MODEL,
        LARCH_CURSOR_MODEL,
        LARCH_GH_TOKEN,
        LARCH_NO_LOGS_COMMIT,
        LARCH_RUN_ID,
        LOGNAME,
        OPENAI_API_KEY,
        PATH,
        REPO,
        SESSION_ID,
        SESSION_TMPDIR,
        TMPDIR,
        USER,
    ];
}

#[cfg(test)]
mod tests {
    use super::env;
    use std::collections::BTreeSet;

    #[test]
    fn environment_names_preserve_live_public_strings() {
        assert_eq!(env::GH_TOKEN, "GH_TOKEN");
        assert_eq!(env::GITHUB_TOKEN, "GITHUB_TOKEN");
        assert_eq!(env::LARCH_GH_TOKEN, "LARCH_GH_TOKEN");
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
    }

    #[test]
    fn centralized_environment_names_are_unique() {
        let unique = env::ALL.into_iter().collect::<BTreeSet<_>>();
        assert_eq!(unique.len(), env::ALL.len());
        assert!(unique.iter().all(|name| !name.is_empty()));
    }
}
