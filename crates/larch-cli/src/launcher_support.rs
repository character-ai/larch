//! Behavior every larch vendor launcher shares, owned once.
//!
//! The review, drafter, Claude subprocess, and CI launchers all resolve the
//! same execution-issues log, publish the same vendor failure-diagnostic parts,
//! discover the same work tree, emit the same launcher failure envelope, and
//! record Claude usage against the same ledger row. Each of those lives here so
//! a launcher never re-derives one.

use std::{env, ffi::OsString, path::Path, path::PathBuf, time::SystemTime, time::UNIX_EPOCH};

use larch_adapters::{
    TemporaryRoot, atomic_write_utf8_in, ensure_directory_chain, read_optional_utf8_lossy,
};
use larch_core::{
    AuthVerdict, ClaudeUsageTotals, LaunchFailureInputs, LauncherArtifact, RepositoryRead as _,
    SafeText, VendorProgram, classify_launch_failure, emit_kv,
};

use crate::python_verb::run_python_verb_best_effort;

/// Default cap on one vendor failure-diagnostic part, in bytes.
const DEFAULT_VENDOR_FAILURE_DIAG_BYTES: usize = 20_000;

/// Resolve the execution-issues log this session writes launcher failures to.
///
/// `session_env` is the caller's `--session-env-path`, which wins over the
/// session tmpdir variables but not over an explicit log override.
pub fn execution_issues_log(session_env: &str) -> Option<PathBuf> {
    env::var_os("LARCH_EXECUTION_ISSUES_LOG")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .or_else(|| {
            (!session_env.is_empty())
                .then(|| PathBuf::from(session_env))
                .and_then(|path| {
                    path.parent()
                        .map(|parent| parent.join("execution-issues.md"))
                })
        })
        .or_else(|| {
            ["IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "REVIEW_TMPDIR"]
                .into_iter()
                .find_map(|name| {
                    env::var_os(name)
                        .filter(|value| !value.is_empty())
                        .map(PathBuf::from)
                })
                .map(|path| path.join("execution-issues.md"))
        })
}

/// Append one redacted vendor failure-diagnostic part under `IMPLEMENT_TMPDIR`.
///
/// `label` is the full `===== … =====` heading, so the caller decides how its
/// site and tool read. Every step is best effort: a missing tmpdir, an
/// unresolvable root, or a failed write leaves the run untouched.
pub fn append_vendor_failure_diagnostic(source: &Path, label: &str, exit_code: i32) {
    let Some(root_path) = env::var_os("IMPLEMENT_TMPDIR")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
    else {
        return;
    };
    let Ok(root) = TemporaryRoot::resolve(Some(&root_path)) else {
        return;
    };
    let parts = root.path().join("vendor-failure-diagnostics.parts");
    if ensure_directory_chain(&parts).is_err() {
        return;
    }
    let Ok(parts_root) = TemporaryRoot::resolve(Some(&parts)) else {
        return;
    };
    let body = read_optional_utf8_lossy(source)
        .unwrap_or_default()
        .unwrap_or_default();
    let body = if body.is_empty() {
        format!("no diagnostics captured (exit {exit_code})\n")
    } else {
        body
    };
    let text = format!(
        "===== {label} =====\nexit-code: {exit_code}\n{}\n",
        body.trim_end()
    );
    let redacted = SafeText::from_untrusted(&text).as_str().to_owned();
    let capped = larch_core::truncate_utf8_bytes(&redacted, vendor_failure_diagnostic_cap());
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    let _written = atomic_write_utf8_in(
        &parts_root,
        &parts.join(format!("part.{stamp:032x}")),
        capped,
        true,
        0o600,
    );
}

fn vendor_failure_diagnostic_cap() -> usize {
    env::var("LARCH_VENDOR_FAILURE_DIAG_BYTES")
        .ok()
        .and_then(|raw| raw.parse::<usize>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(DEFAULT_VENDOR_FAILURE_DIAG_BYTES)
}

/// Resolve the work-tree root that owns one directory.
pub fn git_workdir(path: &Path) -> Option<PathBuf> {
    let repository = larch_adapters::GixRepository::discover(path).ok()?;
    let work_dir = repository.location().work_dir?;
    Some(PathBuf::from(
        String::from_utf8_lossy(work_dir.as_bytes()).into_owned(),
    ))
}

/// One launcher's terminal failure classification inputs.
pub struct LauncherFailureEnvelope<'a> {
    /// Launcher exit code.
    pub launcher_exit: i32,
    /// Vendor whose failure vocabulary applies.
    pub tool: VendorProgram,
    /// Authentication verdict already computed by the caller.
    pub auth_verdict: AuthVerdict,
    /// Whether the vendor executable was present.
    pub binary_present: bool,
    /// Diagnostic carrier text.
    pub sidecar: String,
    /// Published launcher output text.
    pub output: String,
    /// Reason used when the classifier has none.
    pub fallback_reason: &'a str,
    /// Output path exactly as the caller supplied it.
    pub output_label: &'a str,
}

/// Emit `LAUNCHER_FAILURE_CLASS`, `LAUNCHER_FAILURE_REASON`, and `OUTPUT`.
///
/// `LAUNCHER_EXIT` stays with the caller: some launchers emit it before the
/// artifacts that this classification reads exist.
pub fn emit_launcher_failure_envelope(envelope: &LauncherFailureEnvelope<'_>) {
    let sidecar = LauncherArtifact::present(envelope.sidecar.clone());
    let output = LauncherArtifact::present(envelope.output.clone());
    let failure = classify_launch_failure(&LaunchFailureInputs {
        launcher_exit: envelope.launcher_exit,
        tool: envelope.tool,
        auth_verdict: envelope.auth_verdict,
        binary_present: envelope.binary_present,
        sidecar: Some(&sidecar),
        output: Some(&output),
    });
    emit_kv("LAUNCHER_FAILURE_CLASS", failure.class().as_str());
    let reason = failure.reason().as_str();
    emit_kv(
        "LAUNCHER_FAILURE_REASON",
        if reason.is_empty() {
            envelope.fallback_reason
        } else {
            reason
        },
    );
    emit_kv("OUTPUT", envelope.output_label);
}

/// Resolve Cursor's model argv tokens, or an explicit single-model override.
pub fn cursor_model_argv(override_model: Option<&str>) -> Result<Vec<String>, String> {
    if let Some(model) = override_model.filter(|value| !value.is_empty()) {
        return Ok(vec!["--model".to_owned(), model.to_owned()]);
    }
    larch_core::resolve_model_args(
        larch_core::ModelTool::Cursor,
        true,
        "",
        larch_core::CodexModelRole::Default,
        &env::vars().collect(),
    )
    .map(|resolved| resolved.argv().to_vec())
    .map_err(|error| error.to_string())
}

/// Record one Claude subprocess's usage against the shared `claude_sub` row.
pub fn record_claude_sub_usage(usage: ClaudeUsageTotals, raw: &str, ledger_model: &str) {
    run_python_verb_best_effort([
        OsString::from("token"),
        OsString::from("record-vendor"),
        OsString::from("claude_sub"),
        OsString::from(format!("input={}", usage.input_tokens())),
        OsString::from(format!("output={}", usage.output_tokens())),
        OsString::from(format!("cache_read={}", usage.cache_read_tokens())),
        OsString::from(format!("cache_create={}", usage.cache_create_tokens())),
        OsString::from(format!("total={}", usage.total_tokens())),
        OsString::from(format!("raw={raw}")),
        OsString::from(format!("model={ledger_model}")),
    ]);
}
