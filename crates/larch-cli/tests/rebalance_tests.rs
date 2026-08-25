use assert_cmd::Command;
use serde_json::Value;
use std::process::Output;

fn larch() -> Command {
    Command::cargo_bin("larch").expect("larch binary should build")
}

fn run(verb: &str, input: &str) -> Output {
    larch()
        .args(["rebalance-tests", verb])
        .write_stdin(input)
        .output()
        .expect("rebalance-tests command should launch")
}

fn stdout(output: &Output) -> String {
    String::from_utf8(output.stdout.clone()).expect("stdout should be UTF-8")
}

fn stderr(output: &Output) -> String {
    String::from_utf8(output.stderr.clone()).expect("stderr should be UTF-8")
}

fn result(verb: &str, input: &str, success: bool) -> Value {
    let output = run(verb, input);
    assert_eq!(output.status.success(), success, "{}", stderr(&output));
    assert_eq!(stderr(&output), "");
    serde_json::from_str(&stdout(&output)).expect("valid result JSON")
}

fn invalid(verb: &str, input: &str, message: &str) {
    let output = run(verb, input);
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(stdout(&output), "");
    assert!(stderr(&output).contains(message), "{}", stderr(&output));
}

const NOOP_HARNESS_TIMING: &str = r#"{"schema_version":2,"kind":"harness","sampled_run_ids":[11,12],"rows":[{"run_id":11,"shard":1,"target":"test-a","seconds":20.0},{"run_id":11,"shard":2,"target":"test-c","seconds":15.0},{"run_id":11,"shard":2,"target":"test-b","seconds":10.0},{"run_id":12,"shard":1,"target":"test-a","seconds":20.0},{"run_id":12,"shard":2,"target":"test-c","seconds":15.0},{"run_id":12,"shard":2,"target":"test-b","seconds":10.0}],"bootstrap_rows":[{"run_id":11,"shard":1,"target":"test-a","bootstrap_kind":"cold","seconds":10.0},{"run_id":11,"shard":2,"target":"test-c","bootstrap_kind":"cold","seconds":10.0},{"run_id":11,"shard":2,"target":"test-b","bootstrap_kind":"warm","seconds":1.0},{"run_id":12,"shard":1,"target":"test-a","bootstrap_kind":"cold","seconds":10.0},{"run_id":12,"shard":2,"target":"test-c","bootstrap_kind":"cold","seconds":10.0},{"run_id":12,"shard":2,"target":"test-b","bootstrap_kind":"warm","seconds":1.0}],"target_medians":[{"target":"test-a","seconds":20.0},{"target":"test-c","seconds":15.0},{"target":"test-b","seconds":10.0}],"shard_medians":[{"shard":1,"seconds":20.0},{"shard":2,"seconds":25.0}],"untimed_targets":[],"skipped_run_ids":[]}"#;

const NOOP_JOBS: &str = r#"{"schema_version":2,"kind":"jobs","sampled_run_ids":[11,12],"rows":[{"run_id":11,"shard":1,"seconds":130.0},{"run_id":11,"shard":2,"seconds":136.0},{"run_id":12,"shard":1,"seconds":130.0},{"run_id":12,"shard":2,"seconds":136.0}],"shard_medians":[{"shard":1,"seconds":130.0},{"shard":2,"seconds":136.0}],"skipped_run_ids":[]}"#;

const NOOP_SHARDS: &str = r#"{"1":["test-a"],"2":["test-c","test-b"]}"#;

fn harness_plan_request(max_shard_wall_clock: f64, override_note: &str) -> String {
    format!(
        r#"{{"schema_version":2,"kind":"plan","selection":"harness","options":{{"max_shard_wall_clock":{max_shard_wall_clock},"experimental_wall_clock_override":{override_note},"compile_affinities":[]}},"harness":{{"expected_run_ids":[11,12],"current_shards":{NOOP_SHARDS},"timing":{NOOP_HARNESS_TIMING},"jobs":{NOOP_JOBS}}},"rust":null}}"#
    )
}

fn harness_verify_request(
    max_shard_wall_clock: f64,
    approved_slowest_wall_clock: f64,
    override_note: &str,
) -> String {
    format!(
        r#"{{"schema_version":2,"kind":"verify","selection":"harness","options":{{"max_shard_wall_clock":{max_shard_wall_clock},"experimental_wall_clock_override":{override_note}}},"harness":{{"expected_run_ids":[11,12],"expected_shards":{NOOP_SHARDS},"baseline_slowest_wall_clock":136.0,"baseline_runner_seconds":266.0,"approved_slowest_wall_clock":{approved_slowest_wall_clock},"timing":{NOOP_HARNESS_TIMING},"jobs":{NOOP_JOBS}}},"rust":null}}"#
    )
}

const RUST_MONOLITHIC_TIMING: &str = r#"{"schema_version":2,"kind":"rust-jobs","sampled_run_ids":[11,12],"rows":[{"run_id":11,"shard":1,"seconds":711.0},{"run_id":12,"shard":1,"seconds":693.0}],"shard_medians":[{"shard":1,"seconds":702.0}],"skipped_run_ids":[]}"#;

const RUST_FOUR_SHARD_TIMING: &str = r#"{"schema_version":2,"kind":"rust-jobs","sampled_run_ids":[21,22],"rows":[{"run_id":21,"shard":1,"seconds":563.0},{"run_id":21,"shard":2,"seconds":431.0},{"run_id":21,"shard":3,"seconds":428.0},{"run_id":21,"shard":4,"seconds":425.0},{"run_id":22,"shard":1,"seconds":557.0},{"run_id":22,"shard":2,"seconds":435.0},{"run_id":22,"shard":3,"seconds":430.0},{"run_id":22,"shard":4,"seconds":427.0}],"shard_medians":[{"shard":1,"seconds":560.0},{"shard":2,"seconds":433.0},{"shard":3,"seconds":429.0},{"shard":4,"seconds":426.0}],"skipped_run_ids":[]}"#;

fn rust_plan_request(target_shards: u32) -> String {
    format!(
        r#"{{"schema_version":2,"kind":"plan","selection":"rust","options":{{"max_shard_wall_clock":300.0,"max_rust_shard_wall_clock":600.0,"n_rust_shards":{target_shards},"experimental_wall_clock_override":null,"compile_affinities":[]}},"harness":null,"rust":{{"expected_run_ids":[11,12],"current_shard_count":1,"timing":{RUST_MONOLITHIC_TIMING}}}}}"#
    )
}

fn rust_verify_request(timing: &str) -> String {
    format!(
        r#"{{"schema_version":2,"kind":"verify","selection":"rust","options":{{"max_shard_wall_clock":300.0,"max_rust_shard_wall_clock":600.0,"experimental_wall_clock_override":null}},"harness":null,"rust":{{"expected_run_ids":[21,22],"expected_shard_count":4,"baseline_shard_count":1,"baseline_slowest_wall_clock":702.0,"approved_slowest_wall_clock":600.0,"timing":{timing}}}}}"#
    )
}

#[test]
fn plan_noop_fixture_is_byte_stable_at_the_threshold_boundary() {
    let request = harness_plan_request(136.0, "null");
    let first = run("plan", &request);
    let second = run("plan", &request);

    assert!(first.status.success(), "{}", stderr(&first));
    assert!(second.status.success(), "{}", stderr(&second));
    assert_eq!(stdout(&first), stdout(&second));
    assert_eq!(stderr(&first), "");
    let result: Value = serde_json::from_str(&stdout(&first)).expect("valid plan JSON");
    assert_eq!(
        result["harness"]["proposed_shards"],
        serde_json::json!({"1": ["test-a"], "2": ["test-c", "test-b"]})
    );
    assert_eq!(result["decision"], "noop");
    assert_eq!(result["harness"]["is_noop"], true);
    assert!(result.get("rust").is_none());
}

#[test]
fn plan_rejects_or_overrides_a_modeled_threshold_regression() {
    let rejected_json = result("plan", &harness_plan_request(135.0, "null"), false);
    assert_eq!(rejected_json["decision"], "rejected");
    assert_eq!(
        rejected_json["violations"][0],
        "predicted slowest shard 136.0s exceeds approved wall-clock 135.0s"
    );

    let overridden_json = result(
        "plan",
        &harness_plan_request(135.0, "\"measure runner image migration\""),
        true,
    );
    assert_eq!(overridden_json["decision"], "overridden");
    assert_eq!(
        overridden_json["experimental_override"],
        "measure runner image migration"
    );
}

#[test]
fn plan_and_verify_support_an_explicit_rust_coverage_resize() {
    let planned = result("plan", &rust_plan_request(4), true);
    assert_eq!(planned["decision"], "change");
    assert_eq!(planned["rust"]["current_shard_count"], 1);
    assert_eq!(planned["rust"]["shard_count"], 4);
    assert_eq!(planned["rust"]["baseline_slowest_wall_clock"], 702.0);
    assert_eq!(planned["rust"]["approved_slowest_wall_clock"], 600.0);

    let verified = result("verify", &rust_verify_request(RUST_FOUR_SHARD_TIMING), true);
    assert_eq!(verified["outcome"], "passed");
    assert_eq!(verified["rust"]["observed_slowest_wall_clock"], 560.0);
}

#[test]
fn an_over_budget_unchanged_leg_rejects_a_multi_leg_change() {
    let mut request: Value =
        serde_json::from_str(&harness_plan_request(136.0, "null")).expect("valid harness request");
    let rust: Value = serde_json::from_str(&rust_plan_request(1)).expect("valid Rust request");
    request["selection"] = Value::String("all".to_owned());
    request["rust"] = rust["rust"].clone();

    let rejected = result(
        "plan",
        &serde_json::to_string(&request).expect("render all-leg request"),
        false,
    );

    assert_eq!(rejected["decision"], "rejected");
    assert!(rejected["violations"].as_array().is_some_and(|violations| {
        violations.iter().any(|violation| {
            violation
                == "baseline measured slowest Rust coverage shard 702.0s exceeds max_rust_shard_wall_clock 600.0s"
        })
    }));
}

#[test]
fn rust_coverage_verification_rejects_incomplete_or_slow_cohorts() {
    let incomplete =
        RUST_FOUR_SHARD_TIMING.replacen(r#",{"run_id":22,"shard":4,"seconds":427.0}"#, "", 1);
    invalid(
        "verify",
        &rust_verify_request(&incomplete),
        "missing or duplicate Rust coverage shard rows",
    );

    let slow = RUST_FOUR_SHARD_TIMING
        .replace("\"seconds\":563.0", "\"seconds\":640.0")
        .replace(
            "\"shard\":1,\"seconds\":560.0",
            "\"shard\":1,\"seconds\":601.0",
        );
    let rejected = result("verify", &rust_verify_request(&slow), false);
    assert_eq!(rejected["outcome"], "rejected");
    assert_eq!(rejected["rust"]["observed_slowest_wall_clock"], 601.0);
}

#[test]
fn malformed_or_incomplete_timing_evidence_fails_closed() {
    let stale = harness_plan_request(136.0, "null").replacen(
        "\"sampled_run_ids\":[11,12]",
        "\"sampled_run_ids\":[11]",
        1,
    );
    invalid(
        "plan",
        &stale,
        "harness timing cohort does not match requested complete run ids",
    );

    let incomplete = harness_plan_request(136.0, "null").replacen(
        "\"bootstrap_kind\":\"warm\"",
        "\"bootstrap_kind\":\"unknown\"",
        1,
    );
    invalid(
        "plan",
        &incomplete,
        "harness bootstrap evidence is incomplete",
    );

    let duplicate = harness_plan_request(136.0, "null").replacen(
        "\"kind\":\"harness\"",
        "\"kind\":\"harness\",\"kind\":\"harness\"",
        1,
    );
    invalid("plan", &duplicate, "duplicate JSON key");

    let duplicate_medians = harness_plan_request(136.0, "null").replacen(
        "\"shard_medians\":[{\"shard\":1,\"seconds\":130.0},{\"shard\":2,\"seconds\":136.0}]",
        "\"shard_medians\":[{\"shard\":1,\"seconds\":130.0},{\"shard\":1,\"seconds\":136.0}]",
        1,
    );
    invalid("plan", &duplicate_medians, "contains a duplicate shard");
}

#[test]
fn verify_reports_pass_rejection_and_experimental_override_without_mutation() {
    let passed_json = result(
        "verify",
        &harness_verify_request(136.0, 136.0, "null"),
        true,
    );
    assert_eq!(passed_json["outcome"], "passed");
    assert_eq!(passed_json["harness"]["observed_slowest_wall_clock"], 136.0);
    assert!(passed_json.get("rust").is_none());

    let rejected_json = result(
        "verify",
        &harness_verify_request(135.0, 135.0, "null"),
        false,
    );
    assert_eq!(rejected_json["outcome"], "rejected");
    assert_eq!(
        rejected_json["harness"]["violations"],
        serde_json::json!([
            "measured slowest shard exceeds max_shard_wall_clock",
            "measured slowest shard 136.0s regresses approved threshold 135.0s"
        ])
    );

    let overridden_json = result(
        "verify",
        &harness_verify_request(135.0, 135.0, "\"measure runner image migration\""),
        true,
    );
    assert_eq!(overridden_json["outcome"], "overridden");
}
