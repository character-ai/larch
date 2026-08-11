//! Pure planning and verification decisions for CI test rebalancing.

use std::{
    cmp::Ordering,
    collections::{BTreeMap, BTreeSet, HashMap, HashSet},
};

use serde::{Deserialize, Serialize, de::DeserializeOwned};

use crate::{
    HarnessBootstrapRow, HarnessTimingReport, HarnessTimingRow, JobTimingReport, JobTimingRow,
    OrderedJson, PytestTimingReport, ShardTiming, TestShardTiming, pack_test_shards,
    pack_test_shards_with_fixed_startup,
};

/// Version of the `rebalance-tests` JSON contract.
pub const REBALANCE_TESTS_SCHEMA_VERSION: u8 = 1;
const GUARD_TARGET: &str = "test-harness-shards-coverage";

/// A canonical JSON result and whether it represents an accepted decision.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RebalanceJsonResult {
    /// Compact JSON without a trailing newline.
    pub json: String,
    /// False only for a valid rejected policy decision.
    pub success: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Request<Options, Harness, Python> {
    schema_version: u8,
    kind: String,
    selection: Selection,
    options: Options,
    harness: Option<Harness>,
    python: Option<Python>,
}

type PlanWire = Request<PlanOptions, HarnessPlanWire, PythonPlanWire>;
type VerifyWire = Request<VerifyOptions, HarnessVerifyWire, PythonVerifyWire>;

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "lowercase")]
enum Selection {
    Harness,
    Python,
    All,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PlanOptions {
    max_shard_wall_clock: f64,
    balance_threshold: f64,
    n_python_shards: Option<u32>,
    #[serde(rename = "experimental_wall_clock_override")]
    experimental_override: Option<String>,
    compile_affinities: Vec<CompileAffinity>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct VerifyOptions {
    max_shard_wall_clock: f64,
    balance_threshold: f64,
    #[serde(rename = "experimental_wall_clock_override")]
    experimental_override: Option<String>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct CompileAffinity {
    target: String,
    group: String,
    setup_seconds: f64,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct HarnessPlanWire {
    expected_run_ids: Vec<u64>,
    current_shards: BTreeMap<String, Vec<String>>,
    timing: HarnessTimingReport,
    jobs: JobTimingReport,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PythonPlanWire {
    expected_run_ids: Vec<u64>,
    current_assignments: BTreeMap<String, u32>,
    timing: PytestTimingReport,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct HarnessVerifyWire {
    expected_run_ids: Vec<u64>,
    expected_shards: BTreeMap<String, Vec<String>>,
    baseline_slowest_wall_clock: f64,
    baseline_runner_seconds: f64,
    approved_slowest_wall_clock: f64,
    timing: HarnessTimingReport,
    jobs: JobTimingReport,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PythonVerifyWire {
    expected_run_ids: Vec<u64>,
    expected_shard_count: u32,
    timing: PytestTimingReport,
}

#[derive(Clone, Debug)]
struct AffinityCost {
    group: String,
    setup_seconds: f64,
}

#[derive(Clone, Debug)]
struct Model {
    fixed_startup_seconds: f64,
    shared_setup_seconds: f64,
    target_seconds: BTreeMap<String, f64>,
    affinities: BTreeMap<String, AffinityCost>,
}

#[derive(Clone, Debug)]
struct Candidate {
    layout: BTreeMap<u32, Vec<String>>,
    predicted: BTreeMap<u32, f64>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "kebab-case")]
enum PlanDecision {
    Change,
    Noop,
    Rejected,
    Overridden,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "kebab-case")]
enum Outcome {
    Passed,
    Rejected,
    Overridden,
}

#[derive(Serialize)]
struct PlanResponse {
    schema_version: u8,
    kind: &'static str,
    decision: PlanDecision,
    violations: Vec<String>,
    experimental_override: Option<String>,
    harness: Option<HarnessPlanResponse>,
    python: Option<PythonPlanResponse>,
}

#[derive(Clone, Serialize)]
struct HarnessPlanResponse {
    proposed_shards: BTreeMap<u32, Vec<String>>,
    active_runner_count: u32,
    predicted_current: BTreeMap<u32, f64>,
    predicted_proposed: BTreeMap<u32, f64>,
    baseline_wall_clock: BTreeMap<u32, f64>,
    baseline_slowest_wall_clock: f64,
    baseline_runner_seconds: f64,
    approved_slowest_wall_clock: f64,
    is_noop: bool,
}

#[derive(Clone, Serialize)]
struct PythonPlanResponse {
    assignments: BTreeMap<String, u32>,
    shard_count: u32,
    is_noop: bool,
}

#[derive(Serialize)]
struct VerifyResponse {
    schema_version: u8,
    kind: &'static str,
    outcome: Outcome,
    experimental_override: Option<String>,
    harness: Option<HarnessVerifyResponse>,
    python: Option<PythonVerifyResponse>,
}

#[derive(Serialize)]
struct HarnessVerifyResponse {
    outcome: Outcome,
    wall_clock: BTreeMap<u32, f64>,
    baseline_slowest_wall_clock: f64,
    observed_slowest_wall_clock: f64,
    observed_runner_seconds: f64,
    violations: Vec<String>,
}

#[derive(Serialize)]
struct PythonVerifyResponse {
    outcome: Outcome,
    shard_medians: BTreeMap<u32, f64>,
    spread: f64,
    balance_threshold: f64,
    violations: Vec<String>,
}

/// Validate baseline evidence and render one pure, deterministic plan result.
///
/// # Errors
///
/// Malformed or incomplete evidence returns an error. A valid policy rejection
/// returns JSON with `success` false.
pub fn plan_json(source: &str) -> Result<RebalanceJsonResult, String> {
    let wire: PlanWire = decode(source, "plan request")?;
    validate_header(wire.schema_version, &wire.kind, "plan")?;
    validate_plan_options(&wire.options)?;
    validate_legs(
        wire.selection,
        wire.harness.is_some(),
        wire.python.is_some(),
    )?;
    let (harness, harness_violations) = wire
        .harness
        .map(|input| build_harness_plan(input, &wire.options))
        .transpose()?
        .map_or((None, Vec::new()), |(response, violations)| {
            (Some(response), violations)
        });
    let python = wire
        .python
        .map(|input| build_python_plan(input, &wire.options))
        .transpose()?;
    let noop = harness.as_ref().is_none_or(|response| response.is_noop)
        && python.as_ref().is_none_or(|response| response.is_noop);
    let mut violations = harness_violations;
    let mut decision = if violations.is_empty() {
        if noop {
            PlanDecision::Noop
        } else {
            PlanDecision::Change
        }
    } else if wire.options.experimental_override.is_some() {
        PlanDecision::Overridden
    } else {
        PlanDecision::Rejected
    };
    if let Some(response) = harness.as_ref()
        && decision == PlanDecision::Noop
        && response.baseline_slowest_wall_clock > wire.options.max_shard_wall_clock
    {
        violations.push(format!(
            "baseline measured slowest shard {:.1}s exceeds max_shard_wall_clock {:.1}s",
            response.baseline_slowest_wall_clock, wire.options.max_shard_wall_clock
        ));
        decision = if wire.options.experimental_override.is_some() {
            PlanDecision::Overridden
        } else {
            PlanDecision::Rejected
        };
    }
    render(
        &PlanResponse {
            schema_version: REBALANCE_TESTS_SCHEMA_VERSION,
            kind: "plan",
            decision,
            violations,
            experimental_override: wire.options.experimental_override,
            harness,
            python,
        },
        decision != PlanDecision::Rejected,
    )
}

/// Validate post-run evidence and render one pure, deterministic verdict.
///
/// # Errors
///
/// Malformed or incomplete evidence returns an error. A valid policy rejection
/// returns JSON with `success` false.
pub fn verify_json(source: &str) -> Result<RebalanceJsonResult, String> {
    let wire: VerifyWire = decode(source, "verify request")?;
    validate_header(wire.schema_version, &wire.kind, "verify")?;
    validate_verify_options(&wire.options)?;
    validate_legs(
        wire.selection,
        wire.harness.is_some(),
        wire.python.is_some(),
    )?;
    let harness = wire
        .harness
        .map(|input| verify_harness(input, &wire.options))
        .transpose()?;
    let python = wire
        .python
        .map(|input| verify_python(input, &wire.options))
        .transpose()?;
    let outcome = if harness
        .as_ref()
        .is_some_and(|value| value.outcome == Outcome::Rejected)
        || python
            .as_ref()
            .is_some_and(|value| value.outcome == Outcome::Rejected)
    {
        Outcome::Rejected
    } else if harness
        .as_ref()
        .is_some_and(|value| value.outcome == Outcome::Overridden)
    {
        Outcome::Overridden
    } else {
        Outcome::Passed
    };
    render(
        &VerifyResponse {
            schema_version: REBALANCE_TESTS_SCHEMA_VERSION,
            kind: "verify",
            outcome,
            experimental_override: wire.options.experimental_override,
            harness,
            python,
        },
        outcome != Outcome::Rejected,
    )
}

fn decode<T: DeserializeOwned>(source: &str, context: &str) -> Result<T, String> {
    OrderedJson::parse_unique(source)
        .map_err(|error| format!("rebalance-tests {context} is not valid JSON: {error}"))?;
    serde_json::from_str(source)
        .map_err(|error| format!("rebalance-tests {context} has an invalid schema: {error}"))
}

fn render(value: &impl Serialize, success: bool) -> Result<RebalanceJsonResult, String> {
    Ok(RebalanceJsonResult {
        json: serde_json::to_string(value)
            .map_err(|error| format!("cannot render rebalance-tests JSON: {error}"))?,
        success,
    })
}

fn validate_header(version: u8, kind: &str, expected: &str) -> Result<(), String> {
    if version != REBALANCE_TESTS_SCHEMA_VERSION {
        return Err(format!(
            "rebalance-tests schema_version must be {REBALANCE_TESTS_SCHEMA_VERSION}"
        ));
    }
    if kind != expected {
        return Err(format!("rebalance-tests kind must be {expected:?}"));
    }
    Ok(())
}

fn validate_legs(selection: Selection, harness: bool, python: bool) -> Result<(), String> {
    let expected = match selection {
        Selection::Harness => (true, false),
        Selection::Python => (false, true),
        Selection::All => (true, true),
    };
    ((harness, python) == expected)
        .then_some(())
        .ok_or_else(|| "rebalance-tests selection does not match supplied legs".to_owned())
}

fn validate_plan_options(options: &PlanOptions) -> Result<(), String> {
    positive(options.max_shard_wall_clock, "max_shard_wall_clock")?;
    positive(options.balance_threshold, "balance_threshold")?;
    if options.n_python_shards == Some(0) {
        return Err("rebalance-tests n_python_shards must be positive".to_owned());
    }
    validate_experiment(options.experimental_override.as_deref())?;
    for affinity in &options.compile_affinities {
        nonnegative(affinity.setup_seconds, "compile affinity setup_seconds")?;
        if affinity.target.is_empty()
            || affinity.group.is_empty()
            || affinity
                .target
                .chars()
                .chain(affinity.group.chars())
                .any(char::is_whitespace)
        {
            return Err("rebalance-tests compile affinity target and group must be nonempty without whitespace".to_owned());
        }
    }
    Ok(())
}

fn validate_verify_options(options: &VerifyOptions) -> Result<(), String> {
    positive(options.max_shard_wall_clock, "max_shard_wall_clock")?;
    positive(options.balance_threshold, "balance_threshold")?;
    validate_experiment(options.experimental_override.as_deref())
}

fn validate_experiment(value: Option<&str>) -> Result<(), String> {
    if value.is_some_and(|note| note.trim().is_empty()) {
        return Err(
            "rebalance-tests experimental override must name the documented experiment".to_owned(),
        );
    }
    Ok(())
}

fn run_ids(values: Vec<u64>, context: &str) -> Result<Vec<u64>, String> {
    valid_ids(&values, true, context)?;
    Ok(values)
}

fn shards(
    values: BTreeMap<String, Vec<String>>,
    context: &str,
) -> Result<BTreeMap<u32, Vec<String>>, String> {
    let mut output = BTreeMap::new();
    let mut targets = HashSet::new();
    for (key, list) in values {
        let shard = key
            .parse::<u32>()
            .ok()
            .filter(|value| *value > 0 && value.to_string() == key)
            .ok_or_else(|| format!("rebalance-tests {context} has invalid shard id {key:?}"))?;
        for target in &list {
            if target.is_empty() || !targets.insert(target.clone()) {
                return Err(format!(
                    "rebalance-tests {context} has an empty or duplicate target"
                ));
            }
        }
        output.insert(shard, list);
    }
    contiguous(&output, context)?;
    Ok(output)
}

fn assignments(
    values: BTreeMap<String, u32>,
    context: &str,
) -> Result<BTreeMap<String, u32>, String> {
    if values.keys().any(String::is_empty) || values.values().any(|value| *value == 0) {
        return Err(format!(
            "rebalance-tests {context} has an empty nodeid or zero shard"
        ));
    }
    Ok(values)
}

fn contiguous(values: &BTreeMap<u32, Vec<String>>, context: &str) -> Result<(), String> {
    let count = u32::try_from(values.len())
        .map_err(|_| format!("rebalance-tests {context} has too many shards"))?;
    if count == 0 || values.keys().copied().ne(1..=count) {
        return Err(format!(
            "rebalance-tests {context} shards must be contiguous from 1"
        ));
    }
    Ok(())
}

fn harness_report(report: HarnessTimingReport) -> Result<HarnessTimingReport, String> {
    report_header(report.schema_version, &report.kind, "harness")?;
    report_ids(&report.sampled_run_ids, &report.skipped_run_ids, "harness")?;
    Ok(report)
}

fn pytest_report(report: PytestTimingReport) -> Result<PytestTimingReport, String> {
    report_header(report.schema_version, &report.kind, "pytest")?;
    report_ids(&report.sampled_run_ids, &report.skipped_run_ids, "pytest")?;
    Ok(report)
}

fn jobs_report(report: JobTimingReport) -> Result<JobTimingReport, String> {
    report_header(report.schema_version, &report.kind, "jobs")?;
    report_ids(&report.sampled_run_ids, &report.skipped_run_ids, "jobs")?;
    Ok(report)
}

fn report_header(version: u8, kind: &str, expected: &str) -> Result<(), String> {
    (version == 2 && kind == expected)
        .then_some(())
        .ok_or_else(|| format!("rebalance-tests expected ci-timing {expected} schema-v2 report"))
}

fn report_ids(sampled: &[u64], skipped: &[u64], kind: &str) -> Result<(), String> {
    valid_ids(sampled, true, &format!("{kind} timing sampled_run_ids"))?;
    valid_ids(skipped, false, &format!("{kind} timing skipped_run_ids"))
}

fn valid_ids(values: &[u64], nonempty: bool, context: &str) -> Result<(), String> {
    if (nonempty && values.is_empty())
        || values.contains(&0)
        || values.iter().copied().collect::<HashSet<_>>().len() != values.len()
    {
        return Err(format!(
            "rebalance-tests {context} must be unique positive run ids"
        ));
    }
    Ok(())
}

fn nonzero<T>(value: T, context: &str) -> Result<T, String>
where
    T: PartialEq + From<u8>,
{
    (value != T::from(0))
        .then_some(value)
        .ok_or_else(|| format!("rebalance-tests {context} must be positive"))
}

fn positive(value: f64, context: &str) -> Result<f64, String> {
    (value.is_finite() && value > 0.0)
        .then_some(value)
        .ok_or_else(|| format!("rebalance-tests {context} must be a positive finite number"))
}

fn nonnegative(value: f64, context: &str) -> Result<f64, String> {
    (value.is_finite() && value >= 0.0)
        .then_some(value)
        .ok_or_else(|| format!("rebalance-tests {context} must be a non-negative finite number"))
}

fn build_harness_plan(
    wire: HarnessPlanWire,
    options: &PlanOptions,
) -> Result<(HarnessPlanResponse, Vec<String>), String> {
    let expected_run_ids = run_ids(wire.expected_run_ids, "harness.expected_run_ids")?;
    let shards = shards(wire.current_shards, "harness.current_shards")?;
    let timing = harness_report(wire.timing)?;
    let jobs = jobs_report(wire.jobs)?;
    if !timing.untimed_targets.is_empty() {
        return Err(format!(
            "rebalance-tests harness timing has untimed targets: {}",
            timing.untimed_targets.join(", ")
        ));
    }
    validate_harness_cohort(&timing, &shards, &expected_run_ids)?;
    let count = u32::try_from(shards.len())
        .map_err(|_| "rebalance-tests harness shard count is too large".to_owned())?;
    validate_jobs_cohort(&jobs, &expected_run_ids, count)?;
    let targets = shards.values().flatten().cloned().collect::<Vec<_>>();
    let model = model(
        &timing,
        &jobs,
        &targets,
        affinities(&options.compile_affinities, &targets)?,
    )?;
    let current = predict(&shards, &model)?;
    let (baseline_slowest_wall_clock, baseline_runner_seconds) = job_metrics(&jobs.rows)?;
    let approved_slowest_wall_clock = options
        .max_shard_wall_clock
        .min(baseline_slowest_wall_clock);
    let candidate = select(&model, &targets, &shards, approved_slowest_wall_clock)?;
    let baseline_wall_clock = shard_map(&jobs.shard_medians, "jobs timing shard_medians")?;
    validate_shard_map(&baseline_wall_clock, count, "jobs timing shard_medians")?;
    let is_noop = candidate.layout == shards;
    Ok((
        HarnessPlanResponse {
            proposed_shards: candidate.layout.clone(),
            active_runner_count: u32::try_from(
                candidate
                    .layout
                    .values()
                    .filter(|targets| !targets.is_empty())
                    .count(),
            )
            .map_err(|_| "rebalance-tests active runner count is too large".to_owned())?,
            predicted_current: current.clone(),
            predicted_proposed: candidate.predicted.clone(),
            baseline_wall_clock,
            baseline_slowest_wall_clock,
            baseline_runner_seconds,
            approved_slowest_wall_clock,
            is_noop,
        },
        violations(&current, &candidate.predicted, approved_slowest_wall_clock),
    ))
}

fn build_python_plan(
    wire: PythonPlanWire,
    options: &PlanOptions,
) -> Result<PythonPlanResponse, String> {
    let expected_run_ids = run_ids(wire.expected_run_ids, "python.expected_run_ids")?;
    let current_assignments = assignments(wire.current_assignments, "python.current_assignments")?;
    let timing = pytest_report(wire.timing)?;
    validate_pytest_cohort(&timing, &expected_run_ids)?;
    let count = match (options.n_python_shards, timing.observed_shard_count) {
        (Some(expected), Some(observed)) if expected != observed => {
            return Err(format!(
                "rebalance-tests n_python_shards={expected} does not match observed pytest shard count {observed}"
            ));
        }
        (Some(expected), _) => expected,
        (None, Some(observed)) => observed,
        (None, None) => {
            return Err("rebalance-tests pytest timing has no observed shard count".to_owned());
        }
    };
    if timing.nodeid_medians.is_empty() {
        return Err("rebalance-tests pytest timing has no nodeid medians".to_owned());
    }
    if current_assignments.values().any(|shard| *shard > count) {
        return Err(format!(
            "rebalance-tests python assignments have a shard outside 1..={count}"
        ));
    }
    let timings = timing
        .nodeid_medians
        .iter()
        .map(|row| TestShardTiming {
            target: row.nodeid.clone(),
            seconds: row.seconds,
            affinity_group: None,
            affinity_setup_seconds: 0.0,
        })
        .collect::<Vec<_>>();
    let packed = pack_test_shards(&timings, count, "", &[])
        .map_err(|error| format!("rebalance-tests cannot pack pytest nodeids: {error}"))?;
    let assignments = packed
        .into_iter()
        .flat_map(|(shard, nodeids)| nodeids.into_iter().map(move |nodeid| (nodeid, shard)))
        .collect::<BTreeMap<_, _>>();
    if assignments.len() != timing.nodeid_medians.len() {
        return Err("rebalance-tests test-shard owner omitted a pytest nodeid".to_owned());
    }
    Ok(PythonPlanResponse {
        is_noop: assignments == current_assignments,
        assignments,
        shard_count: count,
    })
}

fn validate_harness_cohort(
    report: &HarnessTimingReport,
    shards: &BTreeMap<u32, Vec<String>>,
    expected_runs: &[u64],
) -> Result<(), String> {
    if report.sampled_run_ids != expected_runs || !report.skipped_run_ids.is_empty() {
        return Err(
            "rebalance-tests harness timing cohort does not match requested complete run ids"
                .to_owned(),
        );
    }
    let expected_targets = shards.values().flatten().cloned().collect::<BTreeSet<_>>();
    if report
        .rows
        .iter()
        .any(|row| !row.seconds.is_finite() || row.seconds < 0.0)
        || report
            .bootstrap_rows
            .iter()
            .any(|row| !row.seconds.is_finite() || row.seconds < 0.0)
    {
        return Err("rebalance-tests harness timing has invalid duration values".to_owned());
    }
    let mut timing = HashMap::<(u64, u32), Vec<&HarnessTimingRow>>::new();
    let mut bootstrap = HashMap::<(u64, u32), Vec<&HarnessBootstrapRow>>::new();
    for row in &report.rows {
        timing.entry((row.run_id, row.shard)).or_default().push(row);
    }
    for row in &report.bootstrap_rows {
        bootstrap
            .entry((row.run_id, row.shard))
            .or_default()
            .push(row);
    }
    let runs = expected_runs.iter().copied().collect::<BTreeSet<_>>();
    if timing.keys().map(|(run, _)| *run).collect::<BTreeSet<_>>() != runs
        || bootstrap
            .keys()
            .map(|(run, _)| *run)
            .collect::<BTreeSet<_>>()
            != runs
    {
        return Err(
            "rebalance-tests harness timing cohort is missing target or bootstrap evidence"
                .to_owned(),
        );
    }
    validate_harness_runs(
        &timing,
        &bootstrap,
        shards,
        expected_runs,
        &expected_targets,
    )?;
    validate_harness_medians(report, &expected_targets)
}

fn validate_harness_runs(
    timing: &HashMap<(u64, u32), Vec<&HarnessTimingRow>>,
    bootstrap: &HashMap<(u64, u32), Vec<&HarnessBootstrapRow>>,
    shards: &BTreeMap<u32, Vec<String>>,
    expected_runs: &[u64],
    expected_targets: &BTreeSet<String>,
) -> Result<(), String> {
    let nonempty = shards
        .iter()
        .filter_map(|(shard, targets)| (!targets.is_empty()).then_some(*shard))
        .collect::<BTreeSet<_>>();
    let mut marks = BTreeMap::<u32, BTreeMap<String, usize>>::new();
    for run in expected_runs {
        if shard_coverage(timing, *run) != nonempty || shard_coverage(bootstrap, *run) != nonempty {
            return Err(format!(
                "rebalance-tests harness timing has incompatible shard coverage in run {run}"
            ));
        }
        let mut seen = BTreeSet::new();
        for (&shard, targets) in shards {
            let rows = timing.get(&(*run, shard)).map_or(&[][..], Vec::as_slice);
            let boots = bootstrap.get(&(*run, shard)).map_or(&[][..], Vec::as_slice);
            let timing_counts = counts(rows.iter().map(|row| row.target.as_str()));
            if timing_counts.keys().cloned().collect::<BTreeSet<_>>()
                != targets.iter().cloned().collect()
            {
                return Err(format!(
                    "rebalance-tests harness target inventory drift in run {run}, shard {shard}"
                ));
            }
            if timing_counts != counts(boots.iter().map(|row| row.target.as_str())) {
                return Err(format!(
                    "rebalance-tests harness bootstrap evidence does not pair in run {run}, shard {shard}"
                ));
            }
            if marks
                .get(&shard)
                .is_some_and(|prior| prior != &timing_counts)
            {
                return Err(format!(
                    "rebalance-tests harness target marks differ in run {run}, shard {shard}"
                ));
            }
            marks.entry(shard).or_insert_with(|| timing_counts.clone());
            if !rows.is_empty() {
                let kinds = counts(boots.iter().map(|row| row.bootstrap_kind.as_str()));
                if kinds.get("unknown").copied().unwrap_or_default() > 0
                    || kinds.get("cold").copied().unwrap_or_default() != 1
                    || kinds.get("warm").copied().unwrap_or_default() != boots.len() - 1
                {
                    return Err(format!(
                        "rebalance-tests harness bootstrap evidence is incomplete in run {run}, shard {shard}"
                    ));
                }
            }
            seen.extend(timing_counts.into_keys());
        }
        if seen != *expected_targets {
            return Err(format!(
                "rebalance-tests harness target inventory drift in run {run}"
            ));
        }
    }
    Ok(())
}

fn shard_coverage<T>(rows: &HashMap<(u64, u32), Vec<T>>, run: u64) -> BTreeSet<u32> {
    rows.keys()
        .filter_map(|(candidate, shard)| (*candidate == run).then_some(*shard))
        .collect()
}

fn validate_harness_medians(
    report: &HarnessTimingReport,
    expected_targets: &BTreeSet<String>,
) -> Result<(), String> {
    let targets = report
        .target_medians
        .iter()
        .map(|row| row.target.clone())
        .collect::<BTreeSet<_>>();
    if targets.len() != report.target_medians.len()
        || targets != *expected_targets
        || report
            .target_medians
            .iter()
            .any(|row| !row.seconds.is_finite() || row.seconds < 0.0)
    {
        return Err(
            "rebalance-tests harness median inventory does not match current shards".to_owned(),
        );
    }
    Ok(())
}

fn validate_jobs_cohort(
    report: &JobTimingReport,
    expected_runs: &[u64],
    shard_count: u32,
) -> Result<(), String> {
    if report.sampled_run_ids != expected_runs || !report.skipped_run_ids.is_empty() {
        return Err(
            "rebalance-tests jobs timing cohort does not match requested complete run ids"
                .to_owned(),
        );
    }
    let expected = expected_runs
        .iter()
        .flat_map(|run| (1..=shard_count).map(move |shard| (*run, shard)))
        .collect::<BTreeSet<_>>();
    let observed = report
        .rows
        .iter()
        .map(|row| (row.run_id, row.shard))
        .collect::<BTreeSet<_>>();
    if expected != observed
        || observed.len() != report.rows.len()
        || report
            .rows
            .iter()
            .any(|row| !row.seconds.is_finite() || row.seconds < 0.0)
    {
        return Err(
            "rebalance-tests jobs timing has missing or duplicate harness shard rows".to_owned(),
        );
    }
    Ok(())
}

fn validate_pytest_cohort(
    report: &PytestTimingReport,
    expected_runs: &[u64],
) -> Result<(), String> {
    if report.sampled_run_ids != expected_runs || !report.skipped_run_ids.is_empty() {
        return Err(
            "rebalance-tests pytest timing cohort does not match requested complete run ids"
                .to_owned(),
        );
    }
    if report.rows.is_empty()
        || report
            .rows
            .iter()
            .map(|row| row.run_id)
            .collect::<BTreeSet<_>>()
            != expected_runs.iter().copied().collect()
        || report.rows.iter().any(|row| {
            row.shard == 0
                || row.nodeid.is_empty()
                || row.attempt == 0
                || !row.seconds.is_finite()
                || row.seconds < 0.0
        })
    {
        return Err("rebalance-tests pytest timing has incomplete rows".to_owned());
    }
    if let Some(count) = report.observed_shard_count {
        let expected = (1..=count).collect::<BTreeSet<_>>();
        if count == 0
            || report.rows.iter().any(|row| {
                row.shard > count
                    || row
                        .shard_total
                        .is_some_and(|total| total == 0 || total != count)
            })
            || expected_runs.iter().any(|run| {
                report
                    .rows
                    .iter()
                    .filter_map(|row| (row.run_id == *run).then_some(row.shard))
                    .collect::<BTreeSet<_>>()
                    != expected
            })
        {
            return Err("rebalance-tests pytest timing has incompatible shard counts".to_owned());
        }
    }
    Ok(())
}

fn counts<'a>(values: impl Iterator<Item = &'a str>) -> BTreeMap<String, usize> {
    let mut result = BTreeMap::new();
    for value in values {
        *result.entry(value.to_owned()).or_default() += 1;
    }
    result
}

fn affinities(
    specs: &[CompileAffinity],
    targets: &[String],
) -> Result<BTreeMap<String, AffinityCost>, String> {
    let expected = targets.iter().collect::<HashSet<_>>();
    let mut output = BTreeMap::new();
    let mut groups = BTreeMap::<String, f64>::new();
    for spec in specs {
        if !expected.contains(&spec.target) || output.contains_key(&spec.target) {
            return Err(format!(
                "rebalance-tests compile affinity target {:?} is invalid or repeated",
                spec.target
            ));
        }
        if groups
            .get(&spec.group)
            .is_some_and(|prior| prior.to_bits() != spec.setup_seconds.to_bits())
        {
            return Err(format!(
                "rebalance-tests compile affinity group {:?} has inconsistent setup seconds",
                spec.group
            ));
        }
        groups.insert(spec.group.clone(), spec.setup_seconds);
        output.insert(
            spec.target.clone(),
            AffinityCost {
                group: spec.group.clone(),
                setup_seconds: spec.setup_seconds,
            },
        );
    }
    Ok(output)
}

fn model(
    report: &HarnessTimingReport,
    jobs: &JobTimingReport,
    targets: &[String],
    affinities: BTreeMap<String, AffinityCost>,
) -> Result<Model, String> {
    let mut work = HashMap::<(u64, u32), Vec<&HarnessTimingRow>>::new();
    let mut boots = HashMap::<(u64, u32), Vec<&HarnessBootstrapRow>>::new();
    for row in &report.rows {
        work.entry((row.run_id, row.shard)).or_default().push(row);
    }
    for row in &report.bootstrap_rows {
        boots.entry((row.run_id, row.shard)).or_default().push(row);
    }
    let mut fixed = Vec::new();
    let mut cold = Vec::new();
    let mut warm = Vec::new();
    let mut marks = BTreeMap::<String, Vec<usize>>::new();
    for job in &jobs.rows {
        let key = (job.run_id, job.shard);
        let target_rows = work.get(&key).map_or(&[][..], Vec::as_slice);
        let boot_rows = boots.get(&key).map_or(&[][..], Vec::as_slice);
        let startup = job.seconds
            - sum(target_rows.iter().map(|row| row.seconds))?
            - sum(boot_rows.iter().map(|row| row.seconds))?;
        if !startup.is_finite() || startup < 0.0 {
            return Err(format!(
                "rebalance-tests jobs wall-clock is below recorded work in run {}, shard {}",
                job.run_id, job.shard
            ));
        }
        fixed.push(startup);
        for row in boot_rows {
            if row.bootstrap_kind == "cold" {
                cold.push(row.seconds);
            }
            if row.bootstrap_kind == "warm" {
                warm.push(row.seconds);
            }
        }
        for (target, count) in counts(boot_rows.iter().map(|row| row.target.as_str())) {
            marks.entry(target).or_default().push(count);
        }
    }
    let warm = median(&warm, "warm timer-bootstrap")?;
    let cold = median(&cold, "cold timer-bootstrap")?;
    if cold < warm {
        return Err("rebalance-tests cold timer-bootstrap median is below warm median".to_owned());
    }
    let medians = report
        .target_medians
        .iter()
        .map(|row| {
            nonnegative(row.seconds, "harness target median")
                .map(|seconds| (row.target.clone(), seconds))
        })
        .collect::<Result<BTreeMap<_, _>, _>>()?;
    let mut target_seconds = BTreeMap::new();
    for target in targets {
        let counts = marks
            .get(target)
            .filter(|values| !values.is_empty())
            .ok_or_else(|| format!("rebalance-tests target marks are missing for {target:?}"))?;
        if counts.iter().any(|count| *count != counts[0]) {
            return Err(format!(
                "rebalance-tests target marks differ for {target:?}"
            ));
        }
        let marks = u32::try_from(counts[0])
            .map_err(|_| format!("rebalance-tests target has too many marks: {target:?}"))?;
        let seconds = medians
            .get(target)
            .ok_or_else(|| format!("rebalance-tests target median is missing for {target:?}"))?
            + f64::from(marks) * warm;
        nonnegative(seconds, "harness target cost")?;
        target_seconds.insert(target.clone(), seconds);
    }
    Ok(Model {
        fixed_startup_seconds: median(&fixed, "fixed job-startup")?,
        shared_setup_seconds: cold - warm,
        target_seconds,
        affinities,
    })
}

fn predict(
    shards: &BTreeMap<u32, Vec<String>>,
    model: &Model,
) -> Result<BTreeMap<u32, f64>, String> {
    shards
        .iter()
        .map(|(shard, targets)| {
            let mut total = model.fixed_startup_seconds;
            if !targets.is_empty() {
                total += model.shared_setup_seconds;
            }
            let mut charged = HashSet::new();
            for target in targets {
                total += model
                    .target_seconds
                    .get(target)
                    .ok_or_else(|| format!("rebalance-tests target cost missing for {target:?}"))?;
                if let Some(affinity) = model.affinities.get(target)
                    && charged.insert(affinity.group.as_str())
                {
                    total += affinity.setup_seconds;
                }
            }
            nonnegative(total, "predicted shard time").map(|value| (*shard, value))
        })
        .collect()
}

fn sum(mut values: impl Iterator<Item = f64>) -> Result<f64, String> {
    values.try_fold(0.0, |total, value| {
        nonnegative(value, "timing sample")?;
        nonnegative(total + value, "timing sum")
    })
}

fn median(values: &[f64], context: &str) -> Result<f64, String> {
    if values.is_empty() {
        return Err(format!(
            "rebalance-tests has no comparable {context} samples"
        ));
    }
    let mut sorted = values.to_vec();
    sorted.sort_by(f64::total_cmp);
    let index = sorted.len() / 2;
    nonnegative(
        if sorted.len().is_multiple_of(2) {
            sorted[index - 1] / 2.0 + sorted[index] / 2.0
        } else {
            sorted[index]
        },
        context,
    )
}

fn select(
    model: &Model,
    targets: &[String],
    current: &BTreeMap<u32, Vec<String>>,
    approved: f64,
) -> Result<Candidate, String> {
    let current = Candidate {
        layout: current.clone(),
        predicted: predict(current, model)?,
    };
    let count = u32::try_from(current.layout.len())
        .map_err(|_| "rebalance-tests shard count is too large".to_owned())?;
    let mut candidates = vec![current.clone()];
    for active_count in 1..=count {
        let active = active_ids(&current.layout, active_count);
        let layout = pack_harness(model, targets, count, &active)?;
        candidates.push(Candidate {
            predicted: predict(&layout, model)?,
            layout,
        });
    }
    let mut safe = None;
    for candidate in &candidates {
        if violations(&current.predicted, &candidate.predicted, approved).is_empty()
            && safe
                .as_ref()
                .is_none_or(|best| better(candidate, best, &current.layout))
        {
            safe = Some(candidate.clone());
        }
    }
    if let Some(candidate) = safe {
        return Ok(candidate);
    }
    Ok(candidates
        .into_iter()
        .reduce(|best, candidate| {
            if compare(&candidate.predicted, &best.predicted) == Ordering::Less {
                candidate
            } else {
                best
            }
        })
        .expect("current candidate exists"))
}

fn active_ids(shards: &BTreeMap<u32, Vec<String>>, count: u32) -> Vec<u32> {
    let mut ids = shards
        .iter()
        .filter_map(|(id, targets)| (!targets.is_empty()).then_some(*id))
        .collect::<Vec<_>>();
    ids.extend(
        shards
            .iter()
            .filter_map(|(id, targets)| targets.is_empty().then_some(*id)),
    );
    ids.truncate(usize::try_from(count).expect("u32 fits usize"));
    ids
}

fn pack_harness(
    model: &Model,
    targets: &[String],
    shard_count: u32,
    active: &[u32],
) -> Result<BTreeMap<u32, Vec<String>>, String> {
    if active.is_empty() || active.iter().copied().collect::<BTreeSet<_>>().len() != active.len() {
        return Err("rebalance-tests active shard ids must be nonempty and unique".to_owned());
    }
    let timings = targets
        .iter()
        .map(|target| {
            let affinity = model.affinities.get(target);
            Ok(TestShardTiming {
                target: target.clone(),
                seconds: *model
                    .target_seconds
                    .get(target)
                    .ok_or_else(|| format!("rebalance-tests target cost missing for {target:?}"))?,
                affinity_group: affinity.map(|value| value.group.clone()),
                affinity_setup_seconds: affinity.map_or(0.0, |value| value.setup_seconds),
            })
        })
        .collect::<Result<Vec<_>, String>>()?;
    let packed = pack_test_shards_with_fixed_startup(
        &timings,
        u32::try_from(active.len())
            .map_err(|_| "rebalance-tests active shard count is too large".to_owned())?,
        GUARD_TARGET,
        &[],
        model.fixed_startup_seconds + model.shared_setup_seconds,
    )
    .map_err(|error| format!("rebalance-tests cannot pack harness targets: {error}"))?;
    let mut output = (1..=shard_count)
        .map(|id| (id, Vec::new()))
        .collect::<BTreeMap<_, _>>();
    for (index, physical) in active.iter().enumerate() {
        let virtual_id = u32::try_from(index + 1)
            .map_err(|_| "rebalance-tests active shard count is too large".to_owned())?;
        output.insert(
            *physical,
            packed
                .get(&virtual_id)
                .ok_or_else(|| "rebalance-tests test-shard owner omitted a shard".to_owned())?
                .clone(),
        );
    }
    Ok(output)
}

fn violations(
    current: &BTreeMap<u32, f64>,
    proposed: &BTreeMap<u32, f64>,
    approved: f64,
) -> Vec<String> {
    let current_slowest = maximum(current).expect("nonempty current shards");
    let proposed_slowest = maximum(proposed).expect("nonempty proposed shards");
    let current_total = sum(current.values().copied()).expect("validated current times");
    let proposed_total = sum(proposed.values().copied()).expect("validated proposed times");
    let mut output = Vec::new();
    if proposed_slowest > current_slowest {
        output.push(format!("predicted slowest shard {proposed_slowest:.1}s exceeds current model {current_slowest:.1}s"));
    }
    if proposed_slowest > approved {
        output.push(format!("predicted slowest shard {proposed_slowest:.1}s exceeds approved wall-clock {approved:.1}s"));
    }
    if proposed_total > current_total {
        output.push(format!("predicted summed harness runner time {proposed_total:.1}s exceeds current model {current_total:.1}s"));
    }
    output
}

fn better(candidate: &Candidate, best: &Candidate, current: &BTreeMap<u32, Vec<String>>) -> bool {
    match compare(&candidate.predicted, &best.predicted) {
        Ordering::Less => true,
        Ordering::Greater => false,
        Ordering::Equal => {
            (candidate.layout != *current).cmp(&(best.layout != *current)) == Ordering::Less
        }
    }
}

fn compare(left: &BTreeMap<u32, f64>, right: &BTreeMap<u32, f64>) -> Ordering {
    maximum(left)
        .expect("nonempty shards")
        .total_cmp(&maximum(right).expect("nonempty shards"))
        .then_with(|| {
            sum(left.values().copied())
                .expect("finite values")
                .total_cmp(&sum(right.values().copied()).expect("finite values"))
        })
}

fn maximum(values: &BTreeMap<u32, f64>) -> Option<f64> {
    values.values().copied().max_by(f64::total_cmp)
}

fn shard_map(rows: &[ShardTiming], context: &str) -> Result<BTreeMap<u32, f64>, String> {
    let mut values = BTreeMap::new();
    for row in rows {
        if values.insert(row.shard, row.seconds).is_some() {
            return Err(format!(
                "rebalance-tests {context} contains a duplicate shard"
            ));
        }
    }
    Ok(values)
}

fn validate_shard_map(
    values: &BTreeMap<u32, f64>,
    count: u32,
    context: &str,
) -> Result<(), String> {
    (values.keys().copied().eq(1..=count)
        && values
            .values()
            .all(|seconds| seconds.is_finite() && *seconds >= 0.0))
    .then_some(())
    .ok_or_else(|| format!("rebalance-tests {context} does not cover valid expected shards"))
}

fn job_metrics(rows: &[JobTimingRow]) -> Result<(f64, f64), String> {
    let mut by_run = BTreeMap::<u64, Vec<f64>>::new();
    for row in rows {
        by_run.entry(row.run_id).or_default().push(row.seconds);
    }
    let slowest = by_run
        .values()
        .map(|values| {
            values
                .iter()
                .copied()
                .max_by(f64::total_cmp)
                .ok_or_else(|| "rebalance-tests jobs timing has an empty run".to_owned())
        })
        .collect::<Result<Vec<_>, _>>()?;
    let totals = by_run
        .values()
        .map(|values| sum(values.iter().copied()))
        .collect::<Result<Vec<_>, _>>()?;
    Ok((
        median(&slowest, "slowest harness-job wall-clock")?,
        median(&totals, "summed harness-runner")?,
    ))
}

fn verify_harness(
    wire: HarnessVerifyWire,
    options: &VerifyOptions,
) -> Result<HarnessVerifyResponse, String> {
    let expected_run_ids = run_ids(wire.expected_run_ids, "harness.expected_run_ids")?;
    let shards = shards(wire.expected_shards, "harness.expected_shards")?;
    let baseline_slowest_wall_clock = nonnegative(
        wire.baseline_slowest_wall_clock,
        "harness.baseline_slowest_wall_clock",
    )?;
    let baseline_runner_seconds = nonnegative(
        wire.baseline_runner_seconds,
        "harness.baseline_runner_seconds",
    )?;
    let approved_slowest_wall_clock = nonnegative(
        wire.approved_slowest_wall_clock,
        "harness.approved_slowest_wall_clock",
    )?;
    if approved_slowest_wall_clock > baseline_slowest_wall_clock.min(options.max_shard_wall_clock) {
        return Err(
            "rebalance-tests harness approved_slowest_wall_clock exceeds its baseline cap"
                .to_owned(),
        );
    }
    let timing = harness_report(wire.timing)?;
    let jobs = jobs_report(wire.jobs)?;
    validate_harness_cohort(&timing, &shards, &expected_run_ids)?;
    let count = u32::try_from(shards.len())
        .map_err(|_| "rebalance-tests shard count is too large".to_owned())?;
    validate_jobs_cohort(&jobs, &expected_run_ids, count)?;
    let wall_clock = shard_map(&jobs.shard_medians, "jobs timing shard_medians")?;
    validate_shard_map(&wall_clock, count, "jobs timing shard_medians")?;
    let slowest = maximum(&wall_clock)
        .ok_or_else(|| "rebalance-tests jobs timing has no shard medians".to_owned())?;
    let (_, runner_seconds) = job_metrics(&jobs.rows)?;
    let mut violations = Vec::new();
    if wall_clock
        .values()
        .any(|seconds| *seconds > options.max_shard_wall_clock)
    {
        violations.push("measured slowest shard exceeds max_shard_wall_clock".to_owned());
    }
    if slowest > approved_slowest_wall_clock {
        violations.push(format!(
            "measured slowest shard {slowest:.1}s regresses approved threshold {approved_slowest_wall_clock:.1}s",
        ));
    }
    if runner_seconds > baseline_runner_seconds {
        violations.push(format!(
            "measured summed harness runner time {runner_seconds:.1}s exceeds baseline {baseline_runner_seconds:.1}s",
        ));
    }
    let outcome = if violations.is_empty() {
        Outcome::Passed
    } else if options.experimental_override.is_some() {
        Outcome::Overridden
    } else {
        Outcome::Rejected
    };
    Ok(HarnessVerifyResponse {
        outcome,
        wall_clock,
        baseline_slowest_wall_clock,
        observed_slowest_wall_clock: slowest,
        observed_runner_seconds: runner_seconds,
        violations,
    })
}

fn verify_python(
    wire: PythonVerifyWire,
    options: &VerifyOptions,
) -> Result<PythonVerifyResponse, String> {
    let expected_run_ids = run_ids(wire.expected_run_ids, "python.expected_run_ids")?;
    let shard_count = nonzero(wire.expected_shard_count, "python.expected_shard_count")?;
    let timing = pytest_report(wire.timing)?;
    validate_pytest_cohort(&timing, &expected_run_ids)?;
    let shard_medians = shard_map(&timing.shard_medians, "pytest timing shard_medians")?;
    validate_shard_map(&shard_medians, shard_count, "pytest timing shard_medians")?;
    let slowest = maximum(&shard_medians)
        .ok_or_else(|| "rebalance-tests pytest timing has no shard medians".to_owned())?;
    let fastest = shard_medians
        .values()
        .copied()
        .min_by(f64::total_cmp)
        .expect("nonempty checked above");
    let spread = slowest - fastest;
    let violations = (spread > options.balance_threshold)
        .then(|| {
            format!(
                "pytest shard spread {spread:.1}s exceeds balance_threshold {threshold:.1}s",
                threshold = options.balance_threshold
            )
        })
        .into_iter()
        .collect::<Vec<_>>();
    Ok(PythonVerifyResponse {
        outcome: if violations.is_empty() {
            Outcome::Passed
        } else {
            Outcome::Rejected
        },
        shard_medians,
        spread,
        balance_threshold: options.balance_threshold,
        violations,
    })
}
