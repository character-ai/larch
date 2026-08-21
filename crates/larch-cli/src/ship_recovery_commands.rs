//! Rust owner for operator-approved manual-merge reconciliation (#8628).

use std::{
    collections::{BTreeMap, BTreeSet},
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{
    PathIntent, PathSafetyErrorKind, TemporaryRoot, github::PullRequestState, read_utf8,
};
use larch_core::{
    ChildEnvironment, DuplicatePolicy, KvDocument, ParseOptions, kv_text, private_atomic_write,
    redact_outbound, validate_run_id,
};
use serde_json::Value;

use crate::{
    argparse_compat::{missing, parse_python_int, parse_with_flags},
    github_repository_resolution::repository_ref,
    github_service::with_github_service,
    implement_child_seam::delegate_larch_with_environment,
    ship_commands::validate_tmpdir,
};

const PROGRAM: &str = "cli.py ship reconcile-manual-merge";
const USAGE: &str = concat!(
    "usage: cli.py ship reconcile-manual-merge [-h] --implement-tmpdir\n",
    "                                          IMPLEMENT_TMPDIR --pr PR\n",
    "                                          [--repo REPO]",
);
const HELP: &str = concat!(
    "usage: cli.py ship reconcile-manual-merge [-h] --implement-tmpdir\n",
    "                                          IMPLEMENT_TMPDIR --pr PR\n",
    "                                          [--repo REPO]\n\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --implement-tmpdir IMPLEMENT_TMPDIR\n",
    "  --pr PR\n",
    "  --repo REPO",
);
const OPTIONS: &[&str] = &["--implement-tmpdir", "--pr", "--repo"];
#[rustfmt::skip]
const CLEAR_FIELDS: &[(&str, &str)] = &[
    ("STALL_TRACKING", "false"), ("STALL_STEP", ""), ("BAIL_REASON", ""),
    ("BAIL_NEEDS_USER_INPUT", "false"), ("BAIL_FAILURE_DETAIL_LOG", ""),
    ("FAILED_RUN_ID", ""), ("EXIT_CODE", "0"), ("IMPLEMENT_BAIL_REASON", ""),
];

#[derive(Debug)]
struct Request {
    tmpdir: PathBuf,
    number: u64,
    repo: Option<String>,
}

struct MergedPullRequest {
    number: u64,
    url: String,
}

/// Reconcile one confirmed manual merge into every durable workflow layer.
pub fn reconcile_manual_merge(arguments: &[OsString]) -> ExitCode {
    let request = match parse(arguments) {
        Ok(request) => request,
        Err(error) => return failed(error),
    };
    match reconcile(&request) {
        Ok(()) => {
            println!("RECONCILE_STATUS=ok");
            println!("PR_NUMBER={}", request.number);
            println!("MERGE_RESULT=merged");
            ExitCode::SUCCESS
        }
        Err(error) => failed(&error),
    }
}

#[rustfmt::skip]
fn parse(arguments: &[OsString]) -> Result<Request, &'static str> {
    let parsed = parse_with_flags(arguments, OPTIONS, &["-h", "--help"], 0);
    if parsed.flag("-h") || parsed.flag("--help") {
        println!("{HELP}"); return Err("usage");
    }
    if let Some(error) = parsed.value_error() {
        eprintln!("{USAGE}\n{PROGRAM}: error: {error}"); return Err("usage");
    }
    let required = [
        ("--implement-tmpdir", parsed.value("--implement-tmpdir").is_some()),
        ("--pr", parsed.value("--pr").is_some()),
    ];
    if required.iter().any(|(_name, present)| !present) {
        eprintln!("{USAGE}\n{PROGRAM}: error: {}", missing(&required)); return Err("usage");
    }
    if let Some(error) = parsed.error() {
        eprintln!("{USAGE}\n{PROGRAM}: error: {error}"); return Err("usage");
    }
    let value = |name| parsed.value(name).map(|value| value.to_string_lossy().into_owned()).unwrap_or_default();
    let raw_pr = value("--pr");
    let number = parse_python_int(&raw_pr).ok_or_else(|| {
        eprintln!("{USAGE}\n{PROGRAM}: error: argument --pr: invalid int value: '{raw_pr}'");
        "usage"
    })?;
    let number = u64::try_from(number).ok().filter(|number| *number > 0).ok_or("invalid-pr")?;
    Ok(Request {
        tmpdir: PathBuf::from(value("--implement-tmpdir")),
        number,
        repo: parsed.value("--repo").map(|value| value.to_string_lossy().into_owned()),
    })
}

fn reconcile(request: &Request) -> Result<(), String> {
    validate_tmpdir(&request.tmpdir).map_err(|_| "unsafe-implement-tmpdir".to_owned())?;
    let tmpdir =
        fs::canonicalize(&request.tmpdir).map_err(|_| "unsafe-implement-tmpdir".to_owned())?;
    let ship = read_layer(&tmpdir, "ship-pr-state.sh", false)?;
    let finalize = read_layer(&tmpdir, "finalize-state.sh", false)?;
    let session = read_layer(&tmpdir, "session-env.sh", true)?;
    let run_id = session
        .get("LARCH_RUN_ID")
        .map(String::as_str)
        .unwrap_or_default()
        .trim();
    validate_run_id(run_id).map_err(|_| "invalid-run-id".to_owned())?;
    validate_run_identity(run_id, [&ship, &finalize, &session])?;
    validate_manifest_identity(&tmpdir, run_id)?;
    let persisted = [&ship, &finalize, &session]
        .into_iter()
        .filter_map(|layer| layer.get("REPO").filter(|value| !value.is_empty()).cloned())
        .collect::<BTreeSet<_>>();
    let repo = request
        .repo
        .clone()
        .filter(|value| !value.is_empty())
        .or_else(|| persisted.first().cloned())
        .ok_or_else(|| "invalid-repo".to_owned())?;
    repository_ref(&repo).map_err(|()| "invalid-repo".to_owned())?;
    if persisted.iter().any(|saved| saved != &repo) {
        return Err("repository-mismatch".to_owned());
    }
    let pull_request = merged_pull_request(&repo, request.number)?;
    persist_reconciliation(&tmpdir, run_id, &repo, &pull_request, update_manifest)
}

fn persist_reconciliation(
    tmpdir: &Path,
    run_id: &str,
    repo: &str,
    pull_request: &MergedPullRequest,
    update: impl FnOnce(&Path, &str, u64) -> Result<(), String>,
) -> Result<(), String> {
    #[rustfmt::skip]
    let updates = BTreeMap::from([
        ("PHASE".to_owned(), "done".to_owned()), ("PR_CLOSED".to_owned(), "true".to_owned()),
        ("PR_NUMBER".to_owned(), pull_request.number.to_string()), ("PR_URL".to_owned(), pull_request.url.clone()),
        ("MERGE_RESULT".to_owned(), "merged".to_owned()), ("REPO".to_owned(), repo.to_owned()),
        ("REPO_UNAVAILABLE".to_owned(), "false".to_owned()), ("RUN_ID".to_owned(), run_id.to_owned()),
    ]);
    write_terminal_layer(
        tmpdir,
        "ship-pr-state.sh",
        &updates,
        &[("IMPLEMENT_TMPDIR", tmpdir.display().to_string())],
    )?;
    write_terminal_layer(tmpdir, "finalize-state.sh", &updates, &[])?;
    write_terminal_layer(
        tmpdir,
        "session-env.sh",
        &updates,
        &[("LARCH_RUN_ID", run_id.to_owned())],
    )?;
    private_atomic_write(
        &tmpdir.join("post-merge-sentinel"),
        "MERGE_RESULT=merged\n",
        tmpdir,
    )
    .map_err(|error| error.to_string())?;
    update(tmpdir, run_id, pull_request.number)?;
    verify(tmpdir, run_id, repo, pull_request)
}

fn merged_pull_request(repo: &str, number: u64) -> Result<MergedPullRequest, String> {
    let target = repository_ref(repo).map_err(|()| "invalid-repo".to_owned())?;
    let (pull_request, audit) = with_github_service(async |service, cancellation| {
        let pull_request = service
            .get_pull_request(cancellation, target.owner(), target.name(), number)
            .await
            .map_err(|_error| "pr-probe-failed".to_owned())?;
        let audit = service
            .audit_pull_request(cancellation, target.owner(), target.name(), number)
            .await
            .map_err(|_error| "pr-probe-failed".to_owned())?;
        Ok((pull_request, audit))
    })
    .map_err(crate::github_service::ServiceFailure::into_detail)?;
    if pull_request.number() != number || audit.number != number {
        return Err("pr-identity-mismatch".to_owned());
    }
    if pull_request.state() != PullRequestState::Closed
        || !pull_request.merged()
        || audit.merged_at.is_none()
    {
        return Err("pr-not-merged".to_owned());
    }
    Ok(MergedPullRequest {
        number,
        url: format!("https://github.com/{repo}/pull/{number}"),
    })
}

fn read_layer(
    tmpdir: &Path,
    name: &str,
    required: bool,
) -> Result<BTreeMap<String, String>, String> {
    let Some(text) = read_safe(
        tmpdir,
        &tmpdir.join(name),
        !required,
        &format!("{name}-missing"),
    )?
    else {
        return Ok(BTreeMap::new());
    };
    if text.contains('\r') {
        return Err(format!("{name}-invalid"));
    }
    let document =
        KvDocument::parse(&text, ParseOptions::legacy()).map_err(|_| format!("{name}-invalid"))?;
    for row in document.rows() {
        if !valid_key(row.key()) {
            return Err(format!("{name}-invalid"));
        }
    }
    Ok(document.select(DuplicatePolicy::Last))
}

fn read_safe(
    tmpdir: &Path,
    path: &Path,
    optional: bool,
    failure: &str,
) -> Result<Option<String>, String> {
    let root = TemporaryRoot::resolve(Some(tmpdir)).map_err(|_| failure.to_owned())?;
    let relative = path.strip_prefix(tmpdir).map_err(|_| failure.to_owned())?;
    let confined = match root.confine(root.path().join(relative), PathIntent::Read) {
        Err(error) if optional && error.kind() == PathSafetyErrorKind::Missing => return Ok(None),
        Err(_) => return Err(failure.to_owned()),
        Ok(confined) => confined,
    };
    read_utf8(&confined)
        .map(Some)
        .map_err(|_| failure.to_owned())
}

fn write_terminal_layer(
    tmpdir: &Path,
    name: &str,
    updates: &BTreeMap<String, String>,
    extra: &[(&str, String)],
) -> Result<(), String> {
    let mut layer = read_layer(tmpdir, name, name == "session-env.sh")?;
    for (key, value) in CLEAR_FIELDS {
        let _ = layer.insert((*key).to_owned(), (*value).to_owned());
    }
    layer.extend(updates.clone());
    for (key, value) in extra {
        let _ = layer.insert((*key).to_owned(), value.clone());
    }
    let rows = layer
        .iter()
        .map(|(key, value)| (key.as_str(), value.as_str()))
        .collect::<Vec<_>>();
    let text = kv_text(&rows).map_err(|error| error.to_string())?;
    private_atomic_write(&tmpdir.join(name), &text, tmpdir).map_err(|error| error.to_string())
}

fn validate_run_identity<'a>(
    run_id: &str,
    layers: impl IntoIterator<Item = &'a BTreeMap<String, String>>,
) -> Result<(), String> {
    for layer in layers {
        for key in ["RUN_ID", "LARCH_RUN_ID"] {
            if let Some(value) = layer.get(key).filter(|value| !value.trim().is_empty())
                && (validate_run_id(value.trim()).is_err() || value.trim() != run_id)
            {
                return Err("run-id-mismatch".to_owned());
            }
        }
    }
    Ok(())
}

#[rustfmt::skip]
fn manifest_path(tmpdir: &Path, run_id: &str) -> PathBuf {
    tmpdir.join("larch-logs").join("implement").join(run_id).join("manifest.json")
}

fn validate_manifest_identity(tmpdir: &Path, run_id: &str) -> Result<(), String> {
    let path = manifest_path(tmpdir, run_id);
    let Some(text) = read_safe(tmpdir, &path, true, "manifest-invalid")? else {
        return Ok(());
    };
    let manifest: Value = serde_json::from_str(&text).map_err(|_| "manifest-invalid".to_owned())?;
    let object = manifest
        .as_object()
        .ok_or_else(|| "manifest-invalid".to_owned())?;
    if let Some(saved) = object.get("run_id")
        && saved.as_str() != Some(run_id)
    {
        return Err("manifest-run-mismatch".to_owned());
    }
    Ok(())
}

fn update_manifest(tmpdir: &Path, run_id: &str, number: u64) -> Result<(), String> {
    let fields = ["status=done".to_owned(), format!("pr_number={number}")];
    let arguments = crate::run_log_commands::manifest_update_arguments(
        &tmpdir.join("larch-logs"),
        "implement",
        run_id,
        &fields,
    );
    let output = delegate_larch_with_environment(
        &arguments,
        &[(
            ChildEnvironment::ImplementTmpdir,
            tmpdir.as_os_str().to_owned(),
        )],
    )
    .map_err(|_| "manifest-update-failed".to_owned())?;
    if output.status().success() {
        Ok(())
    } else {
        Err("manifest-update-failed".to_owned())
    }
}

fn verify(
    tmpdir: &Path,
    run_id: &str,
    repo: &str,
    pull_request: &MergedPullRequest,
) -> Result<(), String> {
    let number = pull_request.number.to_string();
    let layers = [
        read_layer(tmpdir, "ship-pr-state.sh", true)?,
        read_layer(tmpdir, "finalize-state.sh", true)?,
        read_layer(tmpdir, "session-env.sh", true)?,
    ];
    validate_run_identity(run_id, layers.iter())?;
    if layers.iter().any(has_overlay) {
        return Err("bail-overlay-remains".to_owned());
    }
    for layer in &layers {
        if layer.get("PHASE").map(String::as_str) != Some("done")
            || layer.get("MERGE_RESULT").map(String::as_str) != Some("merged")
            || layer.get("PR_NUMBER").map(String::as_str) != Some(number.as_str())
            || layer.get("PR_CLOSED").map(String::as_str) != Some("true")
            || layer.get("PR_URL").map(String::as_str) != Some(pull_request.url.as_str())
            || layer.get("REPO").map(String::as_str) != Some(repo)
        {
            return Err("reconciliation-postcondition-failed".to_owned());
        }
    }
    if read_safe(
        tmpdir,
        &tmpdir.join("post-merge-sentinel"),
        false,
        "reconciliation-postcondition-failed",
    )?
    .as_deref()
        != Some("MERGE_RESULT=merged\n")
    {
        return Err("reconciliation-postcondition-failed".to_owned());
    }
    let manifest_text = read_safe(
        tmpdir,
        &manifest_path(tmpdir, run_id),
        false,
        "reconciliation-postcondition-failed",
    )?
    .ok_or_else(|| "reconciliation-postcondition-failed".to_owned())?;
    let manifest: Value = serde_json::from_str(&manifest_text)
        .map_err(|_| "reconciliation-postcondition-failed".to_owned())?;
    if manifest.get("status").and_then(Value::as_str) != Some("done")
        || manifest.get("pr_number").and_then(Value::as_u64) != Some(pull_request.number)
    {
        return Err("reconciliation-postcondition-failed".to_owned());
    }
    Ok(())
}

#[rustfmt::skip]
fn has_overlay(layer: &BTreeMap<String, String>) -> bool {
    let nonempty = |key: &str| layer.get(key).is_some_and(|value| !value.trim().is_empty());
    ["BAIL_REASON", "IMPLEMENT_BAIL_REASON", "BAIL_FAILURE_DETAIL_LOG", "FAILED_RUN_ID", "STALL_STEP"].iter().any(|key| nonempty(key))
        || ["BAIL_NEEDS_USER_INPUT", "STALL_TRACKING"].iter().any(|key| layer.get(*key).is_some_and(|value| truthy(value)))
        || layer.get("PHASE").map(String::as_str) == Some("stalled")
        || layer.get("EXIT_CODE").is_some_and(|value| !value.is_empty() && value != "0")
}

#[rustfmt::skip]
fn valid_key(key: &str) -> bool {
    let mut bytes = key.bytes();
    bytes.next().is_some_and(|byte| byte.is_ascii_alphabetic() || byte == b'_')
        && bytes.all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
}

#[rustfmt::skip]
fn truthy(value: &str) -> bool {
    matches!(value.trim().to_ascii_lowercase().as_str(), "1" | "true" | "yes" | "on")
}

fn failed(error: &str) -> ExitCode {
    let error = redact_outbound(error).replace(['\r', '\n'], " ");
    let error = if error.contains("[content truncated") {
        "redacted".to_owned()
    } else {
        error.chars().take(200).collect()
    };
    println!("RECONCILE_STATUS=failed");
    println!("ERROR={error}");
    ExitCode::from(1)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        github_service::with_test_github_service,
        implement_child_seam::{clear_hooks, install_larch},
    };
    use larch_adapters::github::OctocrabGitHubService;
    use larch_core::{ProcessOutput, ProcessStatus};
    use larch_test_support::{IssueServiceExchange, IssueServiceStub};
    use serde_json::json;
    use std::sync::Arc;
    use tempfile::TempDir;

    fn output(code: i32, stdout: &str) -> ProcessOutput {
        ProcessOutput::new(
            ProcessStatus::new(code == 0, Some(code)),
            stdout.as_bytes().to_vec(),
            Vec::new(),
            false,
            false,
        )
    }

    fn service(
        responses: impl IntoIterator<Item = String>,
    ) -> (
        Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync>,
        IssueServiceStub,
    ) {
        let exchanges = responses
            .into_iter()
            .map(|body| IssueServiceExchange::any_json(200, body.into_bytes()).expect("response"))
            .collect::<Vec<_>>();
        let server = IssueServiceStub::start(exchanges).expect("stub");
        let base = server.base_url().to_owned();
        let factory: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        (factory, server)
    }

    #[rustfmt::skip]
    fn seed_recovery_layers(root: &Path) {
        for name in ["ship-pr-state.sh", "finalize-state.sh"] {
            fs::write(root.join(name), "KEEP=value\nBAIL_REASON=stop\n").expect("state layer");
        }
        fs::write(root.join("session-env.sh"), "KEEP=value\nLARCH_RUN_ID=run-a\nREPO=owner/repo\nSTALL_TRACKING=true\n").expect("session layer");
    }

    #[test]
    #[rustfmt::skip]
    fn terminal_layer_clears_every_bail_overlay_and_preserves_unknown_keys() {
        let root = TempDir::new().expect("tmpdir");
        fs::write(root.path().join("ship-pr-state.sh"), "KEEP=value\nPHASE=stalled\nSTALL_TRACKING=true\nBAIL_REASON=stop\n").expect("state");
        let updates = BTreeMap::from([("PHASE".to_owned(), "done".to_owned())]);
        write_terminal_layer(root.path(), "ship-pr-state.sh", &updates, &[])
            .expect("reconciled layer");
        let layer = read_layer(root.path(), "ship-pr-state.sh", true).expect("layer");
        assert_eq!(layer.get("KEEP").map(String::as_str), Some("value"));
        assert_eq!(layer.get("PHASE").map(String::as_str), Some("done"));
        assert!(!has_overlay(&layer));
    }

    #[test]
    #[rustfmt::skip]
    fn mismatched_run_identity_fails_before_any_reconciliation() {
        let first = BTreeMap::from([("RUN_ID".to_owned(), "run-a".to_owned())]);
        let second = BTreeMap::from([("LARCH_RUN_ID".to_owned(), "run-b".to_owned())]);
        assert_eq!(validate_run_identity("run-a", [&first, &second]), Err("run-id-mismatch".to_owned()));
    }

    #[test]
    #[rustfmt::skip]
    fn reconciliation_converges_and_surfaces_manifest_failure() {
        let root = TempDir::new().expect("tmpdir");
        let pull_request = MergedPullRequest {
            number: 12,
            url: "https://github.com/owner/repo/pull/12".to_owned(),
        };
        seed_recovery_layers(root.path());
        let failed = persist_reconciliation(root.path(), "run-a", "owner/repo", &pull_request,
            |_tmpdir, _run_id, _number| Err("manifest-update-failed".to_owned()));
        assert_eq!(failed, Err("manifest-update-failed".to_owned()));

        let manifest = manifest_path(root.path(), "run-a");
        fs::create_dir_all(manifest.parent().expect("manifest parent")).expect("manifest tree");
        persist_reconciliation(root.path(), "run-a", "owner/repo", &pull_request, |_, _, number| {
            fs::write(&manifest, format!("{{\"status\":\"done\",\"pr_number\":{number}}}\n"))
                .map_err(|error| error.to_string())
        })
        .expect("reconciled");
        for name in ["ship-pr-state.sh", "finalize-state.sh", "session-env.sh"] {
            let layer = read_layer(root.path(), name, true).expect("terminal layer");
            assert_eq!(layer.get("KEEP").map(String::as_str), Some("value"));
            assert!(!has_overlay(&layer));
        }
    }

    #[test]
    fn parser_and_confined_layers_reject_ambiguous_inputs() {
        assert!(parse(&[]).is_err());
        assert!(parse(&["--help".into()]).is_err());
        assert_eq!(
            parse(&[
                "--implement-tmpdir".into(),
                "/tmp/claude-implement-test".into(),
                "--pr".into(),
                "0".into(),
            ])
            .expect_err("zero PR"),
            "invalid-pr"
        );
        let parsed = parse(&[
            "--implement-tmpdir".into(),
            "/tmp/claude-implement-test".into(),
            "--pr".into(),
            "12".into(),
            "--repo".into(),
            "owner/repo".into(),
        ])
        .expect("request");
        assert_eq!(parsed.number, 12);
        assert_eq!(parsed.repo.as_deref(), Some("owner/repo"));

        let root = TempDir::new().expect("tmpdir");
        assert!(
            read_layer(root.path(), "optional.env", false)
                .expect("optional")
                .is_empty()
        );
        fs::write(root.path().join("bad.env"), "KEY=value\r\n").expect("bad layer");
        assert_eq!(
            read_layer(root.path(), "bad.env", true),
            Err("bad.env-invalid".to_owned())
        );
        let manifest = manifest_path(root.path(), "run-a");
        fs::create_dir_all(manifest.parent().expect("parent")).expect("manifest tree");
        fs::write(&manifest, "{\"run_id\":\"run-b\"}\n").expect("manifest");
        assert_eq!(
            validate_manifest_identity(root.path(), "run-a"),
            Err("manifest-run-mismatch".to_owned())
        );
        assert!(valid_key("VALID_1") && !valid_key("1INVALID"));
        assert!(truthy("on") && !truthy("off"));
    }

    #[test]
    #[rustfmt::skip]
    fn full_reconciliation_proves_two_typed_merge_reads_and_manifest_postcondition() {
        let root = TempDir::new().expect("tmpdir");
        seed_recovery_layers(root.path());
        let manifest = manifest_path(root.path(), "run-a");
        fs::create_dir_all(manifest.parent().expect("parent")).expect("manifest tree");
        fs::write(&manifest, "{\"run_id\":\"run-a\"}\n").expect("manifest");
        let typed = json!({
            "number": 12, "state": "closed", "title": "Ship", "body": "Body",
            "head": { "ref": "feature", "label": "owner:feature" }, "base": { "ref": "main" },
            "draft": false, "merged": true,
            "merge_commit_sha": "1111111111111111111111111111111111111111",
        }).to_string();
        let audit = json!({
            "number": 12, "title": "Ship", "body": "Body", "base": { "ref": "main" },
            "merged_at": "2026-08-21T00:00:00Z",
        }).to_string();
        let (factory, server) = service([typed, audit]);
        let written_manifest = manifest.clone();
        install_larch(move |arguments, _environment| {
            assert!(arguments.iter().any(|value| value == "manifest"));
            fs::write(&written_manifest, "{\"run_id\":\"run-a\",\"status\":\"done\",\"pr_number\":12}\n")
                .expect("manifest update");
            Ok(output(0, ""))
        });
        let request = Request { tmpdir: root.path().to_path_buf(), number: 12, repo: None };
        with_test_github_service(factory, || reconcile(&request)).expect("reconciled");
        verify(
            root.path(), "run-a", "owner/repo",
            &MergedPullRequest { number: 12, url: "https://github.com/owner/repo/pull/12".to_owned() },
        ).expect("postcondition");
        server.join().expect("stub completed");
        clear_hooks();
    }
}
