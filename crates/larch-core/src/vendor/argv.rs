//! Exact vendor argv builders. Builders never compose an executable path.

use super::{VendorLaunchRequest, VendorSessionHandle, VendorSessionVendor};
use crate::VendorProgram;
use std::{error::Error, fmt};

/// Whether Codex env-key auth `-c` overrides are included in argv.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum CodexEnvAuth {
    /// Omit the openai-larch-env provider overrides.
    #[default]
    Omit,
    /// Include the fixed openai-larch-env provider overrides.
    Include,
}

/// Decide Codex env-auth inclusion from an explicit key value.
///
/// Callers pass the key they already resolved. This helper never reads process
/// environment, so tests and parallel clones stay isolated.
#[must_use]
pub fn codex_env_auth_from_key(openai_api_key: Option<&str>) -> CodexEnvAuth {
    match openai_api_key {
        Some(value) if !value.trim().is_empty() => CodexEnvAuth::Include,
        _ => CodexEnvAuth::Omit,
    }
}

/// Typed vendor argv: closed program plus arguments without the executable.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VendorArgv {
    program: VendorProgram,
    arguments: Vec<String>,
}

impl VendorArgv {
    /// Build from a closed program and its trailing arguments.
    #[must_use]
    pub const fn new(program: VendorProgram, arguments: Vec<String>) -> Self {
        Self {
            program,
            arguments,
        }
    }

    /// Closed vendor program for the process port.
    #[must_use]
    pub const fn program(&self) -> VendorProgram {
        self.program
    }

    /// Arguments after the executable name.
    #[must_use]
    pub fn arguments(&self) -> &[String] {
        &self.arguments
    }

    /// Full argv including `VendorProgram::executable()` as argv[0].
    #[must_use]
    pub fn full_argv(&self) -> Vec<String> {
        let mut argv = Vec::with_capacity(self.arguments.len() + 1);
        argv.push(self.program.executable().to_owned());
        argv.extend(self.arguments.iter().cloned());
        argv
    }
}

/// Argv construction failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VendorArgvError {
    kind: VendorArgvErrorKind,
    detail: String,
}

impl VendorArgvError {
    fn new(kind: VendorArgvErrorKind, detail: impl Into<String>) -> Self {
        Self {
            kind,
            detail: detail.into(),
        }
    }

    /// Stable failure category.
    #[must_use]
    pub const fn kind(&self) -> VendorArgvErrorKind {
        self.kind
    }

    /// Human-readable detail.
    #[must_use]
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

/// Categories of argv-builder rejection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VendorArgvErrorKind {
    /// Profile name is not declared for the vendor family.
    UnknownProfile,
    /// Required request field is missing.
    MissingField,
    /// Session handle vendor does not match the builder.
    WrongVendor,
    /// Session handle failed revalidation.
    InvalidSession,
}

impl fmt::Display for VendorArgvError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.detail)
    }
}

impl Error for VendorArgvError {}

/// Codex `projects."<workdir>".trust_level="trusted"` config override.
#[must_use]
pub fn trust_config_arg(workdir: &str) -> String {
    let key = workdir.replace('\\', "\\\\").replace('"', "\\\"");
    format!("projects.\"{key}\".trust_level=\"trusted\"")
}

/// Fixed Codex env-key auth `-c` pairs when auth is included.
#[must_use]
pub fn codex_auth_args(auth: CodexEnvAuth) -> Vec<String> {
    match auth {
        CodexEnvAuth::Omit => Vec::new(),
        CodexEnvAuth::Include => vec![
            "-c".to_owned(),
            "model_provider=\"openai-larch-env\"".to_owned(),
            "-c".to_owned(),
            "model_providers.openai-larch-env.name=\"OpenAI API (larch env key)\"".to_owned(),
            "-c".to_owned(),
            "model_providers.openai-larch-env.base_url=\"https://api.openai.com/v1\"".to_owned(),
            "-c".to_owned(),
            "model_providers.openai-larch-env.env_key=\"OPENAI_API_KEY\"".to_owned(),
            "-c".to_owned(),
            "model_providers.openai-larch-env.wire_api=\"responses\"".to_owned(),
        ],
    }
}

/// Extract a model from Codex `-m`, Cursor `--model`, or Claude `--model`.
///
/// Missing or dangling flags return an empty string. Prefers `--model` over `-m`.
#[must_use]
pub fn extract_model_from_argv(argv: &[String]) -> String {
    for flag in ["--model", "-m"] {
        if let Some(idx) = argv.iter().position(|token| token == flag)
            && idx + 1 < argv.len()
        {
            return argv[idx + 1].clone();
        }
    }
    String::new()
}

/// Build Codex `codex exec` argv for `read-only` or `workspace-write`.
///
/// # Errors
/// Rejects unknown profiles.
pub fn build_codex_argv(
    profile: &str,
    request: &VendorLaunchRequest,
    auth: CodexEnvAuth,
) -> Result<VendorArgv, VendorArgvError> {
    let sandbox = match profile {
        "read-only" => "read-only",
        "workspace-write" => "workspace-write",
        _ => {
            return Err(VendorArgvError::new(
                VendorArgvErrorKind::UnknownProfile,
                format!("unknown Codex argv profile: {profile}"),
            ));
        }
    };
    let mut arguments = vec![
        "exec".to_owned(),
        "--sandbox".to_owned(),
        sandbox.to_owned(),
        "-C".to_owned(),
        request.workdir.clone(),
    ];
    for directory in &request.add_dirs {
        arguments.push("--add-dir".to_owned());
        arguments.push(directory.clone());
    }
    arguments.extend(request.model_args.iter().cloned());
    arguments.push("-c".to_owned());
    arguments.push(trust_config_arg(&request.workdir));
    arguments.extend(codex_auth_args(auth));
    arguments.push("--output-last-message".to_owned());
    arguments.push(request.output.clone());
    arguments.push("--json".to_owned());
    arguments.push("--".to_owned());
    arguments.push(if request.prompt_via_stdin {
        "-".to_owned()
    } else {
        request.prompt.clone()
    });
    Ok(VendorArgv::new(VendorProgram::Codex, arguments))
}

/// Build the read-only Codex initial-session argv used before explicit resume.
///
/// # Errors
/// Propagates unknown-profile errors from [`build_codex_argv`].
pub fn build_codex_session_argv(
    request: &VendorLaunchRequest,
) -> Result<VendorArgv, VendorArgvError> {
    build_codex_argv("read-only", request, request.codex_env_auth)
}

/// Build `codex exec resume <UUID>` argv without latest-session fallback.
///
/// # Errors
/// Rejects non-Codex handles and revalidates the session id.
pub fn build_codex_resume_argv(
    handle: &VendorSessionHandle,
    request: &VendorLaunchRequest,
) -> Result<VendorArgv, VendorArgvError> {
    if handle.vendor() != VendorSessionVendor::Codex {
        return Err(VendorArgvError::new(
            VendorArgvErrorKind::WrongVendor,
            format!("wrong vendor for codex resume: {}", handle.vendor().as_str()),
        ));
    }
    let validated = VendorSessionHandle::create(handle.vendor().as_str(), handle.session_id())
        .map_err(|error| {
            VendorArgvError::new(VendorArgvErrorKind::InvalidSession, error.to_string())
        })?;
    let mut arguments = vec![
        "exec".to_owned(),
        "resume".to_owned(),
        validated.session_id().to_owned(),
    ];
    arguments.extend(request.model_args.iter().cloned());
    arguments.push("-c".to_owned());
    arguments.push(trust_config_arg(&request.workdir));
    arguments.extend(codex_auth_args(request.codex_env_auth));
    arguments.push("-c".to_owned());
    arguments.push("sandbox_mode=\"read-only\"".to_owned());
    arguments.push("--output-last-message".to_owned());
    arguments.push(request.output.clone());
    arguments.push("--json".to_owned());
    arguments.push(if request.prompt_via_stdin {
        "-".to_owned()
    } else {
        request.prompt.clone()
    });
    Ok(VendorArgv::new(VendorProgram::Codex, arguments))
}

/// Build the verified option-free `cursor agent create-chat` argv.
#[must_use]
pub fn build_cursor_create_chat_argv() -> VendorArgv {
    VendorArgv::new(
        VendorProgram::Cursor,
        vec!["agent".to_owned(), "create-chat".to_owned()],
    )
}

/// Build `cursor agent -p --resume <chatId>` argv in plan mode with `--trust`.
///
/// # Errors
/// Rejects non-Cursor handles and revalidates the session id.
pub fn build_cursor_resume_argv(
    handle: &VendorSessionHandle,
    request: &VendorLaunchRequest,
) -> Result<VendorArgv, VendorArgvError> {
    if handle.vendor() != VendorSessionVendor::Cursor {
        return Err(VendorArgvError::new(
            VendorArgvErrorKind::WrongVendor,
            format!(
                "wrong vendor for cursor resume: {}",
                handle.vendor().as_str()
            ),
        ));
    }
    let validated = VendorSessionHandle::create(handle.vendor().as_str(), handle.session_id())
        .map_err(|error| {
            VendorArgvError::new(VendorArgvErrorKind::InvalidSession, error.to_string())
        })?;
    let mut arguments = vec![
        "agent".to_owned(),
        "-p".to_owned(),
        "--resume".to_owned(),
        validated.session_id().to_owned(),
        "--mode".to_owned(),
        "plan".to_owned(),
        "--trust".to_owned(),
        "--output-format".to_owned(),
        "json".to_owned(),
    ];
    arguments.extend(request.model_args.iter().cloned());
    arguments.push("--workspace".to_owned());
    arguments.push(request.workdir.clone());
    arguments.push(request.prompt.clone());
    Ok(VendorArgv::new(VendorProgram::Cursor, arguments))
}

/// Build Cursor `cursor agent -p` argv for a named profile.
///
/// # Errors
/// Rejects unknown profiles.
pub fn build_cursor_argv(
    profile: &str,
    request: &VendorLaunchRequest,
) -> Result<VendorArgv, VendorArgvError> {
    let mut arguments = vec!["agent".to_owned(), "-p".to_owned()];
    match profile {
        "review-ask" => {
            arguments.extend([
                "--trust".to_owned(),
                "--mode".to_owned(),
                "ask".to_owned(),
                "--output-format".to_owned(),
                "json".to_owned(),
            ]);
            arguments.extend(request.model_args.iter().cloned());
        }
        "ci-write" => {
            arguments.extend(["--force".to_owned(), "--trust".to_owned()]);
            arguments.extend(request.model_args.iter().cloned());
            arguments.extend(["--output-format".to_owned(), "json".to_owned()]);
        }
        "implement-write" => {
            arguments.extend([
                "--force".to_owned(),
                "--trust".to_owned(),
                "--output-format".to_owned(),
                "json".to_owned(),
            ]);
            arguments.extend(request.model_args.iter().cloned());
        }
        "negotiation-write" => {
            arguments.extend(["--force".to_owned(), "--trust".to_owned()]);
            arguments.extend(request.model_args.iter().cloned());
        }
        "lint-fix-write" => {
            arguments.push("--trust".to_owned());
            arguments.extend(request.model_args.iter().cloned());
        }
        _ => {
            return Err(VendorArgvError::new(
                VendorArgvErrorKind::UnknownProfile,
                format!("unknown Cursor argv profile: {profile}"),
            ));
        }
    }
    arguments.push("--workspace".to_owned());
    arguments.push(request.workdir.clone());
    arguments.push(request.prompt.clone());
    Ok(VendorArgv::new(VendorProgram::Cursor, arguments))
}

/// Build Claude argv for a named profile. Prompt is stdin-transported.
///
/// # Errors
/// Rejects unknown profiles and a missing `read_tools_add_dir` for review-subprocess.
pub fn build_claude_argv(
    profile: &str,
    request: &VendorLaunchRequest,
) -> Result<VendorArgv, VendorArgvError> {
    let model = request.model.clone();
    let arguments = match profile {
        "review-subprocess" => {
            if request.read_tools_add_dir.is_empty() {
                return Err(VendorArgvError::new(
                    VendorArgvErrorKind::MissingField,
                    "Claude review-subprocess requires read_tools_add_dir",
                ));
            }
            vec![
                "--print".to_owned(),
                "--output-format".to_owned(),
                "json".to_owned(),
                "--model".to_owned(),
                model,
                "--add-dir".to_owned(),
                request.read_tools_add_dir.clone(),
                "--allowedTools".to_owned(),
                "Read".to_owned(),
                "--permission-mode".to_owned(),
                "plan".to_owned(),
            ]
        }
        "review-subprocess-base" => {
            vec![
                "--print".to_owned(),
                "--output-format".to_owned(),
                "json".to_owned(),
                "--model".to_owned(),
                model,
            ]
        }
        "drafter-read" => {
            vec![
                "--model".to_owned(),
                model,
                "--print".to_owned(),
                "--output-format".to_owned(),
                "json".to_owned(),
                "--add-dir".to_owned(),
                request.workdir.clone(),
                "--allowedTools".to_owned(),
                "Read,Glob,Grep,LS".to_owned(),
                "--permission-mode".to_owned(),
                "plan".to_owned(),
            ]
        }
        "workspace-write" => {
            vec![
                "-p".to_owned(),
                "--output-format".to_owned(),
                "json".to_owned(),
                "--model".to_owned(),
                model,
                "--add-dir".to_owned(),
                request.workdir.clone(),
                "--allowedTools".to_owned(),
                "Read,Edit,Write".to_owned(),
            ]
        }
        _ => {
            return Err(VendorArgvError::new(
                VendorArgvErrorKind::UnknownProfile,
                format!("unknown Claude argv profile: {profile}"),
            ));
        }
    };
    Ok(VendorArgv::new(VendorProgram::Claude, arguments))
}