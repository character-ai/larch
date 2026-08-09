//! Black-box compatibility coverage for the pure combine-issues workflow stages.

use std::{fs, process::Command};

use serde_json::{Value, json};
use tempfile::TempDir;

fn write(temp: &TempDir, name: &str, value: &Value) -> String {
    let path = temp.path().join(name);
    fs::write(&path, serde_json::to_vec(value).expect("JSON fixture")).expect("write fixture");
    path.to_string_lossy().into_owned()
}

fn run(arguments: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(arguments)
        .output()
        .expect("larch runs")
}

fn output_json(output: &std::process::Output) -> Value {
    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).expect("JSON stdout")
}

#[test]
fn inherited_plan_remaps_and_classifies_the_recorded_edge_shapes() {
    let temp = TempDir::new().expect("tempdir");
    let deps = write(
        &temp,
        "deps.json",
        &json!({"status":"ok","issues":{
            "1":{"blocked_by":[1,2,5],"blocking":[6],"read_ok":true},
            "2":{"blocked_by":[1],"blocking":[],"read_ok":true}
        },"warnings":[]}),
    );
    let mapping = write(&temp, "mapping.json", &json!({"1":100,"2":200}));
    let open = write(
        &temp,
        "open.json",
        &json!({"status":"ok","issues":[
            {"number":5,"title":"normal blocker","state":"open"},
            {"number":6,"title":"normal client","state":"open"}
        ]}),
    );
    let combined = write(
        &temp,
        "combined.json",
        &json!([
            {"number":100,"title":"[OOS] one","source_issues":[1]},
            {"number":200,"title":"[OOS] two","source_issues":[2]}
        ]),
    );
    let output = output_json(&run(&[
        "combine-issues",
        "plan-inherited",
        "--deps-file",
        &deps,
        "--source-to-combined-file",
        &mapping,
        "--open-issues-file",
        &open,
        "--combined-issues-file",
        &combined,
    ]));

    assert_eq!(output["self_edges_skipped"], 1);
    assert_eq!(output["edge_provenance"]["6:100"], json!([1]));
    assert_eq!(
        output["safe_edges"]
            .as_array()
            .expect("safe edges")
            .iter()
            .map(|row| row["edge"].clone())
            .collect::<Vec<_>>(),
        vec![json!([100, 5]), json!([100, 200]), json!([200, 100])]
    );
    assert_eq!(output["exception_edges"][0]["edge"], json!([6, 100]));
}

#[test]
fn eligibility_refuses_a_source_without_a_verified_inherited_write() {
    let temp = TempDir::new().expect("tempdir");
    let plan = write(
        &temp,
        "plan.json",
        &json!({"status":"ok","safe_edges":[{"edge":[100,5],"source_issues":[1]}],
            "exception_edges":[],"unknown_edges":[],
            "per_source_initial_eligibility":{"1":{"eligible":true,"reasons":[]}}}),
    );
    let writes = write(&temp, "writes.json", &json!({"write_results":[]}));
    let decisions = write(&temp, "decisions.json", &json!({"decisions":[]}));
    let mapping = write(&temp, "mapping.json", &json!({"1":100}));
    let blocked = write(&temp, "blocked.json", &json!({"blocked_sources":[]}));
    let output = output_json(&run(&[
        "combine-issues",
        "close-eligible",
        "--inherited-plan-file",
        &plan,
        "--write-results-file",
        &writes,
        "--exception-decisions-file",
        &decisions,
        "--source-to-combined-file",
        &mapping,
        "--blocked-sources-file",
        &blocked,
    ]));

    assert_eq!(output["eligible_by_combined"], json!({}));
    assert_eq!(output["ineligible_sources"], json!([1]));
    assert_eq!(
        output["reasons"]["1"],
        json!(["inherited_safe_write_missing_or_failed:100:5"])
    );
}

#[test]
fn plan_audit_keeps_a_semantic_prose_candidate_over_an_earlier_tier_one_duplicate() {
    let temp = TempDir::new().expect("tempdir");
    let prose = write(
        &temp,
        "prose.json",
        &json!({"candidates":[
            {"edge":[100,5],"source_kind":"tier1_prose","confidence":"explicit","reason":"tier one"},
            {"edge":[100,5],"source_kind":"tier2_semantic","confidence":"high","reason":"semantic"}
        ]}),
    );
    let empty = write(&temp, "empty.json", &json!({"candidates":[]}));
    let edges = write(&temp, "edges.json", &json!([]));
    let decisions = write(&temp, "decisions.json", &json!({"decisions":[]}));
    let open = write(
        &temp,
        "open.json",
        &json!({"issues":[{"number":5,"title":"blocker","state":"open"}]}),
    );
    let combined = write(
        &temp,
        "combined.json",
        &json!([{"number":100,"title":"[OOS] combined","source_issues":[1]}]),
    );
    let output = output_json(&run(&[
        "combine-issues",
        "plan-audit",
        "--prose-candidates-file",
        &prose,
        "--tier2-candidates-file",
        &empty,
        "--existing-edges-file",
        &edges,
        "--decided-edges-file",
        &decisions,
        "--open-issues-file",
        &open,
        "--combined-issues-file",
        &combined,
    ]));

    assert_eq!(output["auto_write_edges"], json!([]));
    assert_eq!(
        output["approval_required_edges"][0]["reason"],
        json!("semantic")
    );
}

#[test]
fn dry_run_closure_and_apply_keep_the_legacy_key_value_wire() {
    let temp = TempDir::new().expect("tempdir");
    let body = temp.path().join("body.md");
    fs::write(&body, "Combined body\n").expect("body fixture");
    let body = body.to_string_lossy().into_owned();
    let apply = run(&[
        "combine-issues",
        "apply",
        "--title",
        "T",
        "--body-file",
        &body,
        "--source-issues",
        "1,2",
        "--dry-run",
    ]);
    assert!(apply.status.success());
    assert_eq!(
        String::from_utf8(apply.stdout).expect("UTF-8 stdout"),
        "DRY_RUN=true\nWOULD_CREATE=T\nWOULD_CLOSE=2 issues: 1,2\n"
    );
    let stale = run(&[
        "combine-issues",
        "close-stale",
        "--issues",
        "1,2",
        "--reason",
        "not planned",
        "--dry-run",
    ]);
    assert!(stale.status.success());
    assert_eq!(
        String::from_utf8(stale.stdout).expect("UTF-8 stdout"),
        "DRY_RUN=true\nWOULD_CLOSE=1,2\nCLOSED_ISSUES=0\nPARTIAL=false\n"
    );
}
