//! Pure validation policy for stall-recovery state and public artifacts.
use regex::Regex;
use std::{collections::BTreeMap, sync::LazyLock};
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

#[must_use]
pub fn artifact_prefix_valid(value: &str) -> bool {
    let mut parts = value.split('-');
    value.is_empty()
        || parts
            .all(|part| !part.is_empty() && part.bytes().all(|byte| byte.is_ascii_alphanumeric()))
}

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
        if let Some((_, value)) = token.split_once('=') {
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
        if matches!(key, "RUN_ID" | "LARCH_TOKEN_SESSION_ID")
            && !value.is_empty()
            && value.bytes().all(|byte| {
                byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b':' | b'-')
            })
        {
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

#[cfg(test)]
mod tests {
    use super::{public_text_is_sensitive, terminal_state_valid, token_valid};

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
    }
}
