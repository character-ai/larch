//! Rust owner for `/design` Step 3.5 settlement and Step 5b annotation (#8585).
//!
//! This atomically replaces `design step35-settle`, `plan-review step35-settle`,
//! `design step5b-prepare`, and `design step5b-annotate`. Sibling commands run
//! through the verified bootstrap seam.

use std::{
    collections::BTreeMap,
    ffi::OsString,
    fs::{self, OpenOptions},
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::validate_design_tmpdir;
use larch_core::{
    ArchitecturalKind, ArchitecturalStatus, AssessmentKind, CommentPolicy, KvDocument,
    ParseOptions, cleanup_cache_sessions_root, read_architectural_knowledge,
};

use crate::{
    design_commands::parse_stdout_kv,
    design_step0_commands::{
        ChildOutcome, Env, LiveStep0Runner, Step0Runner, WrapperNs, atomic_write_string, env_get,
        load_source_env_allowed, load_wrapper_env, pause_save_arguments, require_plugin_root,
        utf8_arguments, write_text,
    },
    design_step1_commands::{append_failure_args, consumer_repo_root},
    voter_calibration_commands::resolve_like_python,
};

const SETTLE_LABEL: &str = "design-step35-settle";
const DEDUP_REVISE_ACTION: &str = "dedup-revise";
const PAUSE_ACTION: &str = "pause";
const DIALECTIC_WARNING: &str = "**\u{26A0} design-step35-settle: dialectic-clear-stale failed after {where}; stale clarifier artifacts may linger (Gate C fingerprint binding still gates debate).**";
const STEP5B_PREPARE_LABEL: &str = "design-step5b-prepare.sh";
const STEP5B_ANNOTATE_LABEL: &str = "design-step5b-annotate.sh";
const STEP5B_SITE: &str = "design Step 5b";
const STEP5B_SOURCE_ENV_ALLOW: [&str; 1] = ["REPO_ROOT"];

struct CommonArgs {
    ns: WrapperNs,
    mode: String,
    site: String,
    outcome: String,
    skip_validate: bool,
    step3_review_loop_status: String,
    loop_status: String,
    public_argv: Vec<String>,
    round_num: String,
    force_dedup: bool,
}

fn default_common_args() -> CommonArgs {
    CommonArgs {
        ns: WrapperNs {
            session_env_path: String::new(),
            claude_pid: String::new(),
            plugin_root: std::env::var("CLAUDE_PLUGIN_ROOT").unwrap_or_default(),
            outcome: std::env::var("SUMMARY_OUTCOME").unwrap_or_default(),
            issue_number: String::new(),
            exit_code: std::env::var("CLARIFY_HARD_HALT_RC")
                .ok()
                .filter(|value| !value.is_empty())
                .unwrap_or_else(|| "1".to_owned()),
            failure_detail_log: std::env::var("CLARIFY_FAILURE_LOG").unwrap_or_default(),
            reason: "external tool unhealthy; re-run once it recovers.".to_owned(),
            tool: "degraded-tools-gate".to_owned(),
            public_argv: Vec::new(),
        },
        mode: String::new(),
        site: String::new(),
        outcome: String::new(),
        skip_validate: false,
        step3_review_loop_status: String::new(),
        loop_status: String::new(),
        public_argv: Vec::new(),
        round_num: String::new(),
        force_dedup: false,
    }
}

fn parse_common(arguments: &[OsString]) -> Result<CommonArgs, String> {
    let args = utf8_arguments(arguments);
    let mut out = default_common_args();
    let mut index = 0;
    while index < args.len() {
        let token = args[index].as_str();
        if token == "--" {
            out.public_argv = args[index + 1..].to_vec();
            break;
        }
        if token == "--force-dedup" {
            out.force_dedup = true;
            index += 1;
            continue;
        }
        if token == "--round-num" {
            let Some(value) = args.get(index + 1) else {
                return Err("--round-num requires a value".to_owned());
            };
            out.round_num.clone_from(value);
            index += 2;
            continue;
        }
        let requires_value = matches!(
            token,
            "--session-env-path"
                | "--claude-pid"
                | "--plugin-root"
                | "--mode"
                | "--site"
                | "--outcome"
                | "--step3-review-loop-status"
                | "--loop-status"
                | "--validator-target-file"
                | "--validate-log-file"
                | "--validate-defect-count"
                | "--validate-unsafe-token-count"
                | "--validate-skipped-count"
        );
        if requires_value {
            let Some(value) = args.get(index + 1) else {
                return Err(format!("{token} requires a value"));
            };
            match token {
                "--session-env-path" => out.ns.session_env_path.clone_from(value),
                "--claude-pid" => out.ns.claude_pid.clone_from(value),
                "--plugin-root" => out.ns.plugin_root.clone_from(value),
                "--mode" => out.mode.clone_from(value),
                "--site" => out.site.clone_from(value),
                "--outcome" => out.outcome.clone_from(value),
                "--step3-review-loop-status" => out.step3_review_loop_status.clone_from(value),
                "--loop-status" => out.loop_status.clone_from(value),
                _ => {}
            }
            index += 2;
            continue;
        }
        if matches!(
            token,
            "--snapshot-original"
                | "--skip-validate"
                | "--write-completion-only"
                | "--include-step2b"
                | "--write-step2b-completion-only"
                | "--operator-cancel"
        ) {
            out.skip_validate = token == "--skip-validate";
            index += 1;
            continue;
        }
        if token.starts_with("--")
            && args
                .get(index + 1)
                .is_some_and(|value| !value.starts_with("--"))
        {
            index += 2;
        } else {
            index += 1;
        }
    }
    Ok(out)
}

fn hydrated_env(common: &CommonArgs) -> Env {
    let mut env = load_wrapper_env(&common.ns);
    for (key, value) in load_source_env_allowed(
        &common.ns.session_env_path,
        &common.ns.claude_pid,
        &STEP5B_SOURCE_ENV_ALLOW,
    ) {
        let _ = env.insert(key, value);
    }
    if !common.mode.is_empty() {
        let _ = env.insert("MODE".to_owned(), common.mode.clone());
    }
    if !common.site.is_empty() {
        let _ = env.insert("SITE".to_owned(), common.site.clone());
    }
    if !common.outcome.is_empty() {
        let _ = env.insert("SUMMARY_OUTCOME".to_owned(), common.outcome.clone());
    }
    if common.skip_validate {
        let _ = env.insert("SKIP_VALIDATE".to_owned(), "1".to_owned());
    }
    if !common.step3_review_loop_status.is_empty() {
        let _ = env.insert(
            "STEP3_REVIEW_LOOP_STATUS".to_owned(),
            common.step3_review_loop_status.clone(),
        );
    }
    if !common.loop_status.is_empty() {
        let _ = env.insert("LOOP_STATUS".to_owned(), common.loop_status.clone());
    }
    env
}

fn print_text(text: &str) {
    if text.is_empty() {
        return;
    }
    print!("{text}");
    if !text.ends_with('\n') {
        println!();
    }
}

fn print_child(child: &ChildOutcome) {
    print_text(&child.stdout);
    if !child.stderr.is_empty() {
        eprint!("{}", child.stderr);
        if !child.stderr.ends_with('\n') {
            eprintln!();
        }
    }
}

fn run_larch(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    arguments: impl IntoIterator<Item = String>,
    environment: &[(String, String)],
) -> ChildOutcome {
    let args = arguments.into_iter().collect::<Vec<_>>();
    runner.run(plugin_root, &args, environment, false)
}

fn last_kv(rows: &[(String, String)], key: &str) -> String {
    rows.iter()
        .rev()
        .find(|(candidate, _value)| candidate == key)
        .map_or_else(String::new, |(_candidate, value)| value.clone())
}

fn read_text_lossy(path: &Path) -> Option<String> {
    fs::read(path)
        .ok()
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
}

fn path_nonempty(path: &Path) -> bool {
    path.is_file() && path.metadata().is_ok_and(|metadata| metadata.len() > 0)
}

fn touch(path: &Path) {
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let _ = OpenOptions::new()
        .create(true)
        .write(true)
        .truncate(false)
        .open(path);
}

fn mark_step5b_complete(design_tmpdir: &Path) {
    touch(&design_tmpdir.join(".completed/step-5b"));
}

fn append_failure_if_nonempty(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    tool: &str,
    exit_code: i32,
    category: &str,
    stderr_path: &Path,
) {
    if !path_nonempty(stderr_path) {
        return;
    }
    let args = append_failure_args(
        design_tmpdir
            .join("execution-issues.md")
            .display()
            .to_string(),
        STEP5B_SITE,
        tool,
        &exit_code.to_string(),
        category,
        stderr_path,
    );
    let _ = run_larch(runner, plugin_root, args, &[]);
}

fn call_pause_save(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    env: &Env,
) -> i32 {
    let args = pause_save_arguments(
        design_tmpdir,
        env_get(env, "ISSUE_NUMBER", ""),
        env_get(env, "REPO", ""),
    )
    .into_iter()
    .map(|value| value.to_string_lossy().into_owned())
    .collect::<Vec<_>>();
    let child = run_larch(runner, plugin_root, args, &[]);
    print_child(&child);
    child.code
}

fn mark_design_timing(runner: &dyn Step0Runner, plugin_root: &Path, label: &str) {
    let root = plugin_root.to_string_lossy();
    if root.is_empty() || root == "${CLAUDE_PLUGIN_ROOT}" {
        return;
    }
    let _ = run_larch(
        runner,
        plugin_root,
        ["timing".to_owned(), "mark".to_owned(), label.to_owned()],
        &[
            ("LARCH_TIMING_SKILL".to_owned(), "design".to_owned()),
            ("CLAUDE_PLUGIN_ROOT".to_owned(), root.into_owned()),
        ],
    );
}

// ---------------------------------------------------------------------------
// Step 3.5 settlement
// ---------------------------------------------------------------------------

#[derive(Clone)]
struct SettleRequest {
    site: String,
    design_tmpdir: PathBuf,
    round_num: String,
    force_dedup: bool,
    session_env_path: String,
    claude_pid: String,
    plugin_root: PathBuf,
    public_argv: Vec<String>,
    issue_number: String,
    repo: String,
    final_round_num: String,
    step3_review_round_num: String,
    env_round_num: String,
}

fn settle_design_tmpdir(env: &Env) -> Result<PathBuf, ExitCode> {
    let raw = env_get(env, "DESIGN_TMPDIR", "");
    if raw.is_empty() {
        eprintln!("/design Step 3.5 settle: DESIGN_TMPDIR required");
        return Err(ExitCode::from(2));
    }
    let cache = cleanup_cache_sessions_root(
        std::env::var_os("XDG_CACHE_HOME").as_deref(),
        std::env::var_os("HOME").as_deref(),
    );
    if let Err(error) = validate_design_tmpdir(raw, std::env::var_os("TMPDIR").as_deref(), &cache) {
        eprintln!("ERROR={error}");
        return Err(ExitCode::from(2));
    }
    Ok(resolve_like_python(Path::new(raw)))
}

fn read_round_env(path: &str) -> BTreeMap<String, String> {
    if path.is_empty() {
        return BTreeMap::new();
    }
    let source = Path::new(path);
    if source.is_symlink() || !source.is_file() {
        return BTreeMap::new();
    }
    let Some(text) = read_text_lossy(source) else {
        return BTreeMap::new();
    };
    let mut options = ParseOptions::legacy();
    options.comments = CommentPolicy::Skip;
    let document = KvDocument::parse(&text, options).expect("legacy parser is non-rejecting");
    let mut rows = BTreeMap::new();
    for row in document.rows() {
        let key = row.key();
        if matches!(
            key,
            "FINAL_ROUND_NUM" | "STEP3_REVIEW_ROUND_NUM" | "ROUND_NUM"
        ) {
            let _ = rows
                .entry(key.to_owned())
                .or_insert_with(|| row.value().to_owned());
        }
    }
    rows
}

fn valid_settle_site(site: &str) -> bool {
    matches!(site, "gate-a" | "gate-b" | "discussion-round2" | "gate-c")
}

fn postplan_site(site: &str) -> &'static str {
    match site {
        "gate-a" | "discussion-round2" => "discussion-round2",
        "gate-b" => "gate-b",
        "gate-c" => "gate-c",
        _ => unreachable!("site is validated before postplan routing"),
    }
}

fn build_settle_request(arguments: &[OsString]) -> Result<SettleRequest, ExitCode> {
    let common = match parse_common(arguments) {
        Ok(value) => value,
        Err(error) => {
            eprintln!("{SETTLE_LABEL}: {error}");
            return Err(ExitCode::from(2));
        }
    };
    if !valid_settle_site(&common.site) {
        eprintln!("{SETTLE_LABEL}: --site must be gate-b, gate-a, discussion-round2, or gate-c");
        return Err(ExitCode::from(2));
    }
    let env = hydrated_env(&common);
    let plugin_root = resolve_like_python(&require_plugin_root(env_get(
        &env,
        "CLAUDE_PLUGIN_ROOT",
        "",
    ))?);
    let design_tmpdir = settle_design_tmpdir(&env)?;
    let rounds = read_round_env(&common.ns.session_env_path);
    Ok(SettleRequest {
        site: common.site,
        design_tmpdir,
        round_num: common.round_num,
        force_dedup: common.force_dedup,
        session_env_path: common.ns.session_env_path,
        claude_pid: common.ns.claude_pid,
        plugin_root,
        public_argv: common.public_argv,
        issue_number: env_get(&env, "ISSUE_NUMBER", "").to_owned(),
        repo: env_get(&env, "REPO", "").to_owned(),
        final_round_num: rounds
            .get("FINAL_ROUND_NUM")
            .cloned()
            .unwrap_or_else(|| std::env::var("FINAL_ROUND_NUM").unwrap_or_default()),
        step3_review_round_num: rounds
            .get("STEP3_REVIEW_ROUND_NUM")
            .cloned()
            .unwrap_or_else(|| std::env::var("STEP3_REVIEW_ROUND_NUM").unwrap_or_default()),
        env_round_num: rounds
            .get("ROUND_NUM")
            .cloned()
            .unwrap_or_else(|| std::env::var("ROUND_NUM").unwrap_or_default()),
    })
}

fn resolve_gate_b_round(request: &SettleRequest) -> Option<&str> {
    [
        request.round_num.as_str(),
        request.final_round_num.as_str(),
        request.step3_review_round_num.as_str(),
        request.env_round_num.as_str(),
    ]
    .into_iter()
    .find(|value| !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()))
}

fn parse_postplan_rc(stdout: &str) -> (String, usize) {
    let mut first = String::new();
    let mut count = 0;
    for line in stdout.lines() {
        if let Some(value) = line.strip_prefix("POSTPLAN_RC=") {
            if count == 0 {
                first.clone_from(&value.to_owned());
            }
            count += 1;
        }
    }
    (first, count)
}

fn pause_signal_in_output(stdout: &str) -> bool {
    stdout.lines().any(|line| {
        matches!(
            line,
            "PAUSE_OK=true"
                | "POSTPLAN_EMIT_STATUS=paused"
                | "POSTPLAN_RC=11"
                | "POSTPLAN_STATUS=pause-save"
        )
    })
}

fn parse_next_action(stdout: &str) -> (String, Option<i32>) {
    let mut action = String::new();
    let mut exit = None;
    for line in stdout.lines() {
        if let Some(value) = line.strip_prefix("SETTLE_NEXT_ACTION=") {
            action.clone_from(&value.to_owned());
        } else if let Some(value) = line.strip_prefix("SETTLE_EXIT_RC=")
            && let Ok(value) = value.parse::<i32>()
        {
            exit = Some(value);
        }
    }
    (action, exit)
}

fn emit_next_action(runner: &dyn Step0Runner, request: &SettleRequest, postplan_rc: i32) -> i32 {
    let child = run_larch(
        runner,
        &request.plugin_root,
        [
            "design".to_owned(),
            "settle-next-action".to_owned(),
            "--site".to_owned(),
            request.site.clone(),
            "--postplan-rc".to_owned(),
            postplan_rc.to_string(),
        ],
        &[],
    );
    let (action, exit) = parse_next_action(&child.stdout);
    if action.is_empty() {
        eprintln!(
            "{SETTLE_LABEL}: settle-next-action failed for site={} postplan_rc={postplan_rc}",
            request.site
        );
        return 3;
    }
    println!("SETTLE_NEXT_ACTION={action}");
    exit.unwrap_or(postplan_rc)
}

fn clear_dialectic(request: &SettleRequest, runner: &dyn Step0Runner) -> i32 {
    run_larch(
        runner,
        &request.plugin_root,
        [
            "design".to_owned(),
            "dialectic-clear-stale".to_owned(),
            "--design-tmpdir".to_owned(),
            request.design_tmpdir.display().to_string(),
            "--reason".to_owned(),
            "plan-rewrite".to_owned(),
        ],
        &[],
    )
    .code
}

fn settle_pause(request: &SettleRequest, runner: &dyn Step0Runner) -> Option<i32> {
    if !request.design_tmpdir.join(".pause-requested").is_file() {
        return None;
    }
    let args = pause_save_arguments(&request.design_tmpdir, &request.issue_number, &request.repo)
        .into_iter()
        .map(|value| value.to_string_lossy().into_owned())
        .collect::<Vec<_>>();
    let child = run_larch(runner, &request.plugin_root, args, &[]);
    print_child(&child);
    if child.stdout.lines().any(|line| line == "PAUSE_OK=true")
        || request.design_tmpdir.join(".pause-save-complete").is_file()
    {
        println!("SETTLE_NEXT_ACTION={PAUSE_ACTION}");
        Some(11)
    } else {
        Some(child.code)
    }
}

fn gate_b_dedup(
    request: &SettleRequest,
    round: Option<&str>,
    runner: &dyn Step0Runner,
) -> Option<i32> {
    let (ready, phase) = round.map_or_else(
        || (PathBuf::new(), PathBuf::new()),
        |round| {
            (
                request
                    .design_tmpdir
                    .join(format!(".gate-b-postapply-ready-{round}")),
                request
                    .design_tmpdir
                    .join(format!(".step3-round-{round}.phase")),
            )
        },
    );
    let skip = request.site == "gate-b"
        && !request.force_dedup
        && ready.is_file()
        && (!phase.is_file()
            || phase.is_symlink()
            || read_text_lossy(&phase)
                .is_none_or(|text| text.trim_end_matches('\n') != "awaiting-postplan-operator"));
    if skip {
        return None;
    }
    let child = run_larch(
        runner,
        &request.plugin_root,
        [
            "plan-review".to_owned(),
            "gate-b-dedup".to_owned(),
            "--design-tmpdir".to_owned(),
            request.design_tmpdir.display().to_string(),
            "--dedup".to_owned(),
        ],
        &[],
    );
    print_child(&child);
    if child.code == 1 {
        if let Some(round) = round {
            let snapshot = request
                .design_tmpdir
                .join(format!("plan-pre-apply-round-{round}.txt"));
            if snapshot.is_file() && !snapshot.is_symlink() {
                let _ = fs::copy(snapshot, request.design_tmpdir.join("plan.txt"));
            }
        }
        println!("SETTLE_NEXT_ACTION={DEDUP_REVISE_ACTION}");
        eprintln!(
            "{SETTLE_LABEL}: post-rewrite dedup requires plan revision; retry settle after cleanup"
        );
        return Some(1);
    }
    if child.code != 0 {
        eprintln!(
            "{SETTLE_LABEL}: post-rewrite dedup failed with rc {}",
            child.code
        );
        return Some(child.code);
    }
    if clear_dialectic(request, runner) != 0 {
        eprintln!("{}", DIALECTIC_WARNING.replace("{where}", "dedup"));
    }
    if request.site == "gate-b" {
        let _ = atomic_write_string(&ready, "ready\n");
    }
    None
}

fn settle_postplan(request: &SettleRequest, runner: &dyn Step0Runner) -> ChildOutcome {
    let mut args = vec![
        "design".to_owned(),
        "step2b-postplan".to_owned(),
        "--session-env-path".to_owned(),
        request.session_env_path.clone(),
        "--claude-pid".to_owned(),
        request.claude_pid.clone(),
        "--plugin-root".to_owned(),
        request.plugin_root.display().to_string(),
        "--site".to_owned(),
        postplan_site(&request.site).to_owned(),
    ];
    args.extend(request.public_argv.iter().cloned());
    run_larch(
        runner,
        &request.plugin_root,
        args,
        &[(
            "DESIGN_TMPDIR".to_owned(),
            request.design_tmpdir.display().to_string(),
        )],
    )
}

fn dispatch_postplan(
    request: &SettleRequest,
    round: Option<&str>,
    postplan: &ChildOutcome,
    runner: &dyn Step0Runner,
) -> i32 {
    let (machine_rc, count) = parse_postplan_rc(&postplan.stdout);
    if count != 1 {
        let message = if count == 0 {
            "postplan output missing anchored POSTPLAN_RC row"
        } else {
            "postplan output contained multiple POSTPLAN_RC rows"
        };
        eprintln!("{SETTLE_LABEL}: {message}");
        return 3;
    }
    let phase = round.map(|round| {
        request
            .design_tmpdir
            .join(format!(".step3-round-{round}.phase"))
    });
    if machine_rc == "0" {
        if postplan.code != 0 {
            eprintln!(
                "{SETTLE_LABEL}: POSTPLAN_RC=0 with child rc {}",
                postplan.code
            );
            return 3;
        }
        if clear_dialectic(request, runner) != 0 {
            eprintln!("{}", DIALECTIC_WARNING.replace("{where}", "postplan"));
        }
        if let Some(phase) = phase {
            let _ = atomic_write_string(&phase, "awaiting-continuation\n");
        }
        return emit_next_action(runner, request, 0);
    }
    if matches!(machine_rc.as_str(), "10" | "11" | "12" | "13") {
        if matches!(machine_rc.as_str(), "10" | "13")
            && let Some(phase) = phase
        {
            let _ = atomic_write_string(&phase, "awaiting-postplan-operator\n");
        }
        return emit_next_action(runner, request, machine_rc.parse().unwrap_or(3));
    }
    eprintln!("{SETTLE_LABEL}: unexpected POSTPLAN_RC={machine_rc}");
    3
}

fn step35_settle_for(request: &SettleRequest, runner: &dyn Step0Runner) -> i32 {
    if let Some(code) = settle_pause(request, runner) {
        return code;
    }
    let round = if request.site == "gate-b" {
        if let Some(round) = resolve_gate_b_round(request) {
            Some(round)
        } else {
            eprintln!(
                "{SETTLE_LABEL}: Gate B requires --round-num or FINAL_ROUND_NUM, STEP3_REVIEW_ROUND_NUM, or ROUND_NUM"
            );
            return 2;
        }
    } else {
        None
    };
    if let Some(code) = gate_b_dedup(request, round, runner) {
        return code;
    }
    if let Some(round) = round {
        let _ = atomic_write_string(
            &request
                .design_tmpdir
                .join(format!(".step3-round-{round}.phase")),
            "awaiting-post-apply\n",
        );
    }
    let _ = fs::remove_file(request.design_tmpdir.join(".pause-save-complete"));
    let postplan = settle_postplan(request, runner);
    print_child(&postplan);
    if pause_signal_in_output(&postplan.stdout)
        || request.design_tmpdir.join(".pause-save-complete").is_file()
    {
        println!("SETTLE_NEXT_ACTION={PAUSE_ACTION}");
        return 11;
    }
    dispatch_postplan(request, round, &postplan, runner)
}

/// Entry point for both `design step35-settle` and `plan-review step35-settle`.
pub fn step35_settle(arguments: &[OsString]) -> ExitCode {
    let request = match build_settle_request(arguments) {
        Ok(request) => request,
        Err(code) => return code,
    };
    ExitCode::from(u8::try_from(step35_settle_for(&request, &LiveStep0Runner)).unwrap_or(1))
}

// ---------------------------------------------------------------------------
// Step 5b OOS filing preparation and annotation
// ---------------------------------------------------------------------------

fn step5b_prelude(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    env: &Env,
) -> i32 {
    if design_tmpdir.join(".pause-requested").is_file() {
        return call_pause_save(runner, plugin_root, design_tmpdir, env);
    }
    let repo_root = if env_get(env, "REPO_ROOT", "").is_empty() {
        consumer_repo_root().unwrap_or_else(|| plugin_root.to_path_buf())
    } else {
        resolve_like_python(Path::new(env_get(env, "REPO_ROOT", "")))
    };
    let mut missing = Vec::new();
    let invariants = read_architectural_knowledge(&repo_root, ArchitecturalKind::Invariants);
    if invariants.status == ArchitecturalStatus::Present && !invariants.content.trim().is_empty() {
        missing.push(AssessmentKind::Invariants.design_assessment_filename());
    }
    if read_architectural_knowledge(&repo_root, ArchitecturalKind::Guidelines).status
        == ArchitecturalStatus::Present
    {
        missing.push(AssessmentKind::Guidelines.design_assessment_filename());
    }
    missing.retain(|artifact| {
        let path = design_tmpdir.join(artifact);
        !path.is_file() || path.is_symlink()
    });
    if missing.is_empty() {
        return 0;
    }
    println!(
        "**⚠ 5b: finalize refused: missing {}; return to Gate C to persist required assessment artifacts before Step 5.**",
        missing.join(" and ")
    );
    4
}

fn step5b_issue_args(env: &Env) -> Vec<String> {
    let mut args = Vec::new();
    let issue = env_get(env, "ISSUE_NUMBER", "");
    if !issue.is_empty() {
        args.push("--issue-number".to_owned());
        args.push(issue.to_owned());
    }
    let repo = env_get(env, "REPO", "");
    if !repo.is_empty() {
        args.push("--repo".to_owned());
        args.push(repo.to_owned());
    }
    args
}

fn step5b_mutation_args(env: &Env, design_tmpdir: &Path) -> Vec<String> {
    vec![
        "--context-file".to_owned(),
        design_tmpdir
            .join("source-env.sh")
            .to_string_lossy()
            .into_owned(),
        "--run-id".to_owned(),
        env_get(env, "LARCH_RUN_ID", "").to_owned(),
        "--trusted-root".to_owned(),
        design_tmpdir.to_string_lossy().into_owned(),
    ]
}

fn step5b_prepare_args(env: &Env, design_tmpdir: &Path) -> Vec<String> {
    let mut args = vec![
        "design".to_owned(),
        "file-oos-prepare".to_owned(),
        "--design-tmpdir".to_owned(),
        design_tmpdir.to_string_lossy().into_owned(),
    ];
    args.extend(step5b_issue_args(env));
    args
}

fn step5b_annotate_args(
    env: &Env,
    design_tmpdir: &Path,
    oos_issue_stdout: &Path,
    label_only: bool,
) -> Vec<String> {
    let mut args = vec![
        "design".to_owned(),
        "file-oos-annotate".to_owned(),
        "--design-tmpdir".to_owned(),
        design_tmpdir.to_string_lossy().into_owned(),
        "--issue-stdout-file".to_owned(),
        oos_issue_stdout.to_string_lossy().into_owned(),
    ];
    args.extend(step5b_issue_args(env));
    args.extend(step5b_mutation_args(env, design_tmpdir));
    if label_only {
        args.push("--label-only".to_owned());
    }
    args
}

fn step5b_next_action(status: &str) -> &'static str {
    match status {
        "ready" => "file-issues",
        "label-only-retry" => "label-only",
        "skip-sentinel" | "skip-already-filed-sentinel" | "skip-no-items" | "skip-all-security" => {
            "skip-pipeline"
        }
        _ => "unknown-oos-status",
    }
}

fn step5b_breadcrumb(status: &str) -> &'static str {
    match status {
        "skip-sentinel" => "⏩ 5b: oos filing; sentinel recovery (skip pipeline)",
        "skip-already-filed-sentinel" => {
            "⏩ 5b: oos filing; oos-issue-sentinel present (already filed); skip pipeline"
        }
        "skip-no-items" => "⏩ 5b: oos filing; no accepted-OOS items",
        "skip-all-security" => "⏩ 5b: oos filing; no non-security OOS items",
        "label-only-retry" => "⏩ 5b: oos filing; label-only retry (pending priority labels)",
        _ => "",
    }
}

fn annotate_sequencing_error(oos_issue_stdout: &Path) -> bool {
    read_text_lossy(oos_issue_stdout).is_none_or(|text| text.trim().is_empty())
}

fn write_prepare_env(path: &Path, stdout: &str, rows: &[String]) {
    let separator = if stdout.is_empty() || stdout.ends_with('\n') {
        ""
    } else {
        "\n"
    };
    let text = format!("{stdout}{separator}{}\n", rows.join("\n"));
    write_text(path, &text);
}

fn emit_prepare_success(
    design_tmpdir: &Path,
    prepare_env: &Path,
    stdout: &str,
    oos_issue_stdout: &Path,
) -> String {
    let kv = parse_stdout_kv(stdout);
    for line in stdout.lines() {
        if line.starts_with("FILE_DESIGN_OOS_") || line.starts_with("WARN=") {
            println!("{line}");
        }
    }
    let status = last_kv(&kv, "FILE_DESIGN_OOS_STATUS");
    let combined = last_kv(&kv, "FILE_DESIGN_OOS_COMBINED");
    let deps_tsv = last_kv(&kv, "FILE_DESIGN_OOS_DEPS_TSV");
    let deps_available = last_kv(&kv, "FILE_DESIGN_OOS_DEPS_AVAILABLE");
    let upstream_next_action = last_kv(&kv, "NEXT_ACTION");
    let mut next_action = step5b_next_action(&status).to_owned();
    if !upstream_next_action.is_empty() && upstream_next_action != next_action {
        "unknown-oos-status".clone_into(&mut next_action);
    }
    let unknown = next_action == "unknown-oos-status";
    let emit_status = if unknown {
        "unknown-oos-status"
    } else {
        &status
    };
    let breadcrumb = step5b_breadcrumb(&status);
    let needs_annotate = !unknown
        && (matches!(status.as_str(), "ready" | "label-only-retry")
            || (status == "skip-already-filed-sentinel"
                && !annotate_sequencing_error(oos_issue_stdout)));
    let mut rows = vec![
        format!("STEP5B_STATUS={emit_status}"),
        "OOS_PREP_RC=0".to_owned(),
        format!("OOS_ISSUE_STDOUT_PATH={}", oos_issue_stdout.display()),
        format!("NEXT_ACTION={next_action}"),
    ];
    if !breadcrumb.is_empty() {
        rows.push(format!("OOS_SKIP_BREADCRUMB={breadcrumb}"));
    }
    if needs_annotate {
        rows.push("STEP5B_NEEDS_ANNOTATE=true".to_owned());
    }
    println!("{}", rows.join("\n"));
    if !combined.is_empty() {
        println!("FILE_DESIGN_OOS_COMBINED={combined}");
    }
    if !deps_tsv.is_empty() {
        println!("FILE_DESIGN_OOS_DEPS_TSV={deps_tsv}");
    }
    if !deps_available.is_empty() {
        println!("FILE_DESIGN_OOS_DEPS_AVAILABLE={deps_available}");
    }
    if !unknown
        && matches!(
            status.as_str(),
            "skip-sentinel" | "skip-already-filed-sentinel" | "skip-no-items" | "skip-all-security"
        )
        && !needs_annotate
    {
        mark_step5b_complete(design_tmpdir);
    }
    write_prepare_env(prepare_env, stdout, &rows);
    next_action
}

fn step5b_context(
    arguments: &[OsString],
    label: &str,
) -> Result<(Env, PathBuf, PathBuf), ExitCode> {
    let common = match parse_common(arguments) {
        Ok(value) => value,
        Err(error) => {
            eprintln!("{label}: {error}");
            return Err(ExitCode::from(2));
        }
    };
    let env = hydrated_env(&common);
    let plugin_root = resolve_like_python(&require_plugin_root(env_get(
        &env,
        "CLAUDE_PLUGIN_ROOT",
        "",
    ))?);
    let raw = env_get(&env, "DESIGN_TMPDIR", "");
    if raw.is_empty() {
        let site = if label == STEP5B_PREPARE_LABEL {
            "prepare"
        } else {
            "annotate"
        };
        eprintln!("/design Step 5b {site}: DESIGN_TMPDIR required");
        return Err(ExitCode::from(1));
    }
    let design_tmpdir = PathBuf::from(raw);
    Ok((env, design_tmpdir, plugin_root))
}

/// Rust owner for `design step5b-prepare`.
pub fn step5b_prepare(arguments: &[OsString]) -> ExitCode {
    let (env, design_tmpdir, plugin_root) = match step5b_context(arguments, STEP5B_PREPARE_LABEL) {
        Ok(context) => context,
        Err(code) => return code,
    };
    let runner = LiveStep0Runner;
    let prelude = step5b_prelude(&runner, &plugin_root, &design_tmpdir, &env);
    if prelude != 0 {
        return ExitCode::from(u8::try_from(prelude).unwrap_or(1));
    }
    touch(&design_tmpdir.join(".completed/step-4b"));
    mark_design_timing(&runner, &plugin_root, "design Step 5 — finalize");
    let stderr_path = design_tmpdir.join("oos-filing-prepare.stderr.log");
    let child = run_larch(
        &runner,
        &plugin_root,
        step5b_prepare_args(&env, &design_tmpdir),
        &[],
    );
    write_text(&stderr_path, &child.stderr);
    let prepare_env = design_tmpdir.join("oos-filing-prepare.env");
    write_text(&prepare_env, &child.stdout);
    let oos_issue_stdout = design_tmpdir.join("oos-issue.stdout.txt");
    if child.code != 0 {
        append_failure_if_nonempty(
            &runner,
            &plugin_root,
            &design_tmpdir,
            "file-design-oos.sh prepare",
            child.code,
            "Tool Failures",
            &stderr_path,
        );
        println!(
            "**⚠ /design: OOS filing prepare failed; skipping /larch:issue; continuing to Step 5b.5**"
        );
        let rows = vec![
            "STEP5B_STATUS=prepare-failed-continue".to_owned(),
            format!("OOS_PREP_RC={}", child.code),
            format!("OOS_ISSUE_STDOUT_PATH={}", oos_issue_stdout.display()),
            "NEXT_ACTION=skip-pipeline".to_owned(),
        ];
        write_prepare_env(&prepare_env, &child.stdout, &rows);
        println!("{}", rows.join("\n"));
        mark_step5b_complete(&design_tmpdir);
        return ExitCode::SUCCESS;
    }
    if emit_prepare_success(
        &design_tmpdir,
        &prepare_env,
        &child.stdout,
        &oos_issue_stdout,
    ) == "unknown-oos-status"
    {
        println!(
            "**⚠ /design: unrecognized OOS prepare status; stop for repair before Step 5b.5**"
        );
        return ExitCode::from(2);
    }
    ExitCode::SUCCESS
}

fn issues_failed(path: &Path) -> bool {
    read_text_lossy(path).is_some_and(|text| {
        text.lines().any(|line| {
            line.strip_prefix("ISSUES_FAILED=").is_some_and(|value| {
                value
                    .as_bytes()
                    .first()
                    .is_some_and(|first| matches!(first, b'1'..=b'9'))
                    && value.as_bytes()[1..].iter().all(u8::is_ascii_digit)
            })
        })
    })
}

fn handle_empty_stdout_retry(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    stderr_path: &Path,
    exit_code: i32,
    verb: &str,
) -> i32 {
    let sentinel = design_tmpdir.join(".oos-issue-retry-used");
    if sentinel.is_file() {
        let args = append_failure_args(
            design_tmpdir
                .join("execution-issues.md")
                .display()
                .to_string(),
            "design Step 5b annotate-skip",
            "file-design-oos.sh annotate",
            &exit_code.to_string(),
            "Tool Failures",
            stderr_path,
        );
        let _ = run_larch(runner, plugin_root, args, &[]);
        println!(
            "**⚠ /design: annotate {verb} (empty issue stdout) after retry sentinel; stop before Step 5b.5**"
        );
        return 1;
    }
    write_text(&sentinel, "used\n");
    let args = append_failure_args(
        design_tmpdir
            .join("execution-issues.md")
            .display()
            .to_string(),
        "design Step 5b annotate-skip",
        "file-design-oos.sh annotate",
        &exit_code.to_string(),
        "Warnings",
        stderr_path,
    );
    let _ = run_larch(runner, plugin_root, args, &[]);
    println!(
        "**⚠ /design: annotate {verb} (empty issue stdout); status unclear; see execution-issues**"
    );
    1
}

fn annotation_failure(
    runner: &dyn Step0Runner,
    plugin_root: &Path,
    design_tmpdir: &Path,
    oos_issue_stdout: &Path,
    stderr_path: &Path,
    child: &ChildOutcome,
    label_only: bool,
) -> ExitCode {
    append_failure_if_nonempty(
        runner,
        plugin_root,
        design_tmpdir,
        "file-design-oos.sh annotate",
        child.code,
        "Tool Failures",
        stderr_path,
    );
    if issues_failed(oos_issue_stdout) {
        println!(
            "**⚠ /design: OOS filing completed with ISSUES_FAILED>0; see execution-issues and oos-issue.stdout.txt**"
        );
    }
    let rows = parse_stdout_kv(&child.stdout);
    let status = last_kv(&rows, "FILE_DESIGN_OOS_STATUS");
    if status == "annotate-failed-empty-stdout" && !last_kv(&rows, "WARN").is_empty() {
        return ExitCode::from(
            u8::try_from(handle_empty_stdout_retry(
                runner,
                plugin_root,
                design_tmpdir,
                stderr_path,
                child.code,
                "failed",
            ))
            .unwrap_or(1),
        );
    }
    if status == "annotate-label-failed"
        || design_tmpdir.join(".oos-priority-label-pending").is_file()
    {
        if !path_nonempty(stderr_path) {
            write_text(
                stderr_path,
                "design Step 5b: priority label application failed\n",
            );
            append_failure_if_nonempty(
                runner,
                plugin_root,
                design_tmpdir,
                "file-design-oos.sh annotate",
                child.code,
                "Tool Failures",
                stderr_path,
            );
        }
        println!("STEP5B_STATUS=annotate-label-failed");
        return ExitCode::from(u8::try_from(child.code).unwrap_or(1));
    }
    println!("STEP5B_STATUS=annotate-failed");
    if !label_only && !annotate_sequencing_error(oos_issue_stdout) {
        mark_step5b_complete(design_tmpdir);
    }
    ExitCode::from(u8::try_from(child.code).unwrap_or(1))
}

pub fn step5b_annotate(arguments: &[OsString]) -> ExitCode {
    let (env, design_tmpdir, plugin_root) = match step5b_context(arguments, STEP5B_ANNOTATE_LABEL) {
        Ok(context) => context,
        Err(code) => return code,
    };
    let runner = LiveStep0Runner;
    let oos_issue_stdout = design_tmpdir.join("oos-issue.stdout.txt");
    if design_tmpdir.join(".pause-requested").is_file() {
        return ExitCode::from(
            u8::try_from(call_pause_save(&runner, &plugin_root, &design_tmpdir, &env)).unwrap_or(1),
        );
    }
    let stderr_path = design_tmpdir.join("oos-filing-annotate.stderr.log");
    let prepare_env =
        read_text_lossy(&design_tmpdir.join("oos-filing-prepare.env")).unwrap_or_default();
    let prepare_rows = parse_stdout_kv(&prepare_env);
    let prepare_status = last_kv(&prepare_rows, "FILE_DESIGN_OOS_STATUS");
    let prepare_next_action = last_kv(&prepare_rows, "NEXT_ACTION");
    let label_only = prepare_status == "label-only-retry" || prepare_next_action == "label-only";
    let child = run_larch(
        &runner,
        &plugin_root,
        step5b_annotate_args(&env, &design_tmpdir, &oos_issue_stdout, label_only),
        &[],
    );
    write_text(&stderr_path, &child.stderr);
    write_text(
        &design_tmpdir.join("oos-filing-annotate.stdout.txt"),
        &child.stdout,
    );
    print_text(&child.stdout);
    println!("OOS_ANN_RC={}", child.code);
    if child.code != 0 {
        return annotation_failure(
            &runner,
            &plugin_root,
            &design_tmpdir,
            &oos_issue_stdout,
            &stderr_path,
            &child,
            label_only,
        );
    }
    let status = last_kv(&parse_stdout_kv(&child.stdout), "FILE_DESIGN_OOS_STATUS");
    if design_tmpdir.join(".oos-priority-label-pending").is_file() {
        println!("STEP5B_STATUS=annotate-label-failed");
        return ExitCode::from(1);
    }
    mark_step5b_complete(&design_tmpdir);
    let final_status = if status == "annotate-label-complete" {
        "annotate-label-complete"
    } else {
        "annotate-complete"
    };
    println!("STEP5B_STATUS={final_status}");
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use std::{
        cell::RefCell,
        fs,
        path::{Path, PathBuf},
    };

    use super::{
        ChildOutcome, Env, SettleRequest, Step0Runner, parse_next_action, parse_postplan_rc,
        step5b_annotate_args, step5b_next_action, step5b_prepare_args, step35_settle_for,
    };

    struct Runner {
        calls: RefCell<Vec<Vec<String>>>,
        dedup_code: i32,
        postplan: (i32, String),
        pause: (i32, String),
    }

    impl Runner {
        fn new(dedup_code: i32, postplan: &str, pause: &str) -> Self {
            Self {
                calls: RefCell::new(Vec::new()),
                dedup_code,
                postplan: (0, postplan.to_owned()),
                pause: (0, pause.to_owned()),
            }
        }
    }

    impl Step0Runner for Runner {
        fn run(
            &self,
            _plugin_root: &Path,
            args: &[String],
            _env: &[(String, String)],
            _merge_stderr: bool,
        ) -> ChildOutcome {
            self.calls.borrow_mut().push(args.to_vec());
            let (code, stdout) = match args.get(1).map(String::as_str) {
                Some("gate-b-dedup") => (self.dedup_code, String::new()),
                Some("step2b-postplan") => self.postplan.clone(),
                Some("pause-save") => self.pause.clone(),
                Some("settle-next-action") => (
                    0,
                    format!(
                        "SETTLE_NEXT_ACTION=ok\nSETTLE_EXIT_RC={}\n",
                        args.last().expect("postplan rc")
                    ),
                ),
                _ => (0, String::new()),
            };
            ChildOutcome {
                code,
                stdout,
                stderr: String::new(),
            }
        }
    }

    fn request(design_tmpdir: PathBuf, site: &str, round_num: &str) -> SettleRequest {
        SettleRequest {
            site: site.to_owned(),
            design_tmpdir,
            round_num: round_num.to_owned(),
            force_dedup: false,
            session_env_path: String::new(),
            claude_pid: String::new(),
            plugin_root: PathBuf::from("/tmp/larch-settle-test-plugin"),
            public_argv: Vec::new(),
            issue_number: "1".to_owned(),
            repo: String::new(),
            final_round_num: String::new(),
            step3_review_round_num: String::new(),
            env_round_num: String::new(),
        }
    }

    fn design_dir() -> (tempfile::TempDir, PathBuf) {
        let temp = tempfile::TempDir::new().expect("tempdir");
        let design = temp.path().join("design");
        fs::create_dir_all(&design).expect("design dir");
        (temp, design)
    }

    #[test]
    fn parser_keeps_postplan_first_row_and_counts_duplicates() {
        assert_eq!(
            parse_postplan_rc("POSTPLAN_RC=0\nPOSTPLAN_RC=12\n"),
            ("0".to_owned(), 2)
        );
    }

    #[test]
    fn next_action_uses_last_rows_and_optional_exit() {
        assert_eq!(
            parse_next_action(
                "SETTLE_NEXT_ACTION=first\nSETTLE_EXIT_RC=nope\nSETTLE_NEXT_ACTION=last\nSETTLE_EXIT_RC=11\n"
            ),
            ("last".to_owned(), Some(11))
        );
    }

    #[test]
    fn settlement_routes_each_site_and_persists_gate_b_state() {
        for (site, postplan_site) in [
            ("gate-b", "gate-b"),
            ("gate-a", "discussion-round2"),
            ("discussion-round2", "discussion-round2"),
            ("gate-c", "gate-c"),
        ] {
            let (_temp, design) = design_dir();
            let runner = Runner::new(0, "POSTPLAN_RC=0\n", "");
            assert_eq!(
                step35_settle_for(&request(design.clone(), site, "3"), &runner),
                0
            );
            let calls = runner.calls.borrow();
            let postplan = calls
                .iter()
                .find(|call| call.get(1).is_some_and(|verb| verb == "step2b-postplan"))
                .expect("step2b-postplan call");
            assert_eq!(postplan.last().map(String::as_str), Some(postplan_site));
            assert!(calls.iter().any(|call| {
                call.get(1)
                    .is_some_and(|verb| verb == "dialectic-clear-stale")
            }));
            if site == "gate-b" {
                assert_eq!(
                    fs::read_to_string(design.join(".gate-b-postapply-ready-3")).unwrap(),
                    "ready\n"
                );
                assert_eq!(
                    fs::read_to_string(design.join(".step3-round-3.phase")).unwrap(),
                    "awaiting-continuation\n"
                );
            }
        }
    }

    #[test]
    fn settlement_preserves_postplan_and_dedup_recovery() {
        for (postplan, expected_rc, phase) in [
            ("POSTPLAN_RC=10\n", 10, "awaiting-postplan-operator\n"),
            ("POSTPLAN_RC=12\n", 12, "awaiting-post-apply\n"),
            ("POSTPLAN_RC=13\n", 13, "awaiting-postplan-operator\n"),
        ] {
            let (_temp, design) = design_dir();
            let runner = Runner::new(0, postplan, "");
            assert_eq!(
                step35_settle_for(&request(design.clone(), "gate-b", "7"), &runner),
                expected_rc
            );
            assert_eq!(
                fs::read_to_string(design.join(".step3-round-7.phase")).unwrap(),
                phase
            );
        }
        let (_temp, design) = design_dir();
        fs::write(design.join("plan-pre-apply-round-9.txt"), "snapshot\n").unwrap();
        fs::write(design.join("plan.txt"), "mutated\n").unwrap();
        let runner = Runner::new(1, "POSTPLAN_RC=0\n", "");
        assert_eq!(
            step35_settle_for(&request(design.clone(), "gate-b", "9"), &runner),
            1
        );
        assert_eq!(
            fs::read_to_string(design.join("plan.txt")).unwrap(),
            "snapshot\n"
        );
    }

    #[test]
    fn settlement_refuses_invalid_output_and_honors_pause_and_resume() {
        let (_temp, design) = design_dir();
        let runner = Runner::new(0, "POSTPLAN_RC=0\nPOSTPLAN_RC=0\n", "");
        assert_eq!(
            step35_settle_for(&request(design, "gate-a", ""), &runner),
            3
        );

        let (_temp, design) = design_dir();
        fs::write(design.join(".gate-b-postapply-ready-4"), "ready\n").unwrap();
        let runner = Runner::new(3, "POSTPLAN_RC=0\n", "");
        assert_eq!(
            step35_settle_for(&request(design, "gate-b", "4"), &runner),
            0
        );
        assert!(
            runner
                .calls
                .borrow()
                .iter()
                .all(|args| args.get(1) != Some(&"gate-b-dedup".to_owned()))
        );

        let (_temp, design) = design_dir();
        fs::write(design.join(".pause-requested"), "").unwrap();
        let runner = Runner::new(0, "POSTPLAN_RC=0\n", "PAUSE_OK=true\n");
        assert_eq!(
            step35_settle_for(&request(design, "gate-a", ""), &runner),
            11
        );
        assert_eq!(
            runner.calls.borrow()[0].get(1).map(String::as_str),
            Some("pause-save")
        );
    }

    #[test]
    fn step5b_actions_are_closed_sets() {
        assert_eq!(step5b_next_action("ready"), "file-issues");
        assert_eq!(step5b_next_action("unknown"), "unknown-oos-status");
    }

    #[test]
    fn step5b_oos_commands_use_rust_routes_and_session_authorization() {
        let design = PathBuf::from("/tmp/larch-design-step5b");
        let mut env = Env::new();
        env.insert("ISSUE_NUMBER".to_owned(), "8590".to_owned());
        env.insert("REPO".to_owned(), "character-ai/larch".to_owned());
        env.insert("LARCH_RUN_ID".to_owned(), "design-run-8590".to_owned());

        assert_eq!(
            step5b_prepare_args(&env, &design),
            [
                "design",
                "file-oos-prepare",
                "--design-tmpdir",
                "/tmp/larch-design-step5b",
                "--issue-number",
                "8590",
                "--repo",
                "character-ai/larch",
            ]
        );
        assert_eq!(
            step5b_annotate_args(&env, &design, &design.join("oos-issue.stdout.txt"), true),
            [
                "design",
                "file-oos-annotate",
                "--design-tmpdir",
                "/tmp/larch-design-step5b",
                "--issue-stdout-file",
                "/tmp/larch-design-step5b/oos-issue.stdout.txt",
                "--issue-number",
                "8590",
                "--repo",
                "character-ai/larch",
                "--context-file",
                "/tmp/larch-design-step5b/source-env.sh",
                "--run-id",
                "design-run-8590",
                "--trusted-root",
                "/tmp/larch-design-step5b",
                "--label-only",
            ]
        );
    }
}
