//! Rust owner for the deferred Step 3 `MainAgent` vote and re-tally flow.

use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs::{self, File},
    io::{self, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
    time::{SystemTime, UNIX_EPOCH},
};

use larch_adapters::{ensure_directory_chain, validate_design_tmpdir};
use larch_core::{
    ChildEnvironment, DuplicatePolicy, KvDocument, ParseOptions, ProcessOutput,
    cleanup_cache_sessions_root, emit_kv, positive_integer, private_atomic_write,
};
use tempfile::NamedTempFile;

use crate::{
    design_step0_commands::{
        load_source_env_allowed, pause_save_arguments, phase_driver_read_result_env,
        replay_result_env_warn_error, require_plugin_root,
    },
    design_step1_commands::append_failure_args,
    plan_review_commands::step3_round_timing_arguments,
    runtime_entrypoint::{
        run_verified_larch_from_root_with_environment, validate_verified_plugin_root,
    },
};

// Keep the retired script name in the public diagnostics: callers and clean-install
// tests treat these strings as a frozen compatibility surface.
const PROGRAM: &str = "design-step3-mav.sh";
const USAGE: &str = "usage: design-step3-mav.sh --phase pre|post --session-env-path PATH --claude-pid PID --plugin-root PATH";
const FRAME_BEGIN: &str = "DESIGN_STEP3_MAV_KV_BEGIN";
const FRAME_END: &str = "DESIGN_STEP3_MAV_KV_END";
const RESULT_ENV_KEYS: &[&str] = &[
    "LOOP_STATUS",
    "STEP3_REVIEW_LOOP_STATUS",
    "TALLY_PLAN_REVIEW_STATUS",
    "ACCEPTED_COUNT",
    "IMPORTANT_ACCEPTED_COUNT",
    "SCOPE_ANCHOR_FILE",
    "STEP3_REVIEW_ROUND_NUM",
    "ROUND_NUM",
    "ROUNDS_COMPLETED",
    "REVIEW_ROUND_COUNT",
    "FINAL_ROUND_NUM",
];
const SESSION_ENV_KEYS: &[&str] = &[
    "DESIGN_TMPDIR",
    "ISSUE_NUMBER",
    "REPO",
    "STEP3_REVIEW_LOOP_STATUS",
    "LOOP_STATUS",
    "TALLY_PLAN_REVIEW_STATUS",
    "SCOPE_ANCHOR_FILE",
    "STEP3_REVIEW_ROUND_NUM",
    "ROUND_NUM",
    "ROUNDS_COMPLETED",
    "REVIEW_ROUND_COUNT",
    "FINAL_ROUND_NUM",
    "ACCEPTED_COUNT",
    "IMPORTANT_ACCEPTED_COUNT",
];

#[derive(Default)]
struct Options {
    session_env_path: String,
    claude_pid: String,
    plugin_root: String,
    phase: String,
}

struct MavRuntime<'a> {
    design_root: &'a Path,
    plugin_root: &'a Path,
}

impl MavRuntime<'_> {
    fn run_child(&self, arguments: &[OsString]) -> Result<ProcessOutput, String> {
        run_verified_larch_from_root_with_environment(
            self.plugin_root,
            arguments,
            &child_environment(self.design_root),
        )
    }
}

fn usage() {
    eprintln!("{USAGE}");
}

fn exit_code(code: i32) -> ExitCode {
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

fn parse_options(arguments: &[OsString]) -> Result<Option<Options>, ExitCode> {
    let mut options = Options {
        plugin_root: env::var("CLAUDE_PLUGIN_ROOT").unwrap_or_default(),
        ..Options::default()
    };
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_string_lossy();
        if token == "--help" || token == "-h" {
            usage();
            return Ok(None);
        }
        let target = match token.as_ref() {
            "--session-env-path" => &mut options.session_env_path,
            "--claude-pid" => &mut options.claude_pid,
            "--plugin-root" => &mut options.plugin_root,
            "--phase" => &mut options.phase,
            _ => {
                eprintln!("{PROGRAM}: unknown argument: {token}");
                usage();
                return Err(ExitCode::from(2));
            }
        };
        let Some(value) = arguments.get(index + 1) else {
            usage();
            return Err(ExitCode::from(2));
        };
        *target = value.to_string_lossy().into_owned();
        index += 2;
    }
    if !matches!(options.phase.as_str(), "pre" | "post") {
        usage();
        return Err(ExitCode::from(2));
    }
    Ok(Some(options))
}

fn initial_state(options: &Options) -> BTreeMap<String, String> {
    let mut state = BTreeMap::new();
    for key in SESSION_ENV_KEYS {
        let _ = state.insert((*key).to_owned(), env::var(key).unwrap_or_default());
    }
    for (key, value) in load_source_env_allowed(
        &options.session_env_path,
        &options.claude_pid,
        SESSION_ENV_KEYS,
    ) {
        let _ = state.insert(key, value);
    }
    state
}

fn state_value<'a>(state: &'a BTreeMap<String, String>, key: &str) -> &'a str {
    state.get(key).map_or("", String::as_str)
}

fn design_tmpdir(state: &BTreeMap<String, String>) -> Result<PathBuf, ExitCode> {
    let raw = state_value(state, "DESIGN_TMPDIR");
    let path = Path::new(raw);
    if raw.is_empty() || !path.is_dir() {
        eprintln!("/design Step 3 MAV: DESIGN_TMPDIR required");
        return Err(ExitCode::FAILURE);
    }
    if path.is_symlink() {
        eprintln!("/design Step 3 MAV: DESIGN_TMPDIR must not be a symlink");
        return Err(ExitCode::from(2));
    }
    if let Err(error) = validate_design_tmpdir(
        raw,
        env::var_os("TMPDIR").as_deref(),
        &cleanup_cache_sessions_root(
            env::var_os("XDG_CACHE_HOME").as_deref(),
            env::var_os("HOME").as_deref(),
        ),
    ) {
        eprintln!("/design Step 3 MAV: {error}");
        return Err(ExitCode::from(2));
    }
    fs::canonicalize(path).map_err(|error| {
        eprintln!("/design Step 3 MAV: {error}");
        ExitCode::FAILURE
    })
}

fn child_environment(root: &Path) -> [(ChildEnvironment, OsString); 1] {
    [(ChildEnvironment::DesignTmpdir, root.as_os_str().to_owned())]
}

fn forward(output: &ProcessOutput) {
    let _ = io::stdout().write_all(output.stdout());
    let _ = io::stderr().write_all(output.stderr());
}

fn child_code(output: &ProcessOutput) -> i32 {
    output.status().code().unwrap_or(1)
}

fn run_pause(runtime: &MavRuntime<'_>, state: &BTreeMap<String, String>) -> ExitCode {
    let arguments = pause_save_arguments(
        runtime.design_root,
        state_value(state, "ISSUE_NUMBER"),
        state_value(state, "REPO"),
    );
    match runtime.run_child(&arguments) {
        Ok(output) => {
            forward(&output);
            exit_code(child_code(&output))
        }
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}

fn overlay_result_env(path: &Path, state: &mut BTreeMap<String, String>) -> Result<(), String> {
    let metadata = match fs::symlink_metadata(path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(()),
        Err(error) => return Err(error.to_string()),
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(format!(
            "result env is not a regular file: {}",
            path.display()
        ));
    }
    replay_result_env_warn_error(path);
    let rows = phase_driver_read_result_env(path, RESULT_ENV_KEYS)
        .map_err(|()| format!("failed to read result env: {}", path.display()))?;
    for (key, value) in rows {
        let _ = state.insert(key, value);
    }
    Ok(())
}

fn read_step3_result_state(
    root: &Path,
    state: &mut BTreeMap<String, String>,
) -> Result<(), String> {
    overlay_result_env(&root.join(".step3-plan-review-result.env"), state)?;
    overlay_result_env(&root.join(".step3-review-result.env"), state)
}

fn artifact_round(state: &BTreeMap<String, String>) -> u64 {
    [
        "ROUND_NUM",
        "ROUNDS_COMPLETED",
        "STEP3_REVIEW_ROUND_NUM",
        "REVIEW_ROUND_COUNT",
    ]
    .into_iter()
    .find_map(|key| positive_integer(state_value(state, key)))
    .unwrap_or(1)
}

fn resume_round(state: &BTreeMap<String, String>) -> Option<u64> {
    [
        "FINAL_ROUND_NUM",
        "STEP3_REVIEW_ROUND_NUM",
        "ROUND_NUM",
        "ROUNDS_COMPLETED",
        "REVIEW_ROUND_COUNT",
    ]
    .into_iter()
    .find_map(|key| positive_integer(state_value(state, key)))
}

fn emit_checked(key: &str, value: &str) -> Result<(), ExitCode> {
    if value.contains(['\n', '\r']) {
        eprintln!("emit_kv: value for key {key} must not contain newline or carriage return");
        return Err(ExitCode::from(2));
    }
    emit_kv(key, value);
    Ok(())
}

fn emit_pre_frame(
    root: &Path,
    state: &BTreeMap<String, String>,
    round: Option<u64>,
) -> Result<(), ExitCode> {
    println!("{FRAME_BEGIN}");
    emit_checked(
        "BALLOT_PATH",
        &root.join("ballot.txt").display().to_string(),
    )?;
    for key in [
        "SCOPE_ANCHOR_FILE",
        "TALLY_PLAN_REVIEW_STATUS",
        "STEP3_REVIEW_LOOP_STATUS",
    ] {
        let value = state_value(state, key);
        if !value.is_empty() {
            emit_checked(key, value)?;
        }
    }
    if let Some(round) = round {
        emit_checked("STEP3_RESUME_ROUND", &round.to_string())?;
    }
    println!("{FRAME_END}");
    Ok(())
}

fn sanitized_diagnostic(line: &str) -> String {
    line.chars()
        .filter(|character| !character.is_control())
        .collect()
}

fn run_pre(runtime: &MavRuntime<'_>, state: &mut BTreeMap<String, String>) -> ExitCode {
    let root = runtime.design_root;
    if read_step3_result_state(root, state).is_err() {
        eprintln!("**⚠ Step 3 MAV: could not read Step 3 result env**");
        return ExitCode::FAILURE;
    }
    let scope_anchor = state_value(state, "SCOPE_ANCHOR_FILE").to_owned();
    if !scope_anchor.is_empty() {
        println!("## MainAgent scope anchor evidence");
        let arguments = vec![
            "render".into(),
            "scope-anchor".into(),
            "--scope-anchor-file".into(),
            scope_anchor.into(),
            "--design-tmpdir".into(),
            root.as_os_str().to_owned(),
        ];
        let output = match runtime.run_child(&arguments) {
            Ok(output) => output,
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        };
        let stderr_path = root.join("step3-mav-scope-anchor.err");
        if private_atomic_write(
            &stderr_path,
            &String::from_utf8_lossy(output.stderr()),
            root,
        )
        .is_err()
        {
            return ExitCode::FAILURE;
        }
        if !output.status().success() {
            for line in String::from_utf8_lossy(output.stderr()).lines() {
                eprintln!("{}", sanitized_diagnostic(line));
            }
            return exit_code(child_code(&output));
        }
        let rendered = String::from_utf8_lossy(output.stdout());
        let rendered = rendered.trim_end_matches('\n');
        for line in rendered.split('\n') {
            println!("SCOPE_ANCHOR_EVIDENCE: {line}");
        }
    }
    match emit_pre_frame(root, state, resume_round(state)) {
        Ok(()) => ExitCode::SUCCESS,
        Err(code) => code,
    }
}

fn write_confined(root: &Path, path: &Path, body: &str) -> Result<(), ExitCode> {
    private_atomic_write(path, body, root).map_err(|error| {
        eprintln!("{PROGRAM}: {error}");
        ExitCode::FAILURE
    })
}

fn readable(path: &Path) -> bool {
    File::open(path).is_ok()
}

fn replay_lines(text: &str) {
    for line in text.split_terminator('\n') {
        println!("{line}");
    }
}

fn last_kv_value(text: &str, key: &str) -> String {
    KvDocument::parse(text, ParseOptions::legacy())
        .expect("legacy parser accepts every tally result")
        .select(DuplicatePolicy::Last)
        .remove(key)
        .unwrap_or_default()
}

fn append_warning_once(runtime: &MavRuntime<'_>, round: u64) -> Result<(), ExitCode> {
    let root = runtime.design_root;
    let warning_path = root.join(format!(
        "step3-main-agent-adjudication-r{round}.warning.log"
    ));
    let sentinel = root.join(format!(
        ".step3-main-agent-adjudication-warning-appended-r{round}"
    ));
    if sentinel.is_file() {
        return Ok(());
    }
    write_confined(
        root,
        &warning_path,
        "Step 3 — 0-judge plan-review panel: main-agent adjudication performed\n",
    )?;
    let arguments = append_failure_args(
        root.join("execution-issues.md").display().to_string(),
        "design Step 3",
        "MainAgent plan-review adjudication",
        "0",
        "Warnings",
        &warning_path,
    )
    .into_iter()
    .map(OsString::from)
    .collect::<Vec<_>>();
    let _ignored = runtime.run_child(&arguments);
    write_confined(root, &sentinel, "")
}

fn accepted_count(root: &Path) -> usize {
    let path = root.join("accepted-plan-findings.md");
    if !path.metadata().is_ok_and(|metadata| metadata.len() > 0) {
        return 0;
    }
    fs::read_to_string(path).map_or(0, |body| {
        body.lines()
            .filter(|line| {
                let Some(rest) = line.strip_prefix("### FINDING_") else {
                    return false;
                };
                let Some((number, _title)) = rest.split_once(':') else {
                    return false;
                };
                !number.is_empty() && number.bytes().all(|byte| byte.is_ascii_digit())
            })
            .count()
    })
}

fn record_round_timing(runtime: &MavRuntime<'_>, round: u64) {
    let root = runtime.design_root;
    let start_path = root
        .join("plan-review")
        .join(format!("round-{round}"))
        .join("round-start-s");
    if !start_path
        .metadata()
        .is_ok_and(|metadata| metadata.len() > 0)
    {
        return;
    }
    let start = fs::read(start_path).map_or_else(
        |_| String::new(),
        |bytes| {
            bytes
                .into_iter()
                .filter(|byte| !byte.is_ascii_whitespace())
                .map(char::from)
                .collect()
        },
    );
    let Some(start) = positive_integer(&start) else {
        return;
    };
    let end = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |duration| duration.as_secs());
    let arguments = step3_round_timing_arguments(root, round, start, end);
    match runtime.run_child(&arguments) {
        Ok(output) => forward(&output),
        Err(error) => eprintln!("{error}"),
    }
}

fn emit_post_frame(
    state: &BTreeMap<String, String>,
    tally_status: &str,
    count: usize,
    phase: &str,
    round: Option<u64>,
) -> Result<(), ExitCode> {
    println!("{FRAME_BEGIN}");
    if tally_status == "tally-error" {
        emit_checked("NEXT_ACTION", "step3b-bypass")?;
    }
    emit_checked("TALLY_PLAN_REVIEW_STATUS", tally_status)?;
    emit_checked("LOOP_STATUS", "complete")?;
    emit_checked("ACCEPTED_COUNT", &count.to_string())?;
    emit_checked("PHASE", phase)?;
    if let Some(round) = round {
        emit_checked("STEP3_RESUME_ROUND", &round.to_string())?;
    }
    let loop_status = state_value(state, "STEP3_REVIEW_LOOP_STATUS");
    if !loop_status.is_empty() {
        emit_checked("STEP3_REVIEW_LOOP_STATUS", loop_status)?;
    }
    println!("{FRAME_END}");
    Ok(())
}

fn missing_voter_retally(
    runtime: &MavRuntime<'_>,
    classification_path: &Path,
) -> Result<String, ExitCode> {
    let root = runtime.design_root;
    let header =
        match runtime.run_child(&["voting".into(), "findings-classification-header".into()]) {
            Ok(output) => output,
            Err(error) => {
                eprintln!("{error}");
                return Err(ExitCode::FAILURE);
            }
        };
    write_confined(
        root,
        classification_path,
        &String::from_utf8_lossy(header.stdout()),
    )?;
    let code = child_code(&header);
    let _ = io::stderr().write_all(header.stderr());
    if code != 0 {
        return Err(exit_code(code));
    }
    write_confined(
        root,
        &root.join("voting-tally.md"),
        "# Plan Review Voting Tally\n\n**⚠ Tally aborted: MainAgent voter file unreadable; no votes tallied.**\n",
    )?;
    Ok(format!(
        "TALLY_PLAN_REVIEW_STATUS=tally-error\nVOTING_TALLY_FILE={}/voting-tally.md\n",
        root.display()
    ))
}

fn run_tally(
    runtime: &MavRuntime<'_>,
    classification_path: &Path,
) -> Result<(String, i32), ExitCode> {
    let root = runtime.design_root;
    let voter = root.join("voter-main-agent.txt");
    if !readable(&voter) {
        return missing_voter_retally(runtime, classification_path).map(|text| (text, 0));
    }
    let mut arguments = vec![
        "plan-review".into(),
        "tally".into(),
        "--ballot-file".into(),
        root.join("ballot.txt").into_os_string(),
        "--design-tmpdir".into(),
        root.as_os_str().to_owned(),
        "--voter".into(),
        format!("MainAgent:{}", voter.display()).into(),
        "--findings-classification-out".into(),
        classification_path.as_os_str().to_owned(),
    ];
    let proposer_map = root.join("proposer-map.tsv");
    if readable(&proposer_map) {
        arguments.push("--proposer-map-file".into());
        arguments.push(proposer_map.into_os_string());
    }
    match runtime.run_child(&arguments) {
        Ok(output) => {
            let _ = io::stderr().write_all(output.stderr());
            Ok((
                String::from_utf8_lossy(output.stdout()).into_owned(),
                child_code(&output),
            ))
        }
        Err(error) => {
            eprintln!("{error}");
            Ok((String::new(), 1))
        }
    }
}

fn persist_retally(
    runtime: &MavRuntime<'_>,
    retally_file: &Path,
    input_anchor: &str,
    tally_status: &str,
) -> Result<(), ExitCode> {
    let root = runtime.design_root;
    let mut arguments = vec![
        "plan-review".into(),
        "persist-retally-env".into(),
        "--design-tmpdir".into(),
        root.as_os_str().to_owned(),
        "--retally-stdout-file".into(),
        retally_file.as_os_str().to_owned(),
    ];
    if !input_anchor.is_empty() {
        arguments.push("--retally-input-anchor".into());
        arguments.push(input_anchor.into());
    }
    arguments.extend([
        "--tally-plan-review-status".into(),
        tally_status.into(),
        "--loop-status".into(),
        "complete".into(),
    ]);
    match runtime.run_child(&arguments) {
        Ok(output) => {
            forward(&output);
            let code = child_code(&output);
            if code == 0 {
                Ok(())
            } else {
                Err(exit_code(code))
            }
        }
        Err(error) => {
            eprintln!("{error}");
            Err(ExitCode::FAILURE)
        }
    }
}

fn run_post(runtime: &MavRuntime<'_>, state: &mut BTreeMap<String, String>) -> ExitCode {
    let root = runtime.design_root;
    if read_step3_result_state(root, state).is_err() {
        eprintln!("**⚠ Step 3 MAV: could not read Step 3 result env**");
        return ExitCode::FAILURE;
    }
    let loop_mode = !state_value(state, "STEP3_REVIEW_LOOP_STATUS").is_empty();
    let artifact_round = artifact_round(state);
    let resume_round = resume_round(state);
    if loop_mode && resume_round.is_none() {
        eprintln!("**⚠ Step 3 MAV: STEP3_RESUME_ROUND missing or invalid**");
        return ExitCode::FAILURE;
    }
    let input_anchor = state_value(state, "SCOPE_ANCHOR_FILE").to_owned();
    let round_dir = root
        .join("plan-review")
        .join(format!("round-{artifact_round}"));
    if let Err(error) = ensure_directory_chain(&round_dir) {
        eprintln!("{PROGRAM}: {error}");
        return ExitCode::FAILURE;
    }
    let classification_path = round_dir.join("findings-classification.tsv");
    let mut retally_file = match NamedTempFile::new_in(env::temp_dir()) {
        Ok(file) => file,
        Err(error) => {
            eprintln!("{PROGRAM}: {error}");
            return ExitCode::FAILURE;
        }
    };
    let (retally_text, retally_code) = match run_tally(runtime, &classification_path) {
        Ok(result) => result,
        Err(code) => return code,
    };
    if retally_file.write_all(retally_text.as_bytes()).is_err() || retally_file.flush().is_err() {
        return ExitCode::FAILURE;
    }
    let tally_status = if last_kv_value(&retally_text, "TALLY_PLAN_REVIEW_STATUS") == "ok" {
        "ok"
    } else {
        "tally-error"
    };
    if let Err(code) = persist_retally(runtime, retally_file.path(), &input_anchor, tally_status) {
        return code;
    }
    if let Err(code) = append_warning_once(runtime, artifact_round) {
        return code;
    }
    let count = accepted_count(root);
    let mut phase = "unchanged";
    if tally_status == "ok" {
        record_round_timing(runtime, artifact_round);
        if loop_mode {
            phase = if count == 0 {
                "awaiting-continuation"
            } else {
                "awaiting-apply"
            };
            let phase_path = root.join(format!(
                ".step3-round-{}.phase",
                resume_round.expect("loop mode validated a resume round")
            ));
            if let Err(code) = write_confined(root, &phase_path, &format!("{phase}\n")) {
                return code;
            }
        }
    }
    if let Err(code) = emit_post_frame(state, tally_status, count, phase, resume_round) {
        return code;
    }
    replay_lines(&retally_text);
    if retally_code == 2 && tally_status != "tally-error" {
        ExitCode::from(2)
    } else {
        ExitCode::SUCCESS
    }
}

/// Run the deferred Step 3 `MainAgent` transaction.
#[must_use]
pub fn run(arguments: &[OsString]) -> ExitCode {
    let options = match parse_options(arguments) {
        Ok(Some(options)) => options,
        Ok(None) => return ExitCode::SUCCESS,
        Err(code) => return code,
    };
    let declared_plugin_root = match require_plugin_root(&options.plugin_root) {
        Ok(root) => root,
        Err(code) => return code,
    };
    let plugin_root = match validate_verified_plugin_root(&declared_plugin_root) {
        Ok(root) => root,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    let mut state = initial_state(&options);
    let root = match design_tmpdir(&state) {
        Ok(root) => root,
        Err(code) => return code,
    };
    let runtime = MavRuntime {
        design_root: &root,
        plugin_root: &plugin_root,
    };
    if root.join(".pause-requested").is_file() {
        return run_pause(&runtime, &state);
    }
    match options.phase.as_str() {
        "pre" => run_pre(&runtime, &mut state),
        "post" => run_post(&runtime, &mut state),
        _ => unreachable!("phase validated by parse_options"),
    }
}
