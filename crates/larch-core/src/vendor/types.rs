//! Frozen vendor launch data model.

use crate::VendorProgram;
use std::collections::BTreeSet;

/// Wire payload written when a token budget cap is hit.
pub const CAP_HIT_PAYLOAD: &str = "STATUS=cap_hit\n";

/// Inputs for argv construction and (later) the shared launch lifecycle.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VendorLaunchRequest {
    /// Working directory passed to vendor argv builders.
    pub workdir: String,
    /// Output path for last-message or result files.
    pub output: String,
    /// Prompt text or stdin marker content.
    pub prompt: String,
    /// Timing / budget step label.
    pub timing_task_kind: String,
    /// Precomposed model flag tokens (`-m` / `--model` pairs).
    pub model_args: Vec<String>,
    /// Explicit model name used by Claude builders.
    pub model: String,
    /// Extra `--add-dir` paths for Codex.
    pub add_dirs: Vec<String>,
    /// When true, Codex / resume builders emit `-` as the prompt token.
    pub prompt_via_stdin: bool,
    /// Claude review-subprocess read-tools directory.
    pub read_tools_add_dir: String,
    /// Optional positive token-budget cap string.
    pub token_cap: String,
    /// Explicit Codex env-auth inclusion; never read from process environment.
    pub codex_env_auth: super::CodexEnvAuth,
}

impl VendorLaunchRequest {
    /// Build a request with empty optional fields and omitted Codex env auth.
    #[must_use]
    pub fn new(
        workdir: impl Into<String>,
        output: impl Into<String>,
        prompt: impl Into<String>,
    ) -> Self {
        Self {
            workdir: workdir.into(),
            output: output.into(),
            prompt: prompt.into(),
            timing_task_kind: String::new(),
            model_args: Vec::new(),
            model: String::new(),
            add_dirs: Vec::new(),
            prompt_via_stdin: false,
            read_tools_add_dir: String::new(),
            token_cap: String::new(),
            codex_env_auth: super::CodexEnvAuth::Omit,
        }
    }
}

/// Terminal result of a vendor process invocation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VendorProcessResult {
    /// Process exit code.
    pub exit_code: i32,
    /// Captured stdout.
    pub stdout: String,
    /// Captured stderr.
    pub stderr: String,
}

impl VendorProcessResult {
    /// Build a result with empty streams.
    #[must_use]
    pub const fn new(exit_code: i32) -> Self {
        Self {
            exit_code,
            stdout: String::new(),
            stderr: String::new(),
        }
    }
}

/// Typed post-parse outcome for family postprocessing (Claude envelopes).
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VendorParsedResult {
    /// Envelope status token.
    pub status: super::ClaudeEnvelopeStatus,
    /// Successful result text when status is ok.
    pub text: String,
    /// Original raw envelope bytes as text.
    pub raw: String,
    /// Whether the envelope declared `is_error`.
    pub is_error: bool,
}

/// Injectable lifecycle hooks. Behavior is wired in the launch-lifecycle leaf.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct VendorFamilyHooks;

/// Immutable vendor identity, capabilities, profiles, and argv builder surface.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VendorDescriptor {
    key: &'static str,
    program: VendorProgram,
    capabilities: BTreeSet<&'static str>,
    argv_profiles: BTreeSet<&'static str>,
    hooks: VendorFamilyHooks,
}

impl VendorDescriptor {
    /// Construct a descriptor. Callers must validate through the registry builder.
    #[must_use]
    pub const fn new(
        key: &'static str,
        program: VendorProgram,
        capabilities: BTreeSet<&'static str>,
        argv_profiles: BTreeSet<&'static str>,
        hooks: VendorFamilyHooks,
    ) -> Self {
        Self {
            key,
            program,
            capabilities,
            argv_profiles,
            hooks,
        }
    }

    /// Stable registry key (`codex`, `cursor`, `claude`).
    #[must_use]
    pub const fn key(&self) -> &'static str {
        self.key
    }

    /// Closed vendor program named by the process port.
    #[must_use]
    pub const fn program(&self) -> VendorProgram {
        self.program
    }

    /// Declared capability set.
    #[must_use]
    pub const fn capabilities(&self) -> &BTreeSet<&'static str> {
        &self.capabilities
    }

    /// Declared argv profile names.
    #[must_use]
    pub const fn argv_profiles(&self) -> &BTreeSet<&'static str> {
        &self.argv_profiles
    }

    /// Family hooks placeholder.
    #[must_use]
    pub const fn hooks(&self) -> &VendorFamilyHooks {
        &self.hooks
    }

    /// Build argv for a named profile.
    ///
    /// # Errors
    /// Returns when the profile is unknown or required request fields are missing.
    pub fn build_argv(
        &self,
        profile: &str,
        request: &VendorLaunchRequest,
    ) -> Result<super::VendorArgv, super::VendorArgvError> {
        match self.program {
            VendorProgram::Codex => {
                super::build_codex_argv(profile, request, request.codex_env_auth)
            }
            VendorProgram::Cursor => super::build_cursor_argv(profile, request),
            VendorProgram::Claude => super::build_claude_argv(profile, request),
        }
    }

    /// Extract a model token from a full argv including the executable name.
    #[must_use]
    pub fn extract_model(&self, argv: &[String]) -> String {
        let _ = self;
        super::extract_model_from_argv(argv)
    }
}

/// Outcome of an optional token-budget cap check.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct VendorCapCheckResult {
    /// Whether the budget cap was hit.
    pub hit: bool,
    /// Argv used for the check command when one ran.
    pub argv: Vec<String>,
    /// Captured check stdout.
    pub stdout: String,
    /// Cap-hit payload when hit.
    pub payload: String,
}

/// Terminal status of a shared vendor launch.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VendorLaunchStatus {
    /// Launch completed through execution hooks.
    Completed,
    /// Token budget cap refused the launch.
    CapHit,
    /// Preflight refused the launch.
    PreflightRefused,
}

impl VendorLaunchStatus {
    /// Wire token matching the Python literal.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Completed => "completed",
            Self::CapHit => "cap_hit",
            Self::PreflightRefused => "preflight_refused",
        }
    }
}

/// Terminal outcome of `run_vendor_launch` (data shape only in this leaf).
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VendorLaunchOutcome {
    /// Terminal status.
    pub status: VendorLaunchStatus,
    /// Process result when execution ran.
    pub process_result: Option<VendorProcessResult>,
    /// Resolved model token.
    pub model: String,
    /// Full argv including the executable name.
    pub argv: Vec<String>,
    /// Cap-check outcome when one ran.
    pub cap_check: Option<VendorCapCheckResult>,
}