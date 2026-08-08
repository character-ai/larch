//! The terminal `## /<skill> run <id>: <outcome>` summary block.
//!
//! Port of the rendering half of Python `larch.git.pr_body.render_run_summary`.
//! Every input arrives already resolved, so this module performs no filesystem,
//! process, or environment work and stays byte-exact against its fixtures.

use crate::{CLAUDE_GLM_5_2_MODEL, canonicalize_glm_main_model, report::format_money};

/// Divisor turning GLM-5.2 API-equivalent token cost into plan cost.
pub const GLM_TOKEN_TO_PLAN_DIVISOR: u32 = 15;

/// `/implement` outcomes that render as a completed run.
const IMPLEMENT_SUCCESS_OUTCOMES: [&str; 6] = [
    "merged",
    "force-merged-externally",
    "pr-created",
    "pr-created-draft",
    "design-only",
    "forked-dry-run",
];

/// `/design` outcomes that render as a completed run.
const DESIGN_SUCCESS_OUTCOMES: [&str; 2] = ["approved", "approved-partition"];

/// Run identity rows shown at the foot of every summary.
#[derive(Clone, Debug, Default)]
pub struct RunSummaryIdentity {
    /// Plugin version that produced the run.
    pub larch_version: String,
    /// Main-agent model id.
    pub main_model: String,
    /// Main-agent effort level.
    pub effort: String,
}

/// Priced cost fields, each already formatted the way `token cost` emits them.
///
/// A value that does not parse as a float renders as `N/A`, matching the Python
/// owner's tolerant `_fmt_money`.
#[derive(Clone, Debug, Default)]
pub struct RunSummaryCost {
    /// Whether pricing was unavailable for this run.
    pub cost_unavailable: bool,
    /// Headline total.
    pub total_cost: String,
    /// Main-agent Claude cost.
    pub claude_cost: String,
    /// Model-summed Codex cost, used only by legacy callers.
    pub codex_cost: String,
    /// Codex default-bucket cost.
    pub codex_gpt_5_5_cost: String,
    /// Codex mini-bucket cost.
    pub codex_gpt_5_4_mini_cost: String,
    /// Aggregate Cursor cost.
    pub cursor_cost: String,
    /// Cursor composer component, absent without per-bucket detail.
    pub cursor_composer_cost: Option<String>,
    /// Cursor grok component, absent without per-bucket detail.
    pub cursor_grok_cost: Option<String>,
    /// Spawned-Claude cost.
    pub claude_sub_cost: String,
    /// Total priced tokens across every lane.
    pub total_tokens: i64,
}

/// Every field one run summary renders.
#[derive(Clone, Debug, Default)]
pub struct RunSummaryFields {
    /// Workflow that produced the run.
    pub skill: String,
    /// Normalized run outcome.
    pub outcome: String,
    /// Run identifier.
    pub run_id: String,
    /// `/implement` workflow path label.
    pub workflow_path: String,
    /// Human-readable run duration.
    pub duration: String,
    /// Tracking issue number.
    pub issue_number: String,
    /// Tracking issue URL.
    pub issue_url: String,
    /// Pull request number.
    pub pr_number: String,
    /// Pull request URL.
    pub pr_url: String,
    /// Plan-review tally line.
    pub plan_review_line: String,
    /// Optional plan-coverage line.
    pub plan_coverage_line: String,
    /// Optional difficulty line.
    pub difficulty_line: String,
    /// Optional dynamic-archetypes line.
    pub dynamic_archetypes_line: String,
    /// Code-review tally line.
    pub code_review_line: String,
    /// Added code lines in the PR diff.
    pub code_added: String,
    /// Deleted code lines in the PR diff.
    pub code_deleted: String,
    /// Added `larch-logs` lines in the PR diff.
    pub logs_added: String,
    /// Deleted `larch-logs` lines in the PR diff.
    pub logs_deleted: String,
    /// Number of filed out-of-scope issues.
    pub oos_count: String,
    /// Comma-separated filed out-of-scope issue URLs.
    pub oos_urls: String,
    /// Execution-issue count.
    pub exec_issues: usize,
    /// Warning count.
    pub warnings: usize,
    /// Provider-neutral run-log reference.
    pub run_logs_path: String,
    /// Whether `--force` was requested, as `true` or `false`.
    pub force_requested: String,
    /// Whether a requested merge was downgraded, as `true` or `false`.
    pub merge_downgraded: String,
    /// Terminal needs-user ship-handoff reason, when one applies.
    pub needs_user_reason: String,
    /// Pending next action for a needs-user ship handoff.
    pub needs_user_next_action: String,
    /// Resolved run identity rows.
    pub identity: RunSummaryIdentity,
    /// Priced cost fields.
    pub cost: RunSummaryCost,
}

/// Render one outcome as its display string.
#[must_use]
pub fn map_outcome_display(outcome: &str) -> String {
    if IMPLEMENT_SUCCESS_OUTCOMES.contains(&outcome) || DESIGN_SUCCESS_OUTCOMES.contains(&outcome) {
        return "\u{2705} DONE".to_owned();
    }
    if outcome == "stalled" {
        return "\u{274c} STALLED".to_owned();
    }
    outcome.to_owned()
}

/// Render the distinct display for a terminal needs-user ship handoff.
fn needs_user_outcome_display(reason: &str, next_action: &str) -> String {
    let pending = if next_action.is_empty() {
        String::new()
    } else {
        format!("; pending: {next_action}")
    };
    format!(
        "\u{26a0}\u{fe0f} NEEDS USER \u{2014} merge and CI watch skipped (reason: {reason}{pending})"
    )
}

/// Format one money field, degrading an unparseable value to `N/A`.
fn money(raw: &str) -> String {
    raw.trim().parse::<f64>().map_or_else(
        |_error| "N/A".to_owned(),
        |value| format!("${}", format_money(value)),
    )
}

/// Render the per-model Codex portion of the cost line.
fn codex_cost_segment(cost: &RunSummaryCost) -> String {
    let (default_bucket, mini_bucket) =
        if cost.codex_gpt_5_5_cost.is_empty() || cost.codex_gpt_5_5_cost == "N/A" {
            (or_default(&cost.codex_cost, "0"), "0")
        } else {
            (
                cost.codex_gpt_5_5_cost.as_str(),
                cost.codex_gpt_5_4_mini_cost.as_str(),
            )
        };
    format!(
        "Codex-5.6 {}, Codex-mini {}",
        money(default_bucket),
        money(mini_bucket)
    )
}

/// Render the Cursor portion of the cost line.
fn cursor_cost_segment(cost: &RunSummaryCost) -> String {
    let aggregate = money(&cost.cursor_cost);
    match (
        cost.cursor_composer_cost.as_deref(),
        cost.cursor_grok_cost.as_deref(),
    ) {
        (Some(composer), Some(grok)) => format!(
            "Cursor {aggregate} (Composer {}, Grok {})",
            money(composer),
            money(grok)
        ),
        _absent => format!("Cursor {aggregate}"),
    }
}

/// Round like Python's two-decimal `round`, which ties to even.
fn round_two(value: f64) -> f64 {
    format!("{value:.2}").parse::<f64>().unwrap_or(value)
}

/// Build the GLM main-lane cost bullet and its note, or `None` when inapplicable.
fn glm_main_lane_cost_parts(fields: &RunSummaryFields) -> Option<(String, String)> {
    if canonicalize_glm_main_model(&fields.identity.main_model) != CLAUDE_GLM_5_2_MODEL {
        return None;
    }
    let cost = &fields.cost;
    let token_cost = cost.claude_cost.trim().parse::<f64>().ok()?;
    let headline_total = cost.total_cost.trim().parse::<f64>().ok()?;
    let estimated = round_two(token_cost / f64::from(GLM_TOKEN_TO_PLAN_DIVISOR));
    let adjusted_total = round_two(headline_total - token_cost + estimated);
    let line = format!(
        "\u{1f4b0} TOTAL ~${}: Claude/GLM-5.2 token ${} (estimated ${}), {}, {}, \
Claude (subprocess) {}  |  Tokens: {}k",
        format_money(adjusted_total),
        format_money(token_cost),
        format_money(estimated),
        codex_cost_segment(cost),
        cursor_cost_segment(cost),
        money(&cost.claude_sub_cost),
        (cost.total_tokens + 500) / 1000,
    );
    let note = format!(
        "- **Cost note**: Token is API-equivalent GLM-5.2 pricing; \
estimated is plan cost (token \u{f7} {GLM_TOKEN_TO_PLAN_DIVISOR})."
    );
    Some((line, note))
}

/// Render the `- **Cost**:` bullet plus the optional GLM plan-estimate note.
fn cost_lines(fields: &RunSummaryFields) -> Vec<String> {
    let cost = &fields.cost;
    if cost.cost_unavailable || cost.total_cost == "N/A" {
        return vec!["- **Cost**: N/A".to_owned()];
    }
    if let Some((line, note)) = glm_main_lane_cost_parts(fields) {
        return vec![format!("- **Cost**: {line}"), note];
    }
    vec![format!(
        "- **Cost**: \u{1f4b0} TOTAL ~{}: Claude {}, {}, {}, \
Claude (subprocess) {}  |  Tokens: {}k",
        money(&cost.total_cost),
        money(&cost.claude_cost),
        codex_cost_segment(cost),
        cursor_cost_segment(cost),
        money(&cost.claude_sub_cost),
        (cost.total_tokens + 500) / 1000,
    )]
}

/// Render one reference of the form `#N` or `#N: URL`.
fn numbered_reference(number: &str, url: &str) -> String {
    if number.is_empty() || number == "0" {
        return "N/A".to_owned();
    }
    if url.is_empty() || url == "N/A" {
        format!("#{number}")
    } else {
        format!("#{number}: {url}")
    }
}

/// Render the run summary block, including its trailing newline.
#[expect(
    clippy::too_many_lines,
    reason = "One ordered bullet list; splitting it would hide the rendered row order."
)]
#[must_use]
pub fn render_run_summary(fields: &RunSummaryFields) -> String {
    let skill = if fields.skill.is_empty() {
        "implement"
    } else {
        fields.skill.as_str()
    };
    let outcome = if fields.outcome.is_empty() {
        "unknown"
    } else {
        fields.outcome.as_str()
    };
    let run_id = if fields.run_id.is_empty() {
        "unknown"
    } else {
        fields.run_id.as_str()
    };
    let design = skill == "design";
    let issue = numbered_reference(&fields.issue_number, &fields.issue_url);
    let pull_request = numbered_reference(&fields.pr_number, &fields.pr_url);
    let counts = [
        &fields.code_added,
        &fields.code_deleted,
        &fields.logs_added,
        &fields.logs_deleted,
    ];
    let lines_display = if counts
        .iter()
        .all(|value| !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
    {
        format!(
            "code +{}/-{}, larch-logs +{}/-{}",
            fields.code_added, fields.code_deleted, fields.logs_added, fields.logs_deleted
        )
    } else {
        "N/A".to_owned()
    };
    let oos_count = if fields.oos_count.is_empty() {
        "0"
    } else {
        fields.oos_count.as_str()
    };
    let oos_display = if fields.oos_urls.is_empty() || fields.oos_urls == "N/A" || oos_count == "0"
    {
        oos_count.to_owned()
    } else {
        format!("{oos_count}: {}", fields.oos_urls)
    };
    let mut run_logs_reference = fields.run_logs_path.clone();
    if run_logs_reference.is_empty()
        && run_id != "unknown"
        && !matches!(outcome, "failed-publish" | "publish-skipped")
    {
        run_logs_reference = format!("provider `unknown`, skill `{skill}`, run ID `{run_id}`");
    }

    let mut lines = vec![
        format!("## /{skill} run {run_id}: {outcome}"),
        String::new(),
    ];
    let outcome_display = if fields.needs_user_reason.is_empty() {
        map_outcome_display(outcome)
    } else {
        needs_user_outcome_display(&fields.needs_user_reason, &fields.needs_user_next_action)
    };
    lines.push(format!("- **Outcome**: {outcome_display}"));
    if !design && !fields.workflow_path.is_empty() {
        lines.push(format!("- **Path**: {}", fields.workflow_path));
    }
    if fields.force_requested == "true" {
        lines.push("- Force: true".to_owned());
    }
    lines.push(format!(
        "- **Duration**: {}",
        or_default(&fields.duration, "N/A")
    ));
    lines.extend(cost_lines(fields));
    lines.push(format!("- **Issue**: {issue}"));
    if !design && pull_request != "N/A" {
        lines.push(format!("- **PR**: {pull_request}"));
    }
    if !design && fields.merge_downgraded == "true" {
        lines.push(
            "- **\u{26a0} Merge downgraded**: requested `--merge`, but panel-failed \
recovery shipped a PR without merging. Manual review and merge required."
                .to_owned(),
        );
    }
    lines.push(format!(
        "- **Plan review**: {}",
        or_default(&fields.plan_review_line, "N/A")
    ));
    if !fields.plan_coverage_line.is_empty() {
        lines.push(format!(
            "- **Plan coverage**: {}",
            fields.plan_coverage_line
        ));
    }
    if !fields.difficulty_line.is_empty() {
        lines.push(format!("- **Difficulty**: {}", fields.difficulty_line));
    }
    if !fields.dynamic_archetypes_line.is_empty() {
        lines.push(format!(
            "- **Dynamic archetypes**: {}",
            fields.dynamic_archetypes_line
        ));
    }
    if !design {
        lines.push(format!(
            "- **Code review**: {}",
            or_default(&fields.code_review_line, "N/A")
        ));
        lines.push(format!("- **Lines (PR diff)**: {lines_display}"));
    }
    lines.push(format!("- **OOS filed**: {oos_display}"));
    lines.push(format!("- **Exec issues**: {}", fields.exec_issues));
    lines.push(format!("- **Warnings**: {}", fields.warnings));
    lines.push(format!(
        "- **Run log**: {}",
        or_default(&run_logs_reference, "N/A")
    ));
    lines.push(format!(
        "- **Main agent model**: {}",
        or_default(&fields.identity.main_model, "unknown")
    ));
    lines.push(format!(
        "- **Effort**: {}",
        or_default(&fields.identity.effort, "unknown")
    ));
    lines.push(format!(
        "- **Larch version**: {}",
        or_default(&fields.identity.larch_version, "unknown")
    ));
    lines.push(String::new());
    lines.push("<!-- larch:run-summary v=1 -->".to_owned());
    let mut rendered = lines.join("\n");
    while rendered.ends_with('\n') {
        let _removed = rendered.pop();
    }
    rendered.push('\n');
    rendered
}

const fn or_default<'a>(value: &'a str, fallback: &'a str) -> &'a str {
    if value.is_empty() { fallback } else { value }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn baseline() -> RunSummaryFields {
        RunSummaryFields {
            skill: "implement".to_owned(),
            outcome: "merged".to_owned(),
            run_id: "run-1".to_owned(),
            issue_number: "42".to_owned(),
            issue_url: "https://github.com/o/r/issues/42".to_owned(),
            pr_number: "7".to_owned(),
            pr_url: "https://github.com/o/r/pull/7".to_owned(),
            code_added: "10".to_owned(),
            code_deleted: "2".to_owned(),
            logs_added: "3".to_owned(),
            logs_deleted: "0".to_owned(),
            oos_count: "0".to_owned(),
            duration: "1m".to_owned(),
            identity: RunSummaryIdentity {
                larch_version: "1.2.3".to_owned(),
                main_model: "claude-opus-4-8".to_owned(),
                effort: "high".to_owned(),
            },
            cost: RunSummaryCost {
                total_cost: "3.00".to_owned(),
                claude_cost: "1.00".to_owned(),
                codex_gpt_5_5_cost: "1.00".to_owned(),
                codex_gpt_5_4_mini_cost: "0.50".to_owned(),
                cursor_cost: "0.25".to_owned(),
                claude_sub_cost: "0.25".to_owned(),
                total_tokens: 1_500,
                ..RunSummaryCost::default()
            },
            ..RunSummaryFields::default()
        }
    }

    #[test]
    fn renders_the_merged_summary_shape() {
        let rendered = render_run_summary(&baseline());
        assert!(rendered.starts_with("## /implement run run-1: merged\n\n"));
        assert!(rendered.contains("- **Outcome**: \u{2705} DONE\n"));
        assert!(rendered.contains("- **PR**: #7: https://github.com/o/r/pull/7\n"));
        assert!(rendered.contains("- **Lines (PR diff)**: code +10/-2, larch-logs +3/-0\n"));
        assert!(rendered.contains(
            "- **Cost**: \u{1f4b0} TOTAL ~$3.00: Claude $1.00, Codex-5.6 $1.00, \
Codex-mini $0.50, Cursor $0.25, Claude (subprocess) $0.25  |  Tokens: 2k\n"
        ));
        assert!(rendered.ends_with("<!-- larch:run-summary v=1 -->\n"));
    }

    #[test]
    fn needs_user_handoff_replaces_the_done_display() {
        let mut fields = baseline();
        fields.outcome = "pr-created".to_owned();
        fields.needs_user_reason = "assessments unavailable".to_owned();
        fields.needs_user_next_action = "merge manually".to_owned();
        let rendered = render_run_summary(&fields);
        assert!(rendered.contains(
            "- **Outcome**: \u{26a0}\u{fe0f} NEEDS USER \u{2014} merge and CI watch skipped \
(reason: assessments unavailable; pending: merge manually)\n"
        ));
    }

    #[test]
    fn design_summaries_omit_pull_request_and_code_rows() {
        let mut fields = baseline();
        fields.skill = "design".to_owned();
        fields.outcome = "approved".to_owned();
        fields.workflow_path = "fast".to_owned();
        let rendered = render_run_summary(&fields);
        assert!(!rendered.contains("- **PR**:"));
        assert!(!rendered.contains("- **Path**:"));
        assert!(!rendered.contains("- **Code review**:"));
        assert!(!rendered.contains("- **Lines (PR diff)**:"));
    }

    #[test]
    fn unavailable_cost_renders_not_available() {
        let mut fields = baseline();
        fields.cost.cost_unavailable = true;
        assert!(render_run_summary(&fields).contains("- **Cost**: N/A\n"));
    }

    #[test]
    fn glm_main_lane_adds_the_plan_estimate_note() {
        let mut fields = baseline();
        fields.identity.main_model = CLAUDE_GLM_5_2_MODEL.to_owned();
        let rendered = render_run_summary(&fields);
        assert!(rendered.contains("Claude/GLM-5.2 token $1.00 (estimated $0.07)"));
        assert!(rendered.contains(
            "- **Cost note**: Token is API-equivalent GLM-5.2 pricing; \
estimated is plan cost (token \u{f7} 15).\n"
        ));
    }

    #[test]
    fn partial_line_counts_degrade_to_not_available() {
        let mut fields = baseline();
        fields.logs_added = String::new();
        assert!(render_run_summary(&fields).contains("- **Lines (PR diff)**: N/A\n"));
    }

    #[test]
    fn filed_out_of_scope_urls_join_the_count() {
        let mut fields = baseline();
        fields.oos_count = "2".to_owned();
        fields.oos_urls = "https://x/issues/1,https://x/issues/2".to_owned();
        assert!(
            render_run_summary(&fields)
                .contains("- **OOS filed**: 2: https://x/issues/1,https://x/issues/2\n")
        );
    }
}
