//! Rust owner for the `plan` validation and auto-fix command surface (#8576).
//!
//! Topology row `design.plan_commands.validate`: Tier2+opt-in Tier3.
//!
//! Atomically replaces the Python registrations for `parse-commands`,
//! `validate-commands`, `validate`, `check-size`, `set-oversize-override`,
//! `revise-waterfall`, `auto-fix-commands`, `validator-autofix`,
//! `optional-trailers`, and `compose-goals-test`.

#![allow(
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    clippy::option_if_let_else,
    clippy::assigning_clones,
    clippy::similar_names,
    clippy::map_unwrap_or,
    clippy::collapsible_if,
    clippy::redundant_pub_crate,
    clippy::needless_bool,
    clippy::manual_let_else,
    clippy::redundant_closure,
    clippy::single_match_else,
    clippy::if_same_then_else,
    clippy::manual_range_patterns,
    clippy::collection_is_never_read,
    clippy::bool_to_int_with_if,
    clippy::if_not_else,
    clippy::useless_format,
    clippy::format_push_string
)]

use std::{
    collections::{BTreeMap, HashMap, HashSet},
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::{Command, ExitCode, Stdio},
};

use larch_adapters::validate_design_tmpdir;
use larch_core::{
    DuplicatePolicy, KvDocument, OVERSIZE_OVERRIDE_OPERATOR, ParseOptions, PlanCommandRow,
    ValidationSummary, assess_plan_size, cleanup_cache_sessions_root, compose_plan_goals_test,
    drift_exceeds, drift_ratio_token, emit_kv, parse_final_trailers, parse_optional_metadata,
    parse_plan_commands, redact_secrets, render_plan_command_tsv, set_oversize_override_text,
    tier_valid, trailing_plan_difficulty, trailing_plan_metadata_lines,
};
use regex::Regex;

use crate::{
    argparse_compat::{
        finish_parse, parse_required_with_help, parse_with_flags,
        usage_error as argparse_usage_error,
    },
    oos_commands::atomic_write,
    python_verb::plugin_root_directory,
    runtime_entrypoint::run_verified_larch,
};

const RC2: u8 = 2;
const RC3: u8 = 3;

fn usage(program: &str, usage: &str, error: &str) -> ExitCode {
    argparse_usage_error(usage, program, error, RC2)
}

fn diagnostic(message: &str) {
    eprintln!("{message}");
}

fn plugin_root() -> PathBuf {
    plugin_root_directory().unwrap_or_else(|| PathBuf::from("."))
}

/// Plugin root for sibling plan-quality command modules.
pub(crate) fn plugin_root_for_commands() -> PathBuf {
    plugin_root()
}

fn validated_design_tmpdir(raw: &str) -> Result<PathBuf, String> {
    let tmpdir = env::var_os("TMPDIR");
    let cache_root = cleanup_cache_sessions_root(
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    );
    validate_design_tmpdir(raw, tmpdir.as_deref(), &cache_root)?;
    fs::canonicalize(PathBuf::from(raw)).map_err(|error| error.to_string())
}

/// Design-tmpdir validation for sibling plan-quality command modules.
pub(crate) fn validated_design_tmpdir_for_commands(raw: &str) -> Result<PathBuf, String> {
    validated_design_tmpdir(raw)
}

/// Capture stdout+stderr text and exit code from a finished process.
pub(crate) fn captured_process_text(output: &std::process::Output) -> (i32, String) {
    (
        output.status.code().unwrap_or(1),
        String::from_utf8_lossy(&output.stdout).into_owned()
            + &String::from_utf8_lossy(&output.stderr),
    )
}

fn repo_root_from(start: &Path) -> PathBuf {
    let mut cursor = start.to_path_buf();
    loop {
        if cursor.join(".git").exists() {
            return cursor;
        }
        if !cursor.pop() {
            break;
        }
    }
    env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

/// Repository-root probe for sibling plan-quality command modules.
pub(crate) fn repo_root_from_path(start: &Path) -> PathBuf {
    repo_root_from(start)
}

fn repo_root_for_plan(plan: &Path, explicit: Option<&str>) -> PathBuf {
    if let Some(root) = explicit {
        return PathBuf::from(root)
            .canonicalize()
            .unwrap_or_else(|_| PathBuf::from(root));
    }
    repo_root_from(plan.parent().unwrap_or_else(|| Path::new(".")))
}

fn read_text(path: &Path) -> String {
    fs::read_to_string(path).unwrap_or_else(|_| String::new())
}

fn sha256_text(text: &str) -> String {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(text.as_bytes());
    format!("{:x}", hasher.finalize())
}

/// `plan parse-commands`
pub fn parse_commands(arguments: &[OsString]) -> ExitCode {
    const PROGRAM: &str = "cli.py plan parse-commands";
    const USAGE: &str =
        include_str!("../../../fixtures/rust-parity/plan_quality_help/parse-commands.usage.txt");
    let parsed = match parse_required_with_help(
        arguments,
        PROGRAM,
        USAGE,
        include_str!("../../../fixtures/rust-parity/plan_quality_help/parse-commands.txt"),
        &["--plan-file", "--output", "--repo-root"],
        &[],
        &["--plan-file", "--output"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let plan = PathBuf::from(parsed.value("--plan-file").unwrap_or_default());
    let output = PathBuf::from(parsed.value("--output").unwrap_or_default());
    if !plan.is_file() {
        diagnostic(&format!(
            "parse-commands: plan file missing or unreadable: {}",
            plan.display()
        ));
        return ExitCode::from(RC2);
    }
    let repo = repo_root_for_plan(
        &plan,
        parsed
            .value("--repo-root")
            .map(|value| value.to_string_lossy())
            .as_deref(),
    );
    let plugin = plugin_root();
    let rows = parse_plan_commands(&read_text(&plan), &repo, &plugin);
    if let Err(error) = atomic_write(&output, &render_plan_command_tsv(&rows)) {
        diagnostic(&format!("parse-commands: {error}"));
        return ExitCode::from(RC2);
    }
    ExitCode::SUCCESS
}

fn read_tsv(path: &Path) -> Vec<PlanCommandRow> {
    let mut rows = Vec::new();
    for (idx, line) in read_text(path).lines().enumerate() {
        if idx == 0 {
            continue;
        }
        let mut parts: Vec<&str> = line.split('\t').collect();
        while parts.len() < 7 {
            parts.push("");
        }
        let source_line = parts[1].parse().unwrap_or(0);
        rows.push(PlanCommandRow {
            row_type: parts[0].to_owned(),
            source_line,
            script_path: parts[2].to_owned(),
            flag: parts[3].to_owned(),
            flag_value: parts[4].to_owned(),
            note: parts[5].to_owned(),
            cmd_uid: parts[6].to_owned(),
        });
    }
    rows
}

fn is_repo_script(path: &str) -> bool {
    let mut path = path;
    while let Some(rest) = path.strip_prefix("./") {
        path = rest;
    }
    if path.contains("..") {
        return false;
    }
    path.starts_with("scripts/")
        || (path.starts_with("skills/") && path.contains("/scripts/"))
        || (path.starts_with(".claude/skills/") && path.contains("/scripts/"))
}

fn canonical_script_path(path: &str) -> String {
    let mut path = path.to_owned();
    while path.starts_with("./") {
        path = path[2..].to_owned();
    }
    path
}

fn distinct_flag_in_help(flag: &str, help_text: &str) -> bool {
    let target = format!("--{flag}");
    let mut start = 0;
    while let Some(offset) = help_text[start..].find(&target) {
        let match_start = start + offset;
        let before = if match_start == 0 {
            ' '
        } else {
            help_text.chars().nth(match_start - 1).unwrap_or(' ')
        };
        if match_start > 0 && before.is_ascii_alphanumeric() || before == '_' {
            start = match_start + target.len();
            continue;
        }
        let after = help_text
            .chars()
            .nth(match_start + target.len())
            .unwrap_or('\0');
        if after == '\0'
            || after == '='
            || after.is_whitespace()
            || matches!(after, ')' | ',' | ';' | ':' | ']' | '|')
        {
            return true;
        }
        if after.is_ascii_alphanumeric() || after == '_' || after == '-' {
            start = match_start + target.len();
            continue;
        }
        return true;
    }
    false
}

fn registry_hooks(path: &Path) -> HashMap<String, String> {
    let mut hooks = HashMap::new();
    if !path.is_file() {
        return hooks;
    }
    for (idx, line) in read_text(path).lines().enumerate() {
        if idx == 0 {
            continue;
        }
        let mut parts = line.splitn(2, '\t');
        if let (Some(script), Some(hook)) = (parts.next(), parts.next()) {
            hooks.insert(script.to_owned(), hook.to_owned());
        }
    }
    hooks
}

fn unsafe_token(token: &str) -> bool {
    token.chars().any(|ch| {
        matches!(
            ch,
            '`' | '$' | '*' | '?' | '[' | ']' | ';' | '|' | '&' | '>' | '<' | '(' | ')'
        ) || token.contains("..")
    }) || token.contains("..")
}

fn is_new_script(rows: &[PlanCommandRow], script: &str) -> bool {
    let script = canonical_script_path(script);
    rows.iter().any(|row| {
        row.row_type == "new_script" && canonical_script_path(&row.script_path) == script
    })
}

fn allow_flag(rows: &[PlanCommandRow], script: &str, flag: &str) -> bool {
    let script = canonical_script_path(script);
    rows.iter().any(|row| {
        row.row_type == "updated_flag"
            && canonical_script_path(&row.script_path) == script
            && row.flag == flag
    })
}

fn redact_capture(_repo_root: &Path, text: &str) -> String {
    let clipped: String = text.chars().take(65536).collect();
    redact_secrets(&clipped).text().to_owned()
}

fn resolve_repo_script(
    script: &str,
    repo: &Path,
    plugin: Option<&Path>,
) -> (Option<PathBuf>, String) {
    let mut roots = vec![repo.to_path_buf()];
    if let Some(plugin) = plugin {
        if plugin != repo {
            roots.push(plugin.to_path_buf());
        }
    }
    let mut canonical_seen = false;
    for root in roots {
        let candidate = root.join(script);
        let Ok(resolved) = candidate.canonicalize() else {
            if root.join(script).exists() {
                canonical_seen = true;
            }
            continue;
        };
        if resolved.starts_with(&root) {
            canonical_seen = true;
            if resolved.is_file() {
                return (Some(resolved), String::new());
            }
        }
    }
    (
        None,
        if canonical_seen {
            "missing-script".to_owned()
        } else {
            "non-canonical-path".to_owned()
        },
    )
}

fn validate_plan_command_rows(
    rows: &[PlanCommandRow],
    repo_root: &Path,
    registry: Option<&Path>,
    source_kind: &str,
    help_timeout: f64,
    dry_run_timeout: f64,
    plugin_root: Option<&Path>,
) -> ValidationSummary {
    let repo = repo_root
        .canonicalize()
        .unwrap_or_else(|_| repo_root.to_path_buf());
    let plugin = plugin_root.map(|path| path.canonicalize().unwrap_or_else(|_| path.to_path_buf()));
    let reg = registry
        .map(PathBuf::from)
        .unwrap_or_else(|| repo.join("scripts/dry-runnable-scripts.tsv"));
    let hooks = registry_hooks(&reg);
    let mut log = Vec::new();
    let mut defect_count = 0usize;
    let mut skipped_count = 0usize;
    let mut unsafe_count = 0usize;
    let mut grouped: BTreeMap<(String, String, String), Vec<PlanCommandRow>> = BTreeMap::new();
    let mut noflags: HashSet<(String, String, String)> = HashSet::new();
    for row in rows {
        if row.row_type != "invocation" && row.row_type != "invocation_no_flags" {
            continue;
        }
        let key = (
            row.source_line.to_string(),
            row.cmd_uid.clone(),
            row.script_path.clone(),
        );
        grouped.entry(key.clone()).or_default();
        if row.row_type == "invocation" {
            grouped.get_mut(&key).expect("entry").push(row.clone());
        } else {
            noflags.insert(key);
        }
    }
    let mut help_cache: HashMap<String, (i32, String, bool)> = HashMap::new();
    for ((_line, _uid, script), flags) in &grouped {
        if script.is_empty() || !is_repo_script(script) {
            continue;
        }
        if is_new_script(rows, script) {
            log.push(format!("SKIPPED script={script} reason=new-script"));
            skipped_count += 1;
            continue;
        }
        let (abs_path, existence_defect) = resolve_repo_script(script, &repo, plugin.as_deref());
        let Some(abs_path) = abs_path else {
            log.push(format!("DEFECT script={script} kind={existence_defect}"));
            defect_count += 1;
            continue;
        };
        if !help_cache.contains_key(script) {
            let mut command = Command::new(&abs_path); // lint-subprocess-via-runner: ok plan-command help probes arbitrary consumer scripts without a typed owner
            command.arg("--help").env("LARCH_QUIET_DISABLE", "1");
            let output = command
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .output();
            let (code, text, empty) = match output {
                Ok(output) => {
                    let text = String::from_utf8_lossy(&output.stdout).into_owned()
                        + &String::from_utf8_lossy(&output.stderr);
                    let code = output.status.code().unwrap_or(127);
                    let empty = text.is_empty() || !matches!(code, 0 | 1 | 2);
                    (code, text, empty)
                }
                Err(_) => (127, String::new(), true),
            };
            let _ = help_timeout;
            help_cache.insert(script.clone(), (code, text, empty));
        }
        let (_code, help_text, help_empty) = help_cache.get(script).cloned().unwrap_or_default();
        let help_ok = !help_empty;
        if !help_ok {
            log.push(format!("SKIPPED_FLAG_CHECK script={script} reason=no-help"));
            skipped_count += 1;
        }
        let mut tier2_defect = false;
        for row in flags {
            if help_ok
                && !allow_flag(rows, script, &row.flag)
                && !distinct_flag_in_help(&row.flag, &help_text)
            {
                log.push(format!(
                    "DEFECT script={script} kind=unknown-flag flag={}",
                    row.flag
                ));
                defect_count += 1;
                tier2_defect = true;
            }
        }
        if source_kind == "composed" {
            continue;
        }
        let Some(hook) = hooks.get(script) else {
            continue;
        };
        if hook != "--validate-only" && hook != "LARCH_DRY_RUN=1" {
            log.push(format!(
                "DEFECT script={script} kind=unknown-registry-hook hook={hook}"
            ));
            defect_count += 1;
            continue;
        }
        if tier2_defect {
            continue;
        }
        let mut argv = vec![abs_path.display().to_string()];
        for row in flags {
            argv.push(format!("--{}", row.flag));
            if !row.flag_value.is_empty() {
                argv.push(row.flag_value.clone());
            }
        }
        if argv.iter().any(|token| unsafe_token(token)) {
            log.push(format!(
                "DEFECT script={script} kind=unsafe-token token=<redacted>"
            ));
            defect_count += 1;
            unsafe_count += 1;
            continue;
        }
        let mut command = Command::new(&argv[0]); // lint-subprocess-via-runner: ok plan-command dry-run probes arbitrary consumer scripts without a typed owner
        command.args(&argv[1..]).current_dir(&repo);
        command.env_clear();
        for key in ["PATH", "HOME", "TMPDIR", "USER", "LOGNAME", "LANG"] {
            if let Ok(value) = env::var(key) {
                if key != "LANG" || !value.is_empty() {
                    command.env(key, value);
                }
            }
        }
        if env::var("TMPDIR").is_err() {
            command.env("TMPDIR", "/tmp");
        }
        if hook == "--validate-only" {
            command.arg("--validate-only");
        } else {
            command.env("LARCH_DRY_RUN", "1");
        }
        let _ = dry_run_timeout;
        let (dry_rc, cap) = match command.output() {
            Ok(output) => captured_process_text(&output),
            Err(_) => (127, String::new()),
        };
        log.push(format!("TIER3_CAPTURE script={script} exit={dry_rc}"));
        log.push(if cap.is_empty() {
            "(empty capture)".to_owned()
        } else {
            redact_capture(&repo, &cap)
        });
        if dry_rc != 0 {
            log.push(format!(
                "DEFECT script={script} kind=dry-run-failed exit={dry_rc}"
            ));
            defect_count += 1;
        }
    }
    let status = if defect_count > 0 {
        "defects-found"
    } else {
        "ok"
    };
    let summary = format!(
        "VALIDATE_STATUS={status}\tDEFECT_COUNT={defect_count}\tSKIPPED_COUNT={skipped_count}\tUNSAFE_TOKEN_COUNT={unsafe_count}"
    );
    log.push(summary);
    ValidationSummary {
        status: status.to_owned(),
        defect_count,
        skipped_count,
        unsafe_token_count: unsafe_count,
        log_text: log.join("\n") + "\n",
    }
}

/// `plan validate-commands`
pub fn validate_commands(arguments: &[OsString]) -> ExitCode {
    const PROGRAM: &str = "cli.py plan validate-commands";
    const USAGE: &str =
        include_str!("../../../fixtures/rust-parity/plan_quality_help/validate-commands.usage.txt");
    if let Some(error) = crate::argparse_compat::choice_error(
        arguments,
        &[
            "--tsv-file",
            "--log-file",
            "--dry-runnable-registry",
            "--source-kind",
            "--help-timeout",
            "--dry-run-timeout",
            "--repo-root",
        ],
        &[("--source-kind", &["plan", "composed"])],
    ) {
        return usage(PROGRAM, USAGE, &error);
    }
    let parsed = match parse_required_with_help(
        arguments,
        PROGRAM,
        USAGE,
        include_str!("../../../fixtures/rust-parity/plan_quality_help/validate-commands.txt"),
        &[
            "--tsv-file",
            "--log-file",
            "--dry-runnable-registry",
            "--source-kind",
            "--help-timeout",
            "--dry-run-timeout",
            "--repo-root",
        ],
        &[],
        &["--tsv-file", "--log-file"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let tsv = PathBuf::from(parsed.value("--tsv-file").unwrap_or_default());
    let log_file = PathBuf::from(parsed.value("--log-file").unwrap_or_default());
    if !tsv.is_file() {
        diagnostic(&format!(
            "validate-commands: unreadable TSV: {}",
            tsv.display()
        ));
        return ExitCode::from(RC2);
    }
    let repo = repo_root_for_plan(
        tsv.parent().unwrap_or_else(|| Path::new(".")),
        parsed
            .value("--repo-root")
            .map(|value| value.to_string_lossy())
            .as_deref(),
    );
    let source_kind = parsed
        .value("--source-kind")
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_else(|| "plan".to_owned());
    let help_timeout = parsed
        .value("--help-timeout")
        .and_then(|value| value.to_string_lossy().parse().ok())
        .unwrap_or(10.0);
    let dry_run_timeout = parsed
        .value("--dry-run-timeout")
        .and_then(|value| value.to_string_lossy().parse().ok())
        .unwrap_or(10.0);
    let registry = parsed
        .value("--dry-runnable-registry")
        .map(|value| PathBuf::from(value));
    let summary = validate_plan_command_rows(
        &read_tsv(&tsv),
        &repo,
        registry.as_deref(),
        &source_kind,
        help_timeout,
        dry_run_timeout,
        Some(&plugin_root()),
    );
    if let Err(error) = atomic_write(&log_file, &summary.log_text) {
        diagnostic(&format!("validate-commands: {error}"));
        return ExitCode::from(RC2);
    }
    println!(
        "VALIDATE_STATUS={}\tDEFECT_COUNT={}\tSKIPPED_COUNT={}\tUNSAFE_TOKEN_COUNT={}",
        summary.status, summary.defect_count, summary.skipped_count, summary.unsafe_token_count
    );
    ExitCode::SUCCESS
}

fn plan_validation_outcome(
    summary: &ValidationSummary,
    difficulty_defects: usize,
    plan_text: &str,
    require_executable_facets: bool,
) -> (String, usize, String) {
    let facet_defects = if require_executable_facets {
        larch_core::design::validate_plan_facets(plan_text).defects
    } else {
        Vec::new()
    };
    let total = summary.defect_count + difficulty_defects + facet_defects.len();
    let status = if total > 0 {
        "defects-found".to_owned()
    } else {
        summary.status.clone()
    };
    let mut log_text = summary.log_text.clone();
    if difficulty_defects > 0 {
        log_text.push_str("DEFECT plan kind=difficulty-metadata\n");
    }
    for token in facet_defects {
        log_text.push_str(&format!(
            "DEFECT plan kind=executable-plan-contract token={token}\n"
        ));
    }
    (status, total, log_text)
}

/// `plan validate`
pub fn validate(arguments: &[OsString]) -> ExitCode {
    const PROGRAM: &str = "cli.py plan validate";
    const USAGE: &str =
        include_str!("../../../fixtures/rust-parity/plan_quality_help/validate.usage.txt");
    if let Some(error) = crate::argparse_compat::choice_error(
        arguments,
        &[
            "--plan-file",
            "--repo-root",
            "--source-kind",
            "--design-tmpdir",
        ],
        &[("--source-kind", &["plan", "composed"])],
    ) {
        return usage(PROGRAM, USAGE, &error);
    }
    let parsed = match parse_required_with_help(
        arguments,
        PROGRAM,
        USAGE,
        include_str!("../../../fixtures/rust-parity/plan_quality_help/validate.txt"),
        &[
            "--plan-file",
            "--repo-root",
            "--source-kind",
            "--design-tmpdir",
        ],
        &["--require-executable-facets"],
        &["--plan-file"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let plan = PathBuf::from(parsed.value("--plan-file").unwrap_or_default());
    if !plan.is_file() {
        diagnostic(&format!(
            "validate: unreadable plan file: {}",
            plan.display()
        ));
        return ExitCode::from(RC2);
    }
    let repo = repo_root_for_plan(
        &plan,
        parsed
            .value("--repo-root")
            .map(|value| value.to_string_lossy())
            .as_deref(),
    );
    let plugin = plugin_root();
    let source_kind = parsed
        .value("--source-kind")
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_else(|| {
            if plan.file_name().and_then(|name| name.to_str()) == Some("composed-plan.md") {
                "composed".to_owned()
            } else {
                "plan".to_owned()
            }
        });
    let plan_text = read_text(&plan);
    let rows = parse_plan_commands(&plan_text, &repo, &plugin);
    let summary =
        validate_plan_command_rows(&rows, &repo, None, &source_kind, 10.0, 10.0, Some(&plugin));
    let mut difficulty_defects = 0usize;
    for raw in trailing_plan_metadata_lines(&plan_text) {
        if let Some(value) = raw.strip_prefix("difficulty:") {
            if !tier_valid(value.trim()) {
                difficulty_defects = 1;
                break;
            }
        }
    }
    if difficulty_defects == 0
        && env::var("LARCH_REQUIRE_PLAN_DIFFICULTY").ok().as_deref() == Some("1")
        && trailing_plan_difficulty(&plan_text).is_empty()
    {
        difficulty_defects = 1;
    }
    let (status, total, log_text) = plan_validation_outcome(
        &summary,
        difficulty_defects,
        &plan_text,
        parsed.flag("--require-executable-facets"),
    );
    emit_kv("VALIDATE_STATUS", &status);
    emit_kv("VALIDATE_DEFECT_COUNT", &total.to_string());
    emit_kv("VALIDATE_SKIPPED_COUNT", &summary.skipped_count.to_string());
    emit_kv(
        "VALIDATE_UNSAFE_TOKEN_COUNT",
        &summary.unsafe_token_count.to_string(),
    );
    let design_tmpdir_raw = parsed
        .value("--design-tmpdir")
        .map(|value| value.to_string_lossy().into_owned())
        .or_else(|| env::var("DESIGN_TMPDIR").ok())
        .unwrap_or_default();
    let log_path =
        if !design_tmpdir_raw.is_empty() && validated_design_tmpdir(&design_tmpdir_raw).is_ok() {
            let design_tmpdir = PathBuf::from(&design_tmpdir_raw)
                .canonicalize()
                .unwrap_or_else(|_| PathBuf::from(&design_tmpdir_raw));
            let path = design_tmpdir.join("validate-plan-commands.log");
            let _ = atomic_write(&path, &log_text);
            path
        } else {
            let tmp = env::temp_dir().join(format!(
                "larch-validate-plan-commands.log.{}",
                std::process::id()
            ));
            let _ = fs::write(&tmp, &log_text);
            tmp
        };
    emit_kv("VALIDATE_LOG_FILE", &log_path.display().to_string());
    ExitCode::SUCCESS
}

fn validate_optional_trailer_keys_preserved(plan_file: &Path, keys_file: &Path) -> bool {
    let meta = parse_optional_metadata(&read_text(plan_file));
    let expected: Vec<String> = read_text(keys_file)
        .lines()
        .filter(|line| !line.is_empty())
        .map(str::to_owned)
        .collect();
    expected
        .iter()
        .all(|key| meta.keys.iter().any(|item| item == key))
}

fn validate_optional_trailers_preserved(plan_file: &Path, values_file: &Path) -> bool {
    let values_path = values_file.to_path_buf();
    let (keys_path, values_path) = if values_path
        .file_name()
        .and_then(|name| name.to_str())
        .is_some_and(|name| name.ends_with(".values"))
    {
        let keys = PathBuf::from(
            values_path
                .to_string_lossy()
                .trim_end_matches(".values")
                .to_owned(),
        );
        (keys, values_path)
    } else {
        let values = PathBuf::from(format!("{}.values", values_path.display()));
        (values_path, values)
    };
    if !validate_optional_trailer_keys_preserved(plan_file, &keys_path) {
        return false;
    }
    if values_path.is_file() {
        let current = parse_optional_metadata(&read_text(plan_file))
            .values
            .join("\n");
        let current = if current.is_empty() {
            String::new()
        } else {
            current + "\n"
        };
        return read_text(&values_path) == current;
    }
    true
}

/// `plan optional-trailers`
pub fn optional_trailers(arguments: &[OsString]) -> ExitCode {
    if arguments.is_empty() {
        eprintln!(
            "{}\ncli.py plan optional-trailers: error: the following arguments are required: cmd",
            include_str!(
                "../../../fixtures/rust-parity/plan_quality_help/optional-trailers.usage.txt"
            )
        );
        return ExitCode::from(RC2);
    }
    let sub = arguments[0].to_string_lossy().into_owned();
    let rest = &arguments[1..];
    match sub.as_str() {
        "parse" | "keys" | "values" | "has-key" | "snapshot-keys" | "snapshot-values"
        | "validate-keys" | "validate-values" => {}
        "-h" | "--help" => {
            print!(
                "{}",
                include_str!(
                    "../../../fixtures/rust-parity/plan_quality_help/optional-trailers.txt"
                )
            );
            return ExitCode::SUCCESS;
        }
        other => {
            eprintln!("cli.py plan optional-trailers: invalid choice: '{other}'");
            return ExitCode::from(RC2);
        }
    }
    let program = format!("cli.py plan optional-trailers {sub}");
    let (options, flags, required) = match sub.as_str() {
        "has-key" => (
            ["--plan-file", "--key"].as_slice(),
            [].as_slice(),
            ["--plan-file", "--key"].as_slice(),
        ),
        "snapshot-keys" | "snapshot-values" => (
            ["--plan-file", "--output"].as_slice(),
            [].as_slice(),
            ["--plan-file", "--output"].as_slice(),
        ),
        "validate-keys" => (
            ["--plan-file", "--keys-file"].as_slice(),
            [].as_slice(),
            ["--plan-file", "--keys-file"].as_slice(),
        ),
        "validate-values" => (
            ["--plan-file", "--values-file"].as_slice(),
            [].as_slice(),
            ["--plan-file", "--values-file"].as_slice(),
        ),
        _ => (
            ["--plan-file"].as_slice(),
            [].as_slice(),
            ["--plan-file"].as_slice(),
        ),
    };
    let usage = format!("usage: {program} [-h]");
    let parsed = match finish_parse(
        parse_with_flags(rest, options, flags, 0),
        &usage,
        &program,
        required,
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let plan = PathBuf::from(parsed.value("--plan-file").unwrap_or_default());
    let meta = parse_optional_metadata(&read_text(&plan));
    match sub.as_str() {
        "parse" => {
            println!("{}", meta.metadata_trailer_lines);
            println!("{}", meta.diff_added.as_deref().unwrap_or("-"));
            println!("{}", meta.diff_deleted.as_deref().unwrap_or("-"));
            println!("{}", meta.mechanical_churn);
            println!("{}", meta.oversize_override.as_deref().unwrap_or("-"));
            ExitCode::SUCCESS
        }
        "keys" => {
            println!("{}", meta.keys.join("\n"));
            ExitCode::SUCCESS
        }
        "values" => {
            println!("{}", meta.values.join("\n"));
            ExitCode::SUCCESS
        }
        "has-key" => {
            let key = parsed.value("--key").unwrap_or_default().to_string_lossy();
            if meta.keys.iter().any(|item| item == &key) {
                ExitCode::SUCCESS
            } else {
                ExitCode::FAILURE
            }
        }
        "snapshot-keys" => {
            let output = PathBuf::from(parsed.value("--output").unwrap_or_default());
            let text = if meta.keys.is_empty() {
                String::new()
            } else {
                meta.keys.join("\n") + "\n"
            };
            let val_text = if meta.values.is_empty() {
                String::new()
            } else {
                meta.values.join("\n") + "\n"
            };
            let _ = atomic_write(&output, &text);
            let _ = atomic_write(
                &PathBuf::from(format!("{}.values", output.display())),
                &val_text,
            );
            ExitCode::SUCCESS
        }
        "snapshot-values" => {
            let output = PathBuf::from(parsed.value("--output").unwrap_or_default());
            let text = if meta.values.is_empty() {
                String::new()
            } else {
                meta.values.join("\n") + "\n"
            };
            let _ = atomic_write(&output, &text);
            ExitCode::SUCCESS
        }
        "validate-keys" => {
            let keys = PathBuf::from(parsed.value("--keys-file").unwrap_or_default());
            if validate_optional_trailer_keys_preserved(&plan, &keys) {
                ExitCode::SUCCESS
            } else {
                ExitCode::FAILURE
            }
        }
        "validate-values" => {
            let values = PathBuf::from(parsed.value("--values-file").unwrap_or_default());
            if validate_optional_trailers_preserved(&plan, &values) {
                ExitCode::SUCCESS
            } else {
                ExitCode::FAILURE
            }
        }
        _ => ExitCode::from(RC2),
    }
}

fn authority_path(design_tmpdir: &Path) -> PathBuf {
    design_tmpdir.join(".gate-b-oversize-override.sha256")
}

fn trusted_oversize_override(design_tmpdir: &Path, plan_text: &str) -> Option<String> {
    let meta = parse_optional_metadata(plan_text);
    if meta.oversize_override.as_deref() != Some(OVERSIZE_OVERRIDE_OPERATOR) {
        return None;
    }
    let path = authority_path(design_tmpdir);
    if !path.is_file() || path.is_symlink() {
        return None;
    }
    let token = read_text(&path).trim().to_owned();
    if token == sha256_text(plan_text) {
        Some(OVERSIZE_OVERRIDE_OPERATOR.to_owned())
    } else {
        None
    }
}

fn sync_oversize_override_authority(design_tmpdir: &Path, plan: &Path) {
    let plan_text = read_text(plan);
    let path = authority_path(design_tmpdir);
    if parse_optional_metadata(&plan_text)
        .oversize_override
        .as_deref()
        == Some(OVERSIZE_OVERRIDE_OPERATOR)
    {
        let _ = atomic_write(&path, &(sha256_text(&plan_text) + "\n"));
    } else {
        let _ = fs::remove_file(&path);
    }
}

fn canonical_plan_for_override(
    design_tmpdir: &Path,
    plan_file: Option<&str>,
) -> Result<PathBuf, String> {
    let plan = plan_file
        .map(PathBuf::from)
        .unwrap_or_else(|| design_tmpdir.join("plan.txt"));
    let plan = plan.canonicalize().map_err(|error| error.to_string())?;
    if plan.to_string_lossy().contains(['\n', '\r']) {
        return Err("path contains CR/LF".to_owned());
    }
    if !plan.is_file() || plan.is_symlink() {
        return Err("--plan-file must name a regular non-symlink file".to_owned());
    }
    plan.strip_prefix(design_tmpdir)
        .map_err(|_| "plan file escapes design tmpdir".to_owned())?;
    Ok(plan)
}

/// `plan set-oversize-override`
pub fn set_oversize_override(arguments: &[OsString]) -> ExitCode {
    const PROGRAM: &str = "cli.py plan set-oversize-override";
    const USAGE: &str = include_str!(
        "../../../fixtures/rust-parity/plan_quality_help/set-oversize-override.usage.txt"
    );
    let parsed = match parse_required_with_help(
        arguments,
        PROGRAM,
        USAGE,
        include_str!("../../../fixtures/rust-parity/plan_quality_help/set-oversize-override.txt"),
        &["--design-tmpdir", "--plan-file"],
        &["--remove"],
        &["--design-tmpdir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let raw = parsed
        .value("--design-tmpdir")
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned();
    let design_tmpdir = match validated_design_tmpdir(&raw) {
        Ok(path) => path,
        Err(message) => {
            diagnostic(&format!("set-oversize-override: {message}"));
            return ExitCode::from(RC2);
        }
    };
    let remove = parsed.flag("--remove");
    let plan_file = parsed
        .value("--plan-file")
        .map(|value| value.to_string_lossy().into_owned());
    match (|| -> Result<(), String> {
        let plan = canonical_plan_for_override(&design_tmpdir, plan_file.as_deref())?;
        let original = read_text(&plan);
        let updated = set_oversize_override_text(&original, remove)?;
        if updated != original {
            atomic_write(&plan, &updated)?;
        }
        sync_oversize_override_authority(&design_tmpdir, &plan);
        Ok(())
    })() {
        Ok(()) => {
            emit_kv(
                "OVERSIZE_OVERRIDE",
                if remove {
                    ""
                } else {
                    OVERSIZE_OVERRIDE_OPERATOR
                },
            );
            ExitCode::SUCCESS
        }
        Err(error) => {
            diagnostic(&format!("set-oversize-override: {error}"));
            ExitCode::from(RC2)
        }
    }
}

fn drift_baseline_write_once(design_tmpdir: &Path, plan_lines: i64, diff_lines: i64) -> bool {
    match run_verified_larch(&[
        OsString::from("plan-review"),
        OsString::from("drift-baseline"),
        OsString::from("write-once"),
        OsString::from("--design-tmpdir"),
        design_tmpdir.as_os_str().to_owned(),
        OsString::from("--plan-lines"),
        OsString::from(plan_lines.to_string()),
        OsString::from("--diff-lines"),
        OsString::from(diff_lines.to_string()),
    ]) {
        Ok(output) => output.status().success(),
        Err(_) => false,
    }
}

fn plan_counts_from_file(path: &Path) -> Option<(i64, i64)> {
    if !path.is_file() || path.is_symlink() {
        return None;
    }
    let trailers = parse_final_trailers(&read_text(path), true);
    let diff_lines = trailers.diff_lines()?;
    Some((
        i64::try_from(trailers.start_line.saturating_sub(1)).unwrap_or(0),
        diff_lines,
    ))
}

/// `plan check-size`
pub fn check_size(arguments: &[OsString]) -> ExitCode {
    const PROGRAM: &str = "cli.py plan check-size";
    const USAGE: &str =
        include_str!("../../../fixtures/rust-parity/plan_quality_help/check-size.usage.txt");
    let parsed = match parse_required_with_help(
        arguments,
        PROGRAM,
        USAGE,
        include_str!("../../../fixtures/rust-parity/plan_quality_help/check-size.txt"),
        &["--design-tmpdir", "--plan-file"],
        &[],
        &["--design-tmpdir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let raw = parsed
        .value("--design-tmpdir")
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned();
    let design_tmpdir = match validated_design_tmpdir(&raw) {
        Ok(path) => path,
        Err(message) => {
            diagnostic(&format!("check-size: {message}"));
            return ExitCode::from(RC3);
        }
    };
    if !design_tmpdir.is_dir() {
        diagnostic("check-size: --design-tmpdir must be a directory");
        return ExitCode::from(RC3);
    }
    let plan = parsed
        .value("--plan-file")
        .map(|value| PathBuf::from(value))
        .unwrap_or_else(|| design_tmpdir.join("plan.txt"));
    let plan = plan.canonicalize().unwrap_or(plan);
    if !plan.is_file() {
        emit_kv("PLAN_SIZE_STATUS", "missing-plan");
        return ExitCode::from(RC2);
    }
    let text = read_text(&plan);
    let trailers = parse_final_trailers(&text, true);
    let Some(diff_lines) = trailers.diff_lines() else {
        emit_kv("PLAN_SIZE_STATUS", "missing-diff-lines");
        return ExitCode::from(RC2);
    };
    let meta = parse_optional_metadata(&text);
    if meta.mechanical_churn != "true" && meta.mechanical_churn != "false" {
        emit_kv("PLAN_SIZE_STATUS", "invalid-mechanical-churn");
        return ExitCode::from(RC2);
    }
    let trusted_oversize = trusted_oversize_override(&design_tmpdir, &text);
    let plan_lines = i64::try_from(trailers.start_line.saturating_sub(1)).unwrap_or(0);
    let multiple_text = env::var("LARCH_DESIGN_DRIFT_MULTIPLE").unwrap_or_else(|_| "2".to_owned());
    let multiple = multiple_text
        .parse::<i64>()
        .ok()
        .filter(|value| *value > 0)
        .unwrap_or(2);
    let baseline_path = design_tmpdir.join("drift-baseline.env");
    let marker = design_tmpdir.join(".drift-baseline-unreadable");
    let mut baseline_plan = 0i64;
    let mut baseline_diff = 0i64;
    let mut baseline_display_plan = String::new();
    let mut baseline_display_diff = String::new();
    let mut trusted = false;
    let mut drift_trigger = false;
    let recover = |baseline_plan: &mut i64,
                   baseline_diff: &mut i64,
                   baseline_display_plan: &mut String,
                   baseline_display_diff: &mut String,
                   trusted: &mut bool|
     -> bool {
        let Some((plan_count, diff_count)) =
            plan_counts_from_file(&design_tmpdir.join("plan.txt-original"))
        else {
            return false;
        };
        *baseline_plan = plan_count;
        *baseline_diff = diff_count;
        *baseline_display_plan = plan_count.to_string();
        *baseline_display_diff = diff_count.to_string();
        *trusted = true;
        true
    };
    if baseline_path.is_file() && !baseline_path.is_symlink() {
        let raw = read_text(&baseline_path);
        let data = KvDocument::parse(&raw, ParseOptions::legacy())
            .map(|document| document.select(DuplicatePolicy::Last))
            .unwrap_or_default();
        if data
            .get("BASELINE_PLAN_LINES")
            .is_some_and(|value| value.chars().all(|ch| ch.is_ascii_digit()))
            && data
                .get("BASELINE_DIFF_LINES")
                .is_some_and(|value| value.chars().all(|ch| ch.is_ascii_digit()))
        {
            baseline_plan = data["BASELINE_PLAN_LINES"].parse().unwrap_or(0);
            baseline_diff = data["BASELINE_DIFF_LINES"].parse().unwrap_or(0);
            baseline_display_plan = baseline_plan.to_string();
            baseline_display_diff = baseline_diff.to_string();
            trusted = true;
            let _ = fs::remove_file(&marker);
        } else if recover(
            &mut baseline_plan,
            &mut baseline_diff,
            &mut baseline_display_plan,
            &mut baseline_display_diff,
            &mut trusted,
        ) {
            emit_kv(
                "WARN",
                "check-plan-size: drift baseline unreadable; recovered anchor from plan.txt-original",
            );
            if !drift_baseline_write_once(&design_tmpdir, baseline_plan, baseline_diff) {
                emit_kv(
                    "WARN",
                    "check-plan-size: could not write drift baseline; proceeding without drift trigger",
                );
                trusted = false;
            } else {
                let _ = fs::remove_file(&marker);
            }
        } else {
            emit_kv(
                "WARN",
                "check-plan-size: drift baseline unreadable; failing closed on drift trigger",
            );
            let _ = atomic_write(&marker, "unreadable\n");
            drift_trigger = true;
        }
    } else if baseline_path.exists() || baseline_path.is_symlink() || marker.exists() {
        if baseline_path.is_file() && !baseline_path.is_symlink() {
            let _ = fs::remove_file(&baseline_path);
        }
        if recover(
            &mut baseline_plan,
            &mut baseline_diff,
            &mut baseline_display_plan,
            &mut baseline_display_diff,
            &mut trusted,
        ) {
            emit_kv(
                "WARN",
                "check-plan-size: drift baseline unreadable; recovered anchor from plan.txt-original",
            );
            if !drift_baseline_write_once(&design_tmpdir, baseline_plan, baseline_diff) {
                emit_kv(
                    "WARN",
                    "check-plan-size: could not write drift baseline; proceeding without drift trigger",
                );
                trusted = false;
            } else {
                let _ = fs::remove_file(&marker);
            }
        } else {
            emit_kv(
                "WARN",
                "check-plan-size: drift baseline unreadable; failing closed on drift trigger",
            );
            let _ = atomic_write(&marker, "unreadable\n");
            drift_trigger = true;
        }
    } else if recover(
        &mut baseline_plan,
        &mut baseline_diff,
        &mut baseline_display_plan,
        &mut baseline_display_diff,
        &mut trusted,
    ) {
        if !drift_baseline_write_once(&design_tmpdir, baseline_plan, baseline_diff) {
            emit_kv(
                "WARN",
                "check-plan-size: could not write drift baseline; proceeding without drift trigger",
            );
            trusted = false;
        }
    } else {
        baseline_plan = plan_lines;
        baseline_diff = diff_lines;
        baseline_display_plan = plan_lines.to_string();
        baseline_display_diff = diff_lines.to_string();
        trusted = true;
        if !drift_baseline_write_once(&design_tmpdir, plan_lines, diff_lines) {
            emit_kv(
                "WARN",
                "check-plan-size: could not write drift baseline; proceeding without drift trigger",
            );
            trusted = false;
        }
    }
    if !drift_trigger && trusted {
        drift_trigger = drift_exceeds(plan_lines, baseline_plan, multiple)
            || drift_exceeds(diff_lines, baseline_diff, multiple);
    }
    let drift_plan_ratio = if trusted {
        drift_ratio_token(plan_lines, baseline_plan)
    } else {
        "inf".to_owned()
    };
    let drift_diff_ratio = if trusted {
        drift_ratio_token(diff_lines, baseline_diff)
    } else {
        "inf".to_owned()
    };
    let assessment = assess_plan_size(
        &meta,
        &text,
        usize::try_from(plan_lines).unwrap_or(0),
        diff_lines,
        trusted_oversize.as_deref(),
    );
    emit_kv(
        "DRIFT_TRIGGER_FIRED",
        if drift_trigger { "true" } else { "false" },
    );
    emit_kv("DRIFT_MULTIPLE", &multiple.to_string());
    emit_kv("DRIFT_PLAN_RATIO", &drift_plan_ratio);
    emit_kv("DRIFT_DIFF_RATIO", &drift_diff_ratio);
    emit_kv("BASELINE_PLAN_LINES", &baseline_display_plan);
    emit_kv("BASELINE_DIFF_LINES", &baseline_display_diff);
    emit_kv(
        "SIZE_TRIGGER_FIRED",
        if assessment.override_suppressed {
            "false"
        } else if assessment.reasons.is_empty() {
            "false"
        } else {
            "true"
        },
    );
    emit_kv("TRIGGER_REASONS", &assessment.reasons.join(","));
    emit_kv("PLAN_LINES", &plan_lines.to_string());
    emit_kv("DIFF_LINES", &diff_lines.to_string());
    emit_kv("DIFF_ADDED", meta.diff_added.as_deref().unwrap_or(""));
    emit_kv("DIFF_DELETED", meta.diff_deleted.as_deref().unwrap_or(""));
    emit_kv("MECHANICAL_CHURN", &meta.mechanical_churn);
    emit_kv("FIRM_HEADINGS", &assessment.firm_headings.to_string());
    emit_kv("SURFACES_TOUCHED", &assessment.surfaces.to_string());
    emit_kv(
        "OVERSIZE_OVERRIDE",
        trusted_oversize.as_deref().unwrap_or(""),
    );
    emit_kv(
        "SOFT_ADVISORY",
        if assessment.soft || assessment.override_suppressed {
            "true"
        } else {
            "false"
        },
    );
    emit_kv("PLAN_SIZE_STATUS", "ok");
    ExitCode::SUCCESS
}

/// `plan compose-goals-test`
pub fn compose_goals_test(arguments: &[OsString]) -> ExitCode {
    const PROGRAM: &str = "cli.py plan compose-goals-test";
    const USAGE: &str = include_str!(
        "../../../fixtures/rust-parity/plan_quality_help/compose-goals-test.usage.txt"
    );
    let parsed = match parse_required_with_help(
        arguments,
        PROGRAM,
        USAGE,
        include_str!("../../../fixtures/rust-parity/plan_quality_help/compose-goals-test.txt"),
        &["--plan-file", "--goal-text"],
        &[],
        &["--plan-file"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let plan = PathBuf::from(parsed.value("--plan-file").unwrap_or_default());
    if !plan.is_file() {
        diagnostic(&format!("ERROR=plan file not found: {}", plan.display()));
        return ExitCode::from(RC2);
    }
    let data = match fs::read(&plan) {
        Ok(data) => data,
        Err(_) => {
            diagnostic(&format!("ERROR=plan file not found: {}", plan.display()));
            return ExitCode::from(RC2);
        }
    };
    if data.is_empty() {
        diagnostic(&format!("ERROR=plan file is empty: {}", plan.display()));
        return ExitCode::from(RC2);
    }
    if data.len() < 64 {
        diagnostic(&format!(
            "ERROR=plan file is too short: {} ({} bytes)",
            plan.display(),
            data.len()
        ));
        return ExitCode::from(RC2);
    }
    let text = String::from_utf8_lossy(&data);
    let first = text
        .lines()
        .map(str::trim)
        .find(|line| !line.is_empty())
        .unwrap_or("")
        .to_ascii_lowercase();
    let pointer = Regex::new(r"^(see plan\.txt|see attached|see linked|tbd|todo)\.?$")
        .expect("pointer regex");
    if pointer.is_match(&first) {
        diagnostic(&format!(
            "ERROR=plan file is a pointer-only placeholder: {}",
            plan.display()
        ));
        return ExitCode::from(RC2);
    }
    let goal = parsed
        .value("--goal-text")
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default();
    print!("{}", compose_plan_goals_test(&text, &goal));
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        os::unix::fs::PermissionsExt,
        sync::atomic::{AtomicU64, Ordering},
        time::{SystemTime, UNIX_EPOCH},
    };

    fn unique_root(label: &str) -> PathBuf {
        static COUNTER: AtomicU64 = AtomicU64::new(0);
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|duration| duration.as_nanos())
            .unwrap_or(0);
        let root = PathBuf::from("/tmp").join(format!(
            "larch-pq-{label}-{}-{nanos}-{n}",
            std::process::id()
        ));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(&root).expect("create root");
        root
    }

    fn write_exec(path: &Path, body: &str) {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("mkdir");
        }
        fs::write(path, body).expect("write");
        let mut perms = fs::metadata(path).expect("meta").permissions();
        perms.set_mode(0o755);
        fs::set_permissions(path, perms).expect("chmod");
    }

    fn mini_plan() -> &'static str {
        "### NEW: fixture\n\n1. Touch `scripts/noop.sh`.\n\ndifficulty: HARD\nmechanical_churn: false\ndiff_lines: 1\n"
    }

    #[test]
    fn helper_path_and_flag_utilities() {
        assert!(is_repo_script("scripts/a.sh"));
        assert!(is_repo_script("./scripts/a.sh"));
        assert!(is_repo_script("skills/x/scripts/a.sh"));
        assert!(is_repo_script(".claude/skills/x/scripts/a.sh"));
        assert!(!is_repo_script("../scripts/a.sh"));
        assert!(!is_repo_script("docs/a.sh"));
        assert_eq!(canonical_script_path("././scripts/a.sh"), "scripts/a.sh");
        assert!(distinct_flag_in_help("foo", "usage --foo bar"));
        assert!(distinct_flag_in_help("foo", "flags: --foo, --bar"));
        assert!(!distinct_flag_in_help("foo", "prefix--foo-bar"));
        assert!(!distinct_flag_in_help("zzz", "no flags here"));
        assert!(unsafe_token("a`b"));
        assert!(unsafe_token("../x"));
        assert!(!unsafe_token("safe-value"));

        let rows = vec![
            PlanCommandRow {
                row_type: "new_script".into(),
                source_line: 1,
                script_path: "./scripts/new.sh".into(),
                flag: String::new(),
                flag_value: String::new(),
                note: String::new(),
                cmd_uid: "u1".into(),
            },
            PlanCommandRow {
                row_type: "updated_flag".into(),
                source_line: 2,
                script_path: "scripts/old.sh".into(),
                flag: "verbose".into(),
                flag_value: String::new(),
                note: String::new(),
                cmd_uid: "u2".into(),
            },
        ];
        assert!(is_new_script(&rows, "scripts/new.sh"));
        assert!(allow_flag(&rows, "./scripts/old.sh", "verbose"));
        assert!(!allow_flag(&rows, "scripts/old.sh", "quiet"));
        assert_eq!(
            redact_capture(Path::new("/tmp"), &"x".repeat(10)),
            "x".repeat(10)
        );
        assert_eq!(sha256_text("abc").len(), 64);

        let root = unique_root("helpers");
        let nested = root.join("sub").join("leaf");
        fs::create_dir_all(&nested).expect("nested");
        fs::write(nested.join(".git"), "gitdir: ..\n").expect("git marker");
        assert_eq!(repo_root_from(&nested), nested);
        assert_eq!(
            repo_root_for_plan(&nested.join("plan.txt"), Some(root.to_str().unwrap())),
            root.canonicalize().unwrap_or_else(|_| root.clone())
        );
        let _ = fs::remove_dir_all(&root);
    }

    #[test]
    fn read_tsv_registry_and_resolve_script() {
        let root = unique_root("tsv");
        let tsv = root.join("commands.tsv");
        fs::write(
            &tsv,
            "type\tsource_line\tscript_path\tflag\tflag_value\tnote\tcmd_uid\n\
invocation\t10\tscripts/demo.sh\thelp\t\t\tu1\n\
invocation_no_flags\t11\tscripts/demo.sh\t\t\t\tu2\n",
        )
        .expect("tsv");
        let rows = read_tsv(&tsv);
        assert_eq!(rows.len(), 2);
        assert_eq!(rows[0].script_path, "scripts/demo.sh");
        assert_eq!(rows[0].flag, "help");

        let registry = root.join("hooks.tsv");
        fs::write(
            &registry,
            "script\thook\nscripts/demo.sh\t--validate-only\nscripts/dry.sh\tLARCH_DRY_RUN=1\n",
        )
        .expect("registry");
        let hooks = registry_hooks(&registry);
        assert_eq!(
            hooks.get("scripts/demo.sh").map(String::as_str),
            Some("--validate-only")
        );
        assert!(registry_hooks(&root.join("missing.tsv")).is_empty());

        write_exec(
            &root.join("scripts/demo.sh"),
            "#!/bin/sh\necho 'usage --help --mode'\nexit 0\n",
        );
        let repo = root.canonicalize().expect("canonicalize root");
        let (resolved, defect) = resolve_repo_script("scripts/demo.sh", &repo, None);
        assert!(resolved.is_some());
        assert!(defect.is_empty());
        let (missing, defect) = resolve_repo_script("scripts/nope.sh", &repo, None);
        assert!(missing.is_none());
        assert_eq!(defect, "non-canonical-path");
        let _ = fs::remove_dir_all(&root);
    }

    #[test]
    fn validate_plan_command_rows_covers_skip_defect_and_tier3() {
        let root = unique_root("validate-rows");
        write_exec(
            &root.join("scripts/demo.sh"),
            "#!/bin/sh\nif [ \"$1\" = --help ]; then echo 'usage --mode --help'; exit 0; fi\nif [ \"$1\" = --validate-only ]; then exit 0; fi\nexit 1\n",
        );
        write_exec(
            &root.join("scripts/new.sh"),
            "#!/bin/sh\necho help\nexit 0\n",
        );
        write_exec(&root.join("scripts/badhelp.sh"), "#!/bin/sh\nexit 99\n");
        write_exec(
            &root.join("scripts/weird.sh"),
            "#!/bin/sh\necho 'usage --x'\nexit 0\n",
        );
        let registry = root.join("scripts/dry-runnable-scripts.tsv");
        fs::write(
            &registry,
            "script\thook\nscripts/demo.sh\t--validate-only\nscripts/badhelp.sh\t--validate-only\nscripts/weird.sh\tOTHER\n",
        )
        .expect("registry");
        let rows = vec![
            PlanCommandRow {
                row_type: "new_script".into(),
                source_line: 1,
                script_path: "scripts/new.sh".into(),
                flag: String::new(),
                flag_value: String::new(),
                note: String::new(),
                cmd_uid: "n1".into(),
            },
            PlanCommandRow {
                row_type: "invocation".into(),
                source_line: 2,
                script_path: "scripts/new.sh".into(),
                flag: "mode".into(),
                flag_value: String::new(),
                note: String::new(),
                cmd_uid: "i-new".into(),
            },
            PlanCommandRow {
                row_type: "invocation".into(),
                source_line: 3,
                script_path: "scripts/demo.sh".into(),
                flag: "mode".into(),
                flag_value: String::new(),
                note: String::new(),
                cmd_uid: "i-demo".into(),
            },
            PlanCommandRow {
                row_type: "invocation".into(),
                source_line: 4,
                script_path: "scripts/missing.sh".into(),
                flag: "x".into(),
                flag_value: String::new(),
                note: String::new(),
                cmd_uid: "i-miss".into(),
            },
            PlanCommandRow {
                row_type: "invocation".into(),
                source_line: 5,
                script_path: "scripts/badhelp.sh".into(),
                flag: "mode".into(),
                flag_value: String::new(),
                note: String::new(),
                cmd_uid: "i-bad".into(),
            },
            PlanCommandRow {
                row_type: "invocation".into(),
                source_line: 6,
                script_path: "scripts/weird.sh".into(),
                flag: "x".into(),
                flag_value: "ok".into(),
                note: String::new(),
                cmd_uid: "i-weird".into(),
            },
            PlanCommandRow {
                row_type: "invocation".into(),
                source_line: 7,
                script_path: "scripts/demo.sh".into(),
                flag: "mode".into(),
                flag_value: "`unsafe`".into(),
                note: String::new(),
                cmd_uid: "i-unsafe".into(),
            },
            PlanCommandRow {
                row_type: "invocation_no_flags".into(),
                source_line: 8,
                script_path: "scripts/demo.sh".into(),
                flag: String::new(),
                flag_value: String::new(),
                note: String::new(),
                cmd_uid: "i-none".into(),
            },
            PlanCommandRow {
                row_type: "updated_flag".into(),
                source_line: 9,
                script_path: "scripts/demo.sh".into(),
                flag: "mode".into(),
                flag_value: String::new(),
                note: String::new(),
                cmd_uid: "u1".into(),
            },
        ];
        let summary =
            validate_plan_command_rows(&rows, &root, Some(&registry), "plan", 1.0, 1.0, None);
        assert!(summary.log_text.contains("SKIPPED"));
        assert!(summary.log_text.contains("DEFECT"));
        assert!(summary.defect_count >= 1);

        let composed =
            validate_plan_command_rows(&rows, &root, Some(&registry), "composed", 1.0, 1.0, None);
        assert!(composed.log_text.contains("VALIDATE_STATUS="));
        let _ = fs::remove_dir_all(&root);
    }

    #[test]
    fn plan_validation_outcome_and_optional_trailers() {
        let summary = ValidationSummary {
            status: "ok".into(),
            defect_count: 0,
            skipped_count: 0,
            unsafe_token_count: 0,
            log_text: "ok\n".into(),
        };
        let (status, total, log) = plan_validation_outcome(&summary, 1, "body\n", false);
        assert_eq!(status, "defects-found");
        assert_eq!(total, 1);
        assert!(log.contains("difficulty-metadata"));

        let root = unique_root("trailers");
        let plan = root.join("plan.txt");
        fs::write(
            &plan,
            "body\ndifficulty: HARD\ndiff_added: 1\nmechanical_churn: false\noversize_override: operator\ndiff_lines: 1\n",
        )
        .expect("plan");
        let keys = root.join("keys");
        fs::write(
            &keys,
            "difficulty\ndiff_added\nmechanical_churn\noversize_override\n",
        )
        .expect("keys");
        assert!(validate_optional_trailer_keys_preserved(&plan, &keys));
        let values = root.join("keys.values");
        let meta = parse_optional_metadata(&read_text(&plan));
        fs::write(&values, meta.values.join("\n") + "\n").expect("values");
        assert!(validate_optional_trailers_preserved(&plan, &values));
        assert!(validate_optional_trailers_preserved(&plan, &keys));
        let absent = root.join("absent-keys");
        fs::write(&absent, "not-present-in-plan\n").expect("absent keys");
        assert!(!validate_optional_trailer_keys_preserved(&plan, &absent));

        assert_eq!(
            optional_trailers(&[
                "parse".into(),
                "--plan-file".into(),
                plan.as_os_str().into(),
            ]),
            ExitCode::SUCCESS
        );
        assert_eq!(
            optional_trailers(&["keys".into(), "--plan-file".into(), plan.as_os_str().into()]),
            ExitCode::SUCCESS
        );
        assert_eq!(
            optional_trailers(&[
                "values".into(),
                "--plan-file".into(),
                plan.as_os_str().into()
            ]),
            ExitCode::SUCCESS
        );
        assert_eq!(
            optional_trailers(&[
                "has-key".into(),
                "--plan-file".into(),
                plan.as_os_str().into(),
                "--key".into(),
                "diff_added".into(),
            ]),
            ExitCode::SUCCESS
        );
        assert_eq!(
            optional_trailers(&[
                "has-key".into(),
                "--plan-file".into(),
                plan.as_os_str().into(),
                "--key".into(),
                "nope".into(),
            ]),
            ExitCode::FAILURE
        );
        let snap = root.join("snap");
        assert_eq!(
            optional_trailers(&[
                "snapshot-keys".into(),
                "--plan-file".into(),
                plan.as_os_str().into(),
                "--output".into(),
                snap.as_os_str().into(),
            ]),
            ExitCode::SUCCESS
        );
        assert!(snap.is_file());
        assert_eq!(
            optional_trailers(&[
                "snapshot-values".into(),
                "--plan-file".into(),
                plan.as_os_str().into(),
                "--output".into(),
                root.join("vals").as_os_str().into(),
            ]),
            ExitCode::SUCCESS
        );
        assert_eq!(
            optional_trailers(&[
                "validate-keys".into(),
                "--plan-file".into(),
                plan.as_os_str().into(),
                "--keys-file".into(),
                keys.as_os_str().into(),
            ]),
            ExitCode::SUCCESS
        );
        assert_eq!(
            optional_trailers(&[
                "validate-values".into(),
                "--plan-file".into(),
                plan.as_os_str().into(),
                "--values-file".into(),
                values.as_os_str().into(),
            ]),
            ExitCode::SUCCESS
        );
        assert_eq!(optional_trailers(&["--help".into()]), ExitCode::SUCCESS);
        assert_eq!(optional_trailers(&[]), ExitCode::from(RC2));
        assert_eq!(optional_trailers(&["bogus".into()]), ExitCode::from(RC2));
        let _ = fs::remove_dir_all(&root);
    }

    #[test]
    fn oversize_authority_and_set_override_check_size_paths() {
        let root = unique_root("size");
        let plan = root.join("plan.txt");
        fs::write(&plan, mini_plan()).expect("plan");
        assert!(trusted_oversize_override(&root, &read_text(&plan)).is_none());
        let with_override = set_oversize_override_text(&read_text(&plan), false).expect("override");
        fs::write(&plan, &with_override).expect("rewrite");
        sync_oversize_override_authority(&root, &plan);
        assert_eq!(
            trusted_oversize_override(&root, &with_override).as_deref(),
            Some(OVERSIZE_OVERRIDE_OPERATOR)
        );
        let design = root.canonicalize().expect("canonicalize design");
        let plan = design.join("plan.txt");
        assert!(canonical_plan_for_override(&design, None).is_ok());
        assert!(canonical_plan_for_override(&design, Some(plan.to_str().unwrap())).is_ok());
        assert!(canonical_plan_for_override(&design, Some("/tmp")).is_err());

        assert_eq!(
            set_oversize_override(&["--design-tmpdir".into(), design.as_os_str().into(),]),
            ExitCode::SUCCESS
        );
        assert_eq!(
            check_size(&["--design-tmpdir".into(), design.as_os_str().into(),]),
            ExitCode::SUCCESS
        );
        let empty = unique_root("size-empty");
        assert_eq!(
            check_size(&["--design-tmpdir".into(), empty.as_os_str().into(),]),
            ExitCode::from(RC2)
        );
        let bad = unique_root("size-bad");
        fs::write(
            bad.join("plan.txt"),
            "### NEW: x\n\nbody\n\nno trailer here\n",
        )
        .expect("bad plan");
        assert_eq!(
            check_size(&["--design-tmpdir".into(), bad.as_os_str().into()]),
            ExitCode::from(RC2)
        );
        let base = unique_root("size-base");
        fs::write(base.join("plan.txt"), mini_plan()).expect("plan");
        fs::write(
            base.join("drift-baseline.env"),
            "BASELINE_PLAN_LINES=1\nBASELINE_DIFF_LINES=1\n",
        )
        .expect("baseline");
        assert_eq!(
            check_size(&["--design-tmpdir".into(), base.as_os_str().into()]),
            ExitCode::SUCCESS
        );
        let counts = plan_counts_from_file(&base.join("plan.txt")).expect("counts");
        assert_eq!(counts.1, 1);
        assert!(counts.0 >= 1);
        assert!(plan_counts_from_file(&base.join("missing")).is_none());

        let _ = fs::remove_dir_all(&root);
        let _ = fs::remove_dir_all(&empty);
        let _ = fs::remove_dir_all(&bad);
        let _ = fs::remove_dir_all(&base);
    }

    #[test]
    fn parse_validate_and_compose_entrypoints() {
        let root = unique_root("entry");
        let plan = root.join("plan.txt");
        let body = format!(
            "{}\n{}",
            "x".repeat(64),
            "### NEW: fixture\n\n1. Touch `scripts/noop.sh`.\n\ndifficulty: HARD\nmechanical_churn: false\ndiff_lines: 1\n"
        );
        fs::write(&plan, &body).expect("plan");
        let out = root.join("out.tsv");
        assert_eq!(
            parse_commands(&[
                "--plan-file".into(),
                plan.as_os_str().into(),
                "--output".into(),
                out.as_os_str().into(),
                "--repo-root".into(),
                root.as_os_str().into(),
            ]),
            ExitCode::SUCCESS
        );
        assert!(out.is_file());

        let log = root.join("validate.log");
        let tsv = root.join("commands.tsv");
        fs::write(
            &tsv,
            "type\tsource_line\tscript_path\tflag\tflag_value\tnote\tcmd_uid\n",
        )
        .expect("tsv");
        assert_eq!(
            validate_commands(&[
                "--tsv-file".into(),
                tsv.as_os_str().into(),
                "--log-file".into(),
                log.as_os_str().into(),
                "--repo-root".into(),
                root.as_os_str().into(),
            ]),
            ExitCode::SUCCESS
        );
        assert!(log.is_file());

        assert_eq!(
            validate(&[
                "--plan-file".into(),
                plan.as_os_str().into(),
                "--repo-root".into(),
                root.as_os_str().into(),
                "--design-tmpdir".into(),
                root.as_os_str().into(),
            ]),
            ExitCode::SUCCESS
        );
        assert_eq!(
            compose_goals_test(&[
                "--plan-file".into(),
                plan.as_os_str().into(),
                "--goal-text".into(),
                "goal".into(),
            ]),
            ExitCode::SUCCESS
        );
        assert_eq!(
            compose_goals_test(&[
                "--plan-file".into(),
                root.join("missing").as_os_str().into()
            ]),
            ExitCode::from(RC2)
        );
        let short = root.join("short.txt");
        fs::write(&short, "too-short").expect("short");
        assert_eq!(
            compose_goals_test(&["--plan-file".into(), short.as_os_str().into()]),
            ExitCode::from(RC2)
        );
        let pointer = root.join("pointer.txt");
        fs::write(&pointer, format!("see plan.txt\n{}\n", "y".repeat(64))).expect("pointer");
        assert_eq!(
            compose_goals_test(&["--plan-file".into(), pointer.as_os_str().into()]),
            ExitCode::from(RC2)
        );
        assert_eq!(
            captured_process_text(&Command::new("true").output().expect("true")).0,
            0
        );
        assert_eq!(plugin_root_for_commands(), plugin_root());
        let _ = fs::remove_dir_all(&root);
    }
}
