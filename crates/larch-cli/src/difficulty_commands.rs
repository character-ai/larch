//! Rust owner for `difficulty` rating, record, panel, and label commands.

use std::{
    collections::BTreeSet,
    ffi::{OsStr, OsString},
    fs,
    io::Read as _,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{ExactDiffRequest, GitRef, github::IssueMutationOwner};
use larch_core::{
    AUDIT_DENOMINATOR, BuildRecord, DifficultyFloor, DifficultyRating, FLOOR_MANIFEST_RELPATH,
    GitHubLabelCreate, GitHubService as _, IssueMutationRequest, MergeExplicit, RUBRIC,
    blank_merge_explicit, build_record, difficulty_line, known_labels, label_for_tier,
    load_floor_manifest, load_record_data, merge_existing_record_fields, normalize_tier,
    plan_difficulty, rating_from_tier, read_changed_paths, read_rating_file,
    refresh_existing_record, resolve_panel_tier, tier_valid, unsigned_integer,
    validate_rating_object, write_record_map,
};
use serde_json::{Map, Value};

use crate::{
    argparse_compat::{
        ParsedCommandLine, choice_error, finish_parse, parse_with_flags, python_io_error,
        usage_error, write_stdout,
    },
    git_command_runtime::GitCommandRuntime,
    github_repository_resolution::{ambient_repo, repository_ref},
    github_service::{ServiceFailure, with_github_service},
    issue_mutation_support::authorization_request,
    python_verb::plugin_root_directory,
};

const VALIDATE_PROGRAM: &str = "cli.py difficulty validate-rating";
const VALIDATE_USAGE: &str = "\
usage: cli.py difficulty validate-rating [-h] --input-file INPUT_FILE
                                         [--output-file OUTPUT_FILE]";
const VALIDATE_HELP: &str = "\
usage: cli.py difficulty validate-rating [-h] --input-file INPUT_FILE
                                         [--output-file OUTPUT_FILE]

options:
  -h, --help            show this help message and exit
  --input-file INPUT_FILE
  --output-file OUTPUT_FILE
";

const EXTRACT_PROGRAM: &str = "cli.py difficulty extract-plan-metadata";
const EXTRACT_USAGE: &str =
    "usage: cli.py difficulty extract-plan-metadata [-h] --plan-file PLAN_FILE";
const EXTRACT_HELP: &str = "\
usage: cli.py difficulty extract-plan-metadata [-h] --plan-file PLAN_FILE

options:
  -h, --help            show this help message and exit
  --plan-file PLAN_FILE
";

const WRITE_PROGRAM: &str = "cli.py difficulty write-record";
const WRITE_USAGE: &str = "\
usage: cli.py difficulty write-record [-h] --output OUTPUT
                                      [--rater {design,implement,review,fallback}]
                                      [--rater-tool RATER_TOOL]
                                      [--rater-model RATER_MODEL]
                                      [--raw-rating-file RAW_RATING_FILE]
                                      [--design-raw-rating-file DESIGN_RAW_RATING_FILE]
                                      [--implement-raw-rating-file IMPLEMENT_RAW_RATING_FILE]
                                      [--design-tier DESIGN_TIER]
                                      [--changed-paths-file CHANGED_PATHS_FILE]
                                      [--panel-skipped PANEL_SKIPPED]
                                      [--audit-upgrade AUDIT_UPGRADE]
                                      [--escalation ESCALATION]
                                      [--override-source OVERRIDE_SOURCE]
                                      [--override-tier OVERRIDE_TIER]
                                      [--panel-tier PANEL_TIER]
                                      [--round-cap ROUND_CAP]
                                      [--codex-model-role CODEX_MODEL_ROLE]
                                      [--audit-evaluated {,true,false}]
                                      [--escalated-round {,true,false}]
                                      [--fallback-tier FALLBACK_TIER]
                                      [--fallback-rationale FALLBACK_RATIONALE]
                                      [--refresh-existing]
                                      [--refresh-repo-root REFRESH_REPO_ROOT]";
const WRITE_HELP: &str = "\
usage: cli.py difficulty write-record [-h] --output OUTPUT
                                      [--rater {design,implement,review,fallback}]
                                      [--rater-tool RATER_TOOL]
                                      [--rater-model RATER_MODEL]
                                      [--raw-rating-file RAW_RATING_FILE]
                                      [--design-raw-rating-file DESIGN_RAW_RATING_FILE]
                                      [--implement-raw-rating-file IMPLEMENT_RAW_RATING_FILE]
                                      [--design-tier DESIGN_TIER]
                                      [--changed-paths-file CHANGED_PATHS_FILE]
                                      [--panel-skipped PANEL_SKIPPED]
                                      [--audit-upgrade AUDIT_UPGRADE]
                                      [--escalation ESCALATION]
                                      [--override-source OVERRIDE_SOURCE]
                                      [--override-tier OVERRIDE_TIER]
                                      [--panel-tier PANEL_TIER]
                                      [--round-cap ROUND_CAP]
                                      [--codex-model-role CODEX_MODEL_ROLE]
                                      [--audit-evaluated {,true,false}]
                                      [--escalated-round {,true,false}]
                                      [--fallback-tier FALLBACK_TIER]
                                      [--fallback-rationale FALLBACK_RATIONALE]
                                      [--refresh-existing]
                                      [--refresh-repo-root REFRESH_REPO_ROOT]

options:
  -h, --help            show this help message and exit
  --output OUTPUT
  --rater {design,implement,review,fallback}
  --rater-tool RATER_TOOL
  --rater-model RATER_MODEL
  --raw-rating-file RAW_RATING_FILE
  --design-raw-rating-file DESIGN_RAW_RATING_FILE
  --implement-raw-rating-file IMPLEMENT_RAW_RATING_FILE
  --design-tier DESIGN_TIER
  --changed-paths-file CHANGED_PATHS_FILE
  --panel-skipped PANEL_SKIPPED
  --audit-upgrade AUDIT_UPGRADE
  --escalation ESCALATION
  --override-source OVERRIDE_SOURCE
  --override-tier OVERRIDE_TIER
  --panel-tier PANEL_TIER
  --round-cap ROUND_CAP
  --codex-model-role CODEX_MODEL_ROLE
  --audit-evaluated {,true,false}
  --escalated-round {,true,false}
  --fallback-tier FALLBACK_TIER
  --fallback-rationale FALLBACK_RATIONALE
  --refresh-existing
  --refresh-repo-root REFRESH_REPO_ROOT
";

const RUBRIC_PROGRAM: &str = "cli.py difficulty render-rubric";
const RUBRIC_USAGE: &str = "usage: cli.py difficulty render-rubric [-h]";
const RUBRIC_HELP: &str = "\
usage: cli.py difficulty render-rubric [-h]

options:
  -h, --help  show this help message and exit
";

const LINE_PROGRAM: &str = "cli.py difficulty render-line";
const LINE_USAGE: &str = "usage: cli.py difficulty render-line [-h] --record-file RECORD_FILE";
const LINE_HELP: &str = "\
usage: cli.py difficulty render-line [-h] --record-file RECORD_FILE

options:
  -h, --help            show this help message and exit
  --record-file RECORD_FILE
";

const PANEL_PROGRAM: &str = "cli.py difficulty resolve-panel";
const PANEL_USAGE: &str = "\
usage: cli.py difficulty resolve-panel [-h] --record-file RECORD_FILE
                                       [--override OVERRIDE]
                                       [--audit-roll AUDIT_ROLL] [--no-audit]";
const PANEL_HELP: &str = "\
usage: cli.py difficulty resolve-panel [-h] --record-file RECORD_FILE
                                       [--override OVERRIDE]
                                       [--audit-roll AUDIT_ROLL] [--no-audit]

options:
  -h, --help            show this help message and exit
  --record-file RECORD_FILE
  --override OVERRIDE
  --audit-roll AUDIT_ROLL
  --no-audit
";

const SYNC_PROGRAM: &str = "cli.py difficulty sync-labels";
const SYNC_USAGE: &str = "\
usage: cli.py difficulty sync-labels [-h] --issue ISSUE --tier TIER
                                     [--repo REPO]";
const SYNC_HELP: &str = "\
usage: cli.py difficulty sync-labels [-h] --issue ISSUE --tier TIER
                                     [--repo REPO]

options:
  -h, --help     show this help message and exit
  --issue ISSUE
  --tier TIER
  --repo REPO
";

const LABEL_COLOR: &str = "ededed";
const LABEL_DESCRIPTION: &str = "larch difficulty rating";
const RATER_CHOICES: &[&str] = &["design", "implement", "review", "fallback"];
const BOOL_CHOICES: &[&str] = &["", "true", "false"];

/// Dispatch `difficulty validate-rating`.
#[must_use]
pub fn validate_rating(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--input-file", "--output-file"];
    let parsed = match parse_command(
        arguments,
        OPTIONS,
        &[],
        [VALIDATE_USAGE, VALIDATE_PROGRAM, VALIDATE_HELP],
        &["--input-file"],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let input = path_value(&parsed, "--input-file");
    match validate_rating_inner(&input, parsed.value("--output-file").map(Path::new)) {
        Ok(rating) => {
            println!("STATUS=ok");
            println!("PREDICTED_TIER={}", rating.predicted_tier);
            println!("CONFIDENCE={}", rating.confidence);
            println!("ADJUSTED_TIER={}", rating.adjusted_tier);
            ExitCode::SUCCESS
        }
        Err(error) => {
            print!("STATUS=invalid\nERROR={error}\n");
            ExitCode::FAILURE
        }
    }
}

/// Dispatch `difficulty extract-plan-metadata`.
#[must_use]
pub fn extract_plan_metadata(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--plan-file"];
    let parsed = match parse_command(
        arguments,
        OPTIONS,
        &[],
        [EXTRACT_USAGE, EXTRACT_PROGRAM, EXTRACT_HELP],
        &["--plan-file"],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    match extract_plan_difficulty(Path::new(&path_value(&parsed, "--plan-file"))) {
        Ok(tier) => {
            println!("STATUS=ok");
            println!("DESIGN_DIFFICULTY={tier}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            print!("STATUS=error\nERROR={error}\n");
            ExitCode::from(2)
        }
    }
}

/// Read plan-trailer difficulty without printing a command envelope.
///
/// # Errors
/// Returns a Python-shaped `OSError` when the plan file cannot be read.
pub fn extract_plan_difficulty(plan_file: &Path) -> Result<String, String> {
    Ok(plan_difficulty(&read_text(plan_file)?))
}

/// Dispatch `difficulty write-record`.
#[must_use]
pub fn write_record(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &[
        "--output",
        "--rater",
        "--rater-tool",
        "--rater-model",
        "--raw-rating-file",
        "--design-raw-rating-file",
        "--implement-raw-rating-file",
        "--design-tier",
        "--changed-paths-file",
        "--panel-skipped",
        "--audit-upgrade",
        "--escalation",
        "--override-source",
        "--override-tier",
        "--panel-tier",
        "--round-cap",
        "--codex-model-role",
        "--audit-evaluated",
        "--escalated-round",
        "--fallback-tier",
        "--fallback-rationale",
        "--refresh-repo-root",
    ];
    let parsed = match parse_command(
        arguments,
        OPTIONS,
        &["--refresh-existing"],
        [WRITE_USAGE, WRITE_PROGRAM, WRITE_HELP],
        &["--output"],
        &[
            ("--rater", RATER_CHOICES),
            ("--audit-evaluated", BOOL_CHOICES),
            ("--escalated-round", BOOL_CHOICES),
        ],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let output_text = option_text(&parsed, "--output");
    match write_record_inner(&parsed, Path::new(&output_text)) {
        Ok(record) => {
            println!("STATUS=ok");
            println!("OUTPUT={output_text}");
            println!("PREDICTED_TIER={}", json_text(record.get("predicted_tier")));
            println!("APPLIED_TIER={}", json_text(record.get("applied_tier")));
            println!(
                "OVERRIDE_SOURCE={}",
                json_text(record.get("override_source"))
            );
            ExitCode::SUCCESS
        }
        Err(error) => {
            print!("STATUS=error\nERROR={error}\n");
            ExitCode::FAILURE
        }
    }
}

/// Refresh floors on an existing record from `git diff --name-only HEAD`.
///
/// # Errors
/// Returns when the record is invalid, Git cannot list paths, or the write fails.
pub fn refresh_existing_at(output: &Path, repo_root: &Path) -> Result<(), String> {
    let floors = load_floors()?;
    let paths = git_changed_paths(repo_root)?;
    let record = refresh_existing_record(output, &paths, &floors)?;
    write_record_map(output, &record)
}

/// Write the bootstrap fallback record used by `/implement` Step 0.
///
/// # Errors
/// Returns when floors cannot load or the record cannot be written.
pub fn write_bootstrap_record(
    output: &Path,
    prior: &str,
    override_tier: &str,
) -> Result<(), String> {
    let floors = load_floors()?;
    let design = if tier_valid(prior) {
        rating_from_tier(prior, "design wire metadata")
    } else {
        None
    };
    let fallback = rating_from_tier("MODERATE", "initial record seeded before implement rating")
        .ok_or_else(|| "fallback rating is invalid".to_owned())?;
    let override_source = if tier_valid(override_tier) {
        "operator"
    } else {
        ""
    };
    let override_value = if tier_valid(override_tier) {
        override_tier
    } else {
        ""
    };
    let record = build_record(BuildRecord {
        rater: "fallback",
        rater_tool: "bootstrap",
        rater_model: "unknown",
        design_rating: design.as_ref(),
        implement_rating: None,
        fallback_rating: Some(&fallback),
        changed_paths: &[],
        floors: &floors,
        panel_skipped: "",
        audit_upgrade: "",
        escalations: &[],
        override_source,
        override_tier: override_value,
        panel_tier: "",
        round_cap: None,
        codex_model_role: "",
        audit_evaluated: None,
        escalated_round: None,
    })?;
    let merged =
        merge_existing_record_fields(record, &load_record_data(output), &blank_merge_explicit());
    write_record_map(output, &merged)
}

/// Dispatch `difficulty render-rubric`.
#[must_use]
pub fn render_rubric(arguments: &[OsString]) -> ExitCode {
    match parse_command(
        arguments,
        &[],
        &[],
        [RUBRIC_USAGE, RUBRIC_PROGRAM, RUBRIC_HELP],
        &[],
        &[],
    ) {
        Ok(_parsed) => write_stdout(RUBRIC),
        Err(code) => code,
    }
}

/// Dispatch `difficulty render-line`.
#[must_use]
pub fn render_line(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--record-file"];
    let parsed = match parse_command(
        arguments,
        OPTIONS,
        &[],
        [LINE_USAGE, LINE_PROGRAM, LINE_HELP],
        &["--record-file"],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    match render_line_inner(Path::new(&path_value(&parsed, "--record-file"))) {
        Ok(line) => {
            println!("{line}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprint!("STATUS=error\nERROR={error}\n");
            ExitCode::FAILURE
        }
    }
}

/// Dispatch `difficulty resolve-panel`.
#[must_use]
pub fn resolve_panel(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--record-file", "--override", "--audit-roll"];
    let parsed = match parse_command(
        arguments,
        OPTIONS,
        &["--no-audit"],
        [PANEL_USAGE, PANEL_PROGRAM, PANEL_HELP],
        &["--record-file"],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let record_file = path_value(&parsed, "--record-file");
    let override_raw = option_text(&parsed, "--override");
    let override_tier = normalize_tier(&override_raw, "");
    if !override_raw.is_empty() && override_tier.is_empty() {
        print!("STATUS=error\nERROR=invalid-override\n");
        return ExitCode::from(2);
    }
    let roll = match audit_roll(&parsed, Path::new(&record_file)) {
        Ok(roll) => roll,
        Err(error) => {
            print!("STATUS=error\nERROR={error}\n");
            return ExitCode::from(2);
        }
    };
    match resolve_panel_tier(
        Path::new(&record_file),
        &override_tier,
        roll,
        !parsed.flag("--no-audit"),
        None,
    ) {
        Ok(resolution) => {
            println!("STATUS=ok");
            println!("PANEL_TIER={}", resolution.panel_tier);
            println!("ROUND_CAP={}", resolution.round_cap);
            println!("CODEX_MODEL_ROLE={}", resolution.codex_model_role);
            println!(
                "AUDIT_EVALUATED={}",
                if resolution.audit_evaluated {
                    "true"
                } else {
                    "false"
                }
            );
            println!(
                "AUDIT_UPGRADE={}",
                if resolution.audit_upgrade {
                    "true"
                } else {
                    "false"
                }
            );
            println!("OVERRIDE_SOURCE={}", resolution.override_source);
            println!(
                "ESCALATED_ROUND={}",
                if resolution.escalated_round {
                    "true"
                } else {
                    "false"
                }
            );
            ExitCode::SUCCESS
        }
        Err(error) => {
            print!("STATUS=error\nERROR={error}\n");
            ExitCode::FAILURE
        }
    }
}

/// Dispatch `difficulty sync-labels`.
#[must_use]
pub fn sync_labels(arguments: &[OsString]) -> ExitCode {
    const OPTIONS: &[&str] = &["--issue", "--tier", "--repo"];
    let parsed = match parse_command(
        arguments,
        OPTIONS,
        &[],
        [SYNC_USAGE, SYNC_PROGRAM, SYNC_HELP],
        &["--issue", "--tier"],
        &[],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tier = option_text(&parsed, "--tier").to_ascii_uppercase();
    if !tier_valid(&tier) {
        print!("STATUS=error\nERROR=invalid-tier\n");
        return ExitCode::from(2);
    }
    let repo = {
        let supplied = option_text(&parsed, "--repo");
        if supplied.is_empty() {
            ambient_repo().unwrap_or_default()
        } else {
            supplied
        }
    };
    if repo.is_empty() {
        print!("STATUS=error\nERROR=repo-unresolved\n");
        return ExitCode::FAILURE;
    }
    let issue = option_text(&parsed, "--issue");
    sync_labels_inner(&repo, &issue, &tier).map_or_else(
        |_error| {
            print!("STATUS=error\nERROR=label-add-failed\n");
            ExitCode::FAILURE
        },
        |label| {
            println!("STATUS=ok");
            println!("LABEL={label}");
            ExitCode::SUCCESS
        },
    )
}

fn sync_labels_inner(repo: &str, issue: &str, tier: &str) -> Result<String, String> {
    let label = label_for_tier(tier)?;
    let repository = repository_ref(repo).map_err(|()| "repo-unresolved".to_owned())?;
    let number = unsigned_integer(issue).ok_or_else(|| "label-add-failed".to_owned())?;
    let known = known_labels();
    let authorization = authorization_request("", "", "", true);
    let create_request = GitHubLabelCreate {
        repo: repository.clone(),
        name: label.clone(),
        color: LABEL_COLOR.to_owned(),
        description: LABEL_DESCRIPTION.to_owned(),
    };
    let create_failed = with_github_service(async |service, cancellation| {
        if service
            .list_labels(&repository, cancellation)
            .await
            .is_ok_and(|labels| labels.iter().any(|item| item.name == create_request.name))
        {
            return Ok(false);
        }
        match service.create_label(&create_request, cancellation).await {
            Ok(_created) => Ok(false),
            Err(error) => {
                let detail = error.to_string().to_ascii_lowercase();
                if detail.contains("already exists") || detail.contains("already_exists") {
                    Ok(false)
                } else {
                    Ok(true)
                }
            }
        }
    })
    .unwrap_or(true);
    if create_failed {
        println!("STATUS=warning");
        println!("WARNING=label-create-failed");
    }
    match with_github_service(async |service, cancellation| {
        let owner = IssueMutationOwner::new(service);
        let snapshot = owner
            .read_snapshot(&repository, number, cancellation)
            .await
            .map_err(|error| error.to_string())?;
        let mut labels: BTreeSet<String> = snapshot
            .labels
            .iter()
            .filter(|name| !known.iter().any(|item| item == *name))
            .cloned()
            .collect();
        let _inserted = labels.insert(label.clone());
        owner
            .apply(
                cancellation,
                &authorization,
                &IssueMutationRequest::replace_labels(&snapshot, labels),
            )
            .await
            .map(|_verified| ())
            .map_err(|error| error.to_string())
    }) {
        Ok(()) => Ok(label),
        Err(ServiceFailure::Setup(_) | ServiceFailure::Operation(_)) => {
            Err("label-add-failed".to_owned())
        }
    }
}

fn validate_rating_inner(input: &Path, output: Option<&Path>) -> Result<DifficultyRating, String> {
    let text = read_text(input)?;
    let data: Value = serde_json::from_str(&text).map_err(|error| error.to_string())?;
    let rating = validate_rating_object(&data)?;
    if let Some(path) = output {
        let mut encoded = Map::new();
        let _ = encoded.insert(
            "adjusted_tier".to_owned(),
            Value::from(rating.adjusted_tier.as_str()),
        );
        let _ = encoded.insert(
            "confidence".to_owned(),
            Value::from(rating.confidence.as_str()),
        );
        let _ = encoded.insert(
            "predicted_tier".to_owned(),
            Value::from(rating.predicted_tier.as_str()),
        );
        let _ = encoded.insert(
            "rationale".to_owned(),
            Value::from(rating.rationale.as_str()),
        );
        write_record_map(path, &encoded)?;
    }
    Ok(rating)
}

fn write_record_inner(
    parsed: &ParsedCommandLine,
    output: &Path,
) -> Result<Map<String, Value>, String> {
    let floors = load_floors()?;
    if parsed.flag("--refresh-existing") {
        let existing = load_record_data(output);
        let _rating = validate_rating_object(&Value::Object(existing))?;
        let mut paths = read_changed_paths(nonempty_path(parsed, "--changed-paths-file"));
        if paths.is_empty()
            && let Some(root) = nonempty_path(parsed, "--refresh-repo-root")
        {
            paths = git_changed_paths(root)?;
        }
        let record = refresh_existing_record(output, &paths, &floors)?;
        write_record_map(output, &record)?;
        return Ok(record);
    }
    let (rater, rater_tool, rater_model, design_rating, implement_rating, fallback) =
        write_ratings(parsed);
    let changed_paths = read_changed_paths(nonempty_path(parsed, "--changed-paths-file"));
    let panel_skipped = option_text(parsed, "--panel-skipped");
    let audit_upgrade = option_text(parsed, "--audit-upgrade");
    let override_source = option_text(parsed, "--override-source");
    let override_tier = option_text(parsed, "--override-tier");
    let panel_tier = option_text(parsed, "--panel-tier");
    let round_cap_raw = option_text(parsed, "--round-cap");
    let round_cap =
        if round_cap_raw.bytes().all(|byte| byte.is_ascii_digit()) && !round_cap_raw.is_empty() {
            round_cap_raw.parse::<i64>().ok()
        } else {
            None
        };
    let codex_model_role = option_text(parsed, "--codex-model-role");
    let audit_evaluated = parse_optional_bool(&option_text(parsed, "--audit-evaluated"));
    let escalated_round = parse_optional_bool(&option_text(parsed, "--escalated-round"));
    let escalations: Vec<Value> = parsed
        .values("--escalation")
        .into_iter()
        .map(|value| Value::from(value.to_string_lossy().into_owned()))
        .collect();
    let built = build_record(BuildRecord {
        rater: &rater,
        rater_tool: &rater_tool,
        rater_model: &rater_model,
        design_rating: design_rating.as_ref(),
        implement_rating: implement_rating.as_ref(),
        fallback_rating: fallback.as_ref(),
        changed_paths: &changed_paths,
        floors: &floors,
        panel_skipped: &panel_skipped,
        audit_upgrade: &audit_upgrade,
        escalations: &escalations,
        override_source: &override_source,
        override_tier: &override_tier,
        panel_tier: &panel_tier,
        round_cap,
        codex_model_role: &codex_model_role,
        audit_evaluated,
        escalated_round,
    })?;
    let explicit = MergeExplicit {
        override_source: &override_source,
        audit_upgrade: &audit_upgrade,
        has_escalation: parsed.value("--escalation").is_some(),
        round_cap: &round_cap_raw,
        codex_model_role: &codex_model_role,
        audit_evaluated: &option_text(parsed, "--audit-evaluated"),
        escalated_round: &option_text(parsed, "--escalated-round"),
        override_tier: &override_tier,
        panel_tier: &panel_tier,
    };
    let merged = merge_existing_record_fields(built, &load_record_data(output), &explicit);
    write_record_map(output, &merged)?;
    Ok(merged)
}

fn write_ratings(
    parsed: &ParsedCommandLine,
) -> (
    String,
    String,
    String,
    Option<DifficultyRating>,
    Option<DifficultyRating>,
    Option<DifficultyRating>,
) {
    let rater = {
        let value = option_text(parsed, "--rater");
        if value.is_empty() {
            "fallback".to_owned()
        } else {
            value
        }
    };
    let rater_tool = option_text(parsed, "--rater-tool");
    let rater_model = option_text(parsed, "--rater-model");
    let design_file = option_text(parsed, "--design-raw-rating-file");
    let implement_file = option_text(parsed, "--implement-raw-rating-file");
    let raw_file = option_text(parsed, "--raw-rating-file");
    let mut design_rating = if design_file.is_empty() {
        None
    } else {
        read_rating_file(Path::new(&design_file))
    };
    if design_rating.is_none() {
        let design_tier = option_text(parsed, "--design-tier");
        if !design_tier.is_empty() {
            design_rating =
                rating_from_tier(&design_tier.to_ascii_uppercase(), "design wire metadata");
        }
    }
    let mut implement_rating = if implement_file.is_empty() {
        None
    } else {
        read_rating_file(Path::new(&implement_file))
    };
    let raw_rating = if raw_file.is_empty() {
        None
    } else {
        read_rating_file(Path::new(&raw_file))
    };
    if rater == "design" && design_rating.is_none() {
        design_rating.clone_from(&raw_rating);
    } else if rater == "implement" && implement_rating.is_none() {
        implement_rating.clone_from(&raw_rating);
    } else if rater == "review"
        && let Some(raw) = raw_rating
    {
        implement_rating = Some(raw);
    }
    let fallback_tier = {
        let value = option_text(parsed, "--fallback-tier");
        if value.is_empty() {
            "MODERATE".to_owned()
        } else {
            value
        }
    };
    let fallback_rationale = {
        let value = option_text(parsed, "--fallback-rationale");
        if value.is_empty() {
            "fallback rating synthesized for recovery path".to_owned()
        } else {
            value
        }
    };
    let fallback = if fallback_tier.is_empty() {
        None
    } else {
        rating_from_tier(&fallback_tier.to_ascii_uppercase(), &fallback_rationale)
    };
    (
        rater,
        rater_tool,
        rater_model,
        design_rating,
        implement_rating,
        fallback,
    )
}

fn render_line_inner(path: &Path) -> Result<String, String> {
    let text = read_text(path)?;
    let data: Value = serde_json::from_str(&text).map_err(|error| error.to_string())?;
    let Value::Object(record) = data else {
        return Err("record must be object".to_owned());
    };
    Ok(difficulty_line(&record))
}

fn audit_roll(parsed: &ParsedCommandLine, record_file: &Path) -> Result<Option<i64>, String> {
    if parsed.flag("--no-audit") {
        return Ok(None);
    }
    let raw = option_text(parsed, "--audit-roll");
    if !raw.is_empty() {
        return raw
            .parse::<i64>()
            .map(Some)
            .map_err(|_| "invalid-audit-roll".to_owned());
    }
    if load_record_data(record_file).is_empty() {
        return Ok(Some(AUDIT_DENOMINATOR));
    }
    Ok(Some(sample_audit_roll()))
}

fn sample_audit_roll() -> i64 {
    let mut buffer = [0_u8; 8];
    match fs::File::open("/dev/urandom").and_then(|mut file| file.read_exact(&mut buffer)) {
        Ok(()) => {
            let value = u64::from_le_bytes(buffer);
            i64::try_from(value % u64::try_from(AUDIT_DENOMINATOR).unwrap_or(30) + 1)
                .unwrap_or(AUDIT_DENOMINATOR)
        }
        Err(_) => AUDIT_DENOMINATOR,
    }
}

fn git_changed_paths(repo_root: &Path) -> Result<Vec<String>, String> {
    let runtime = GitCommandRuntime::for_repository(repo_root)
        .map_err(|_| "difficulty refresh could not read changed paths".to_owned())?;
    let head = GitRef::new("HEAD")
        .map_err(|_| "difficulty refresh could not read changed paths".to_owned())?;
    let result = runtime
        .runtime
        .block_on(runtime.git_cli().exact_diff(
            ExactDiffRequest {
                cached: false,
                unified_context: None,
                name_only: true,
                name_status: false,
                quiet: false,
                exit_code: false,
                base: None,
                head: Some(head),
                paths: Vec::new(),
            },
            &runtime.cancellation,
        ))
        .map_err(|_| "difficulty refresh could not read changed paths".to_owned())?;
    Ok(String::from_utf8_lossy(result.output().stdout())
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .map(str::to_owned)
        .collect())
}

fn load_floors() -> Result<Vec<DifficultyFloor>, String> {
    let root = plugin_root_directory().ok_or_else(|| {
        format!("difficulty floor manifest not readable: {FLOOR_MANIFEST_RELPATH}")
    })?;
    load_floor_manifest(&root.join(FLOOR_MANIFEST_RELPATH))
}

fn parse_command(
    arguments: &[OsString],
    options: &[&'static str],
    flags: &[&'static str],
    help: [&str; 3],
    required: &[&str],
    choices: &[(&str, &[&str])],
) -> Result<ParsedCommandLine, ExitCode> {
    let [usage, program, help_text] = help;
    let mut all_flags = vec!["-h", "--help"];
    all_flags.extend_from_slice(flags);
    if let Some(error) = choice_error(arguments, options, choices) {
        return Err(usage_error(usage, program, &error, 2));
    }
    let parsed = parse_with_flags(arguments, options, &all_flags, 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        return match write_stdout(help_text) {
            code if code == ExitCode::SUCCESS => Err(ExitCode::SUCCESS),
            code => Err(code),
        };
    }
    finish_parse(parsed, usage, program, required)
}

fn option_text(parsed: &ParsedCommandLine, name: &str) -> String {
    parsed
        .value(name)
        .map(OsStr::to_string_lossy)
        .map(std::borrow::Cow::into_owned)
        .unwrap_or_default()
}

fn path_value(parsed: &ParsedCommandLine, name: &str) -> PathBuf {
    PathBuf::from(option_text(parsed, name))
}

fn nonempty_path<'a>(parsed: &'a ParsedCommandLine, name: &'a str) -> Option<&'a Path> {
    parsed
        .value(name)
        .filter(|value| !value.is_empty())
        .map(Path::new)
}

fn parse_optional_bool(value: &str) -> Option<bool> {
    match value {
        "true" => Some(true),
        "false" => Some(false),
        _ => None,
    }
}

fn read_text(path: &Path) -> Result<String, String> {
    match fs::read(path) {
        Ok(bytes) => Ok(String::from_utf8_lossy(&bytes).into_owned()),
        Err(error) => Err(python_io_error(&error, path)),
    }
}

fn json_text(value: Option<&Value>) -> String {
    match value {
        Some(Value::String(text)) => text.clone(),
        Some(other) => other.to_string(),
        None => String::new(),
    }
}
