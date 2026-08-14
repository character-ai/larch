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
        r#"{{"schema_version":1,"kind":"plan","selection":"harness","options":{{"max_shard_wall_clock":{max_shard_wall_clock},"balance_threshold":15.0,"n_python_shards":null,"experimental_wall_clock_override":{override_note},"compile_affinities":[]}},"harness":{{"expected_run_ids":[11,12],"current_shards":{NOOP_SHARDS},"timing":{NOOP_HARNESS_TIMING},"jobs":{NOOP_JOBS}}},"python":null}}"#
    )
}

fn harness_verify_request(
    max_shard_wall_clock: f64,
    approved_slowest_wall_clock: f64,
    override_note: &str,
) -> String {
    format!(
        r#"{{"schema_version":1,"kind":"verify","selection":"harness","options":{{"max_shard_wall_clock":{max_shard_wall_clock},"balance_threshold":15.0,"experimental_wall_clock_override":{override_note}}},"harness":{{"expected_run_ids":[11,12],"expected_shards":{NOOP_SHARDS},"baseline_slowest_wall_clock":136.0,"baseline_runner_seconds":266.0,"approved_slowest_wall_clock":{approved_slowest_wall_clock},"timing":{NOOP_HARNESS_TIMING},"jobs":{NOOP_JOBS}}},"python":null}}"#
    )
}

const PYTEST_TIMING: &str = r#"{"schema_version":2,"kind":"pytest","sampled_run_ids":[11,12],"rows":[{"run_id":11,"shard":1,"nodeid":"slow","seconds":10.0,"attempt":1,"shard_total":2},{"run_id":11,"shard":2,"nodeid":"medium","seconds":5.0,"attempt":1,"shard_total":2},{"run_id":11,"shard":2,"nodeid":"fast","seconds":1.0,"attempt":1,"shard_total":2},{"run_id":12,"shard":1,"nodeid":"slow","seconds":10.0,"attempt":1,"shard_total":2},{"run_id":12,"shard":2,"nodeid":"medium","seconds":5.0,"attempt":1,"shard_total":2},{"run_id":12,"shard":2,"nodeid":"fast","seconds":1.0,"attempt":1,"shard_total":2}],"nodeid_medians":[{"nodeid":"slow","seconds":10.0},{"nodeid":"medium","seconds":5.0},{"nodeid":"fast","seconds":1.0}],"shard_medians":[{"shard":1,"seconds":10.0},{"shard":2,"seconds":6.0}],"observed_shard_count":2,"skipped_run_ids":[]}"#;

fn python_plan_request(current_assignments: &str) -> String {
    format!(
        r#"{{"schema_version":1,"kind":"plan","selection":"python","options":{{"max_shard_wall_clock":300.0,"balance_threshold":15.0,"n_python_shards":2,"experimental_wall_clock_override":null,"compile_affinities":[]}},"harness":null,"python":{{"expected_run_ids":[11,12],"current_assignments":{current_assignments},"timing":{PYTEST_TIMING}}}}}"#
    )
}

fn python_plan_request_for_count(current_assignments: &str, shard_count: u32) -> String {
    python_plan_request(current_assignments).replace(
        "\"n_python_shards\":2",
        &format!("\"n_python_shards\":{shard_count}"),
    )
}

fn python_verify_request(balance_threshold: f64) -> String {
    format!(
        r#"{{"schema_version":1,"kind":"verify","selection":"python","options":{{"max_shard_wall_clock":300.0,"balance_threshold":{balance_threshold},"experimental_wall_clock_override":null}},"harness":null,"python":{{"expected_run_ids":[11,12],"expected_shard_count":2,"timing":{PYTEST_TIMING}}}}}"#
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
fn plan_uses_the_existing_shard_packer_for_python_nodeids() {
    let output = result("plan", &python_plan_request("{}"), true);
    assert_eq!(output["decision"], "change");
    assert_eq!(
        output["python"]["assignments"],
        serde_json::json!({"fast": 2, "medium": 2, "slow": 1})
    );
}

#[test]
fn plan_allows_an_explicit_python_matrix_resize() {
    let output = result(
        "plan",
        &python_plan_request_for_count("{\"old\":2}", 4),
        true,
    );

    assert_eq!(output["decision"], "change");
    assert_eq!(output["python"]["shard_count"], 4);
    assert_eq!(
        output["python"]["assignments"],
        serde_json::json!({"fast": 3, "medium": 2, "slow": 1})
    );
}

#[test]
fn equal_cost_python_ties_remain_deterministic() {
    let request = python_plan_request("{}")
        .replace("\"seconds\":5.0", "\"seconds\":10.0")
        .replace("\"seconds\":1.0", "\"seconds\":10.0");
    let first = run("plan", &request);
    let second = run("plan", &request);

    assert!(first.status.success(), "{}", stderr(&first));
    assert_eq!(stdout(&first), stdout(&second));
    let result: Value = serde_json::from_str(&stdout(&first)).expect("valid plan JSON");
    assert_eq!(
        result["python"]["assignments"],
        serde_json::json!({"fast": 1, "medium": 2, "slow": 1})
    );
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

    let partial_python =
        python_plan_request("{}").replace("\"run_id\":11,\"shard\":2", "\"run_id\":11,\"shard\":1");
    invalid(
        "plan",
        &partial_python,
        "pytest timing has incompatible shard counts",
    );
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

    let python_json = result("verify", &python_verify_request(3.0), false);
    assert_eq!(python_json["outcome"], "rejected");
    assert_eq!(python_json["python"]["spread"], 4.0);
}
