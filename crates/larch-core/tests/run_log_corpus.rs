use chrono::{DateTime, Utc};
use larch_core::{
    RunLogCorpus, RunLogCorpusEvent, RunLogCorpusWarningKind, RunLogRoundSort, RunLogRun,
    RunLogSelection, RunLogSlug, RunLogTimeWindow, parse_preterminal_outcome_label,
    round_number_from_path, run_log_batch_spec, run_log_batch_specs,
};
use std::{fs, path::Path};
use tempfile::TempDir;
fn write_file(root: &Path, relative: &str, body: &str) {
    let path = root.join(relative);
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    fs::write(path, body).unwrap();
}
fn timestamp(value: &str) -> DateTime<Utc> {
    DateTime::parse_from_rfc3339(value)
        .unwrap()
        .with_timezone(&Utc)
}
fn run_paths(events: &[RunLogCorpusEvent]) -> Vec<String> {
    events
        .iter()
        .filter_map(|event| match event {
            RunLogCorpusEvent::Run(run) => Some(run.layout().run_id().as_str().to_owned()),
            RunLogCorpusEvent::Warning(_) => None,
        })
        .collect()
}
fn run_for_skill<'a>(events: &'a [RunLogCorpusEvent], skill: &str) -> &'a RunLogRun {
    events
        .iter()
        .find_map(|event| match event {
            RunLogCorpusEvent::Run(run) if run.layout().skill().as_str() == skill => Some(run),
            _ => None,
        })
        .unwrap()
}
fn assert_warning_has_path_and_message(events: &[RunLogCorpusEvent]) {
    assert!(events.iter().any(|event| matches!(
        event,
        RunLogCorpusEvent::Warning(warning)
            if !warning.path().as_os_str().is_empty() && !warning.message().is_empty()
    )));
}
fn assert_implement_artifacts(implement: &RunLogRun) {
    assert_eq!(implement.batches().count(), 1);
    let artifact = implement.batches().next().unwrap();
    assert_eq!(artifact.spec().slug(), "token-report");
    assert!(artifact.path().is_file());
    assert_eq!(implement.files().count(), 4);
    assert_eq!(
        implement
            .classification_paths(RunLogRoundSort::Numeric)
            .iter()
            .map(|path| path
                .parent()
                .unwrap()
                .file_name()
                .unwrap()
                .to_str()
                .unwrap())
            .collect::<Vec<_>>(),
        ["round-2", "round-10"]
    );
}
fn assert_unwindowed_selection(corpus: &RunLogCorpus) {
    let events: Vec<_> = corpus.select(RunLogSelection::all()).collect();
    assert_eq!(
        run_paths(&events),
        ["run-design", "run-1", "run-alpha", "run-zulu", "run-review"]
    );
    assert_eq!(
        events
            .iter()
            .filter(|event| matches!(event, RunLogCorpusEvent::Warning(_)))
            .count(),
        9 + usize::from(cfg!(unix))
    );
    let design = run_for_skill(&events, "design");
    let review = run_for_skill(&events, "review");
    assert!(corpus.root().ends_with("larch-logs"));
    assert_warning_has_path_and_message(&events);
    assert_eq!(design.manifest().issue_number(), 1);
    assert_eq!(
        design
            .directory()
            .file_name()
            .and_then(|name| name.to_str()),
        Some("run-design")
    );
    assert!(design.manifest().field("issue_number").is_some());
    assert!(design.manifest().typed_record().is_none());
    assert_eq!(
        [
            design.classification_paths(RunLogRoundSort::Numeric).len(),
            review.classification_paths(RunLogRoundSort::Lexical).len()
        ],
        [1, 2]
    );
    assert!(design.session_transcript_path().is_some());
    assert_implement_artifacts(run_for_skill(&events, "implement"));
    assert_eq!(
        design.started_at(true, false),
        Some(timestamp("2026-04-03T01:02:03Z"))
    );
    assert_eq!(
        design.started_at(false, true),
        Some(timestamp("2026-04-01T00:00:00Z"))
    );
    assert_eq!(
        design.ended_at(true),
        Some(timestamp("2026-04-03T01:02:03Z"))
    );
    assert_eq!(design.larch_version(true), Some("v2.3.4-beta.1".to_owned()));
    assert_eq!(
        design.larch_version(false),
        Some("v2.3.4-beta.1".to_owned())
    );
    assert_eq!(review.started_at(false, false), None);
    assert_eq!(review.started_at(false, true), None);
    assert_eq!(review.ended_at(false), None);
    assert_eq!(review.ended_at(true), None);
    assert_eq!(review.larch_version(false), None);
    assert_eq!(review.larch_version(true), None);
    fs::remove_dir_all(design.directory()).unwrap();
    assert_eq!(design.files().count(), 0);
}
#[test]
fn batch_registry_is_sorted_and_preserves_durable_contracts() {
    let specs: Vec<_> = run_log_batch_specs().collect();
    assert_eq!(specs.len(), 45);
    assert!(specs.windows(2).all(|pair| pair[0].slug() < pair[1].slug()));
    let debate = run_log_batch_spec("debate-round-ledger").unwrap();
    assert_eq!(debate.extension(), ".ndjson");
    assert_eq!(debate.mode().as_str(), "append");
    assert_eq!(debate.sanitizer().as_str(), "json-lines");
    assert!(debate.rejects_session_tmpdir());
    let token_report = run_log_batch_spec("token-report").unwrap();
    let plan_goals = run_log_batch_spec("plan-goals-test").unwrap();
    let review_tally = run_log_batch_spec("code-review-tally").unwrap();
    assert_eq!(token_report.mode().as_str(), "replace");
    assert_eq!(token_report.sanitizer().as_str(), "none");
    assert_eq!(plan_goals.sanitizer().as_str(), "plan-goals");
    assert_eq!(review_tally.sanitizer().as_str(), "json-object");
    assert_eq!(
        token_report.path_in("run"),
        Path::new("run/token-report.json")
    );
    assert_eq!(run_log_batch_spec("missing"), None);
    assert_eq!(
        parse_preterminal_outcome_label("## /x: Success"),
        Some("success".to_owned())
    );
    assert_eq!(
        parse_preterminal_outcome_label("## /x — Done"),
        Some("done".to_owned())
    );
    assert_eq!(
        parse_preterminal_outcome_label("# ignored\n## /x: Earlier — Winner"),
        Some("winner".to_owned())
    );
    assert_eq!(parse_preterminal_outcome_label("## /x"), None);
    let before = timestamp("2026-04-01T00:00:00Z");
    let after = timestamp("2026-04-02T00:00:00Z");
    assert_eq!(
        RunLogTimeWindow::new(Some(after), Some(before))
            .unwrap_err()
            .to_string(),
        "run-log time window start must not fall after its end"
    );
    assert_eq!(
        round_number_from_path(Path::new("notes-round-3.tsv")),
        Some(3)
    );
}
#[test]
fn corpus_rejects_non_directory_root() {
    let temporary = TempDir::new().unwrap();
    let root = temporary.path().join("not-a-directory");
    fs::write(&root, "not a directory").unwrap();
    let events: Vec<_> = RunLogCorpus::new(root)
        .select(RunLogSelection::all())
        .collect();
    assert!(events.iter().any(|event| matches!(
        event,
        RunLogCorpusEvent::Warning(warning)
            if warning.kind() == RunLogCorpusWarningKind::RootMissing
    )));
}
#[test]
fn corpus_selection_is_deterministic_tolerant_and_windowed() {
    let temporary = TempDir::new().unwrap();
    let root = temporary.path().join("larch-logs");
    macro_rules! file {
        ($path:literal, $body:literal) => {
            write_file(&root, $path, $body);
        };
    }
    file!(
        "implement/run-alpha/manifest.json",
        r#"{"issue_number":" 1,234 ","started_at":""}"#
    );
    file!(
        "implement/run-alpha/run-manifest.json",
        r#"{"started_at":"2026-04-02T00:00:00Z","larch_version":"1.2.3"}"#
    );
    file!(
        "implement/run-zulu/manifest.json",
        r#"{"issue_number":9223372036854775808,"started_at":"2026-04-10T00:00:00Z"}"#
    );
    file!("implement/f/manifest.json", r#"{"issue_number":"0.5"}"#);
    file!(
        "design/run-design/manifest.json",
        r#"{"issue_number":1,"started_at":"invalid","updated_at":"2026-04-03 01:02:03","ended_at":false,"larch_version":"invalid"}"#
    );
    file!(
        "design/run-design/run-manifest.json",
        r#"{"started_at":"2026-04-01","completed_at":"2026-04-04T00:00:00Z","larch_version":"v2.3.4-beta.1"}"#
    );
    file!("review/run-review/manifest.json", r#"{"issue_number":2}"#);
    file!("implement/run-1/manifest.json", r#"{"issue_number":7}"#);
    file!("implement/n/manifest.json", r#"{"issue_number":"-1"}"#);
    file!("implement/run-1/token-report.json", "{}\n");
    file!(
        "design/run-design/plan-review/round-12/findings-classification.tsv",
        "ok\n"
    );
    file!("design/run-design/session-transcript.jsonl", "ok\n");
    file!(
        "review/run-review/review-findings-classification-round-.tsv",
        "ok\n"
    );
    file!(
        "review/run-review/review-findings-classification-round-2.tsv",
        "ok\n"
    );
    file!(
        "implement/run-1/round-10/findings-classification.tsv",
        "ok\n"
    );
    file!(
        "implement/run-1/round-2/findings-classification.tsv",
        "ok\n"
    );
    for (name, body) in [("no-issue", "{}"), ("not-object", "[]"), ("not-json", "{")] {
        write_file(&root, &format!("implement/{name}/manifest.json"), body);
    }
    fs::create_dir_all(root.join("implement/no-manifest")).unwrap();
    fs::create_dir_all(root.join("implement/manifest-dir/manifest.json")).unwrap();
    fs::create_dir_all(root.join("implement/bad id")).unwrap();
    fs::create_dir_all(root.join("bad skill/run")).unwrap();
    #[cfg(unix)]
    std::os::unix::fs::symlink(root.join("implement"), root.join("symlink")).unwrap();
    let corpus = RunLogCorpus::new(&root);
    assert_unwindowed_selection(&corpus);
    let window = RunLogTimeWindow::new(
        Some(timestamp("2026-04-03T00:00:00Z")),
        Some(timestamp("2026-04-11T00:00:00Z")),
    )
    .unwrap();
    let selected: Vec<_> = corpus
        .select(
            RunLogSelection::for_skill(RunLogSlug::parse("implement").unwrap()).with_window(window),
        )
        .collect();
    assert_eq!(run_paths(&selected), ["run-zulu"]);
    assert!(selected.iter().any(|event| matches!(
        event,
        RunLogCorpusEvent::Warning(warning)
            if warning.kind() == RunLogCorpusWarningKind::WindowTimestampUnavailable
    )));
    let missing: Vec<_> = RunLogCorpus::new(root.join("missing"))
        .select(RunLogSelection::all())
        .collect();
    assert!(missing.iter().any(|event| match event {
        RunLogCorpusEvent::Warning(warning) =>
            warning.kind() == RunLogCorpusWarningKind::RootMissing
                && warning.path().ends_with("missing")
                && !warning.message().is_empty(),
        RunLogCorpusEvent::Run(_) => false,
    }));
}
