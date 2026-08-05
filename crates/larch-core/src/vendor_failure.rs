//! Vendor launch failure classification and launcher-exit resolution.
//!
//! Every function here is effect-free. A caller reads the launcher artifacts
//! through the adapter layer and passes their decoded text as [`LauncherArtifact`].

use regex::Regex;
use std::sync::LazyLock;

use crate::{CrStrip, DuplicatePolicy, ExitCode, KvDocument, ParseOptions, VendorProgram};

static PARSE_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?i-u:invalid json|unexpected token|parse error|jq: error|syntaxerror|unmarshal|cannot unmarshal)",
    )
    .expect("static parse regex must compile")
});
static REFUSAL_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i-u:refused to|refusal|denied by policy|policy violation)")
        .expect("static refusal regex must compile")
});
static QUOTA_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?i-u:usage limit|rate[ _-]?limit|too many requests|quota|429 too many|over your usage)",
    )
    .expect("static quota regex must compile")
});
static CONTROL_PATTERN: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[\x00-\x1f\x7f]").expect("static control regex must compile"));
static CODEX_METADATA_GATE_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i-u:Model metadata for)\s+(?P<model>\S+)\s+(?i-u:not found)")
        .expect("static codex metadata gate regex must compile")
});
static CODEX_VERSION_GATE_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r#"(?:(?P<model>['"]?[^\s'"]+['"]?)\s+(?i-u:model)\s+)?(?i-u:requires a newer version of Codex)"#,
    )
        .expect("static codex version gate regex must compile")
});
static SAFE_CODEX_MODEL_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\A[A-Za-z0-9][A-Za-z0-9._:-]*\z").expect("static codex model regex must compile")
});
static OPENAI_STREAM_DISCONNECTED_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?i-u:stream disconnected before completion)(?s).*(?i-u:api\.openai\.com|/v1/responses)",
    )
    .expect("static openai stream regex must compile")
});
static CURSOR_API_UNREACHABLE_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i-u:failed to reach the cursor api)")
        .expect("static cursor api regex must compile")
});

/// Coarse routing class carried on the `LAUNCHER_FAILURE_CLASS` wire key.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum FailureClass {
    /// The launch succeeded.
    None,
    /// Infrastructure, credential, or capacity problem worth a health route.
    #[default]
    Health,
    /// A launch-specific defect that health routing cannot repair.
    Other,
}

impl FailureClass {
    /// Return the exact wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Health => "health",
            Self::Other => "other",
        }
    }

    /// Parse one wire token, rejecting every unrecognized value.
    #[must_use]
    pub fn parse(token: &str) -> Option<Self> {
        match token {
            "none" => Some(Self::None),
            "health" => Some(Self::Health),
            "other" => Some(Self::Other),
            _ => None,
        }
    }
}

/// Distinct failure reason emitted next to a [`FailureClass`].
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FailureReason {
    /// No failure occurred.
    None,
    /// The vendor executable is absent from the resolved path.
    BinaryMissing,
    /// Authentication preflight classified the launch as an auth failure.
    Auth,
    /// A diagnostic artifact carries a quota or rate-limit signature.
    Quota,
    /// The launcher exit code and empty output match a transient infra failure.
    HealthProbe,
    /// The launcher reported the reserved timeout exit code.
    Timeout,
    /// A diagnostic artifact carries a parse-error signature.
    Parse,
    /// A diagnostic artifact carries a model-refusal signature.
    Refusal,
    /// The `OpenAI` response stream disconnected before completion.
    OpenAiStreamDisconnected,
    /// The Cursor API was unreachable.
    CursorApiUnreachable,
    /// No recorded signature matched.
    Unknown,
}

impl FailureReason {
    /// Return the exact wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::None => "",
            Self::BinaryMissing => "binary-missing",
            Self::Auth => "auth",
            Self::Quota => "quota",
            Self::HealthProbe => "health-probe",
            Self::Timeout => "timeout",
            Self::Parse => "parse",
            Self::Refusal => "refusal",
            Self::OpenAiStreamDisconnected => "openai-stream-disconnected",
            Self::CursorApiUnreachable => "cursor-api-unreachable",
            Self::Unknown => "unknown",
        }
    }
}

/// One classified launch failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct LaunchFailure {
    class: FailureClass,
    reason: FailureReason,
}

impl LaunchFailure {
    const fn new(class: FailureClass, reason: FailureReason) -> Self {
        Self { class, reason }
    }

    /// Return the routing class.
    #[must_use]
    pub const fn class(self) -> FailureClass {
        self.class
    }

    /// Return the distinct reason token.
    #[must_use]
    pub const fn reason(self) -> FailureReason {
        self.reason
    }
}

/// Codex diagnostic that requires a newer Codex CLI.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CodexGateDetail {
    model: String,
    signal: CodexGateSignal,
    message: String,
}

impl CodexGateDetail {
    /// Return the safe model token named by the gate.
    #[must_use]
    pub fn model(&self) -> &str {
        &self.model
    }

    /// Return the structured gate signal.
    #[must_use]
    pub const fn signal(&self) -> CodexGateSignal {
        self.signal
    }

    /// Return the operator-facing remediation message.
    #[must_use]
    pub fn message(&self) -> &str {
        &self.message
    }
}

/// Which Codex diagnostic produced a CLI gate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CodexGateSignal {
    /// Codex reported missing metadata for the requested model.
    ModelMetadataNotFound,
    /// Codex reported that the model needs a newer CLI.
    NewerCodexRequired,
}

impl CodexGateSignal {
    /// Return the exact wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ModelMetadataNotFound => "model-metadata-not-found",
            Self::NewerCodexRequired => "newer-codex-required",
        }
    }
}

/// One launcher diagnostic artifact the caller already resolved.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct LauncherArtifact {
    exists: bool,
    text: String,
}

impl LauncherArtifact {
    /// Build the record for a path that is not a regular file.
    #[must_use]
    pub const fn missing() -> Self {
        Self {
            exists: false,
            text: String::new(),
        }
    }

    /// Build the record for a regular file whose text the caller decoded.
    #[must_use]
    pub fn present(text: impl Into<String>) -> Self {
        Self {
            exists: true,
            text: text.into(),
        }
    }

    /// Return whether the path resolved to a regular file.
    #[must_use]
    pub const fn exists(&self) -> bool {
        self.exists
    }

    /// Return the decoded text, empty when the artifact is absent.
    #[must_use]
    pub fn text(&self) -> &str {
        &self.text
    }

    /// Return whether the artifact exists and holds no bytes.
    #[must_use]
    pub const fn is_empty_file(&self) -> bool {
        self.exists && self.text.is_empty()
    }
}

/// Authentication preflight verdict consumed by the classifier.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum AuthVerdict {
    /// Preflight proved a credential failure.
    Auth,
    /// Preflight reached no credential conclusion.
    #[default]
    Unclassified,
}

/// Complete input set for [`classify_launch_failure`].
#[derive(Clone, Debug)]
pub struct LaunchFailureInputs<'a> {
    /// Resolved launcher exit code.
    pub launcher_exit: i32,
    /// Vendor whose launch failed.
    pub tool: VendorProgram,
    /// Authentication preflight verdict.
    pub auth_verdict: AuthVerdict,
    /// Whether the vendor executable resolved on the search path.
    pub binary_present: bool,
    /// Sidecar diagnostic artifact, when the launcher declared one.
    pub sidecar: Option<&'a LauncherArtifact>,
    /// Primary output artifact, when the launcher declared one.
    pub output: Option<&'a LauncherArtifact>,
}

/// Classify Codex model diagnostics that require a newer Codex CLI.
#[must_use]
pub fn detect_codex_cli_gate(text: &str, fallback_model: &str) -> Option<CodexGateDetail> {
    let metadata = CODEX_METADATA_GATE_PATTERN.captures(text);
    let version = CODEX_VERSION_GATE_PATTERN.captures(text);
    let (signal, diagnostic_model) = match (&metadata, &version) {
        (Some(captures), _) => (
            CodexGateSignal::ModelMetadataNotFound,
            captures
                .name("model")
                .map_or("", |matched| matched.as_str()),
        ),
        (None, Some(captures)) => (
            CodexGateSignal::NewerCodexRequired,
            captures
                .name("model")
                .map_or("", |matched| matched.as_str()),
        ),
        (None, None) => return None,
    };
    let model = safe_codex_gate_model(diagnostic_model)
        .or_else(|| safe_codex_gate_model(fallback_model))
        .unwrap_or_else(|| String::from("unknown"));
    let message =
        format!("codex CLI too old for {model}; run `npm install -g @openai/codex@latest`");
    Some(CodexGateDetail {
        model,
        signal,
        message,
    })
}

fn safe_codex_gate_model(value: &str) -> Option<String> {
    let candidate = value
        .trim()
        .trim_matches(|character| character == '\'' || character == '"');
    if CONTROL_PATTERN.is_match(candidate) || !SAFE_CODEX_MODEL_PATTERN.is_match(candidate) {
        return None;
    }
    Some(candidate.to_owned())
}

/// Report whether a launcher exit plus an empty output marks a transient failure.
#[must_use]
pub fn is_transient_infra_failure(
    tool: VendorProgram,
    exit_code: i32,
    output: Option<&LauncherArtifact>,
) -> bool {
    let transient_codes: &[i32] = match tool {
        VendorProgram::Codex => &[5, 7],
        VendorProgram::Cursor => &[4, 8],
        VendorProgram::Claude => &[4, 5, 7, 8],
    };
    if !transient_codes.contains(&exit_code) {
        return false;
    }
    output.is_none_or(|artifact| !artifact.exists() || artifact.is_empty_file())
}

/// Report whether a diagnostic artifact carries a quota or rate-limit signature.
#[must_use]
pub fn is_quota_failure(sidecar: Option<&LauncherArtifact>) -> bool {
    sidecar.is_some_and(|artifact| artifact.exists() && QUOTA_PATTERN.is_match(artifact.text()))
}

/// Classify one launch failure from its exit code and diagnostic artifacts.
#[must_use]
pub fn classify_launch_failure(inputs: &LaunchFailureInputs<'_>) -> LaunchFailure {
    if inputs.launcher_exit == 0 {
        return LaunchFailure::new(FailureClass::None, FailureReason::None);
    }
    if !inputs.binary_present {
        return LaunchFailure::new(FailureClass::Health, FailureReason::BinaryMissing);
    }
    if inputs.auth_verdict == AuthVerdict::Auth {
        return LaunchFailure::new(FailureClass::Health, FailureReason::Auth);
    }
    if is_quota_failure(inputs.sidecar) || is_quota_failure(inputs.output) {
        return LaunchFailure::new(FailureClass::Health, FailureReason::Quota);
    }
    if let Some(failure) = diagnostic_failure(inputs) {
        return failure;
    }
    if inputs.output.is_some()
        && is_transient_infra_failure(inputs.tool, inputs.launcher_exit, inputs.output)
    {
        return LaunchFailure::new(FailureClass::Health, FailureReason::HealthProbe);
    }
    if inputs.launcher_exit == ExitCode::Timeout.value() {
        return LaunchFailure::new(FailureClass::Other, FailureReason::Timeout);
    }
    LaunchFailure::new(FailureClass::Other, FailureReason::Unknown)
}

fn diagnostic_failure(inputs: &LaunchFailureInputs<'_>) -> Option<LaunchFailure> {
    let combined = [inputs.sidecar, inputs.output]
        .into_iter()
        .flatten()
        .map(LauncherArtifact::text)
        .collect::<Vec<_>>()
        .join("\n");
    if let Some(failure) = vendor_connectivity_failure(inputs.tool, &combined) {
        return Some(failure);
    }
    if let Some(sidecar) = inputs.sidecar {
        if PARSE_PATTERN.is_match(sidecar.text()) {
            return Some(LaunchFailure::new(
                FailureClass::Other,
                FailureReason::Parse,
            ));
        }
        if REFUSAL_PATTERN.is_match(sidecar.text()) {
            return Some(LaunchFailure::new(
                FailureClass::Other,
                FailureReason::Refusal,
            ));
        }
    }
    if inputs
        .output
        .is_some_and(|output| PARSE_PATTERN.is_match(output.text()))
    {
        return Some(LaunchFailure::new(
            FailureClass::Other,
            FailureReason::Parse,
        ));
    }
    None
}

fn vendor_connectivity_failure(tool: VendorProgram, text: &str) -> Option<LaunchFailure> {
    match tool {
        VendorProgram::Codex if OPENAI_STREAM_DISCONNECTED_PATTERN.is_match(text) => {
            Some(LaunchFailure::new(
                FailureClass::Health,
                FailureReason::OpenAiStreamDisconnected,
            ))
        }
        VendorProgram::Cursor if CURSOR_API_UNREACHABLE_PATTERN.is_match(text) => Some(
            LaunchFailure::new(FailureClass::Health, FailureReason::CursorApiUnreachable),
        ),
        _ => None,
    }
}

/// Launcher output artifacts consulted while resolving a launcher exit code.
#[derive(Clone, Debug, Default)]
pub struct LauncherExitArtifacts {
    /// Decoded `.done` sidecar text, when that path is a regular file.
    pub done: Option<String>,
    /// Decoded output-file text, when that path is a regular file.
    pub output: Option<String>,
}

/// Read `LAUNCHER_EXIT=` from a launcher stdout capture; a failed wrapper fails closed.
#[must_use]
pub fn parse_launcher_exit_text(text: &str, process_rc: i32) -> i32 {
    parse_launcher_exit_value(text).unwrap_or_else(|| fallback_launcher_exit(process_rc))
}

/// Resolve a launcher exit from the sidecar, the captured text, the output file, then the wrapper.
#[must_use]
pub fn resolve_launcher_exit(
    captured_text: &str,
    artifacts: Option<&LauncherExitArtifacts>,
    process_rc: i32,
) -> i32 {
    if let Some(done) = artifacts.and_then(|artifacts| artifacts.done.as_deref())
        && let Ok(exit) = done.trim().parse::<i32>()
    {
        return exit;
    }
    if let Some(parsed) = parse_launcher_exit_value(captured_text) {
        return parsed;
    }
    if let Some(output) = artifacts.and_then(|artifacts| artifacts.output.as_deref())
        && let Some(parsed) = parse_launcher_exit_value(output)
    {
        return parsed;
    }
    fallback_launcher_exit(process_rc)
}

const fn fallback_launcher_exit(process_rc: i32) -> i32 {
    if process_rc == 0 {
        0
    } else if process_rc < 1 {
        1
    } else {
        process_rc
    }
}

fn parse_launcher_exit_value(text: &str) -> Option<i32> {
    let raw = kv_value(text, "LAUNCHER_EXIT", DuplicatePolicy::First)?;
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return None;
    }
    trimmed.parse::<i32>().ok()
}

/// Read the last `LAUNCHER_FAILURE_CLASS=` from a launcher capture; unknown or missing is health.
#[must_use]
pub fn parse_launcher_failure_class(log: Option<&LauncherArtifact>) -> FailureClass {
    let Some(artifact) = log.filter(|artifact| artifact.exists()) else {
        return FailureClass::Health;
    };
    kv_value(
        artifact.text(),
        "LAUNCHER_FAILURE_CLASS",
        DuplicatePolicy::Last,
    )
    .and_then(|value| FailureClass::parse(value.trim()))
    .unwrap_or(FailureClass::Health)
}

/// Prefer the launcher capture's class when one exists, else the recorded attempt class.
#[must_use]
pub fn effective_failure_class(
    failure_log: Option<&LauncherArtifact>,
    attempt_class: FailureClass,
) -> FailureClass {
    match failure_log {
        Some(_) => parse_launcher_failure_class(failure_log),
        None => attempt_class,
    }
}

fn kv_value(text: &str, key: &str, policy: DuplicatePolicy) -> Option<String> {
    let options = ParseOptions {
        cr_strip: CrStrip::Both,
        ..ParseOptions::legacy()
    };
    KvDocument::parse(text, options)
        .ok()?
        .select(policy)
        .remove(key)
}

#[cfg(test)]
mod tests {
    use super::{
        AuthVerdict, CodexGateSignal, FailureClass, FailureReason, LaunchFailureInputs,
        LauncherArtifact, LauncherExitArtifacts, classify_launch_failure, detect_codex_cli_gate,
        effective_failure_class, is_transient_infra_failure, parse_launcher_exit_text,
        parse_launcher_failure_class, resolve_launcher_exit,
    };
    use crate::VendorProgram;

    fn inputs<'a>(
        launcher_exit: i32,
        tool: VendorProgram,
        sidecar: Option<&'a LauncherArtifact>,
        output: Option<&'a LauncherArtifact>,
    ) -> LaunchFailureInputs<'a> {
        LaunchFailureInputs {
            launcher_exit,
            tool,
            auth_verdict: AuthVerdict::Unclassified,
            binary_present: true,
            sidecar,
            output,
        }
    }

    #[test]
    fn success_and_precedence_branches_classify_before_diagnostics() {
        let quota = LauncherArtifact::present("HTTP 429 too many requests");
        assert_eq!(
            classify_launch_failure(&inputs(0, VendorProgram::Codex, Some(&quota), None)).class(),
            FailureClass::None
        );
        let mut missing_binary = inputs(1, VendorProgram::Codex, Some(&quota), None);
        missing_binary.binary_present = false;
        assert_eq!(
            classify_launch_failure(&missing_binary).reason(),
            FailureReason::BinaryMissing
        );
        let mut auth = inputs(1, VendorProgram::Codex, Some(&quota), None);
        auth.auth_verdict = AuthVerdict::Auth;
        assert_eq!(classify_launch_failure(&auth).reason(), FailureReason::Auth);
        assert_eq!(
            classify_launch_failure(&inputs(1, VendorProgram::Codex, Some(&quota), None)).reason(),
            FailureReason::Quota
        );
    }

    #[test]
    fn diagnostic_signatures_outrank_the_transient_probe() {
        let refusal = LauncherArtifact::present("the model refused to comply");
        assert_eq!(
            classify_launch_failure(&inputs(5, VendorProgram::Codex, Some(&refusal), None))
                .reason(),
            FailureReason::Refusal
        );
        let parse = LauncherArtifact::present("unexpected token } in JSON");
        let empty = LauncherArtifact::present("");
        assert_eq!(
            classify_launch_failure(&inputs(5, VendorProgram::Codex, None, Some(&parse))).reason(),
            FailureReason::Parse
        );
        assert_eq!(
            classify_launch_failure(&inputs(5, VendorProgram::Codex, None, Some(&empty))).reason(),
            FailureReason::HealthProbe
        );
        assert_eq!(
            classify_launch_failure(&inputs(124, VendorProgram::Codex, None, None)).reason(),
            FailureReason::Timeout
        );
        assert_eq!(
            classify_launch_failure(&inputs(9, VendorProgram::Codex, None, None)).reason(),
            FailureReason::Unknown
        );
    }

    #[test]
    fn connectivity_signatures_are_vendor_scoped() {
        let openai = LauncherArtifact::present(
            "stream disconnected before completion\nwhile reading https://api.openai.com/v1",
        );
        assert_eq!(
            classify_launch_failure(&inputs(1, VendorProgram::Codex, Some(&openai), None)).reason(),
            FailureReason::OpenAiStreamDisconnected
        );
        assert_eq!(
            classify_launch_failure(&inputs(1, VendorProgram::Cursor, Some(&openai), None))
                .reason(),
            FailureReason::Unknown
        );
        let cursor = LauncherArtifact::present("Failed to reach the Cursor API");
        assert_eq!(
            classify_launch_failure(&inputs(1, VendorProgram::Cursor, Some(&cursor), None))
                .reason(),
            FailureReason::CursorApiUnreachable
        );
    }

    #[test]
    fn transient_infra_codes_are_per_vendor_and_require_empty_output() {
        assert!(is_transient_infra_failure(VendorProgram::Codex, 5, None));
        assert!(!is_transient_infra_failure(VendorProgram::Codex, 4, None));
        assert!(is_transient_infra_failure(VendorProgram::Cursor, 4, None));
        let filled = LauncherArtifact::present("output");
        assert!(!is_transient_infra_failure(
            VendorProgram::Claude,
            7,
            Some(&filled)
        ));
        assert!(is_transient_infra_failure(
            VendorProgram::Claude,
            7,
            Some(&LauncherArtifact::missing())
        ));
    }

    #[test]
    fn codex_gate_prefers_metadata_and_falls_back_to_a_safe_model() {
        let metadata =
            detect_codex_cli_gate("Model metadata for gpt-5.1-codex not found", "fallback")
                .expect("metadata gate");
        assert_eq!(metadata.model(), "gpt-5.1-codex");
        assert_eq!(metadata.signal(), CodexGateSignal::ModelMetadataNotFound);
        assert_eq!(
            metadata.message(),
            "codex CLI too old for gpt-5.1-codex; run `npm install -g @openai/codex@latest`"
        );
        let version = detect_codex_cli_gate("'gpt-6' model requires a newer version of Codex", "")
            .expect("version gate");
        assert_eq!(version.model(), "gpt-6");
        assert_eq!(version.signal(), CodexGateSignal::NewerCodexRequired);
        let unsafe_model =
            detect_codex_cli_gate("requires a newer version of Codex", "!!bad!!").expect("gate");
        assert_eq!(unsafe_model.model(), "unknown");
        assert!(detect_codex_cli_gate("all good", "gpt-5").is_none());
    }

    #[test]
    fn launcher_exit_resolution_prefers_the_done_sidecar() {
        assert_eq!(parse_launcher_exit_text("LAUNCHER_EXIT=7\n", 0), 7);
        assert_eq!(parse_launcher_exit_text("noise\n", 3), 3);
        assert_eq!(parse_launcher_exit_text("LAUNCHER_EXIT=x\n", 0), 0);
        let artifacts = LauncherExitArtifacts {
            done: Some(String::from("9\n")),
            output: Some(String::from("LAUNCHER_EXIT=4\n")),
        };
        assert_eq!(
            resolve_launcher_exit("LAUNCHER_EXIT=2", Some(&artifacts), 0),
            9
        );
        let output_only = LauncherExitArtifacts {
            done: None,
            output: Some(String::from("LAUNCHER_EXIT=4\n")),
        };
        assert_eq!(resolve_launcher_exit("", Some(&output_only), 0), 4);
        assert_eq!(resolve_launcher_exit("", None, 5), 5);
    }

    #[test]
    fn failure_class_reads_the_last_recognized_token_and_defaults_to_health() {
        let capture = LauncherArtifact::present(
            "LAUNCHER_FAILURE_CLASS=other\nLAUNCHER_FAILURE_CLASS=none\n",
        );
        assert_eq!(
            parse_launcher_failure_class(Some(&capture)),
            FailureClass::None
        );
        let unknown = LauncherArtifact::present("LAUNCHER_FAILURE_CLASS=bogus\n");
        assert_eq!(
            parse_launcher_failure_class(Some(&unknown)),
            FailureClass::Health
        );
        assert_eq!(parse_launcher_failure_class(None), FailureClass::Health);
        assert_eq!(
            effective_failure_class(None, FailureClass::Other),
            FailureClass::Other
        );
        assert_eq!(
            effective_failure_class(Some(&capture), FailureClass::Other),
            FailureClass::None
        );
    }
}
