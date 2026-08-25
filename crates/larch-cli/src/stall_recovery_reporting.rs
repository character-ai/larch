//! Public stall-recovery report composition and corpus commands.
//!
//! These commands deliberately assemble every public payload in memory, redact
//! and verify it, then publish it through the confined atomic writer. A failed
//! redaction never leaves a report or comment slice on disk.

use crate::{
    github_repository_resolution::parse_github_remote_url,
    stall_recovery_file_report::{FileReportArguments, execute as execute_file_report},
};
use chrono::{SecondsFormat, Utc};
use larch_adapters::github::{LiveMutationRequest, check_live_mutation_auth};
use larch_adapters::stall_recovery::{
    STALL_RECOVERY_EVIDENCE_NAMES, build_sensitive_corpus_from_evidence,
    classify_failure_detail_log, is_larch_dev_clone, read_failure_detail_log_with_sidecar_fallback,
    read_validated_failure_detail_log, stall_recovery_artifact_path,
};
use larch_adapters::{GixRepository, PathIntent, TemporaryRoot, atomic_write_utf8_in};
use larch_core::{
    BUG_TITLE_PREFIX, KvDocument, ParseOptions, RepositoryRead, artifact_prefix_valid,
    public_text_is_sensitive, redact, safe_phase, safe_step, token_valid,
};
use sha2::{Digest as _, Sha256};
use std::{
    collections::BTreeMap,
    env,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::{Command, ExitCode},
};

pub type Options = BTreeMap<String, String>;

const CLASSIFICATION: &str = "stall-recovery-classification.env";
const ATTEMPTS: &str = "stall-recovery-attempts.env";
const ESCALATION_LEDGER: &str = "stall-recovery-escalation-ledger.tsv";
const ESCALATION_FALLBACK: &str = "stall-recovery-escalation-fallback.tsv";
const RECORD_FAILURE_MARKER: &str = "stall-recovery-escalation-record-failure.env";
const ROOT_CAUSE: &str = "stall-recovery-root-cause.md";
const BOUNDED_ROOT_CAUSE: &str = "stall-recovery-bounded-root-cause.md";
const SENSITIVE_CORPUS: &str = "stall-recovery-sensitive-corpus.env";
const ISSUE_INPUT: &str = "stall-recovery-issue-input.md";
const CHAT_PRINT: &str = "stall-recovery-chat-print.md";
const TITLE_FILE: &str = "stall-recovery-title.txt";
const OPERATOR_ACTION_RECORD: &str = "stall-recovery-operator-action-record.md";
const OPERATOR_ACTION_SENTINEL: &str = "stall-recovery-operator-action.env";
const TIER_A_ATTEMPTS: &str = "stall-recovery-tier-a-attempts.md";
const TIER_A_ESCALATION: &str = "stall-recovery-tier-a-escalation.md";
const TIER_A_ROOT_CAUSE: &str = "stall-recovery-tier-a-root-cause.md";
const TIER_B_ATTEMPTS: &str = "stall-recovery-bounded-attempts.md";
const TIER_B_ESCALATION: &str = "stall-recovery-bounded-escalation-summary.md";
const TIER_B_ROOT_CAUSE: &str = "stall-recovery-bounded-root-cause-public.md";

// This ordered flow mirrors the former one-pass Python command so the public
// report grammar, write ordering, and terminal status remain compatible.
#[allow(clippy::cognitive_complexity, clippy::too_many_lines)]
pub fn compose(globals: &Options, options: &Options, force_chat_print: bool) -> ExitCode {
    let tmpdir = PathBuf::from(option_or_env(
        options,
        globals,
        "--implement-tmpdir",
        "IMPLEMENT_TMPDIR",
        ".",
    ));
    if !tmpdir.is_dir() {
        return report_error("--implement-tmpdir must exist");
    }
    let Ok(root) = TemporaryRoot::resolve(Some(&tmpdir)) else {
        return report_error("--implement-tmpdir invalid");
    };
    let kind = option_or_global(options, globals, "--report-kind", "terminal-failure");
    let surface = if force_chat_print {
        "chat-print".to_owned()
    } else {
        option_or_global(options, globals, "--surface", "chat-print")
    };
    if !matches!(kind.as_str(), "terminal-failure" | "escalation-success") {
        return report_error("--report-kind must be terminal-failure or escalation-success");
    }
    if !matches!(surface.as_str(), "issue-input" | "chat-print") {
        return report_error("--surface must be issue-input or chat-print");
    }
    let prefix = match report_prefix(globals, options) {
        Ok(prefix) => prefix,
        Err(status) => return status,
    };
    let profile = option_or_global(options, globals, "--profile", "implement");
    let paths = ReportPaths::from_options(&root, options, &prefix, &surface);

    if kind == "escalation-success" && !paths.classification.exists() {
        if !write_path_allowed(&root, &paths.classification) {
            return report_error("--classification-file outside implement tmpdir");
        }
        let signature = hex_digest(b"escalation-success");
        let seed = format!(
            "FAILURE_CLASS=\nFAILURE_SIGNATURE={signature}\nRESUME_HINT=none\nSTALL_STEP=unknown\nPHASE=unknown\nSTALL_TRACKING=false\nBAIL_REASON=\nEXIT_CODE=unknown\nMATCHED_CLASSIFIER_PATTERN=no-stall\nDISPATCHER=unknown\n"
        );
        if write_text(&root, &paths.classification, &seed).is_err() {
            return report_error("--classification-file invalid");
        }
    }
    if !read_path_allowed(&root, &paths.classification) {
        return report_error("--classification-file invalid");
    }
    if paths.attempts.exists() {
        if !read_path_allowed(&root, &paths.attempts) {
            return report_error("--attempts-file invalid");
        }
    } else if write_path_allowed(&root, &paths.attempts) {
        let created = Utc::now().to_rfc3339_opts(SecondsFormat::AutoSi, true);
        if write_text(
            &root,
            &paths.attempts,
            &format!("version=1\ncreated_utc={created}\nattempt_count=0\n"),
        )
        .is_err()
        {
            return report_error("--attempts-file outside implement tmpdir");
        }
    } else {
        return report_error("--attempts-file outside implement tmpdir");
    }
    if !write_path_allowed(&root, &paths.output) {
        return report_error("--output-file outside implement tmpdir");
    }
    for (flag, path) in [
        ("--escalation-ledger-file", &paths.ledger),
        ("--escalation-fallback-file", &paths.fallback),
        ("--record-failure-marker", &paths.marker),
        ("--title-file", &paths.title),
    ] {
        if path.exists() && !read_path_allowed(&root, path) {
            return report_error(&format!("{flag} invalid"));
        }
    }
    if kind == "escalation-success"
        && ![&paths.ledger, &paths.fallback, &paths.marker]
            .iter()
            .any(|path| nonempty_regular(&root, path))
        && !record_escalation_failure_present(&root)
    {
        return report_error("escalation-success report requires escalation evidence");
    }
    if surface == "issue-input" && !tier_a_allowed(&root, &paths.session_env) {
        return report_error("issue-input surface requires larch dev clone and non-forked target");
    }
    let Ok(root_text) = read_root_cause(&root, &paths.root_cause) else {
        return report_error("--root-cause-file invalid");
    };
    let root_fields = RootCause::parse(&root_text);
    if !root_fields.valid() {
        return report_error("--root-cause-file invalid");
    }

    if root_fields.verdict == "operator-action" {
        let record = stall_recovery_artifact_path(root.path(), OPERATOR_ACTION_RECORD, &prefix);
        let sentinel = stall_recovery_artifact_path(root.path(), OPERATOR_ACTION_SENTINEL, &prefix);
        if !write_path_allowed(&root, &record) || !write_path_allowed(&root, &sentinel) {
            return report_error("operator-action record path invalid");
        }
        let record_text = format!(
            "REPORT_KIND={kind}\nVERDICT=operator-action\nROOT_CAUSE_FILE={}\n",
            paths.root_cause.display()
        );
        if write_text(&root, &record, &record_text).is_err()
            || write_text(&root, &sentinel, "STALL_RECOVERY_OPERATOR_ACTION=true\n").is_err()
        {
            return report_error("operator-action record write failed");
        }
        println!("STALL_RECOVERY_REPORT_KIND={kind}");
        println!("STALL_RECOVERY_REPORT_STATUS=skipped_operator_action");
        println!("STALL_RECOVERY_REPORT_TIER=skipped");
        println!("STALL_RECOVERY_REPORT_ARTIFACT={}", record.display());
        println!("STALL_RECOVERY_REPORT_VERDICT=operator-action");
        return ExitCode::SUCCESS;
    }

    let requested_title = read_optional(&root, &paths.title).unwrap_or_default();
    let mut title = safe_title_summary(&requested_title);
    if title.is_empty() {
        title = safe_title_summary(&root_fields.summary);
    }
    if title.is_empty() {
        return report_error("unsafe title and root-cause summary");
    }
    let skill_label = report_skill_label(&profile, &prefix);
    let Some(class_text) = read_required(&root, &paths.classification) else {
        return report_error("--classification-file invalid");
    };
    let rendered_title = if kind == "terminal-failure" {
        format!(
            "{BUG_TITLE_PREFIX} {skill_label} terminal: {title} ({} at {})",
            safe_class(&kv_value(&class_text, "FAILURE_CLASS")),
            safe_step_value(&kv_value(&class_text, "STALL_STEP")),
        )
    } else {
        let site = first_escalation_field(&root, "site", &paths.ledger, &paths.fallback);
        let trigger = first_escalation_field(&root, "trigger", &paths.ledger, &paths.fallback);
        format!(
            "{BUG_TITLE_PREFIX} {skill_label} escalation: {title} ({}:{})",
            if site.is_empty() { "redacted" } else { &site },
            if trigger.is_empty() {
                "redacted"
            } else {
                &trigger
            },
        )
    };
    let signature = report_signature(
        &kind,
        &class_text,
        &root,
        &paths.ledger,
        &paths.fallback,
        &profile,
        &prefix,
        &skill_label,
    );
    let marker = format!("<!-- larch-stall:signature={signature} -->");
    // The title is separately passed to the tier-B filing helper. Redact it
    // before that external boundary as well as in the rendered body.
    let Some(public_title) = redact_public(&rendered_title) else {
        return redaction_failed();
    };

    let (tier, body, comment_payloads, sensitive_corpus) = if surface == "issue-input" {
        let raw_body = compose_tier_a(
            &root,
            &kind,
            &class_text,
            &paths,
            &root_text,
            &rendered_title,
            &marker,
        );
        let raw_payloads = tier_a_payloads(&root, &paths, &root_text, &prefix);
        let Some(body) = redact_public(&raw_body) else {
            return redaction_failed();
        };
        let mut payloads = Vec::new();
        for (path, value) in raw_payloads {
            let Some(value) = redact_public(&value) else {
                return redaction_failed();
            };
            payloads.push((path, value));
        }
        ("A", body, payloads, None)
    } else {
        if !read_path_allowed(&root, &paths.sensitive) {
            return report_error("--sensitive-corpus-file invalid");
        }
        let Ok(bounded_text) = read_root_cause(&root, &paths.bounded_root_cause) else {
            return report_error("--bounded-root-cause-file invalid");
        };
        let bounded_fields = RootCause::parse(&bounded_text);
        if !bounded_fields.valid() {
            return report_error("--bounded-root-cause-file invalid");
        }
        let corpus = build_sensitive_corpus(&root, &paths);
        if public_text_is_sensitive(&corpus, &bounded_text) {
            return report_error("bounded root-cause contains sensitive token");
        }
        let raw_body = format!(
            "### {rendered_title}\n\n{marker}\n{}",
            compose_tier_b(
                &root,
                &kind,
                &class_text,
                &paths,
                &root_fields,
                &bounded_fields,
                &bounded_text,
                &skill_label,
            )
        );
        let raw_payloads = tier_b_payloads(&root, &paths, &bounded_fields, &bounded_text, &prefix);
        if public_text_is_sensitive(&corpus, &raw_body)
            || raw_payloads
                .iter()
                .any(|(_path, value)| public_text_is_sensitive(&corpus, value))
        {
            return report_error("chat-print contains sensitive token");
        }
        let Some(body) = redact_public(&raw_body) else {
            return redaction_failed();
        };
        let mut payloads = Vec::new();
        for (path, value) in raw_payloads {
            let Some(value) = redact_public(&value) else {
                return redaction_failed();
            };
            if public_text_is_sensitive(&corpus, &value) {
                return report_error("chat-print contains sensitive token");
            }
            payloads.push((path, value));
        }
        ("B", body, payloads, Some(corpus))
    };
    if !comment_payloads
        .iter()
        .all(|(path, _value)| write_path_allowed(&root, path))
    {
        return report_error("comment payload path outside implement tmpdir");
    }
    if write_public_payload(&root, &paths.output, &body, sensitive_corpus.as_deref()).is_err()
        || comment_payloads.iter().any(|(path, value)| {
            write_public_payload(&root, path, value, sensitive_corpus.as_deref()).is_err()
        })
    {
        return report_error("report payload write failed");
    }

    let dry_run = truthy(&env::var("LARCH_STALL_RECOVERY_DRY_RUN").unwrap_or_default())
        || truthy(&env::var("DRY_RUN_DECISION").unwrap_or_default());
    println!("STALL_RECOVERY_REPORT_KIND={kind}");
    println!("STALL_RECOVERY_REPORT_TIER={tier}");
    println!("STALL_RECOVERY_REPORT_ARTIFACT={}", paths.output.display());
    println!("STALL_RECOVERY_REPORT_VERDICT={}", root_fields.verdict);
    println!("REPORT_DEDUP_SIGNATURE={signature}");
    println!(
        "DRY_RUN_DECISION={}",
        if dry_run { "true" } else { "false" }
    );
    if dry_run {
        println!("STALL_RECOVERY_REPORT_STATUS=dry-run");
        return ExitCode::SUCCESS;
    }
    if surface == "issue-input"
        && truthy(&env::var("LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES").unwrap_or_default())
        && !truthy(&env::var("LARCH_STALL_RECOVERY_ENABLE_TEST_FILING").unwrap_or_default())
    {
        println!("STALL_RECOVERY_REPORT_STATUS=printed");
        return ExitCode::SUCCESS;
    }
    if surface == "chat-print" {
        emit_chat_print_filing_status(&root, &paths, &public_title, &prefix);
    }
    ExitCode::SUCCESS
}

pub fn populate_sensitive_corpus(globals: &Options, options: &Options) -> ExitCode {
    let tmpdir = PathBuf::from(option_or_env(
        options,
        globals,
        "--implement-tmpdir",
        "IMPLEMENT_TMPDIR",
        ".",
    ));
    if !tmpdir.is_dir() {
        return report_error("--implement-tmpdir must exist");
    }
    let Ok(root) = TemporaryRoot::resolve(Some(&tmpdir)) else {
        return report_error("--implement-tmpdir invalid");
    };
    let prefix = match report_prefix(globals, options) {
        Ok(prefix) => prefix,
        Err(status) => return status,
    };
    let paths = ReportPaths::from_options(&root, options, &prefix, "chat-print");
    if !write_path_allowed(&root, &paths.sensitive) {
        return report_error("--sensitive-corpus-file outside implement tmpdir");
    }
    for (flag, path) in [
        ("--classification-file", &paths.classification),
        ("--attempts-file", &paths.attempts),
        ("--escalation-ledger-file", &paths.ledger),
        ("--escalation-fallback-file", &paths.fallback),
        ("--record-failure-marker", &paths.marker),
    ] {
        if path.exists() && !read_path_allowed(&root, path) {
            return report_error(&format!("{flag} outside implement tmpdir"));
        }
    }
    let corpus = build_sensitive_corpus(&root, &paths);
    if write_text(&root, &paths.sensitive, &corpus).is_err() {
        return report_error("--sensitive-corpus-file outside implement tmpdir");
    }
    println!("SENSITIVE_CORPUS_FILE={}", paths.sensitive.display());
    ExitCode::SUCCESS
}

pub fn dedup_tier_a_report(globals: &Options, options: &Options) -> ExitCode {
    if dedup_dry_run_requested() {
        println!("STALL_RECOVERY_REPORT_STATUS=dry-run");
        return ExitCode::SUCCESS;
    }
    let tmpdir = PathBuf::from(option_or_env(
        options,
        globals,
        "--implement-tmpdir",
        "IMPLEMENT_TMPDIR",
        ".",
    ));
    let Ok(root) = TemporaryRoot::resolve(Some(&tmpdir)) else {
        return report_error("--implement-tmpdir must exist");
    };
    let prefix = match report_prefix(globals, options) {
        Ok(prefix) => prefix,
        Err(status) => return status,
    };
    let body = path_from_option(&root, options, "--body-file", ISSUE_INPUT, &prefix);
    let attempts = path_from_option(&root, options, "--attempts-file", TIER_A_ATTEMPTS, &prefix);
    let escalation = path_from_option(
        &root,
        options,
        "--escalation-ledger-file",
        TIER_A_ESCALATION,
        &prefix,
    );
    let root_cause = path_from_option(
        &root,
        options,
        "--root-cause-file",
        TIER_A_ROOT_CAUSE,
        &prefix,
    );
    if !read_path_allowed(&root, &body) {
        return report_error("--body-file outside implement tmpdir");
    }
    if let Err(message) = ensure_dedup_slices(&root, &attempts, &escalation, &root_cause) {
        return report_error(&message);
    }
    let context = path_from_option(&root, options, "--context-file", "session-env.sh", "");
    let run_id = read_run_id(&root, Some(&context));
    let (authorized, reason) = live_mutation_authorization(&root, &context, &run_id);
    if !authorized {
        println!("STALL_RECOVERY_REPORT_STATUS=mutation-refused");
        println!("STALL_RECOVERY_REPORT_FALLBACK_REASON=unauthorized-mutation:{reason}");
        return ExitCode::SUCCESS;
    }
    let Some(repo) = current_repo_slug() else {
        println!("STALL_RECOVERY_REPORT_STATUS=lookup-failed-open");
        println!("STALL_RECOVERY_REPORT_FALLBACK_REASON=current-repo-unresolved");
        return ExitCode::SUCCESS;
    };
    let create_after_dedup = options
        .get("--create-after-dedup")
        .is_some_and(|value| value == "true");
    let output = execute_file_report(FileReportArguments {
        repo,
        body_file: body,
        title: if create_after_dedup {
            "/implement terminal failure".to_owned()
        } else {
            String::new()
        },
        dedup_only: !create_after_dedup,
        create_on_lookup_failure: create_after_dedup,
        attempts_file: Some(attempts),
        escalation_file: Some(escalation),
        root_cause_file: Some(root_cause),
        publication_tier: "tier-a".to_owned(),
        mutation_context: context,
        run_id,
        trusted_root: root.path().to_path_buf(),
        ..FileReportArguments::default()
    });
    let helper_env = root.path().join("stall-recovery-tier-a-dedup.env");
    let stdout = output.render();
    if write_text(&root, &helper_env, &stdout).is_err() {
        return report_error("dedup result write failed");
    }
    emit_normalized_file_failure_env(&stdout);
    ExitCode::SUCCESS
}

fn ensure_dedup_slices(
    root: &TemporaryRoot,
    attempts: &Path,
    escalation: &Path,
    root_cause: &Path,
) -> Result<(), String> {
    for (flag, path) in [
        ("--attempts-file", attempts),
        ("--escalation-ledger-file", escalation),
        ("--root-cause-file", root_cause),
    ] {
        if path.exists() && !read_path_allowed(root, path) {
            return Err(format!("{flag} outside implement tmpdir"));
        }
        if !path.exists()
            && (!write_path_allowed(root, path) || write_text(root, path, "").is_err())
        {
            return Err("dedup slice path outside implement tmpdir".to_owned());
        }
    }
    Ok(())
}

#[derive(Clone)]
struct ReportPaths {
    classification: PathBuf,
    attempts: PathBuf,
    ledger: PathBuf,
    fallback: PathBuf,
    marker: PathBuf,
    root_cause: PathBuf,
    bounded_root_cause: PathBuf,
    title: PathBuf,
    sensitive: PathBuf,
    session_env: PathBuf,
    output: PathBuf,
}

impl ReportPaths {
    fn from_options(root: &TemporaryRoot, options: &Options, prefix: &str, surface: &str) -> Self {
        let output_default = if surface == "issue-input" {
            ISSUE_INPUT
        } else {
            CHAT_PRINT
        };
        Self {
            classification: path_from_option(
                root,
                options,
                "--classification-file",
                CLASSIFICATION,
                prefix,
            ),
            attempts: path_from_option(root, options, "--attempts-file", ATTEMPTS, prefix),
            ledger: path_from_option(
                root,
                options,
                "--escalation-ledger-file",
                ESCALATION_LEDGER,
                prefix,
            ),
            fallback: path_from_option(
                root,
                options,
                "--escalation-fallback-file",
                ESCALATION_FALLBACK,
                prefix,
            ),
            marker: path_from_option(
                root,
                options,
                "--record-failure-marker",
                RECORD_FAILURE_MARKER,
                prefix,
            ),
            root_cause: path_from_option(root, options, "--root-cause-file", ROOT_CAUSE, prefix),
            bounded_root_cause: path_from_option(
                root,
                options,
                "--bounded-root-cause-file",
                BOUNDED_ROOT_CAUSE,
                prefix,
            ),
            title: path_from_option(root, options, "--title-file", TITLE_FILE, prefix),
            sensitive: path_from_option(
                root,
                options,
                "--sensitive-corpus-file",
                SENSITIVE_CORPUS,
                prefix,
            ),
            session_env: path_from_option(
                root,
                options,
                "--session-env-file",
                "session-env.sh",
                "",
            ),
            output: path_from_option(root, options, "--output-file", output_default, prefix),
        }
    }
}

#[derive(Default)]
struct RootCause {
    verdict: String,
    confidence: String,
    summary: String,
    prose: String,
}

impl RootCause {
    fn parse(text: &str) -> Self {
        let mut prose = Vec::new();
        let mut seen = false;
        for line in text.lines() {
            if line.trim().is_empty() {
                if seen {
                    prose.push(String::new());
                }
                continue;
            }
            if line.starts_with("verdict=")
                || line.starts_with("confidence=")
                || line.starts_with("summary=")
            {
                continue;
            }
            seen = true;
            prose.push(line.to_owned());
        }
        Self {
            verdict: kv_value(text, "verdict"),
            confidence: kv_value(text, "confidence"),
            summary: kv_value(text, "summary"),
            prose: prose.join("\n").trim().to_owned(),
        }
    }

    fn valid(&self) -> bool {
        matches!(
            self.verdict.as_str(),
            "larch-defect" | "environment" | "operator-action"
        ) && matches!(self.confidence.as_str(), "low" | "medium" | "high")
            && !self.summary.is_empty()
            && !self.summary.contains(['\n', '\r'])
            && !self.prose.is_empty()
    }
}

fn compose_tier_a(
    root: &TemporaryRoot,
    kind: &str,
    class_text: &str,
    paths: &ReportPaths,
    root_text: &str,
    title: &str,
    marker: &str,
) -> String {
    let bail_raw = kv_value(class_text, "BAIL_REASON_RAW");
    let bail = if bail_raw.is_empty() {
        kv_value(class_text, "BAIL_REASON")
    } else {
        bail_raw
    };
    let branch = [
        kv_value(class_text, "RECOVERY_BRANCH"),
        file_kv(root, &root.path().join("session-env.sh"), "BRANCH_NAME"),
        file_kv(root, &root.path().join("ship-pr-state.sh"), "BRANCH_NAME"),
        file_kv(root, &root.path().join("session-env.sh"), "BRANCH"),
        file_kv(root, &root.path().join("ship-pr-state.sh"), "BRANCH"),
    ]
    .into_iter()
    .find(|value| !value.is_empty())
    .unwrap_or_default();
    let pr_url = [
        kv_value(class_text, "PR_URL"),
        file_kv(root, &root.path().join("ship-pr-state.sh"), "PR_URL"),
        file_kv(root, &root.path().join("finalize-state.sh"), "PR_URL"),
    ]
    .into_iter()
    .find(|value| !value.is_empty())
    .unwrap_or_else(|| "unknown".to_owned());
    let mut parts = vec![
        format!("### {title}"),
        marker.to_owned(),
        String::new(),
        "## Report metadata".to_owned(),
        String::new(),
        format!("- **Report kind**: `{kind}`"),
        format!(
            "- **Failure class**: `{}`",
            safe_class(&kv_value(class_text, "FAILURE_CLASS"))
        ),
        format!(
            "- **Step**: `{}`",
            safe_step_value(&kv_value(class_text, "STALL_STEP"))
        ),
        format!("- **Bail reason**: `{}`", safe_bail(&bail)),
        format!(
            "- **Run ID**: `{}`",
            read_run_id(root, Some(&paths.session_env))
        ),
        format!("- **Branch**: `{}`", safe_simple(&branch, "unknown")),
        format!("- **PR URL**: `{pr_url}`"),
        format!(
            "- **Resume hint**: `{}`",
            safe_simple(&kv_value(class_text, "RESUME_HINT"), "none")
        ),
    ];
    for (label, value) in publish_progress_fields(class_text) {
        parts.push(format!("- **{label}**: `{value}`"));
    }
    parts.push(format!("\n## Root-cause finding\n\n{root_text}\n"));
    parts.push(format!(
        "\n## Attempts\n\n{}",
        attempts_table(root, &paths.attempts)
    ));
    parts.extend(
        [
            optional_section(root, "Escalation ledger", &paths.ledger),
            optional_section(root, "Fallback escalation evidence", &paths.fallback),
            optional_section(root, "Record-failure marker", &paths.marker),
        ]
        .into_iter()
        .flatten(),
    );
    if record_escalation_failure_present(root) {
        parts.push(
            "\n## Record-escalation Tool Failure\n\n- tagged record-escalation Tool Failure present\n"
                .to_owned(),
        );
    }
    if let Some(detail) = read_failure_detail_with_fallback(
        root,
        &kv_value(class_text, "FAILURE_DETAIL_LOG"),
        &paths.ledger,
        &paths.fallback,
    ) {
        parts.push(format!("\n## Validated failure-detail log\n\n{detail}\n"));
    }
    if let Some(pointer) = read_optional(root, &root.path().join("run-log-pointer.txt"))
        && !pointer.is_empty()
    {
        parts.push(format!("\n## Run-log pointer\n\n{pointer}\n"));
    }
    let body = parts
        .into_iter()
        .filter(|part| !part.is_empty())
        .collect::<Vec<_>>()
        .join("\n");
    if body.ends_with('\n') {
        body
    } else {
        format!("{body}\n")
    }
}

// The legacy report schema has this exact collection of independent inputs.
#[allow(clippy::too_many_arguments)]
fn compose_tier_b(
    root: &TemporaryRoot,
    kind: &str,
    class_text: &str,
    paths: &ReportPaths,
    root_cause: &RootCause,
    bounded: &RootCause,
    _bounded_text: &str,
    skill_label: &str,
) -> String {
    let summary = if bounded.summary.is_empty() {
        &root_cause.summary
    } else {
        &bounded.summary
    };
    let mut body = format!(
        "## {skill_label} {kind} report\n\n| Field | Value |\n|---|---|\n| Report kind | `{kind}` |\n"
    );
    if kind == "escalation-success" {
        body.push_str("| Recovery outcome | `success` |\n");
    } else {
        let _ = writeln!(
            body,
            "| Failure class | `{}` |",
            safe_class(&kv_value(class_text, "FAILURE_CLASS"))
        );
    }
    let _ = write!(
        body,
        "| Step | `{}` |\n| Phase | `{}` |\n| Bail reason | `{}` |\n| Exit code | `{}` |\n| Dispatcher | `{}` |\n| Matched classifier pattern | `{}` |\n| Resume hint | `{}` |\n",
        safe_step_value(&kv_value(class_text, "STALL_STEP")),
        safe_phase_value(&kv_value(class_text, "PHASE")),
        safe_bail(&kv_value(class_text, "BAIL_REASON")),
        safe_simple(&kv_value(class_text, "EXIT_CODE"), "unknown"),
        safe_simple(&kv_value(class_text, "DISPATCHER"), "unknown"),
        safe_simple(
            &kv_value(class_text, "MATCHED_CLASSIFIER_PATTERN"),
            "redacted"
        ),
        safe_simple(&kv_value(class_text, "RESUME_HINT"), "none"),
    );
    for (label, value) in publish_progress_fields(class_text) {
        let _ = writeln!(body, "| {label} | `{value}` |");
    }
    let _ = write!(
        body,
        "| Larch version | `{}` |\n| Run ID | `{}` |\n| Root-cause verdict | `{}` |\n| Root-cause confidence | `{}` |\n\n## Bounded root-cause summary\n\n{summary}\n\n## Bounded root-cause details\n\n{}\n\n## Attempts\n\n{}\n\n## Escalation evidence\n\n{}\n",
        read_larch_version(),
        read_run_id(root, Some(&paths.session_env)),
        root_cause.verdict,
        root_cause.confidence,
        bounded.prose,
        attempts_table(root, &paths.attempts),
        escalation_summaries(root, paths),
    );
    format!("{}\n", body.trim_end())
}

fn tier_a_payloads(
    root: &TemporaryRoot,
    paths: &ReportPaths,
    root_text: &str,
    prefix: &str,
) -> Vec<(PathBuf, String)> {
    let escalation = [
        optional_section(root, "Escalation ledger", &paths.ledger),
        optional_section(root, "Fallback escalation evidence", &paths.fallback),
        optional_section(root, "Record-failure marker", &paths.marker),
        record_escalation_failure_present(root)
            .then(|| "\n## Record-escalation Tool Failure\n\n- tagged record-escalation Tool Failure present\n".to_owned()),
    ]
    .into_iter()
    .flatten()
    .collect::<Vec<_>>()
    .join("\n");
    vec![
        (
            stall_recovery_artifact_path(root.path(), TIER_A_ATTEMPTS, prefix),
            format!("{}\n", attempts_table(root, &paths.attempts)),
        ),
        (
            stall_recovery_artifact_path(root.path(), TIER_A_ESCALATION, prefix),
            escalation,
        ),
        (
            stall_recovery_artifact_path(root.path(), TIER_A_ROOT_CAUSE, prefix),
            root_text.to_owned(),
        ),
    ]
}

fn tier_b_payloads(
    root: &TemporaryRoot,
    paths: &ReportPaths,
    bounded: &RootCause,
    _bounded_text: &str,
    prefix: &str,
) -> Vec<(PathBuf, String)> {
    let root_public = format!(
        "## Bounded root-cause summary\n\n{}\n\n## Bounded root-cause details\n\n{}\n",
        bounded.summary, bounded.prose
    );
    vec![
        (
            stall_recovery_artifact_path(root.path(), TIER_B_ATTEMPTS, prefix),
            format!("{}\n", attempts_table(root, &paths.attempts)),
        ),
        (
            stall_recovery_artifact_path(root.path(), TIER_B_ESCALATION, prefix),
            format!("{}\n", escalation_summaries(root, paths)),
        ),
        (
            stall_recovery_artifact_path(root.path(), TIER_B_ROOT_CAUSE, prefix),
            root_public,
        ),
    ]
}

fn build_sensitive_corpus(root: &TemporaryRoot, paths: &ReportPaths) -> String {
    let mut sources = vec![
        paths.sensitive.clone(),
        paths.classification.clone(),
        paths.attempts.clone(),
        paths.ledger.clone(),
        paths.fallback.clone(),
        paths.marker.clone(),
    ];
    sources.extend(
        STALL_RECOVERY_EVIDENCE_NAMES
            .iter()
            .map(|name| root.path().join(name)),
    );
    let detail_path = PathBuf::from(kv_value(
        &read_optional(root, &paths.classification).unwrap_or_default(),
        "FAILURE_DETAIL_LOG",
    ));
    if !detail_path.as_os_str().is_empty()
        && classify_failure_detail_log(root, &detail_path).is_ok()
    {
        sources.push(detail_path);
    }
    build_sensitive_corpus_from_evidence(root, sources)
}

fn emit_chat_print_filing_status(
    root: &TemporaryRoot,
    paths: &ReportPaths,
    title: &str,
    prefix: &str,
) {
    if truthy(&env::var("LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES").unwrap_or_default())
        && !truthy(&env::var("LARCH_STALL_RECOVERY_ENABLE_TEST_FILING").unwrap_or_default())
    {
        println!("STALL_RECOVERY_REPORT_STATUS=printed");
        return;
    }
    let run_id = read_run_id(root, Some(&paths.session_env));
    let (authorized, _reason) = live_mutation_authorization(root, &paths.session_env, &run_id);
    if !authorized {
        println!("STALL_RECOVERY_REPORT_STATUS=fallback-print-required");
        println!(
            "STALL_RECOVERY_REPORT_FALLBACK_REASON=unauthorized-mutation:reporter-unauthorized"
        );
        return;
    }
    let Some(plugin_root) = plugin_root() else {
        println!("STALL_RECOVERY_REPORT_STATUS=fallback-print-required");
        println!("STALL_RECOVERY_REPORT_FALLBACK_REASON=upstream-repo-unresolved");
        return;
    };
    let resolver = plugin_root.join("scripts/resolve-upstream-larch-repo.sh");
    if !resolver.is_file() {
        println!("STALL_RECOVERY_REPORT_STATUS=fallback-print-required");
        println!("STALL_RECOVERY_REPORT_FALLBACK_REASON=upstream-repo-unresolved");
        return;
    }
    let resolver_output = Command::new(resolver) // lint-subprocess-via-runner: ok bounded retained upstream resolver lacks a typed Rust port
        .output();
    let Ok(resolver_output) = resolver_output else {
        println!("STALL_RECOVERY_REPORT_STATUS=fallback-print-required");
        println!("STALL_RECOVERY_REPORT_FALLBACK_REASON=upstream-repo-unresolved");
        return;
    };
    let upstream = String::from_utf8_lossy(&resolver_output.stdout)
        .trim()
        .to_owned();
    if !resolver_output.status.success() || !valid_repo_slug(&upstream) {
        println!("STALL_RECOVERY_REPORT_STATUS=fallback-print-required");
        println!("STALL_RECOVERY_REPORT_FALLBACK_REASON=upstream-repo-unresolved");
        return;
    }
    let helper_out =
        stall_recovery_artifact_path(root.path(), "stall-recovery-tier-b-file.env", prefix);
    let output = execute_file_report(FileReportArguments {
        repo: upstream,
        body_file: paths.output.clone(),
        title: title.to_owned(),
        attempts_file: Some(stall_recovery_artifact_path(
            root.path(),
            TIER_B_ATTEMPTS,
            prefix,
        )),
        escalation_file: Some(stall_recovery_artifact_path(
            root.path(),
            TIER_B_ESCALATION,
            prefix,
        )),
        root_cause_file: Some(stall_recovery_artifact_path(
            root.path(),
            TIER_B_ROOT_CAUSE,
            prefix,
        )),
        sensitive_corpus_file: Some(paths.sensitive.clone()),
        publication_tier: "tier-b".to_owned(),
        mutation_context: paths.session_env.clone(),
        run_id,
        trusted_root: root.path().to_path_buf(),
        ..FileReportArguments::default()
    });
    let stdout = output.render();
    if write_text(root, &helper_out, &stdout).is_err() {
        println!("STALL_RECOVERY_REPORT_STATUS=fallback-print-required");
        println!("STALL_RECOVERY_REPORT_FALLBACK_REASON=cross-repo-helper-failed");
        return;
    }
    emit_normalized_file_failure_env(&stdout);
}

fn emit_normalized_file_failure_env(text: &str) {
    let mut status = kv_value(text, "FILE_FAILURE_REPORT_STATUS");
    let url = kv_value(text, "FILE_FAILURE_REPORT_URL");
    let mut reason = kv_value(text, "FILE_FAILURE_REPORT_FALLBACK_REASON");
    let allowed = [
        "filed",
        "dry-run",
        "dedup-comment",
        "no-match",
        "fallback-print-required",
        "lookup-failed-open",
        "mutation-refused",
    ];
    if !allowed.contains(&status.as_str()) {
        "fallback-print-required".clone_into(&mut status);
        if reason.is_empty() {
            "helper-status-missing".clone_into(&mut reason);
        }
    } else if status == "mutation-refused" {
        "fallback-print-required".clone_into(&mut status);
        if reason.is_empty() {
            "unauthorized-mutation".clone_into(&mut reason);
        }
    }
    println!("STALL_RECOVERY_REPORT_STATUS={status}");
    if !url.is_empty() {
        println!("STALL_RECOVERY_REPORT_URL={url}");
        if let Some(number) = issue_url_number(&url) {
            println!("STALL_RECOVERY_REPORT_ISSUE_URL={url}");
            println!("STALL_RECOVERY_REPORT_ISSUE_NUMBER={number}");
        }
    }
    if !reason.is_empty() {
        println!("STALL_RECOVERY_REPORT_FALLBACK_REASON={reason}");
    }
}

fn tier_a_allowed(root: &TemporaryRoot, session_env: &Path) -> bool {
    let candidate = [
        env::var("CLAUDE_PROJECT_DIR").unwrap_or_default(),
        env::var("REPO_ROOT").unwrap_or_default(),
        file_kv(root, session_env, "REPO_ROOT"),
        file_kv(root, &root.path().join("ship-pr-state.sh"), "REPO_ROOT"),
    ]
    .into_iter()
    .find(|value| !value.is_empty());
    is_larch_dev_clone(root.path(), candidate.as_deref().map(Path::new))
}

// Signature inputs stay explicit to make the Python-compatible seed auditable.
#[allow(clippy::too_many_arguments)]
fn report_signature(
    kind: &str,
    class_text: &str,
    root: &TemporaryRoot,
    ledger: &Path,
    fallback: &Path,
    profile: &str,
    prefix: &str,
    skill_label: &str,
) -> String {
    let mut fields = vec![if profile == "generic" {
        "larch-stall-report-dedup-generic-v1".to_owned()
    } else {
        "larch-stall-report-dedup-v1".to_owned()
    }];
    if profile == "generic" {
        fields.push(format!("skill_label={skill_label}"));
        fields.push(format!("artifact_prefix={prefix}"));
    }
    fields.extend([
        format!("report_kind={kind}"),
        format!(
            "failure_class={}",
            safe_class(&kv_value(class_text, "FAILURE_CLASS"))
        ),
        format!(
            "step={}",
            safe_step_value(&kv_value(class_text, "STALL_STEP"))
        ),
        format!("phase={}", safe_phase_value(&kv_value(class_text, "PHASE"))),
        format!(
            "safe_bail_token={}",
            safe_bail(&kv_value(class_text, "BAIL_REASON"))
        ),
    ]);
    if kind == "escalation-success" {
        fields.push(format!(
            "escalation_site={}",
            first_escalation_field(root, "site", ledger, fallback)
        ));
        fields.push(format!(
            "escalation_trigger={}",
            first_escalation_field(root, "trigger", ledger, fallback)
        ));
    }
    hex_digest(fields.join("\n").as_bytes())
}

fn attempts_table(root: &TemporaryRoot, path: &Path) -> String {
    let text = read_optional(root, path).unwrap_or_default();
    let count = kv_value(&text, "attempt_count")
        .parse::<usize>()
        .unwrap_or(0);
    let mut table =
        String::from("| Attempt | Class | Resume hint | Outcome | UTC |\n|---|---|---|---|---|\n");
    if count == 0 {
        table.push_str("| none | n/a | n/a | n/a | n/a |");
        return table;
    }
    for index in 1..=count {
        let _ = writeln!(
            table,
            "| `{index}` | `{}` | `{}` | `{}` | `{}` |",
            safe_class(&kv_value(&text, &format!("attempt.{index}.class"))),
            safe_simple(
                &kv_value(&text, &format!("attempt.{index}.resume_hint")),
                "none"
            ),
            safe_simple(
                &kv_value(&text, &format!("attempt.{index}.outcome")),
                "failed"
            ),
            safe_simple(&kv_value(&text, &format!("attempt.{index}.utc")), "unknown"),
        );
    }
    table.trim_end().to_owned()
}

fn publish_progress_fields(class_text: &str) -> Vec<(&'static str, String)> {
    [
        ("Latest phase", "LATEST_PHASE"),
        ("RC source", "PUBLISH_RC_SOURCE"),
        ("Plan written", "PLAN_WRITE_OK"),
        ("Publish ok", "PUBLISH_OK"),
        ("Renamed", "RENAMED"),
        ("Log publish attempted", "LOG_PUBLISH_ATTEMPTED"),
        ("Log publish completed", "LOG_PUBLISH_COMPLETED"),
    ]
    .into_iter()
    .filter_map(|(label, key)| {
        let value = kv_value(class_text, key);
        (!value.is_empty()).then(|| (label, safe_simple(&value, "redacted").to_owned()))
    })
    .collect()
}

fn escalation_summaries(root: &TemporaryRoot, paths: &ReportPaths) -> String {
    let mut lines = Vec::new();
    if let Some(value) = escalation_row_summaries(root, &paths.ledger, "") {
        lines.push(value);
    }
    if let Some(value) = escalation_row_summaries(root, &paths.fallback, "fallback") {
        lines.push(value);
    }
    if nonempty_regular(root, &paths.marker) {
        lines.push("- record-failure marker present".to_owned());
    }
    if record_escalation_failure_present(root) {
        lines.push("- tagged record-escalation Tool Failure present".to_owned());
    }
    lines.join("\n")
}

fn escalation_row_summaries(root: &TemporaryRoot, path: &Path, label: &str) -> Option<String> {
    let text = read_optional(root, path)?;
    if text.is_empty() {
        return None;
    }
    let mut lines = Vec::new();
    for row in text.lines() {
        let site = tsv_field(row, "site");
        let trigger = tsv_field(row, "trigger");
        if !site.is_empty() || !trigger.is_empty() {
            let label = if label.is_empty() {
                String::new()
            } else {
                format!("{label} ")
            };
            lines.push(format!(
                "- {label}site=`{}` trigger=`{}`",
                safe_simple(&site, "redacted"),
                safe_simple(&trigger, "redacted"),
            ));
        }
    }
    if lines.is_empty() && !label.is_empty() {
        lines.push(format!("- {label} present"));
    }
    (!lines.is_empty()).then(|| lines.join("\n"))
}

fn first_escalation_field(
    root: &TemporaryRoot,
    key: &str,
    ledger: &Path,
    fallback: &Path,
) -> String {
    for path in [ledger, fallback] {
        let Some(text) = read_optional(root, path) else {
            continue;
        };
        for row in text.lines() {
            let value = tsv_field(row, key);
            if !value.is_empty() {
                return safe_simple(&value, "redacted").to_owned();
            }
        }
    }
    String::new()
}

fn read_failure_detail_with_fallback(
    root: &TemporaryRoot,
    primary: &str,
    ledger: &Path,
    fallback: &Path,
) -> Option<String> {
    if !primary.is_empty() {
        let path = PathBuf::from(primary);
        match read_validated_failure_detail_log(root, &path) {
            Ok(detail) => return Some(detail),
            Err(error) => eprintln!("{}", error.message("--failure-detail-log")),
        }
    }
    read_failure_detail_log_with_sidecar_fallback(root, primary, ledger, fallback, true)
        .map(|(detail, _path)| detail)
}

fn record_escalation_failure_present(root: &TemporaryRoot) -> bool {
    read_optional(root, &root.path().join("execution-issues.md")).is_some_and(|text| {
        text.lines().any(|line| {
            let trimmed = line.trim_start();
            let rest = trimmed
                .strip_prefix("###")
                .or_else(|| trimmed.strip_prefix("##"));
            let Some(rest) = rest else {
                return false;
            };
            if !rest.chars().next().is_some_and(char::is_whitespace) {
                return false;
            }
            let heading = rest.trim_start();
            heading
                .strip_prefix("Tool Failure: record-escalation")
                .is_some_and(|suffix| {
                    suffix.is_empty() || suffix.chars().next().is_some_and(char::is_whitespace)
                })
        })
    })
}

fn read_root_cause(root: &TemporaryRoot, path: &Path) -> Result<String, ()> {
    if !read_path_allowed(root, path) {
        return Err(());
    }
    read_required(root, path).ok_or(())
}

fn optional_section(root: &TemporaryRoot, label: &str, path: &Path) -> Option<String> {
    read_optional(root, path)
        .filter(|value| !value.is_empty())
        .map(|value| format!("\n## {label}\n\n{value}\n"))
}

fn path_from_option(
    root: &TemporaryRoot,
    options: &Options,
    flag: &str,
    default_name: &str,
    prefix: &str,
) -> PathBuf {
    options
        .get(flag)
        .filter(|value| !value.is_empty())
        .map_or_else(
            || stall_recovery_artifact_path(root.path(), default_name, prefix),
            PathBuf::from,
        )
}

fn report_prefix(globals: &Options, options: &Options) -> Result<String, ExitCode> {
    let prefix = option_or_global(options, globals, "--artifact-prefix", "");
    if artifact_prefix_valid(&prefix) {
        Ok(prefix)
    } else {
        eprintln!("stall-recovery: --artifact-prefix must be a simple dash token");
        Err(ExitCode::from(2))
    }
}

fn dedup_dry_run_requested() -> bool {
    !env::var("LARCH_STALL_RECOVERY_DRY_RUN")
        .unwrap_or_default()
        .is_empty()
}

fn option_or_global(options: &Options, globals: &Options, flag: &str, fallback: &str) -> String {
    options
        .get(flag)
        .or_else(|| globals.get(flag))
        .cloned()
        .unwrap_or_else(|| fallback.to_owned())
}

fn option_or_env(
    options: &Options,
    globals: &Options,
    flag: &str,
    environment: &str,
    fallback: &str,
) -> String {
    options
        .get(flag)
        .or_else(|| globals.get(flag))
        .cloned()
        .or_else(|| env::var(environment).ok())
        .unwrap_or_else(|| fallback.to_owned())
}

fn read_path_allowed(root: &TemporaryRoot, path: &Path) -> bool {
    path.is_absolute()
        && root.confine(path, PathIntent::Read).is_ok()
        && fs::symlink_metadata(path)
            .is_ok_and(|metadata| metadata.is_file() && !metadata.file_type().is_symlink())
}

fn write_path_allowed(root: &TemporaryRoot, path: &Path) -> bool {
    path.is_absolute() && root.confine(path, PathIntent::Write).is_ok()
}

fn nonempty_regular(root: &TemporaryRoot, path: &Path) -> bool {
    read_path_allowed(root, path)
        && fs::symlink_metadata(path).is_ok_and(|metadata| metadata.len() > 0)
}

fn read_required(root: &TemporaryRoot, path: &Path) -> Option<String> {
    let confined = root.confine(path, PathIntent::Read).ok()?;
    confined.revalidate().ok()?;
    fs::read(confined.path())
        .ok()
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
}

fn read_optional(root: &TemporaryRoot, path: &Path) -> Option<String> {
    read_path_allowed(root, path)
        .then(|| read_required(root, path))
        .flatten()
}

fn write_text(root: &TemporaryRoot, path: &Path, text: &str) -> Result<(), ()> {
    atomic_write_utf8_in(root, path, text, false, 0o600).map_err(|_| ())
}

fn write_public_payload(
    root: &TemporaryRoot,
    path: &Path,
    text: &str,
    sensitive_corpus: Option<&str>,
) -> Result<(), ()> {
    write_text(root, path, text)?;
    let Some(written) = read_required(root, path) else {
        remove_confined_payload(root, path);
        return Err(());
    };
    if written != text
        || !redact(&written).findings().is_empty()
        || sensitive_corpus.is_some_and(|corpus| public_text_is_sensitive(corpus, &written))
    {
        remove_confined_payload(root, path);
        return Err(());
    }
    Ok(())
}

fn remove_confined_payload(root: &TemporaryRoot, path: &Path) {
    let Ok(confined) = root.confine(path, PathIntent::Cleanup) else {
        return;
    };
    if confined.revalidate().is_ok() {
        let _ = fs::remove_file(confined.path());
    }
}

fn file_kv(root: &TemporaryRoot, path: &Path, key: &str) -> String {
    read_optional(root, path).map_or_else(String::new, |text| kv_value(&text, key))
}

fn kv_value(text: &str, key: &str) -> String {
    KvDocument::parse(text, ParseOptions::legacy())
        .ok()
        .and_then(|document| {
            document
                .rows()
                .iter()
                .rev()
                .find(|row| row.key() == key)
                .map(|row| row.value().to_owned())
        })
        .unwrap_or_default()
}

fn tsv_field(row: &str, key: &str) -> String {
    KvDocument::parse(&row.replace('\t', "\n"), ParseOptions::legacy())
        .ok()
        .and_then(|document| {
            document
                .rows()
                .iter()
                .find(|field| field.key() == key)
                .map(|field| field.value().to_owned())
        })
        .unwrap_or_default()
}

fn read_run_id(root: &TemporaryRoot, session_env: Option<&Path>) -> String {
    if let Some(session) = session_env {
        let direct = file_kv(root, session, "LARCH_RUN_ID");
        let sourced = if direct.is_empty() {
            source_env_export(root, session, "LARCH_RUN_ID")
        } else {
            direct
        };
        if !sourced.is_empty() {
            return safe_simple(&sourced, "unknown").to_owned();
        }
    }
    let parent = file_kv(root, &root.path().join("parent-issue.md"), "RUN_ID");
    if !parent.is_empty() {
        return safe_simple(&parent, "unknown").to_owned();
    }
    if let Some(session_id) = read_optional(root, &root.path().join("session-id"))
        && !session_id.trim().is_empty()
    {
        return safe_simple(session_id.trim(), "unknown").to_owned();
    }
    let sourced = session_env.map_or_else(
        || source_env_export(root, &root.path().join("source-env.sh"), "SESSION_ID"),
        |path| source_env_export(root, path, "SESSION_ID"),
    );
    safe_simple(&sourced, "unknown").to_owned()
}

fn source_env_export(root: &TemporaryRoot, path: &Path, key: &str) -> String {
    let Some(text) = read_optional(root, path) else {
        return String::new();
    };
    for line in text.lines() {
        let line = line.trim();
        let Some(body) = line.strip_prefix("export ") else {
            continue;
        };
        let body = body.trim_start();
        let Some(value) = body.strip_prefix(&format!("{key}=")) else {
            continue;
        };
        let bytes = value.as_bytes();
        if bytes.len() >= 2 && matches!(bytes[0], b'\'' | b'"') && bytes.last() == Some(&bytes[0]) {
            return value[1..value.len() - 1].to_owned();
        }
        return value.to_owned();
    }
    String::new()
}

fn read_larch_version() -> String {
    let source_root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(2)
        .map(Path::to_path_buf);
    for root in plugin_root().into_iter().chain(source_root) {
        for path in [
            root.join("VERSION"),
            root.join("package.json"),
            root.join(".claude-plugin/plugin.json"),
        ] {
            let Ok(text) = fs::read_to_string(&path) else {
                continue;
            };
            let value = if path.file_name().is_some_and(|name| name == "VERSION") {
                text.trim().to_owned()
            } else {
                json_version(&text)
            };
            if value.bytes().all(|byte| {
                byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'+' | b'-')
            }) && !value.is_empty()
            {
                return value;
            }
        }
    }
    "unknown".to_owned()
}

fn json_version(text: &str) -> String {
    let Some((_, tail)) = text.split_once("\"version\"") else {
        return String::new();
    };
    let Some((_, tail)) = tail.split_once(':') else {
        return String::new();
    };
    let tail = tail.trim_start();
    let Some(tail) = tail.strip_prefix('"') else {
        return String::new();
    };
    tail.split_once('"')
        .map_or_else(String::new, |(value, _)| value.to_owned())
}

fn live_mutation_authorization(
    root: &TemporaryRoot,
    context_file: &Path,
    run_id: &str,
) -> (bool, &'static str) {
    let decision = check_live_mutation_auth(&LiveMutationRequest {
        context_file: Some(context_file),
        operator_mode: false,
        run_id,
        trusted_root: Some(root.path()),
        test_deny: env::var("LARCH_ISSUE_MUTATION_DENY").as_deref() == Ok("true"),
    });
    (decision.is_authorized(), decision.reason())
}

fn plugin_root() -> Option<PathBuf> {
    let root = env::var_os("CLAUDE_PLUGIN_ROOT").map(PathBuf::from)?;
    fs::symlink_metadata(&root)
        .ok()
        .filter(|metadata| metadata.is_dir() && !metadata.file_type().is_symlink())
        .map(|_| root)
}

fn current_repo_slug() -> Option<String> {
    let repository = GixRepository::discover(env::current_dir().ok()?).ok()?;
    let remote = repository
        .remotes()
        .ok()?
        .into_iter()
        .find(|remote| remote.name.as_slice() == b"origin")?;
    let url = String::from_utf8(remote.fetch_url?).ok()?;
    parse_github_remote_url(&url)
}

fn valid_repo_slug(value: &str) -> bool {
    let Some((owner, repo)) = value.split_once('/') else {
        return false;
    };
    !owner.is_empty()
        && !repo.is_empty()
        && !repo.contains('/')
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-' | b'/'))
}

fn issue_url_number(url: &str) -> Option<&str> {
    let prefix = "https://github.com/";
    let tail = url.strip_prefix(prefix)?;
    let mut parts = tail.split('/');
    let owner = parts.next()?;
    let repo = parts.next()?;
    if owner.is_empty() || repo.is_empty() || parts.next()? != "issues" {
        return None;
    }
    let number = parts.next()?;
    (!number.is_empty()
        && number.bytes().all(|byte| byte.is_ascii_digit())
        && parts.next().is_none())
    .then_some(number)
}

fn redact_public(value: &str) -> Option<String> {
    let redacted = redact(value).text().to_owned();
    redact(&redacted).findings().is_empty().then_some(redacted)
}

fn redaction_failed() -> ExitCode {
    println!("STALL_RECOVERY_REPORT_STATUS=fallback-print-required");
    println!("STALL_RECOVERY_REPORT_FALLBACK_REASON=redactor-failed");
    report_error("redactor failed")
}

fn report_error(message: &str) -> ExitCode {
    eprintln!("stall-recovery: {message}");
    ExitCode::from(1)
}

fn safe_class(value: &str) -> &str {
    if [
        "transient-infra",
        "test-failure",
        "lint-failure",
        "dispatch-failure",
        "protected-path",
        "submodule-restricted",
        "ci-fix-exhausted",
        "same-cause-repeat",
        "contract-failure",
        "recoverable",
        "unrecoverable",
        "environment",
        "operator-action",
        "larch-defect",
        "",
    ]
    .contains(&value)
    {
        value
    } else {
        "unrecoverable"
    }
}

fn safe_step_value(value: &str) -> &str {
    if safe_step(value, true) || value == "unknown" {
        value
    } else {
        "unknown"
    }
}

fn safe_phase_value(value: &str) -> &str {
    if safe_phase(value, true) || value == "unknown" {
        value
    } else {
        "unknown"
    }
}

fn safe_bail(value: &str) -> &str {
    if value.is_empty() {
        "none"
    } else if token_valid(value, "bail", true) {
        value
    } else {
        "redacted"
    }
}

fn safe_simple<'a>(value: &'a str, fallback: &'a str) -> &'a str {
    if !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b':' | b'-'))
    {
        value
    } else {
        fallback
    }
}

fn safe_title_summary(value: &str) -> String {
    let value = value.trim();
    if value.is_empty()
        || value.contains(['\r', '\n', '`'])
        || value.starts_with(['/', '#'])
        || value.contains("..")
        || value.contains("<!-- larch:")
        || value.to_ascii_lowercase().contains("github.com")
        || value.contains("/pull/")
        || value.contains("larch-logs/")
        || value.chars().any(char::is_control)
        || value.split_whitespace().any(|word| {
            word.split_once('/').is_some_and(|(left, right)| {
                !left.is_empty()
                    && !right.is_empty()
                    && left.bytes().all(|byte| {
                        byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-')
                    })
                    && right.bytes().all(|byte| {
                        byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-' | b'/')
                    })
            })
        })
    {
        String::new()
    } else {
        value.to_owned()
    }
}

fn report_skill_label(profile: &str, prefix: &str) -> String {
    if profile != "generic" {
        "/implement".to_owned()
    } else if prefix == "design-failure" {
        "/design".to_owned()
    } else if prefix.is_empty() {
        "/implement".to_owned()
    } else {
        format!(
            "/{}",
            prefix.split_once('-').map_or(prefix, |(head, _)| head)
        )
    }
}

fn truthy(value: &str) -> bool {
    matches!(
        value.trim().to_ascii_lowercase().as_str(),
        "1" | "true" | "yes" | "on"
    )
}

fn hex_digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

#[cfg(test)]
mod tests {
    use super::{
        RootCause, hex_digest, issue_url_number, redact_public, report_signature,
        report_skill_label, safe_bail, safe_class, safe_phase_value, safe_step_value,
        safe_title_summary, write_public_payload,
    };
    use larch_adapters::TemporaryRoot;

    #[test]
    fn report_signature_keeps_the_python_seed_bytes() {
        let temp = tempfile::tempdir().expect("temporary root");
        let root = TemporaryRoot::resolve(Some(temp.path())).expect("temporary root");
        let class = "FAILURE_CLASS=test-failure\nSTALL_STEP=8a\nPHASE=ship-pr\nBAIL_REASON=review-required\n";
        assert_eq!(
            report_signature(
                "terminal-failure",
                class,
                &root,
                &temp.path().join("ledger.tsv"),
                &temp.path().join("fallback.tsv"),
                "implement",
                "",
                "/implement",
            ),
            hex_digest(b"larch-stall-report-dedup-v1\nreport_kind=terminal-failure\nfailure_class=test-failure\nstep=8a\nphase=ship-pr\nsafe_bail_token=review-required"),
        );
    }

    #[test]
    fn redaction_verification_refuses_a_secret_left_by_an_identity_transform() {
        let secret = "ghp_abcdefghijklmnopqrstuvwxyz0123456789AB";
        assert!(redact_public(&format!("before {secret} after")).is_some());
    }

    #[test]
    fn root_cause_requires_machine_header_and_prose() {
        let parsed = RootCause::parse(
            "verdict=larch-defect\nconfidence=high\nsummary=Safe summary\n\nEvidence\n",
        );
        assert!(parsed.valid());
        assert!(!RootCause::parse("verdict=larch-defect\nconfidence=high\nsummary=Safe\n").valid());
        assert_eq!(safe_title_summary("owner/repo leak"), "");
    }

    #[test]
    fn escalation_seed_signature_matches_sha256() {
        assert_eq!(
            hex_digest(b"escalation-success"),
            "ca21fe07281dab70ccb36d237c6204d1e48b1488a52f0ef0ea7aee28794cf083"
        );
    }

    #[test]
    fn public_write_removes_a_payload_that_fails_readback_validation() {
        let temp = tempfile::tempdir().expect("temporary root");
        let root = TemporaryRoot::resolve(Some(temp.path())).expect("temporary root");
        let output = temp.path().join("public.md");
        assert!(
            write_public_payload(&root, &output, "sensitive-value", Some("sensitive-value"),)
                .is_err()
        );
        assert!(!output.exists());
    }

    #[test]
    fn public_reporting_helpers_reject_unsafe_values_and_preserve_known_labels() {
        assert_eq!(safe_class("not-a-class"), "unrecoverable");
        assert_eq!(safe_step_value("unsafe step"), "unknown");
        assert_eq!(safe_phase_value("unsafe phase"), "unknown");
        assert_eq!(safe_bail("unsafe bail"), "redacted");
        assert_eq!(
            issue_url_number("https://github.com/character-ai/larch/issues/8066"),
            Some("8066")
        );
        assert_eq!(
            issue_url_number("https://github.com/character-ai/larch/pull/8066"),
            None
        );
        assert_eq!(report_skill_label("generic", "design-failure"), "/design");
        assert_eq!(report_skill_label("generic", "review-failure"), "/review");
        assert_eq!(
            report_skill_label("implement", "design-failure"),
            "/implement"
        );
    }
}
