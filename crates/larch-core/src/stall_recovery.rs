//! Pure validation policy for stall-recovery state and public artifacts.
use regex::Regex;
use sha2::{Digest as _, Sha256};
use std::{collections::BTreeMap, sync::LazyLock};

/// Canonical prefix for public bug-report titles.
pub const BUG_TITLE_PREFIX: &str = "[BUG]";

const OUTCOMES: &str = "failed-plan-write failed-publish failed-postplan failed-clarify failed-judge-panel failed-publish-tail approved approved-partition";
const GENERIC_SITES: &str = "step2b gate-b step3-review discussion-round2 step5c design-publish clarify-loop judge-panel decompose-panel";
const COMMON_SITES: &str = "step2 step3 step5 step5-self-review step5-mav step6 step8 step18a review-loop lint-fix-loop ship-pr ship-pr-ci-initial ship-pr-ci-merge ship-pr-ci-per-job ship-pr-internal recovery-inline";
const GENERIC_TRIGGERS: &str = "main-agent-apply-required postplan-operator-required exhausted failed unavailable skipped-cycle-cap postplan-failed publish-tail-failed plan-write-failed publish-failed panel-failed panel-init-failed tally-error degraded-empty-collector judge-panel-collapse decompose-panel-retry-exhausted";
const COMMON_TRIGGERS: &str = "main-agent-required coder-main-agent-required main-agent-vote-required fix-attempts-exhausted design-flaw escalate all-vendors-failed ci-fix-exhausted first-fixer-non-health local-unfixable ship-pr-internal-lint-fix lint-fix-main-agent-required step2-impl step8-shippr dispatch-failed";
const GENERIC_BAILS: &str = "failed-plan-write failed-publish failed-postplan failed-clarify failed-judge-panel failed-publish-tail clarify-hard-halt postplan-failed publish-failed publish-tail-failed plan-write-failed judge-panel-collapse decompose-panel-retry-exhausted validator-autofix-exhausted validator-autofix-failed validator-autofix-unavailable validator-autofix-skipped-cycle-cap operator-action panel-init-failed";
const IMPLEMENT_BAILS: &str = "poll-budget-exhausted ci-wait-unexpected-exit no-ci-checks-observed ci-status-stale ci-decide-error ci-status-error ci-timeout ci-too-many-rebases first-fixer-non-health ci-fix-exhausted fix-attempts-exhausted review-required local-unfixable ship-pr-internal-lint-fix main-ci-fail flaky-defect-unfixed scope-disposition lint-fix-failed lint-fix-attempt-cap lint-fix-main-agent-required lint-fix-commit-failed resume-handoff-commit-failed review-fix-commit-failed implementation-commit-failed review-change-detection-failed quota design-flaw escalate all-vendors-failed adopted-issue-closed adopted-issue-is-pr branch-create-failed dirty-state-after-timeout dirty-tree main-branch-post-dispatch orchestrator-envelope-invalid protected-path-edit-required-out-of-scope qa-loop-exceeded recovery-out-of-scope run-flags-persist-failed tracking-init-failed wrapper-validation-failure branch-changed cap_hit codex-runtime-failure cursor-bailed-no-reason cursor-modified-history cursor-runtime-failure detached-head-prohibited interactive-subprocess-unsupported main-branch-prohibited manifest-missing manifest-oos-materialization-failed manifest-schema-invalid protected-path-modified protected-path-modification-required qa-pending-missing redactor-not-executable resume-incompatible submodule-dirty submodule-edit-required-out-of-scope checks-failed checks-timeout ci-health-failed no-fix-path main-agent-required coder-main-agent-required main-agent-vote-required";
const GENERIC_STEPS: &str =
    "validator postplan publish clarify panel judge-panel step2b step3 step5c";
const COMMON_PHASES: &str = "checks review implementation impl step2 step5 step8 ship ship-pr pr-prep pr-create ci-initial ci-merge evaluate-failure force-push-gate bump merge postmerge rebase-failed";
const GENERIC_PHASES: &str =
    "plan-write publish postplan clarify-loop judge-panel validation teardown";
const GENERIC_SOURCES: &str = "split-path design-publish design-step3-review design-step5c clarify-loop prompt-step validator postplan decompose-panel bash python";
const COMMON_SOURCES: &str =
    "codex cursor claude bash python ship-pr lint-fix-loop run-step5-review";
const ALLOWED_TERMINAL_KEYS: &str = "DESIGN_FAILURE_VERSION DESIGN_FAILURE_KIND FAILURE_OUTCOME SUMMARY_OUTCOME STALL_STEP PHASE SITE TRIGGER BAIL_REASON EXIT_CODE FAILURE_DETAIL_LOG SOURCE_SCRIPT ROOT_CAUSE_HINT OCCURRED_AT EVIDENCE_REF PUBLISH_ATTEMPT_ID PUBLISH_RC_SOURCE LATEST_PHASE PLAN_WRITE_OK PUBLISH_OK RENAMED LOG_PUBLISH_ATTEMPTED LOG_PUBLISH_COMPLETED DESIGNED_ADMISSION_READY PR_URL RECOVERY_BRANCH";
const REQUIRED_TERMINAL_KEYS: &str = "DESIGN_FAILURE_VERSION DESIGN_FAILURE_KIND FAILURE_OUTCOME STALL_STEP PHASE SITE TRIGGER BAIL_REASON EXIT_CODE FAILURE_DETAIL_LOG SOURCE_SCRIPT";

static STEP_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(8|9|10|11|12|13|14|15)([a-z][0-9]?|-[a-z0-9]+(-[a-z0-9]+)*)?$")
        .expect("fixed regex")
});
static CI_TRIGGER_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^ci-local-unfixable:[A-Za-z0-9_,-]+$").expect("fixed regex"));
static ATTEMPT_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9._-]{8,128}$").expect("fixed regex"));
static PR_URL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^https://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+/pull/[1-9][0-9]*$")
        .expect("fixed regex")
});
static ASSIGNMENT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:^|[\s(])([A-Z][A-Z0-9_]{2,})=([^\s]{3,})").expect("fixed regex")
});
static PUBLIC_REMOTE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"https?://|git@github\.com:|github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
        .expect("fixed regex")
});
static PUBLIC_HOST_PATH_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(^|[\s`(])/(Users|home|private|tmp|var|Volumes)/[^\s`)]+").expect("fixed regex")
});
static PUBLIC_REPO_PATH_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(^|[\s`(])[A-Za-z0-9_.-]{2,}/[A-Za-z0-9_./-]{2,}").expect("fixed regex")
});
macro_rules! regexes {
    ($($name:ident = $pattern:literal),+ $(,)?) => {$(
        static $name: LazyLock<Regex> = LazyLock::new(|| Regex::new($pattern).expect("fixed regex"));
    )+};
}
#[rustfmt::skip]
regexes! {
    TEST_FAILURE_RE = r"pytest|jest|vitest|rspec|go test|test failed|failing test|tests failed|failed with",
    LINT_FAILURE_RE = r"relevant-checks.*fail|lint.*failed|lint-fix|shellcheck|markdownlint|pre-commit|lint-fix-loop",
    DISPATCH_FAILURE_RE = r"envelope-invalid|invalid.*envelope|orchestrator-envelope-invalid|wrapper-validation|step2.*dispatch",
    TRANSIENT_RE = r"rate limit|api rate|network/auth issue|network (error|failure|unavailable)|timed? out|timeout|connection (reset|refused)|temporary failure|tls handshake|dns failure|name resolution|github unavailable|github api unavailable|service unavailable|http 5\d\d",
    ISSUE_URL_RE = r"^https://github\.com/[^/#]+/[^/#]+/issues/([0-9]+)$",
    ISSUE_VALUE_URL_RE = r"^https://github\.com/.+/.+/issues/[0-9]+$",
    ISSUE_KEY_RE = r"^(ISSUES_(CREATED|FAILED|DEDUPLICATED)|ISSUE_(?:1_)?(FAILED|NUMBER|URL|DUPLICATE|DUPLICATE_OF_NUMBER|DUPLICATE_OF_URL))=",
}
static KEY_LIKE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Z][A-Z0-9_]*=").expect("fixed regex"));

const LINT_FIX_BAILS: &str = "lint-fix-failed lint-fix-attempt-cap lint-fix-main-agent-required lint-fix-commit-failed resume-handoff-commit-failed review-fix-commit-failed";
const DISPATCH_BAILS: &str = "branch-changed cap_hit codex-runtime-failure cursor-bailed-no-reason cursor-modified-history cursor-runtime-failure detached-head-prohibited dirty-state-after-timeout interactive-subprocess-unsupported main-branch-post-dispatch main-branch-prohibited manifest-missing manifest-oos-materialization-failed manifest-schema-invalid protected-path-modified qa-pending-missing quota redactor-not-executable resume-incompatible submodule-dirty wrapper-validation-failure orchestrator-envelope-invalid";
const TERMINAL_MERGE_RESULTS: &str = "merged admin_merged already_merged";
#[rustfmt::skip]
const STALE_FINALIZE_KEYS: &[&str] = &["STALL_TRACKING", "STALL_STEP", "PHASE", "BAIL_REASON", "IMPLEMENT_BAIL_REASON", "EXIT_CODE", "BAIL_NEEDS_USER_INPUT"];
type State = BTreeMap<String, String>;

/// Effect-free input to the stall classifier.
#[derive(Clone, Copy, Debug, Default)]
#[rustfmt::skip]
pub struct ClassifyTextInput<'a> {
    pub text: &'a str, pub bail: &'a str, pub step: &'a str,
    pub detail_log_valid: bool, pub exit_code: &'a str, pub implement: bool,
}

/// Stable classifier result fields.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[rustfmt::skip]
pub struct Classification {
    pub failure_class: &'static str, pub resume_hint: &'static str, pub pattern: &'static str,
}
#[derive(Clone, Copy, Debug)]
#[rustfmt::skip]
enum RuleMatcher {
    MigrationGovernance, Step(&'static str), ChecksChild, Steps(&'static str), Bail(&'static str),
    BailSet(&'static str), CiFixExhausted, ShipRefresh, ContainsAny(&'static str),
    Regex(&'static LazyLock<Regex>), Fallback,
}
type ClassificationRule = (RuleMatcher, Classification);
#[rustfmt::skip]
const fn classification(failure_class: &'static str, resume_hint: &'static str, pattern: &'static str) -> Classification { Classification { failure_class, resume_hint, pattern } }
macro_rules! rule {
    ($matcher:expr, $class:literal, $hint:literal, $pattern:literal) => {
        ($matcher, classification($class, $hint, $pattern))
    };
}
// Ordering is the compatibility contract; the parity matrix covers every row.
#[rustfmt::skip]
static CLASSIFICATION_RULES: &[ClassificationRule] = &[
    rule!(RuleMatcher::MigrationGovernance, "contract-failure", "none", "migration-governance-block"),
    rule!(RuleMatcher::Step("rebase-failed"), "transient-infra", "step8-shippr", "rebase-transient"),
    rule!(RuleMatcher::ChecksChild, "transient-infra", "checks-commit-route-retry", "checks-child-sigterm"),
    rule!(RuleMatcher::Steps("3 6"), "contract-failure", "none", "step-contract"),
    rule!(RuleMatcher::Step("merge-loop-iteration-cap"), "unrecoverable", "none", "terminal-step"),
    rule!(RuleMatcher::Bail("protected-path-edit-required-out-of-scope"), "protected-path", "step2-impl", "protected-path-bail-token"),
    rule!(RuleMatcher::Bail("submodule-edit-required-out-of-scope"), "submodule-restricted", "none", "submodule-restricted-bail-token"),
    rule!(RuleMatcher::Bail("adopted-issue-closed"), "unrecoverable", "none", "terminal-bail"),
    rule!(RuleMatcher::Bail("tracking-init-failed"), "unrecoverable", "none", "terminal-bail"),
    rule!(RuleMatcher::Bail("recovery-out-of-scope"), "unrecoverable", "none", "recovery-out-of-scope"),
    rule!(RuleMatcher::CiFixExhausted, "unrecoverable", "none", "terminal-bail"),
    rule!(RuleMatcher::ShipRefresh, "transient-infra", "step8-shippr", "transient-output"),
    rule!(RuleMatcher::ContainsAny(LINT_FIX_BAILS), "lint-failure", "step5-review", "lint-fix-bail-token"),
    rule!(RuleMatcher::ContainsAny("submodule-edit-required-out-of-scope"), "submodule-restricted", "none", "submodule-restricted-bail-token"),
    rule!(RuleMatcher::ContainsAny("protected-path-edit-required-out-of-scope"), "protected-path", "step2-impl", "protected-path-bail-token"),
    rule!(RuleMatcher::Regex(&TEST_FAILURE_RE), "test-failure", "step2-impl", "test-output"),
    rule!(RuleMatcher::Regex(&LINT_FAILURE_RE), "lint-failure", "step5-review", "lint-output"),
    rule!(RuleMatcher::BailSet(DISPATCH_BAILS), "dispatch-failure", "step2-impl", "dispatch-bail-token"),
    rule!(RuleMatcher::Regex(&DISPATCH_FAILURE_RE), "dispatch-failure", "step2-impl", "dispatch-output"),
    rule!(RuleMatcher::Regex(&TRANSIENT_RE), "transient-infra", "step8-shippr", "transient-output"),
    rule!(RuleMatcher::Fallback, "unrecoverable", "none", "fallback"),
];
#[must_use] #[rustfmt::skip]
pub fn artifact_prefix_valid(value: &str) -> bool {
    let mut parts = value.split('-');
    value.is_empty() || parts.all(|part| !part.is_empty() && part.bytes().all(|byte| byte.is_ascii_alphanumeric()))
}
/// Classify bounded stall evidence with the Python compatibility precedence.
#[must_use]
pub fn classify_text(input: ClassifyTextInput<'_>) -> Classification {
    let lower = format!("{}\n{}", input.bail, input.text).to_ascii_lowercase();
    for (matcher, result) in CLASSIFICATION_RULES {
        if rule_matches(*matcher, input, &lower) {
            if matches!(*matcher, RuleMatcher::CiFixExhausted) && input.detail_log_valid {
                return classification("unrecoverable", "none", "ci-fix-exhausted-with-detail");
            }
            return *result;
        }
    }
    unreachable!("classification table has a fallback")
}
/// Derive the final compatibility resume hint from a classification and raw state.
#[must_use] #[rustfmt::skip]
pub fn resume_hint_for(failure_class: &str, step: &str, phase: &str, pattern: &str) -> &'static str {
    let step = safe_step_value(step);
    if has("contract-failure same-cause-repeat unrecoverable submodule-restricted", failure_class) { return "none"; }
    if has("3 6 12d bump-branch-guard", step) {
        return if step == "3" && has("checks-leg-abandoned checks-child-sigterm", pattern) { "checks-commit-route-retry" } else { "none" };
    }
    match step {
        "2" => "step2-impl",
        "5" if pattern == "checks-leg-abandoned" => "checks-commit-route-retry",
        "5" => "step5-review",
        "unknown" if phase.starts_with("review") => "step5-review",
        "unknown" if phase.starts_with("impl") || phase.starts_with("step2") => "step2-impl",
        "unknown" if phase.is_empty() => "none",
        "8" | "9" | "10" | "11" | "12" | "13" | "14" | "15" | "rebase-failed" | "unknown" => "step8-shippr",
        _ if STEP_RE.is_match(step) => "step8-shippr",
        _ => "none",
    }
}
/// Return a stable SHA-256 signature for an implement or generic classification.
#[must_use] #[rustfmt::skip]
pub fn classification_signature(generic_skill: Option<&str>, failure_class: &str, hint: &str, step: &str, phase: &str, bail: &str, evidence: &str) -> String {
    let prefix = generic_skill.map_or(String::new(), |skill| {
        format!("profile=generic\nskill={skill}\n")
    });
    let digest = evidence_digest(evidence);
    sha256_hex(&format!("{prefix}class={failure_class}\nhint={hint}\nstep={step}\nphase={phase}\nbail={bail}\nevidence={digest}\n"))
}
/// Derive the deterministic filename for a bounded failure-detail sidecar.
#[must_use] #[rustfmt::skip]
pub fn failure_detail_sidecar_name(resolved: &str, size: u64, prefix: &[u8]) -> String {
    let mut digest = Sha256::new();
    digest.update(resolved.as_bytes()); digest.update([0]); digest.update(size.to_string().as_bytes());
    digest.update([0]); digest.update(prefix);
    let hex = format!("{:x}", digest.finalize());
    format!("stall-recovery-failure-detail-log-{}.truncated.log", &hex[..16])
}
/// Render a raw step for the public classification wire.
#[must_use] #[rustfmt::skip]
pub fn safe_step_value(value: &str) -> &str { render_or(value, safe_step(value, true) || value == "unknown", "unknown") }
/// Render a raw phase for the public classification wire.
#[must_use] #[rustfmt::skip]
pub fn safe_phase_value(value: &str) -> &str { render_or(value, safe_phase(value, true) || value == "unknown", "unknown") }
/// Render a raw bail field without exposing unbounded text.
#[must_use] #[rustfmt::skip]
pub fn safe_bail_value(value: &str, generic: bool) -> &str { render_or(value, value.is_empty() || safe_bail(value, generic), "redacted") }
/// Render a dispatcher or source-script field for the public wire.
#[must_use] #[rustfmt::skip]
pub fn safe_dispatcher_value(value: &str, generic: bool) -> &str { if value.is_empty() { "unknown" } else { render_or(value, safe_source(value, generic), "redacted") } }
/// Render one classifier pattern from the fixed compatibility vocabulary.
#[must_use] #[rustfmt::skip]
pub fn safe_pattern_value(value: &str) -> &str { render_or(value, has("no-stall no-match step-contract terminal-step rebase-transient protected-path-bail-token submodule-restricted-bail-token terminal-bail recovery-out-of-scope test-output lint-output dispatch-output dispatch-bail-token transient-output ci-fix-exhausted-with-detail same-cause-repeat fallback bail-token lint-fix-bail-token checks-leg-abandoned checks-child-sigterm design-publish-tail-current-attempt postmerge-flush-expected postmerge-flush-failure migration-governance-block", value), "redacted") }
const fn render_or<'a>(value: &'a str, accepted: bool, fallback: &'static str) -> &'a str {
    if accepted { value } else { fallback }
}
/// Resolve the stable retry policy for a failure class.
#[must_use] #[rustfmt::skip]
pub fn retry_policy(failure_class: &str) -> (u8, &'static str) {
    match failure_class {
        "transient-infra" => (4, "sleep-seconds.sh 5"), "test-failure" | "lint-failure" => (8, "none"),
        "dispatch-failure" => (3, "none"), "protected-path" => (1, "none"),
        "same-cause-repeat" => (2, "none"), _ => (0, "none"),
    }
}
/// Effect-free state layers consumed by outcome normalization.
#[derive(Clone, Copy, Debug)]
#[rustfmt::skip]
pub struct NormalizeOutcomeInput<'a> {
    pub ship: &'a BTreeMap<String, String>, pub finalize: &'a BTreeMap<String, String>,
    pub session: &'a BTreeMap<String, String>, pub seed: &'a BTreeMap<String, String>,
    pub classification: &'a BTreeMap<String, String>, pub memory_stall: &'a str, pub panel_failed: bool,
}
/// Normalize layered ship state into the stable implement outcome wire.
#[must_use] #[rustfmt::skip]
pub fn normalize_outcome_values(input: NormalizeOutcomeInput<'_>) -> Vec<(String, String)> {
    let fin = effective_finalize(input.ship, input.finalize);
    let memory_stall = if input.memory_stall.is_empty() { "false" } else { input.memory_stall };
    let ship_stall = state_or(input.ship, "STALL_TRACKING", "false");
    let raw_fin_stall = state_or(input.finalize, "STALL_TRACKING", "false");
    let fin_stall = state_or(&fin, "STALL_TRACKING", "false");
    let session_stall = state_or(input.session, "STALL_TRACKING", "false");
    let any_stall = [memory_stall, ship_stall, fin_stall, session_stall].into_iter().any(truthy);
    let phase_stalled = phase_counts_as_stalled(input.ship, &fin, any_stall);
    let merge_result = layered(input.ship, &fin, "MERGE_RESULT"); let merge = layered(input.ship, &fin, "MERGE");
    let draft = layered_or(input.ship, &fin, "DRAFT", "false"); let pr_number = layered(input.ship, &fin, "PR_NUMBER");
    let forked = first_nonempty(&[state(input.ship, "FORKED_TARGET"), state(&fin, "FORKED_TARGET"), state_or(input.session, "FORKED_TARGET", "false")]);
    let ci_passed = layered_or(input.ship, &fin, "CI_PASSED", "false");
    let design_done = state_or(&fin, "DESIGN_ONLY_DONE", "false"); let bail_user = layered_or(input.ship, &fin, "BAIL_NEEDS_USER_INPUT", "false");
    let terminal_merge = has(TERMINAL_MERGE_RESULTS, merge_result);
    let stall_terminal = (terminal_merge && truthy(memory_stall)) || stall_signal_is_terminal(input.ship, &fin, bail_user);
    let has_failure = has_failure_signals(input.ship, &fin, bail_user);
    let mut outcome = if (any_stall || phase_stalled) && stall_terminal {
        "stalled"
    } else if terminal_merge && has_failure {
        "bailed"
    } else if has("merged admin_merged", merge_result) {
        "merged"
    } else if merge_result == "already_merged" {
        "force-merged-externally"
    } else if truthy(forked) {
        "forked-dry-run"
    } else if truthy(design_done) {
        "design-only"
    } else if has_pr_evidence(input.ship, &fin) && matches!(merge_result, "")
        && healthy_pr_snapshot(input.ship, &fin) && !truthy(bail_user) {
        if truthy(draft) { "pr-created-draft" } else { "pr-created" }
    } else if !has_pr_evidence(input.ship, &fin) && matches!(merge_result, "") && !has_failure {
        "shipping"
    } else {
        "bailed"
    };
    if truthy(bail_user) && outcome == "bailed" { outcome = "bailed-needs-user-input"; }
    let succeeded = has("merged force-merged-externally pr-created pr-created-draft forked-dry-run", outcome) && !any_stall;
    let merge_downgraded = outcome == "pr-created"
        && truthy(state_or(input.seed, "MERGE", "false"))
        && !truthy(merge)
        && state(input.classification, "STALL_STEP") == "5"
        && state(input.classification, "RESUME_HINT") == "step8-shippr"
        && input.panel_failed;
    #[rustfmt::skip]
    let rows = [
        ("IMPLEMENT_NORMALIZED_OUTCOME", outcome),
        ("IMPLEMENT_OUTCOME_SUCCEEDED", bool_token(succeeded)), ("IMPLEMENT_MERGE_DOWNGRADED", bool_token(merge_downgraded)),
        ("IMPLEMENT_ANY_STALL_TRACKING", bool_token(any_stall)), ("IMPLEMENT_MEMORY_STALL_TRACKING", memory_stall),
        ("IMPLEMENT_SHIP_STALL_TRACKING", ship_stall), ("IMPLEMENT_FINALIZE_STALL_TRACKING", raw_fin_stall),
        ("IMPLEMENT_SESSION_STALL_TRACKING", session_stall), ("IMPLEMENT_MERGE_RESULT", merge_result),
        ("IMPLEMENT_PR_NUMBER", pr_number), ("IMPLEMENT_DRAFT", draft), ("IMPLEMENT_MERGE", merge),
        ("IMPLEMENT_FORKED_TARGET", forked), ("IMPLEMENT_CI_PASSED", ci_passed),
        ("IMPLEMENT_DESIGN_ONLY_DONE", design_done), ("IMPLEMENT_BAIL_NEEDS_USER_INPUT", bail_user),
    ];
    rows.into_iter()
        .map(|(key, value)| (key.to_owned(), value.to_owned()))
        .collect()
}
/// Pure result of normalizing the issue helper's captured stdout.
#[derive(Clone, Debug, Eq, PartialEq)]
#[rustfmt::skip]
pub enum IssueNormalization {
    Success { number: String, url: String }, Failure(&'static str),
}

/// Filter and normalize the issue helper's machine stdout.
#[must_use] #[rustfmt::skip]
pub fn normalize_issue_output(text: &str, exit_code: Option<&str>) -> IssueNormalization {
    let Some(exit_code) = exit_code else { return IssueNormalization::Failure("issue-exit-code-missing"); };
    if exit_code != "0" { return IssueNormalization::Failure("issue-exit-code"); }
    let filtered = filter_issue_stdout(text);
    let issues_failed = state(&filtered, "ISSUES_FAILED");
    if issues_failed != "0" {
        let reason = if issues_failed.is_empty() || !issues_failed.bytes().all(|byte| byte.is_ascii_digit()) { "issues-failed-invalid" } else { "issues-failed-nonzero" };
        return IssueNormalization::Failure(reason);
    }
    if truthy(state(&filtered, "ISSUE_1_FAILED")) { return IssueNormalization::Failure("issue-1-failed"); }
    let mut number = state(&filtered, "ISSUE_1_NUMBER").to_owned();
    let mut url = state(&filtered, "ISSUE_1_URL").to_owned();
    let duplicate = first_nonempty(&[state(&filtered, "ISSUE_1_DUPLICATE"), state(&filtered, "ISSUE_DUPLICATE")]);
    let duplicate_number = first_nonempty(&[state(&filtered, "ISSUE_1_DUPLICATE_OF_NUMBER"), state(&filtered, "ISSUE_DUPLICATE_OF_NUMBER")]);
    let duplicate_url = first_nonempty(&[state(&filtered, "ISSUE_1_DUPLICATE_OF_URL"), state(&filtered, "ISSUE_DUPLICATE_OF_URL")]);
    if (truthy(duplicate) || number.is_empty()) && (ISSUE_VALUE_URL_RE.is_match(duplicate_url) || !ISSUE_VALUE_URL_RE.is_match(&url)) {
        number = if duplicate_number.is_empty() { issue_url_number(duplicate_url).unwrap_or_default() } else { duplicate_number.to_owned() };
        duplicate_url.clone_into(&mut url);
    }
    if number.is_empty() || !number.bytes().all(|byte| byte.is_ascii_digit()) {
        IssueNormalization::Failure("issue-number-missing")
    } else if !ISSUE_VALUE_URL_RE.is_match(&url) {
        IssueNormalization::Failure("issue-url-missing")
    } else {
        IssueNormalization::Success { number, url }
    }
}

/// Stable normalized fields from the file-failure issue helper.
#[derive(Clone, Debug, Eq, PartialEq)]
#[rustfmt::skip]
pub struct FileFailureReport {
    pub status: String, pub url: String, pub issue_number: Option<String>, pub fallback_reason: String,
}

/// Normalize one parsed file-failure helper environment.
#[must_use] #[rustfmt::skip]
pub fn normalize_file_failure_report(values: &BTreeMap<String, String>) -> FileFailureReport {
    let raw_status = state(values, "FILE_FAILURE_REPORT_STATUS");
    let mut fallback_reason = state(values, "FILE_FAILURE_REPORT_FALLBACK_REASON").to_owned();
    let (status, default_reason) = if raw_status == "mutation-refused" { ("fallback-print-required", "unauthorized-mutation") }
    else if has("filed dry-run dedup-comment no-match fallback-print-required lookup-failed-open", raw_status) {
        (raw_status, "")
    } else { ("fallback-print-required", "helper-status-missing") };
    if fallback_reason.is_empty() { default_reason.clone_into(&mut fallback_reason); }
    let url = state(values, "FILE_FAILURE_REPORT_URL").to_owned();
    FileFailureReport { issue_number: issue_url_number(&url), status: status.to_owned(), url, fallback_reason }
}

fn effective_finalize(ship: &State, finalize: &State) -> State {
    let mut effective = finalize.clone();
    if finalize_contains_stall(finalize) && clean_ship_recovery(ship) {
        effective.extend(
            STALE_FINALIZE_KEYS
                .iter()
                .map(|key| ((*key).to_owned(), String::new())),
        );
    }
    effective
}

fn clean_ship_recovery(ship: &State) -> bool {
    let pr_number = state(ship, "PR_NUMBER").trim();
    let pr_url = state(ship, "PR_URL").trim();
    let merge_result = state(ship, "MERGE_RESULT").trim();
    ((!(pr_number.is_empty() || pr_number == "0"))
        || (!(pr_url.is_empty() || pr_url == "N/A"))
        || has(TERMINAL_MERGE_RESULTS, merge_result))
        && state(ship, "PHASE").trim() != "stalled"
        && state(ship, "BAIL_REASON").trim().is_empty()
        && state(ship, "IMPLEMENT_BAIL_REASON").trim().is_empty()
        && !nonzero_exit(state(ship, "EXIT_CODE"))
}

#[rustfmt::skip]
fn finalize_contains_stall(fin: &State) -> bool { truthy(state_or(fin, "STALL_TRACKING", "false")) || !state(fin, "STALL_STEP").trim().is_empty() || state(fin, "PHASE").trim() == "stalled" || !state(fin, "BAIL_REASON").trim().is_empty() || !state(fin, "IMPLEMENT_BAIL_REASON").trim().is_empty() || nonzero_exit(state(fin, "EXIT_CODE")) || truthy(state_or(fin, "BAIL_NEEDS_USER_INPUT", "false")) }

#[rustfmt::skip]
fn phase_counts_as_stalled(ship: &State, fin: &State, any_stall: bool) -> bool { state(ship, "PHASE").trim() == "stalled" || (state(fin, "PHASE").trim() == "stalled" && (any_stall || !has("ci-initial rebase pr-create", state(ship, "PHASE").trim()))) }

#[rustfmt::skip]
fn stall_signal_is_terminal(ship: &State, fin: &State, bail_user: &str) -> bool { has_failure_signals(ship, fin, bail_user) || state(ship, "PHASE").trim() == "stalled" || truthy(state_or(fin, "STALL_TRACKING", "false")) }

#[rustfmt::skip]
fn has_failure_signals(ship: &State, fin: &State, bail_user: &str) -> bool { !layered(ship, fin, "BAIL_REASON").trim().is_empty() || !layered(ship, fin, "IMPLEMENT_BAIL_REASON").trim().is_empty() || nonzero_exit(layered(ship, fin, "EXIT_CODE")) || truthy(bail_user) }

#[rustfmt::skip]
fn has_pr_evidence(ship: &State, fin: &State) -> bool {
    let number = layered(ship, fin, "PR_NUMBER").trim();
    let url = layered(ship, fin, "PR_URL").trim();
    (!number.is_empty() && number != "0") || (!url.is_empty() && url != "N/A")
}

#[rustfmt::skip]
fn healthy_pr_snapshot(ship: &State, fin: &State) -> bool { layered(ship, fin, "BAIL_REASON").trim().is_empty() && layered(ship, fin, "IMPLEMENT_BAIL_REASON").trim().is_empty() && layered(ship, fin, "PHASE").trim() != "stalled" && !nonzero_exit(layered(ship, fin, "EXIT_CODE")) }

#[rustfmt::skip]
fn nonzero_exit(value: &str) -> bool {
    let value = value.trim();
    let digits = value.strip_prefix(['+', '-']).unwrap_or(value);
    !digits.is_empty() && digits.bytes().all(|byte| byte.is_ascii_digit()) && digits.bytes().any(|byte| byte != b'0')
}

#[rustfmt::skip]
fn filter_issue_stdout(text: &str) -> State {
    let mut records: Vec<(String, String)> = Vec::new();
    for raw in text.lines() {
        let line = raw.replace('\r', " ");
        if ISSUE_KEY_RE.is_match(&line) {
            if let Ok(document) = crate::KvDocument::parse(&line, crate::ParseOptions::legacy()) && let Some(row) = document.rows().first() { records.push((row.key().to_owned(), row.value().to_owned())); }
        } else if !records.is_empty() && !KEY_LIKE_RE.is_match(&line) {
            records.last_mut().expect("checked").1.push(' '); records.last_mut().expect("checked").1.push_str(&line);
        }
    }
    records.into_iter().map(|(key, value)| (key, value.split_whitespace().collect::<Vec<_>>().join(" "))).collect()
}

#[rustfmt::skip]
fn issue_url_number(url: &str) -> Option<String> { ISSUE_URL_RE.captures(url).map(|capture| capture[1].to_owned()) }

#[must_use] #[rustfmt::skip]
pub fn truthy(value: &str) -> bool { matches!(value.trim().to_ascii_lowercase().as_str(), "1" | "true" | "yes" | "on") }

#[rustfmt::skip]
const fn bool_token(value: bool) -> &'static str { if value { "true" } else { "false" } }

#[rustfmt::skip]
pub fn state<'a>(values: &'a BTreeMap<String, String>, key: &str) -> &'a str { values.get(key).map_or("", String::as_str) }

#[rustfmt::skip]
fn state_or<'a>(values: &'a State, key: &str, fallback: &'a str) -> &'a str {
    let value = state(values, key); if value.is_empty() { fallback } else { value }
}

#[rustfmt::skip]
fn layered<'a>(first: &'a State, second: &'a State, key: &str) -> &'a str { first_nonempty(&[state(first, key), state(second, key)]) }

#[rustfmt::skip]
fn layered_or<'a>(first: &'a State, second: &'a State, key: &str, fallback: &'a str) -> &'a str {
    let value = layered(first, second, key);
    if value.is_empty() { fallback } else { value }
}

#[must_use] #[rustfmt::skip]
pub fn first_nonempty<'a>(values: &[&'a str]) -> &'a str { values.iter().copied().find(|value| !value.is_empty()).unwrap_or("") }

#[rustfmt::skip]
fn rule_matches(matcher: RuleMatcher, input: ClassifyTextInput<'_>, lower: &str) -> bool {
    match matcher {
        RuleMatcher::MigrationGovernance => input.implement && migration_governance_blocked(input.bail),
        RuleMatcher::Step(step) => input.step == step, RuleMatcher::ChecksChild => checks_child_failed(input.bail, input.step, input.exit_code),
        RuleMatcher::Steps(steps) => has(steps, input.step), RuleMatcher::Bail(bail) => input.bail == bail, RuleMatcher::BailSet(bails) => has(bails, input.bail),
        RuleMatcher::CiFixExhausted => input.bail == "ci-fix-exhausted",
        RuleMatcher::ShipRefresh => ship_refresh_preterminal(lower, input.step),
        RuleMatcher::ContainsAny(tokens) => tokens.split_ascii_whitespace().any(|token| lower.contains(token)),
        RuleMatcher::Regex(regex) => regex.is_match(lower), RuleMatcher::Fallback => true,
    }
}

#[rustfmt::skip]
fn checks_child_failed(bail: &str, step: &str, exit_code: &str) -> bool { let raw = exit_code.trim(); let digits = raw.strip_prefix(['+', '-']).unwrap_or(raw); bail == "checks-child-failed" && has("3 6", step) && (raw == "unknown" || digits.is_empty() || !digits.bytes().all(|byte| byte.is_ascii_digit()) || (raw.starts_with('-') && digits.bytes().any(|byte| byte != b'0'))) }

#[rustfmt::skip]
fn migration_governance_blocked(bail: &str) -> bool {
    let line = bail.split_once('\n').map_or(bail, |(line, _)| line);
    let lower = line.to_ascii_lowercase();
    lower.find("migration governance blocked:").is_some_and(|index| !lower[index + "migration governance blocked:".len()..].trim().is_empty())
}

#[rustfmt::skip]
fn ship_refresh_preterminal(lower: &str, step: &str) -> bool {
    const REFRESH_STEP: &str = "pr-create-guideline-outcome-refresh";
    step == REFRESH_STEP || lower.contains("preterminal-outcome") || lower.contains(&format!("stall_step={REFRESH_STEP}"))
        || (lower.contains(REFRESH_STEP) && ["pre-terminal", "terminal outcome label", "preterminal"].iter().any(|token| lower.contains(token)))
}

#[rustfmt::skip]
fn evidence_digest(evidence: &str) -> String {
    if evidence.is_empty() { String::new() } else { sha256_hex(&evidence.chars().take(2048).collect::<String>())[..16].to_owned() }
}

#[rustfmt::skip]
fn sha256_hex(value: &str) -> String { format!("{:x}", Sha256::digest(value.as_bytes())) }

#[must_use]
pub fn safe_step(value: &str, generic: bool) -> bool {
    (generic && has(GENERIC_STEPS, value))
        || [
            "main-ci",
            "merge",
            "postmerge-push-watch",
            "bump-branch-guard",
            "merge-loop-iteration-cap",
            "rebase-failed",
        ]
        .contains(&value)
        || matches!(
            value,
            "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11" | "12" | "13" | "14" | "15"
        )
        || STEP_RE.is_match(value)
}

#[must_use]
pub fn safe_phase(value: &str, generic: bool) -> bool {
    has(COMMON_PHASES, value) || (generic && has(GENERIC_PHASES, value))
}

#[must_use]
pub fn token_valid(value: &str, kind: &str, generic: bool) -> bool {
    if value.is_empty() || reject_rawish_token(value) {
        return false;
    }
    match kind {
        "" => true,
        "outcome" => safe_outcome(value),
        "step" => safe_step(value, generic),
        "phase" => safe_phase(value, generic),
        "site" => has(COMMON_SITES, value) || (generic && has(GENERIC_SITES, value)),
        "trigger" => {
            has(COMMON_TRIGGERS, value)
                || (generic && has(GENERIC_TRIGGERS, value))
                || CI_TRIGGER_RE.is_match(value)
        }
        "bail" => safe_bail(value, generic),
        "source-script" => safe_source(value, generic),
        "root-cause" => ["larch-defect", "environment", "operator-action"].contains(&value),
        _ => false,
    }
}

#[must_use]
pub fn terminal_state_valid(
    rows: &[(String, String)],
    generic: bool,
    detail_file_valid: impl Fn(&str) -> bool,
) -> bool {
    let mut found = BTreeMap::new();
    for (key, value) in rows {
        if !has(ALLOWED_TERMINAL_KEYS, key) || found.insert(key.as_str(), value.as_str()).is_some()
        {
            return false;
        }
    }
    if REQUIRED_TERMINAL_KEYS.split_ascii_whitespace().any(|key| {
        !found.contains_key(key) || (key != "FAILURE_DETAIL_LOG" && found[key].is_empty())
    }) {
        return false;
    }
    found.into_iter().all(|(key, value)| {
        if key == "FAILURE_DETAIL_LOG" {
            return value.is_empty() || detail_file_valid(value);
        }
        if !matches!(key, "PR_URL" | "RECOVERY_BRANCH") && reject_rawish_terminal(value) {
            return false;
        }
        terminal_scalar_valid(key, value, generic)
    })
}

#[must_use]
pub fn public_text_is_sensitive(corpus: &str, candidate: &str) -> bool {
    for token in corpus.lines().map(str::trim) {
        if token.is_empty()
            || (token.len() == 1
                && token
                    .bytes()
                    .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-')))
            || has(SENSITIVE_TOKEN_ALLOWLIST, token)
            || sensitive_value_allowlisted(token)
        {
            continue;
        }
        if let Some((key, value)) = token.split_once('=') {
            if matches!(key, "RUN_ID" | "LARCH_RUN_ID" | "SESSION_ID") && safe_run_identifier(value)
            {
                continue;
            }
            if has(SENSITIVE_TOKEN_ALLOWLIST, value) || sensitive_value_allowlisted(value) {
                continue;
            }
            if !value.is_empty() && value != token && candidate.contains(value) {
                return true;
            }
        }
        if candidate.contains(token) {
            return true;
        }
    }
    PUBLIC_REMOTE_RE.is_match(candidate)
        || PUBLIC_HOST_PATH_RE.is_match(candidate)
        || PUBLIC_REPO_PATH_RE.is_match(candidate)
        || candidate_has_sensitive_assignment(candidate)
}

fn terminal_scalar_valid(key: &str, value: &str, generic: bool) -> bool {
    match key {
        "DESIGN_FAILURE_VERSION" => value == "1",
        "DESIGN_FAILURE_KIND" => value == "terminal",
        "FAILURE_OUTCOME" | "SUMMARY_OUTCOME" => safe_outcome(value),
        "STALL_STEP" => safe_step(value, generic),
        "PHASE" => safe_phase(value, generic),
        "SITE" | "TRIGGER" => token_valid(value, &key.to_ascii_lowercase(), generic),
        "BAIL_REASON" => safe_bail(value, generic),
        "EXIT_CODE" => {
            value == "unknown"
                || (!value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
        }
        "SOURCE_SCRIPT" => safe_source(value, generic),
        "ROOT_CAUSE_HINT" => {
            value.is_empty() || ["larch-defect", "environment", "operator-action"].contains(&value)
        }
        "PUBLISH_ATTEMPT_ID" => ATTEMPT_RE.is_match(value),
        "PUBLISH_RC_SOURCE" => matches!(value, "returned" | "exception"),
        "LATEST_PHASE" => {
            !value.is_empty()
                && value
                    .bytes()
                    .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
        }
        "PLAN_WRITE_OK"
        | "PUBLISH_OK"
        | "RENAMED"
        | "LOG_PUBLISH_ATTEMPTED"
        | "LOG_PUBLISH_COMPLETED"
        | "DESIGNED_ADMISSION_READY" => matches!(value, "true" | "false"),
        "PR_URL" => PR_URL_RE.is_match(value),
        "RECOVERY_BRANCH" => valid_recovery_branch(value),
        "OCCURRED_AT" | "EVIDENCE_REF" => value.is_empty() || !reject_rawish_terminal(value),
        _ => false,
    }
}

fn safe_outcome(value: &str) -> bool {
    has(OUTCOMES, value)
        || value.strip_prefix("cancelled-").is_some_and(|_| {
            value.bytes().all(|byte| {
                byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b':' | b'-')
            })
        })
}

fn safe_bail(value: &str, generic: bool) -> bool {
    value.is_empty()
        || (generic && has(GENERIC_BAILS, value))
        || has(IMPLEMENT_BAILS, value)
        || CI_TRIGGER_RE.is_match(value)
}

fn safe_source(value: &str, generic: bool) -> bool {
    has(COMMON_SOURCES, value) || (generic && has(GENERIC_SOURCES, value))
}

fn reject_rawish_token(value: &str) -> bool {
    value.contains(['\n', '\r', ' '])
        || value.contains([
            '{', '}', '(', ')', '[', ']', '<', '>', '|', '&', ';', '`', '$',
        ])
}

fn reject_rawish_terminal(value: &str) -> bool {
    let lower = value.to_ascii_lowercase();
    value.contains(['\n', '\r'])
        || [
            "http://",
            "https://",
            "github.com",
            "/users/",
            "/home/",
            " larch ",
            "```",
        ]
        .iter()
        .any(|token| lower.contains(token))
}

fn valid_recovery_branch(value: &str) -> bool {
    !value.is_empty()
        && !value.starts_with(['/', '-'])
        && !value.contains("..")
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'/' | b'-'))
}

const SENSITIVE_TOKEN_ALLOWLIST: &str = "larch-defect environment operator-action terminal-failure escalation-success merged force-merged-externally pr-created pr-created-draft forked-dry-run main-agent-required lint-fix-loop ship-pr codex cursor claude approved approved-partition failed-plan-write failed-publish failed-postplan failed-clarify failed-judge-panel failed-publish-tail";
const SENSITIVE_VALUE_ALLOWLIST: &str = "lint-failure test-failure transient-infra dispatch-failure protected-path submodule-restricted unrecoverable same-cause-repeat contract-failure ci-fix-exhausted no-stall fallback bail-token step-contract transient-output test-output lint-output lint-fix-bail-token dispatch-output dispatch-bail-token terminal-bail terminal-step rebase-transient recovery-out-of-scope ci-fix-exhausted-with-detail step2-impl step5-review step8-shippr checks-commit-route-retry recoverable resume-post-plan-publish returned exception initialized plan-write difficulty diagram-upsert tracking-issue-rename log-publish log-publish-failed complete no-match protected-path-bail-token submodule-restricted-bail-token checks-leg-abandoned checks-child-sigterm design-publish-tail-current-attempt postmerge-flush-expected postmerge-flush-failure migration-governance-block";

fn sensitive_value_allowlisted(value: &str) -> bool {
    if [
        "", "true", "false", "TRUE", "FALSE", "True", "False", "unknown", "none", "n/a", "N/A", "-",
    ]
    .contains(&value)
        || (value.len() <= 4
            && !value.is_empty()
            && value.bytes().all(|byte| byte.is_ascii_digit()))
        || safe_bail(value, true)
        || safe_step(value, true)
        || safe_phase(value, true)
        || token_valid(value, "site", true)
        || token_valid(value, "trigger", true)
        || safe_source(value, true)
    {
        return true;
    }
    has(SENSITIVE_VALUE_ALLOWLIST, value)
}

fn has(set: &str, value: &str) -> bool {
    set.split_ascii_whitespace().any(|token| token == value)
}

fn candidate_has_sensitive_assignment(candidate: &str) -> bool {
    ASSIGNMENT_RE.captures_iter(candidate).any(|capture| {
        let key = &capture[1];
        let value = capture[2].trim_end_matches(['.', ',', ';', ':', ')']);
        if matches!(key, "RUN_ID" | "LARCH_RUN_ID" | "SESSION_ID") && safe_run_identifier(value) {
            return false;
        }
        if matches!(key, "LARCH_PLUGIN_VERSION" | "LARCH_VERSION")
            && !value.is_empty()
            && value.bytes().all(|byte| {
                byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'+' | b'-')
            })
        {
            return false;
        }
        !sensitive_value_allowlisted(value)
    })
}

fn safe_run_identifier(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b':' | b'-'))
}

#[cfg(test)]
mod tests {
    use super::{
        IssueNormalization, NormalizeOutcomeInput, normalize_issue_output,
        normalize_outcome_values, public_text_is_sensitive, terminal_state_valid, token_valid,
    };
    use std::collections::BTreeMap;

    #[test]
    fn token_rejections_cover_raw_and_kind_specific_branches() {
        for (value, kind, generic) in [
            ("", "", false),
            ("bad value", "", false),
            ("bad$", "", false),
            ("unknown", "outcome", false),
            ("step2b", "step", false),
            ("publish", "phase", false),
            ("gate-b", "site", false),
            ("failed", "trigger", false),
            ("operator-action", "bail", false),
            ("split-path", "source-script", false),
            ("other", "root-cause", false),
            ("approved", "unknown-kind", false),
        ] {
            assert!(
                !token_valid(value, kind, generic),
                "accepted {kind}={value}"
            );
        }
        for (value, kind, generic) in [
            ("approved", "outcome", false),
            ("8a", "step", false),
            ("publish", "phase", true),
            ("gate-b", "site", true),
            ("ci-local-unfixable:job_1,job-2", "trigger", false),
            ("operator-action", "bail", true),
            ("split-path", "source-script", true),
            ("environment", "root-cause", false),
            ("plain-token", "", false),
        ] {
            assert!(token_valid(value, kind, generic), "rejected {kind}={value}");
        }
    }

    #[test]
    fn terminal_state_rejects_partial_duplicate_and_unsafe_values() {
        let valid = [
            ("DESIGN_FAILURE_VERSION", "1"),
            ("DESIGN_FAILURE_KIND", "terminal"),
            ("FAILURE_OUTCOME", "approved"),
            ("STALL_STEP", "8a"),
            ("PHASE", "ship-pr"),
            ("SITE", "ship-pr"),
            ("TRIGGER", "main-agent-required"),
            ("BAIL_REASON", "review-required"),
            ("EXIT_CODE", "4"),
            ("FAILURE_DETAIL_LOG", ""),
            ("SOURCE_SCRIPT", "ship-pr"),
        ]
        .map(|(key, value)| (key.to_owned(), value.to_owned()));
        assert!(terminal_state_valid(&valid, false, |_| false));
        assert!(!terminal_state_valid(&valid[..10], false, |_| false));
        let mut duplicate = valid.to_vec();
        duplicate.push(("PHASE".to_owned(), "ship".to_owned()));
        assert!(!terminal_state_valid(&duplicate, false, |_| false));
        let mut unsafe_rows = valid.to_vec();
        unsafe_rows[4].1 = "https://example.test".to_owned();
        assert!(!terminal_state_valid(&unsafe_rows, false, |_| false));
    }

    #[test]
    fn public_text_rejects_corpus_paths_urls_and_assignments() {
        assert!(public_text_is_sensitive(
            "secret-value\n",
            "found secret-value"
        ));
        assert!(public_text_is_sensitive("", "see https://example.test"));
        assert!(public_text_is_sensitive("", "open source/private.txt"));
        assert!(public_text_is_sensitive("", "TOKEN=secret-value"));
        assert!(!public_text_is_sensitive("approved\n", "approved"));
        assert!(!public_text_is_sensitive("X=approved\n", "X=approved"));
        assert!(!public_text_is_sensitive(
            "LARCH_RUN_ID=report-8066\n",
            "| Run ID | `report-8066` |"
        ));
        assert!(!public_text_is_sensitive(
            "SESSION_ID=report-8066\n",
            "| Run ID | `report-8066` |"
        ));
        assert!(public_text_is_sensitive(
            "LARCH_RUN_ID=private/path\n",
            "| Run ID | `private/path` |"
        ));
        assert!(public_text_is_sensitive(
            "LARCH_TOKEN_SESSION_ID=opaque-session\n",
            "| Run ID | `opaque-session` |"
        ));
    }

    #[test]
    fn issue_output_filters_noise_and_selects_duplicate_identity() {
        let result = normalize_issue_output(
            "noise\nISSUES_FAILED=0\nISSUE_1_NUMBER=\nISSUE_1_URL=bad\nISSUE_1_DUPLICATE=true\nISSUE_1_DUPLICATE_OF_URL=https://github.com/o/r/issues/42\n",
            Some("0"),
        );
        assert_eq!(
            result,
            IssueNormalization::Success {
                number: "42".to_owned(),
                url: "https://github.com/o/r/issues/42".to_owned(),
            }
        );
    }

    #[rustfmt::skip]
    fn outcome(ship: &[(&str, &str)], finalize: &[(&str, &str)], memory_stall: &str) -> Vec<(String, String)> {
        let map = |rows: &[(&str, &str)]| rows.iter().map(|(key, value)| ((*key).to_owned(), (*value).to_owned())).collect();
        let ship = map(ship);
        let finalize = map(finalize);
        let empty = BTreeMap::new();
        normalize_outcome_values(NormalizeOutcomeInput {
            ship: &ship,
            finalize: &finalize,
            session: &empty,
            seed: &empty,
            classification: &empty,
            memory_stall,
            panel_failed: false,
        })
    }

    #[test]
    #[rustfmt::skip]
    fn outcome_normalization_covers_precedence_and_stale_overlays() {
        type Case<'a> = (&'a str, &'a [(&'a str, &'a str)], &'a [(&'a str, &'a str)], &'a str, &'a str); let cases: &[Case<'_>] = &[
            ("merged-before-fork", &[("MERGE_RESULT", "merged"), ("FORKED_TARGET", "true")], &[], "", "merged"),
            ("merge-with-bail", &[("MERGE_RESULT", "merged"), ("BAIL_REASON", "review-required")], &[], "", "bailed"),
            ("memory-stall", &[("MERGE_RESULT", "merged")], &[], "true", "stalled"),
            ("stale-finalize", &[("PR_NUMBER", "8"), ("PHASE", "ci-initial"), ("STALL_TRACKING", "false")], &[("STALL_TRACKING", "true"), ("PHASE", "stalled")], "", "pr-created"),
        ];
        for (name, ship, finalize, memory, expected) in cases {
            let values = outcome(ship, finalize, memory);
            let get = |key| values.iter().find(|(found, _)| found == key).map(|(_, value)| value.as_str());
            assert_eq!(get("IMPLEMENT_NORMALIZED_OUTCOME"), Some(*expected), "{name}");
            if *name == "stale-finalize" {
                assert_eq!(get("IMPLEMENT_FINALIZE_STALL_TRACKING"), Some("true"));
            }
        }
    }
}
