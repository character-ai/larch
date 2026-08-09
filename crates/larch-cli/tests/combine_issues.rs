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
fn inherited_plan_keeps_closed_and_unknown_dependency_evidence_distinct() {
    let temp = TempDir::new().expect("tempdir");
    let deps = write(
        &temp,
        "deps.json",
        &json!({"status":"ok","warnings":[{"code":"prior_warning"}],"issues":{
            "1":{"blocked_by":[5],"blocking":[],"read_ok":true},
            "2":{"blocked_by":[9],"blocking":[],"read_ok":true},
            "3":{"blocked_by":[10],"blocking":[],"read_ok":false}
        }}),
    );
    let mapping = write(
        &temp,
        "mapping.json",
        &json!({"1":100,"2":200,"3":[300,301]}),
    );
    let open = write(
        &temp,
        "open.json",
        &json!({"status":"ok","issues":[
            {"number":5,"title":"ready blocker","state":"open"},
            {"number":10,"title":"done blocker","state":"closed"}
        ]}),
    );
    let combined = write(
        &temp,
        "combined.json",
        &json!([
            {"number":100,"title":"[OOS] one","source_issues":[1]},
            {"number":200,"title":"[OOS] two","source_issues":[2]},
            {"number":300,"title":"[OOS] three","source_issues":[3]},
            {"number":301,"title":"[OOS] four","source_issues":[3]}
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

    assert_eq!(output["safe_edges"][0]["edge"], json!([100, 5]));
    assert_eq!(
        output["satisfied_edges"]
            .as_array()
            .expect("satisfied rows")
            .iter()
            .map(|row| row["edge"].clone())
            .collect::<Vec<_>>(),
        vec![json!([300, 10]), json!([301, 10])]
    );
    assert_eq!(output["unknown_edges"][0]["edge"], json!([200, 9]));
    assert_eq!(
        output["per_source_initial_eligibility"]["1"]["eligible"],
        true
    );
    assert_eq!(
        output["per_source_initial_eligibility"]["2"]["eligible"],
        false
    );
    assert_eq!(
        output["per_source_initial_eligibility"]["3"]["eligible"],
        false
    );
    assert_eq!(output["warnings"], json!([{"code":"prior_warning"}]));
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
#[allow(clippy::too_many_lines)] // One eligibility fixture pins every policy bucket together.
fn eligibility_requires_each_inherited_write_or_exception_decision() {
    let temp = TempDir::new().expect("tempdir");
    let plan = write(
        &temp,
        "plan.json",
        &json!({"status":"ok",
        "safe_edges":[
            {"edge":[100,5],"source_issues":[1]},
            {"edge":[200,6],"source_issues":[2]},
            {"edge":[300,7],"source_issues":[3]}
        ],
        "exception_edges":[
            {"edge":[8,400],"source_issues":[4]},
            {"edge":[9,500],"source_issues":[5]},
            {"edge":[10,600],"source_issues":[6]},
            {"edge":[11,700],"source_issues":[7]},
            {"edge":[12,800],"source_issues":[8]}
        ],
        "unknown_edges":[{"edge":[13,900],"source_issues":[9]}],
        "per_source_initial_eligibility":{
            "1":{"eligible":true,"reasons":[]},"2":{"eligible":true,"reasons":[]},
            "3":{"eligible":true,"reasons":[]},"4":{"eligible":true,"reasons":[]},
            "5":{"eligible":true,"reasons":[]},"6":{"eligible":true,"reasons":[]},
            "7":{"eligible":true,"reasons":[]},"8":{"eligible":true,"reasons":[]},
            "9":{"eligible":true,"reasons":[]},"10":{"eligible":false,"reasons":["dependency_read_failed"]},
            "11":{"eligible":true,"reasons":[]},"12":{"eligible":true,"reasons":[]}
        }}),
    );
    let writes = write(
        &temp,
        "writes.json",
        &json!({"write_results":[
            {"edge":[100,5],"phase":"inherited_safe","status":"failed"},
            {"edge":[100,5],"phase":"inherited_reclassified_safe","status":"already_present"},
            {"edge":[300,7],"phase":"inherited_safe","status":"unresolved"},
            {"edge":[8,400],"phase":"inherited_exception","status":"written"},
            {"edge":[12,800],"phase":"inherited_exception","status":"failed"}
        ]}),
    );
    let decisions = write(
        &temp,
        "decisions.json",
        &json!({"decisions":[
            {"edge":[8,400],"decision":"approved"},
            {"edge":[9,500],"decision":"rejected"},
            {"edge":[10,600],"decision":"unresolved"},
            {"edge":[11,700],"decision":"approved"},
            {"edge":[12,800],"decision":"approved"}
        ]}),
    );
    let mapping = write(
        &temp,
        "mapping.json",
        &json!({"1":100,"2":200,"3":300,"4":400,"5":500,"6":600,"7":700,"8":800,
            "9":900,"10":1000,"11":[1100,1101],"12":1200}),
    );
    let blocked = write(
        &temp,
        "blocked.json",
        &json!({"blocked_sources":[{"source_issue":12,"reason":"blocked item remains"}]}),
    );
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

    assert_eq!(
        output["eligible_by_combined"],
        json!({"100":[1],"400":[4],"500":[5]})
    );
    assert_eq!(
        output["ineligible_sources"],
        json!([2, 3, 6, 7, 8, 9, 10, 11, 12])
    );
    assert!(
        output["reasons"]["5"]
            .as_array()
            .expect("rejected reason")
            .iter()
            .any(|value| value == "inherited_exception_rejected:9:500")
    );
    assert!(
        output["reasons"]["8"]
            .as_array()
            .expect("failed reason")
            .iter()
            .any(|value| value == "inherited_exception_write_failed:12:800")
    );
    assert!(
        output["reasons"]["11"]
            .as_array()
            .expect("multi-host reason")
            .iter()
            .any(|value| value == "multi_combined_host_closure_unsupported")
    );
    assert_eq!(
        output["counts"],
        json!({"eligible_sources":3,"ineligible_sources":9,"blocked_sources":1})
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
            {"edge":[100,5],"source_kind":"tier2_semantic","confidence":"high","reason":"semantic"},
            {"edge":[100,6],"source_kind":"tier1_prose","confidence":"explicit","reason":"decided"}
        ]}),
    );
    let empty = write(&temp, "empty.json", &json!({"candidates":[]}));
    let edges = write(&temp, "edges.json", &json!([]));
    let decisions = write(
        &temp,
        "decisions.json",
        &json!({"decisions":[
            {"edge":[100,6],"decision":"approved"},
            {"edge":[100,6],"decision":"rejected"}
        ]}),
    );
    let open = write(
        &temp,
        "open.json",
        &json!({"issues":[
            {"number":5,"title":"blocker","state":"open"},
            {"number":6,"title":"decided blocker","state":"open"}
        ]}),
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
    assert_eq!(output["duplicate_edges_skipped"], 2);
}

#[test]
fn plan_audit_preserves_each_policy_bucket_and_deduplication_boundary() {
    let temp = TempDir::new().expect("tempdir");
    let prose = write(
        &temp,
        "prose.json",
        &json!({"candidates":[
            {"edge":[100,5],"source_kind":"tier1_prose","confidence":"explicit"},
            {"edge":[5,100],"source_kind":"tier1_prose","confidence":"explicit"},
            {"edge":[100,6],"source_kind":"tier1_prose","confidence":"explicit","reason":"tier one"},
            {"edge":[100,9],"source_kind":"tier1_prose","confidence":"explicit"},
            {"edge":[100,10],"source_kind":"tier1_prose","confidence":"explicit"},
            {"edge":[100,11],"source_kind":"tier1_prose","confidence":"explicit"},
            {"edge":[100,12],"source_kind":"tier1_prose","confidence":"explicit"}
        ]}),
    );
    let tier2 = write(
        &temp,
        "tier2.json",
        &json!({"candidates":[
            {"edge":[100,6],"source_kind":"tier2_semantic","confidence":"high","reason":"semantic"},
            {"edge":[100,7],"source_kind":"tier1_prose","confidence":"explicit"},
            {"edge":[100,8],"source_kind":"tier2_semantic","confidence":"explicit"}
        ]}),
    );
    let existing = write(&temp, "existing.json", &json!([[100, 10]]));
    let decisions = write(
        &temp,
        "decisions.json",
        &json!({"decisions":[
            {"edge":[100,11],"decision":"rejected"},
            {"edge":[100,12],"decision":"unresolved"}
        ]}),
    );
    let open = write(
        &temp,
        "open.json",
        &json!({"status":"ok","issues":[
            {"number":5,"title":"ready","state":"open"},
            {"number":6,"title":"ready","state":"open"},
            {"number":7,"title":"ready","state":"open"},
            {"number":8,"title":"ready","state":"open"},
            {"number":10,"title":"ready","state":"open"},
            {"number":11,"title":"ready","state":"open"},
            {"number":12,"title":"ready","state":"open"}
        ]}),
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
        &tier2,
        "--existing-edges-file",
        &existing,
        "--decided-edges-file",
        &decisions,
        "--open-issues-file",
        &open,
        "--combined-issues-file",
        &combined,
    ]));

    assert_eq!(output["auto_write_edges"][0]["edge"], json!([100, 5]));
    assert_eq!(
        output["approval_required_edges"]
            .as_array()
            .expect("approval rows")
            .iter()
            .map(|row| row["edge"].clone())
            .collect::<Vec<_>>(),
        vec![json!([5, 100]), json!([100, 6])]
    );
    assert_eq!(
        output["policy_rejected_edges"]
            .as_array()
            .expect("rejected rows")
            .iter()
            .map(|row| row["edge"].clone())
            .collect::<Vec<_>>(),
        vec![json!([100, 7]), json!([100, 8]), json!([100, 9])]
    );
    assert_eq!(
        output["approval_required_edges"][1]["reason"],
        json!("semantic")
    );
    assert_eq!(
        output["policy_rejected_edges"][0]["policy_reason"],
        json!("tier2 candidate must declare source_kind=tier2_semantic")
    );
    assert_eq!(
        output["policy_rejected_edges"][1]["policy_reason"],
        json!("tier2 candidate missing low, medium, or high confidence")
    );
    assert_eq!(output["duplicate_edges_skipped"], 4);
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

#[test]
fn offline_mutation_validation_preserves_the_fail_closed_contract() {
    let temp = TempDir::new().expect("tempdir");
    let body = temp.path().join("body.md");
    fs::write(&body, "Combined body\n").expect("body fixture");
    let body = body.to_string_lossy().into_owned();

    let apply = run(&[
        "combine-issues",
        "apply",
        "--repo",
        "owner/repository",
        "--title",
        "T",
        "--body-file",
        &body,
        "--source-issues",
        " , ",
    ]);
    assert!(!apply.status.success());
    assert!(String::from_utf8_lossy(&apply.stderr).contains("ERROR=No source issues provided"));

    let stale = run(&[
        "combine-issues",
        "close-stale",
        "--issues",
        "1",
        "--reason",
        "stale",
    ]);
    assert!(!stale.status.success());
    assert!(
        String::from_utf8_lossy(&stale.stderr)
            .contains("ERROR=--reason must be one of: completed, not planned")
    );

    let deferred = run(&[
        "combine-issues",
        "apply",
        "--title",
        "T\nwith newline",
        "--body-file",
        &body,
        "--source-issues",
        "1,2",
        "--dry-run",
        "--defer-close",
    ]);
    assert!(deferred.status.success());
    assert_eq!(
        String::from_utf8(deferred.stdout).expect("UTF-8 stdout"),
        "DRY_RUN=true\nWOULD_CREATE=T with newline\nWOULD_CLOSE=2 issues: 1,2\nCLOSING_DEFERRED=true\n"
    );
}
