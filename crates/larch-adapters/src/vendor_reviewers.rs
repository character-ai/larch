//! Live `check_reviewers` probe orchestration and Cursor model-list spawning.
//!
//! Credentials and vendor executables never touch this process environment.
//! Probe children receive typed [`ChildEnvironment`] overlays on an approved
//! [`ProcessRequest`] only.

use crate::{
    SecureTempDir, TemporaryRoot,
    vendor_auth::{
        CursorPreflightConfig, CursorProbeSession, CursorTokenPreread, ProbeCache,
        VendorAuthContext, cursor_auth_preflight, cursor_preread_service_token,
    },
    vendor_lifecycle::{StartupLockConfig, StartupLockGuard},
};
use larch_core::{
    CODEX_REVIEW_MODEL_DEFAULT, CURSOR_MODEL_LIST_ARGV, CURSOR_PREFLIGHT_AUTH_RC,
    CheckReviewersConfig, CheckReviewersResult, ChildEnvironment, CodexEnvAuth, CodexModelRole,
    CodexProbeAttempt, CodexProbeLoop, CursorModelListOutcome, CursorProbeLoop,
    ExternalProcessRunner, ExternalProgram, ModelTool, PROBE_NO_RETRY_RC, PROBE_TIMEOUT_EXIT_CODE,
    ProbeStep, ProbeTtl, ProcessCancellation, ProcessErrorKind, ProcessRequest, VendorProgram,
    binary_on_path, codex_auth_args, codex_env_auth_from_key, codex_probe_identity,
    detect_codex_cli_gate, external_auth_verdict, extract_model_from_argv, probe_attempt_rc,
    resolve_model_args, trust_config_arg,
};
use regex::Regex;
use std::{
    collections::BTreeMap,
    ffi::OsString,
    fs,
    io::{self, Write},
    num::NonZeroUsize,
    path::Path,
    sync::OnceLock,
    time::Duration,
};

/// Bounded capture ceiling for one probe or model-list child.
const PROBE_OUTPUT_LIMIT: usize = 256 * 1024;

/// Bounded shutdown grace for one probe or model-list child.
const PROBE_SHUTDOWN_GRACE: Duration = Duration::from_secs(5);

/// Cursor probe prompt matching the Python check-reviewers child.
const CURSOR_PROBE_PROMPT: &str = " /max-mode on. Prompt: Respond with OK";

/// Codex probe prompt matching the Python check-reviewers child.
const CODEX_PROBE_PROMPT: &str = "Respond with OK";

/// Resolved inputs for one `check_reviewers` run.
#[derive(Clone, Copy, Debug)]
pub struct CheckReviewersContext<'a> {
    /// Temporary root owning probe homes, locks, and the probe cache.
    pub temporary_root: &'a TemporaryRoot,
    /// Operator home used to source `~/.codex` and `~/.cursor` material.
    pub home: &'a Path,
    /// Absolute working directory for probe children.
    pub working_directory: &'a Path,
    /// `PATH` value used for binary discovery (never applied to this process).
    pub path_env: Option<&'a str>,
    /// Optional user component for probe-cache and startup-lock basenames.
    pub user: Option<&'a str>,
    /// Optional live `OPENAI_API_KEY` for Codex env-key auth.
    pub openai_api_key: Option<&'a str>,
    /// Optional live `CURSOR_API_KEY` for Cursor preflight / injection.
    pub cursor_api_key: Option<&'a str>,
    /// `uname`-style platform name (`Darwin`, `Linux`, …).
    pub platform: &'a str,
    /// Environment map for [`resolve_model_args`] (never applied to this process).
    pub env_map: &'a BTreeMap<String, String>,
}

/// Probe Codex and Cursor availability, reusing fresh stamps when present.
pub async fn check_reviewers<R: ExternalProcessRunner>(
    runner: &R,
    config: &CheckReviewersConfig,
    context: CheckReviewersContext<'_>,
    cancellation: &dyn ProcessCancellation,
) -> CheckReviewersResult {
    let codex_binary_found = binary_on_path("codex", context.path_env);
    let cursor_binary_found = binary_on_path("cursor", context.path_env);
    let cache = ProbeCache::new(
        context.temporary_root.clone(),
        context.user,
        ProbeTtl::from_seconds(config.ttl_seconds, config.negative_ttl_seconds),
    );

    let (cursor_present, cursor_probe_timed_out) =
        if cursor_binary_found && !config.skip_cursor_probe {
            probe_cursor(runner, config, context, &cache, cancellation).await
        } else {
            (false, false)
        };

    let (codex_present, codex_probe_timed_out, codex_gate_detail) =
        if codex_binary_found && !config.skip_codex_probe {
            probe_codex(runner, config, context, &cache, cancellation).await
        } else {
            (false, false, None)
        };

    CheckReviewersResult::new(
        codex_binary_found,
        cursor_binary_found,
        codex_present,
        cursor_present,
        codex_probe_timed_out,
        cursor_probe_timed_out,
        codex_gate_detail,
    )
}

/// Spawn `cursor agent models` and capture the list outcome.
pub async fn run_cursor_model_list<R: ExternalProcessRunner>(
    runner: &R,
    working_directory: &Path,
    timeout: Duration,
    cancellation: &dyn ProcessCancellation,
) -> CursorModelListOutcome {
    let Ok(request) = ProcessRequest::new(
        ExternalProgram::Vendor(VendorProgram::Cursor),
        CURSOR_MODEL_LIST_ARGV.map(OsString::from),
        working_directory.to_path_buf(),
        timeout,
        PROBE_SHUTDOWN_GRACE,
        NonZeroUsize::new(PROBE_OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN),
    ) else {
        return CursorModelListOutcome {
            returncode: 1,
            stdout: String::new(),
            stderr: String::new(),
            timed_out: false,
        };
    };
    match runner.run(request, cancellation).await {
        Ok(output) => CursorModelListOutcome {
            returncode: output.status().code().unwrap_or(1),
            stdout: String::from_utf8_lossy(output.stdout()).into_owned(),
            stderr: String::from_utf8_lossy(output.stderr()).into_owned(),
            timed_out: false,
        },
        Err(error) if error.kind() == ProcessErrorKind::TimedOut => CursorModelListOutcome {
            returncode: PROBE_TIMEOUT_EXIT_CODE,
            stdout: String::new(),
            stderr: String::new(),
            timed_out: true,
        },
        Err(_) => CursorModelListOutcome {
            returncode: 1,
            stdout: String::new(),
            stderr: String::new(),
            timed_out: false,
        },
    }
}

/// Prepare an isolated Codex home for one probe attempt.
///
/// Ports the focused `_prepare_codex_home` path without trusted-instructions.
///
/// # Errors
/// Returns an operator-facing message when directory setup or auth linking fails.
pub fn prepare_codex_home(
    probe_home: &Path,
    operator_home: &Path,
    openai_api_key: Option<&str>,
) -> Result<(), String> {
    fs::create_dir_all(probe_home).map_err(|error| format!("codex auth setup failed: {error}"))?;
    let user_config = operator_home.join(".codex").join("config.toml");
    let config_text = if user_config.is_file() {
        fs::read_to_string(&user_config)
            .map_err(|error| format!("codex auth setup failed: {error}"))?
    } else {
        String::new()
    };
    let stripped = strip_codex_config(&config_text);
    if !stripped.is_empty() {
        let mut file = fs::File::create(probe_home.join("config.toml"))
            .map_err(|error| format!("codex auth setup failed: {error}"))?;
        file.write_all(stripped.as_bytes())
            .map_err(|error| format!("codex auth setup failed: {error}"))?;
    }
    if codex_env_auth_from_key(openai_api_key) == CodexEnvAuth::Omit {
        let auth = operator_home.join(".codex").join("auth.json");
        if auth.is_file() {
            let target = probe_home.join("auth.json");
            let resolved = fs::canonicalize(&auth)
                .map_err(|error| format!("codex auth setup failed: {error}"))?;
            symlink_file(&resolved, &target)
                .map_err(|error| format!("codex auth setup failed: {error}"))?;
        }
    }
    Ok(())
}

async fn probe_cursor<R: ExternalProcessRunner>(
    runner: &R,
    config: &CheckReviewersConfig,
    context: CheckReviewersContext<'_>,
    cache: &ProbeCache,
    cancellation: &dyn ProcessCancellation,
) -> (bool, bool) {
    if let Some(cached) = cache.read_verdict("cursor") {
        return (cached, false);
    }

    let preflight_config = CursorPreflightConfig::from_values(
        context.platform,
        context.cursor_api_key,
        "agent check-reviewers",
    );
    let startup_lock = startup_lock(VendorProgram::Cursor, context);
    let auth_context = VendorAuthContext {
        temporary_root: context.temporary_root,
        startup_lock: &startup_lock,
        working_directory: context.working_directory,
    };
    let preflight =
        cursor_auth_preflight(runner, &preflight_config, auth_context, cancellation).await;
    let mut retry_limits = config.retry_limits;
    if !preflight.ok || preflight.rc == CURSOR_PREFLIGHT_AUTH_RC {
        retry_limits = retry_limits.after_failed_preflight();
    }

    let preread =
        cursor_preread_service_token(runner, &preflight_config, auth_context, cancellation).await;
    let CursorTokenPreread::Proceed(credential) = preread else {
        let _ = cache.write_verdict("cursor", false);
        return (false, false);
    };

    let Ok(session) = CursorProbeSession::open(context.temporary_root, context.home, credential)
    else {
        let _ = cache.write_verdict("cursor", false);
        return (false, false);
    };

    let model_args = resolve_model_args(
        ModelTool::Cursor,
        false,
        "",
        CodexModelRole::Default,
        context.env_map,
    )
    .map(|result| result.argv().to_vec())
    .unwrap_or_default();

    let mut loop_state = CursorProbeLoop::new(retry_limits);
    let conclusion = loop {
        let rc = run_one_cursor_probe(
            runner,
            context,
            &session,
            &model_args,
            &startup_lock,
            config.timeout_seconds,
            cancellation,
        )
        .await;
        match loop_state.observe(rc) {
            ProbeStep::Retry => {}
            ProbeStep::Stop(conclusion) => break conclusion,
        }
    };
    let _ = session.close();
    let _ = cache.write_verdict("cursor", conclusion.present());
    (conclusion.present(), conclusion.timed_out())
}

async fn run_one_cursor_probe<R: ExternalProcessRunner>(
    runner: &R,
    context: CheckReviewersContext<'_>,
    session: &CursorProbeSession,
    model_args: &[String],
    startup_lock: &StartupLockConfig,
    timeout_seconds: u64,
    cancellation: &dyn ProcessCancellation,
) -> i32 {
    let mut arguments = vec![
        OsString::from("agent"),
        OsString::from("-p"),
        OsString::from(CURSOR_PROBE_PROMPT),
        OsString::from("--trust"),
        OsString::from("--workspace"),
        OsString::from(context.working_directory.as_os_str()),
    ];
    arguments.extend(model_args.iter().map(OsString::from));

    let Ok(mut request) = ProcessRequest::new(
        ExternalProgram::Vendor(VendorProgram::Cursor),
        arguments,
        context.working_directory.to_path_buf(),
        Duration::from_secs(timeout_seconds.max(1)),
        PROBE_SHUTDOWN_GRACE,
        NonZeroUsize::new(PROBE_OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN),
    ) else {
        return PROBE_NO_RETRY_RC;
    };
    for (key, value) in session.child_environment() {
        request = request.with_environment(key, value);
    }

    let _guard = StartupLockGuard::acquire(context.temporary_root, startup_lock);
    match runner.run(request, cancellation).await {
        Ok(output) => {
            let exit_code = output.status().code().unwrap_or(1);
            if exit_code == 0 {
                return 0;
            }
            let stdout = String::from_utf8_lossy(output.stdout());
            let stderr = String::from_utf8_lossy(output.stderr());
            let verdict = external_auth_verdict("cursor", [stdout.as_ref(), stderr.as_ref()]);
            probe_attempt_rc(exit_code, false, verdict)
        }
        Err(error) if error.kind() == ProcessErrorKind::TimedOut => PROBE_TIMEOUT_EXIT_CODE,
        Err(_) => 1,
    }
}

async fn probe_codex<R: ExternalProcessRunner>(
    runner: &R,
    config: &CheckReviewersConfig,
    context: CheckReviewersContext<'_>,
    cache: &ProbeCache,
    cancellation: &dyn ProcessCancellation,
) -> (bool, bool, Option<larch_core::CodexGateDetail>) {
    let model_result = resolve_model_args(
        ModelTool::Codex,
        true,
        "",
        CodexModelRole::Review,
        context.env_map,
    );
    let (model_args, resolved_model) = model_result.map_or_else(
        |_| (Vec::new(), "unknown".to_owned()),
        |result| {
            let model = extract_model_from_argv(result.argv());
            let model = if model.is_empty() {
                CODEX_REVIEW_MODEL_DEFAULT.to_owned()
            } else {
                model
            };
            (result.argv().to_vec(), model)
        },
    );
    let auth = codex_env_auth_from_key(context.openai_api_key);
    let identity = codex_probe_identity(auth, &resolved_model);
    let ttl = ProbeTtl::from_seconds(config.ttl_seconds, config.negative_ttl_seconds);

    if let Some(cached) = cache.read_verdict(&identity) {
        let gate = if cached {
            None
        } else {
            cache.read_gate_detail(&identity, ttl.immediate_gate_max_age())
        };
        return (cached, false, gate);
    }

    let _lock = cache.update_lock(&identity).ok();
    if let Some(cached) = cache.read_verdict(&identity) {
        let gate = if cached {
            None
        } else {
            cache.read_gate_detail(&identity, ttl.immediate_gate_max_age())
        };
        return (cached, false, gate);
    }

    if model_args.is_empty() && resolved_model == "unknown" {
        let _ = cache.write_verdict(&identity, false);
        let _ = cache.clear_gate_detail(&identity);
        return (false, false, None);
    }

    let startup_lock = startup_lock(VendorProgram::Codex, context);
    let mut loop_state = CodexProbeLoop::new(config.retry_limits);
    let (conclusion, gate_detail) = loop {
        let attempt = run_one_codex_probe(
            runner,
            context,
            &model_args,
            &resolved_model,
            auth,
            &startup_lock,
            config.timeout_seconds,
            cancellation,
        )
        .await;
        match loop_state.observe(attempt) {
            ProbeStep::Retry => {}
            ProbeStep::Stop(conclusion) => {
                break (conclusion, loop_state.gate_detail().cloned());
            }
        }
    };

    let _ = cache.write_verdict(&identity, conclusion.present());
    if let Some(ref detail) = gate_detail {
        let _ = cache.write_gate_detail(&identity, detail);
    } else {
        let _ = cache.clear_gate_detail(&identity);
    }
    (conclusion.present(), conclusion.timed_out(), gate_detail)
}

#[allow(clippy::too_many_arguments)] // mirrors the Python one-shot Codex probe surface
async fn run_one_codex_probe<R: ExternalProcessRunner>(
    runner: &R,
    context: CheckReviewersContext<'_>,
    model_args: &[String],
    resolved_model: &str,
    auth: CodexEnvAuth,
    startup_lock: &StartupLockConfig,
    timeout_seconds: u64,
    cancellation: &dyn ProcessCancellation,
) -> CodexProbeAttempt {
    let Ok(codex_home) = SecureTempDir::create(context.temporary_root, "larch-codex-probe-home-")
    else {
        return CodexProbeAttempt::from_exit(PROBE_NO_RETRY_RC);
    };
    if prepare_codex_home(codex_home.path(), context.home, context.openai_api_key).is_err() {
        return CodexProbeAttempt::from_exit(PROBE_NO_RETRY_RC);
    }

    let workdir = context.working_directory.to_string_lossy();
    let mut arguments = vec![
        OsString::from("exec"),
        OsString::from("--sandbox"),
        OsString::from("read-only"),
        OsString::from("-C"),
        OsString::from(context.working_directory.as_os_str()),
    ];
    arguments.extend(model_args.iter().map(OsString::from));
    arguments.push(OsString::from("-c"));
    arguments.push(OsString::from(trust_config_arg(workdir.as_ref())));
    arguments.extend(codex_auth_args(auth).into_iter().map(OsString::from));
    arguments.push(OsString::from("--"));
    arguments.push(OsString::from(CODEX_PROBE_PROMPT));

    let Ok(mut request) = ProcessRequest::new(
        ExternalProgram::Vendor(VendorProgram::Codex),
        arguments,
        context.working_directory.to_path_buf(),
        Duration::from_secs(timeout_seconds.max(1)),
        PROBE_SHUTDOWN_GRACE,
        NonZeroUsize::new(PROBE_OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN),
    ) else {
        return CodexProbeAttempt::from_exit(PROBE_NO_RETRY_RC);
    };
    request = request.with_environment(ChildEnvironment::CodexHome, codex_home.path().as_os_str());
    if let (CodexEnvAuth::Include, Some(key)) = (auth, context.openai_api_key) {
        request = request.with_environment(ChildEnvironment::OpenAiApiKey, key);
    }

    let _guard = StartupLockGuard::acquire(context.temporary_root, startup_lock);
    let (exit_code, timed_out, stdout, stderr) = match runner.run(request, cancellation).await {
        Ok(output) => (
            output.status().code().unwrap_or(1),
            false,
            String::from_utf8_lossy(output.stdout()).into_owned(),
            String::from_utf8_lossy(output.stderr()).into_owned(),
        ),
        Err(error) if error.kind() == ProcessErrorKind::TimedOut => {
            (PROBE_TIMEOUT_EXIT_CODE, true, String::new(), String::new())
        }
        Err(_) => (1, false, String::new(), String::new()),
    };

    let diagnostics = format!("{stdout}\n{stderr}");
    if let Some(detail) = detect_codex_cli_gate(&diagnostics, resolved_model) {
        return CodexProbeAttempt::from_gate(detail);
    }
    let verdict = external_auth_verdict("codex", [stdout.as_ref(), stderr.as_ref()]);
    CodexProbeAttempt::from_exit(probe_attempt_rc(exit_code, timed_out, verdict))
}

fn startup_lock(program: VendorProgram, context: CheckReviewersContext<'_>) -> StartupLockConfig {
    StartupLockConfig::from_values(
        program,
        context.platform,
        context.user,
        None,
        None,
        Some("0"),
    )
    .unwrap_or_else(|_| {
        StartupLockConfig::from_values(
            program,
            context.platform,
            Some("larch"),
            None,
            None,
            Some("0"),
        )
        .expect("fallback startup lock config")
    })
}

fn strip_codex_config(text: &str) -> String {
    static PROVIDER_HEADER: OnceLock<Regex> = OnceLock::new();
    static PROVIDER_ASSIGN: OnceLock<Regex> = OnceLock::new();
    static ENV_KEY: OnceLock<Regex> = OnceLock::new();
    static API_KEY: OnceLock<Regex> = OnceLock::new();
    let provider_header = PROVIDER_HEADER.get_or_init(|| {
        Regex::new(r"\[\[?\s*model_providers\.openai-larch-env\s*\]?\]").expect("provider header")
    });
    let provider_assign = PROVIDER_ASSIGN.get_or_init(|| {
        Regex::new(r#"model_provider\s*=\s*['"]?openai-larch-env"#).expect("provider assign")
    });
    let env_key = ENV_KEY
        .get_or_init(|| Regex::new(r#"env_key\s*=\s*['"]?OPENAI_API_KEY"#).expect("env_key"));
    let api_key = API_KEY.get_or_init(|| {
        Regex::new(r"([A-Za-z0-9_-]+\.)*(api_key|openai_api_key)\s*=").expect("api_key")
    });

    let mut out = Vec::new();
    let mut skip_block_delim = "";
    let mut skip_provider = false;
    for line in text.lines() {
        let stripped = line.trim();
        if !skip_block_delim.is_empty() {
            if line.contains(skip_block_delim) {
                skip_block_delim = "";
            }
            continue;
        }
        if skip_provider {
            if stripped.starts_with('[') {
                skip_provider = false;
            } else {
                continue;
            }
        }
        if provider_header.is_match(stripped) {
            skip_provider = true;
            continue;
        }
        if provider_assign.is_match(stripped) || env_key.is_match(stripped) {
            continue;
        }
        if api_key.is_match(stripped) {
            if stripped.contains("'''") && stripped.matches("'''").count() < 2 {
                skip_block_delim = "'''";
            } else if stripped.contains("\"\"\"") && stripped.matches("\"\"\"").count() < 2 {
                skip_block_delim = "\"\"\"";
            }
            continue;
        }
        out.push(line);
    }
    if out.is_empty() {
        String::new()
    } else {
        let mut rendered = out.join("\n");
        rendered.push('\n');
        rendered
    }
}

fn symlink_file(target: &Path, link: &Path) -> io::Result<()> {
    #[cfg(unix)]
    {
        std::os::unix::fs::symlink(target, link)
    }
    #[cfg(not(unix))]
    {
        fs::copy(target, link).map(|_| ())
    }
}
