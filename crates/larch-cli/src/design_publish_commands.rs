//! The `design publish` Step 5c orchestrator (#8591).
//!
//! Ported from `python/larch/design/design_publish.py`'s `publish_core`. The
//! phase order, refusal text, `KEY=value` rows, result-env checkpoints, and
//! exit codes 0/1/3/4/5 are preserved. Pure gates live in
//! `larch_core::design::publish`; sibling verbs run behind
//! [`SiblingRunner`](crate::clarify_orchestrator::SiblingRunner) so the phase
//! machine stays provable offline. The plan receipt is written through the
//! typed [`IssueMutationOwner`] rather than `gh api` (#7672).

use std::collections::{BTreeSet, HashSet};
use std::ffi::OsString;
use std::fmt::Write as _;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::time::Duration;

use larch_adapters::GixRepository;
use larch_adapters::github::{IssueMutationOwner, OctocrabGitHubService};
use larch_core::{
    AssessmentKind, BlockerSnapshotRow, ChildEnvironment, DESIGN_RAW_RATING_BASENAME,
    DIFFICULTY_RECORD_BASENAME, DifficultyRating, GitHubIssueState, GitHubRepositoryRef,
    IssueMutationField, IssueMutationLease, IssueMutationRequest, IssueMutationSnapshot,
    PLAN_MARKER, PUBLISH_RESULT_ENV_ALLOW, PlanReceipt, ProcessCancellation, ReviewProvenance,
    blocked_review_reason, bounded_diagram_warning_body, check_guideline_assessment_completeness,
    check_invariant_assessment_completeness, count_missing_script_defects, has_designed_prefix,
    hash_blocker_rows, hash_owner_rows, hash_plan_block, is_publish_attempt_id, is_repo_slug,
    parse_named_block, parse_native_blocker_refs, parse_owner_block, parse_receipt,
    persisted_note_publishable, redact_secrets_only, review_provenance, rewrite_plan_difficulty,
    sanitizer_reason_token, splice_plan_provenance, upsert_receipt, validate_plan_contract,
    write_bounded_diagram_failure_log,
};

use crate::blocker_commands::resolve_repo_for;
use crate::clarify_orchestrator::{
    LiveRunner, SiblingRunner, kv_last, plan_named_block_args,
    publish_artifact_ok as nonempty_file, resolve_publish_difficulty_rating, write_result_env,
};
use crate::design_step0_commands::{exit_from_i32, stage_terminal_state_bridge};
use crate::design_step1_commands::consumer_repo_root;
use crate::execution_issue_commands::read_lossy;
use crate::github_repository_resolution::repository_ref;
use crate::github_service::{ServiceFailure, with_github_service};
use crate::implement_bootstrap_continuation::resolve_revision_sha;
use crate::issue_mutation_support::authorization_request;
use crate::python_verb::plugin_root_directory;
use crate::run_log_entry_commands::append_execution_issue;

/// Result-env basename `/design` Step 5c publishes its wire state to.
const PUBLISH_RESULT_FILE: &str = ".design-publish-result.env";
/// Byte cap on a captured phase stderr tail.
const TAIL_BYTE_CAP: usize = 16384;
/// `PUBLISH_RC_SOURCE` value the in-process return path carries.
const RC_SOURCE_RETURNED: &str = "returned";
/// Bounded rename-stderr sidecar name.
const RENAME_STDERR_FILE: &str = "design-publish-rename.stderr.log";
/// Bounded log-publish stderr sidecar name.
const LOG_STDERR_FILE: &str = "design-publish-log.stderr.log";
/// Environment key carrying an orchestrator-supplied publish attempt id.
const ATTEMPT_ID_KEY: &str = "LARCH_DESIGN_PUBLISH_ATTEMPT_ID";

/// Exit code for a publish refusal that leaves the issue untouched.
const RC_REFUSED: i32 = 4;
/// Exit code for a hard publish failure.
const RC_FAILED: i32 = 5;
/// Exit code for a result-env write failure after the rows were emitted.
const RC_RESULT_ENV: i32 = 3;

/// The parsed `design publish` argv.
struct PublishArgs {
    design_tmpdir: String,
    issue: String,
    session_id: String,
    claude_pid: String,
    repo: String,
    skip_validate: bool,
}

/// Ordered `KEY=value` publish rows, replaced in place like the Python list.
struct Rows(Vec<(String, String)>);

impl Rows {
    fn set(&mut self, key: &str, value: &str) {
        if let Some(row) = self.0.iter_mut().rev().find(|row| row.0 == key) {
            value.clone_into(&mut row.1);
            return;
        }
        self.0.push((key.to_owned(), value.to_owned()));
    }

    fn push(&mut self, key: &str, value: &str) {
        self.0.push((key.to_owned(), value.to_owned()));
    }

    fn get(&self, key: &str) -> &str {
        self.0
            .iter()
            .rev()
            .find(|row| row.0 == key)
            .map_or("", |row| row.1.as_str())
    }

    fn emit(&self) {
        for (key, value) in &self.0 {
            println!("{key}={value}");
        }
    }
}

/// Atomically write the allowlisted publish rows to the result env.
fn write_publish_result_env(path: &Path, rows: &Rows) -> Result<(), String> {
    let borrowed: Vec<(&str, &str)> = rows
        .0
        .iter()
        .map(|(key, value)| (key.as_str(), value.as_str()))
        .collect();
    write_result_env(path, &borrowed, &PUBLISH_RESULT_ENV_ALLOW)
}

/// Record the phase and checkpoint the result env, or name the failed phase.
fn checkpoint(path: &Path, rows: &mut Rows, phase: &str) -> Result<(), String> {
    rows.set("LATEST_PHASE", phase);
    write_publish_result_env(path, rows).map_err(|_error| {
        format!(
            "publish result checkpoint failed at {phase}: {}",
            path.display()
        )
    })
}

/// Write the last [`TAIL_BYTE_CAP`] bytes of a phase's stderr to a sidecar.
fn write_bounded_phase_stderr(design_tmpdir: &Path, filename: &str, text: &str) {
    let bytes = text.as_bytes();
    let tail = &bytes[bytes.len().saturating_sub(TAIL_BYTE_CAP)..];
    let path = design_tmpdir.join(filename);
    if path.is_symlink() {
        return;
    }
    let _ = fs::write(&path, String::from_utf8_lossy(tail).as_bytes());
}

// ---------------------------------------------------------------------------
// argv
// ---------------------------------------------------------------------------

/// Parse the publish argv; any malformed line is exit 5, `--help` is exit 0.
fn parse_publish_args(argv: &[OsString]) -> Result<PublishArgs, i32> {
    let tokens: Vec<String> = argv
        .iter()
        .map(|token| token.to_string_lossy().into_owned())
        .collect();
    let mut parsed = PublishArgs {
        design_tmpdir: String::new(),
        issue: String::new(),
        session_id: String::new(),
        claude_pid: String::new(),
        repo: String::new(),
        skip_validate: false,
    };
    let mut session_id_provided = false;
    let mut index = 0;
    while index < tokens.len() {
        let token = tokens[index].as_str();
        if token == "--skip-validate" {
            parsed.skip_validate = true;
            index += 1;
            continue;
        }
        if token == "-h" || token == "--help" {
            return Err(0);
        }
        let slot = match token {
            "--design-tmpdir" => &mut parsed.design_tmpdir,
            "--issue" => &mut parsed.issue,
            "--session-id" => {
                session_id_provided = true;
                &mut parsed.session_id
            }
            "--claude-pid" => &mut parsed.claude_pid,
            "--repo" => &mut parsed.repo,
            _ => return Err(RC_FAILED),
        };
        let Some(value) = tokens.get(index + 1) else {
            return Err(RC_FAILED);
        };
        slot.clone_from(value);
        index += 2;
    }
    if parsed.design_tmpdir.is_empty()
        || parsed.issue.is_empty()
        || !session_id_provided
        || parsed.claude_pid.is_empty()
        || !positive_decimal(&parsed.issue)
        || !positive_decimal(&parsed.claude_pid)
        || (!parsed.repo.is_empty() && !is_repo_slug(&parsed.repo))
    {
        return Err(RC_FAILED);
    }
    Ok(parsed)
}

/// Match the retired `str.isdigit()` plus non-`"0"` spelling.
fn positive_decimal(value: &str) -> bool {
    !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()) && value != "0"
}

/// Return 8 random bytes as lowercase hex, matching `os.urandom(8).hex()`.
fn random_hex() -> String {
    use std::io::Read as _;
    let mut buffer = [0_u8; 8];
    if fs::File::open("/dev/urandom")
        .and_then(|mut file| file.read_exact(&mut buffer))
        .is_err()
    {
        // A publish attempt id only has to be distinct within one session, so a
        // clock-derived suffix keeps the sidecar usable when urandom is absent.
        buffer = u64::try_from(
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|elapsed| elapsed.as_nanos())
                .unwrap_or_default()
                % u128::from(u64::MAX),
        )
        .unwrap_or_default()
        .to_le_bytes();
    }
    let mut hex = String::with_capacity(buffer.len() * 2);
    for byte in buffer {
        let _ = write!(hex, "{byte:02x}");
    }
    hex
}

/// Resolve the publish attempt id from the environment, or mint one.
fn resolve_attempt_id() -> Option<String> {
    let declared = std::env::var(ATTEMPT_ID_KEY).unwrap_or_default();
    let attempt = if declared.is_empty() {
        format!("direct-{}-{}", std::process::id(), random_hex())
    } else {
        declared
    };
    is_publish_attempt_id(&attempt).then_some(attempt)
}

// ---------------------------------------------------------------------------
// refusal emitters
// ---------------------------------------------------------------------------

/// Emit a refusal's rows and result env, then return the refusal exit code.
fn refuse(result_env: &Path, rows: &Rows) -> i32 {
    rows.emit();
    let _ = write_publish_result_env(result_env, rows);
    RC_REFUSED
}

/// Emit the review-provenance or plan-size refusal, matching Python's text.
fn emit_publish_refusal(reason: &str, rows: &mut Rows, result_env: &Path) -> i32 {
    if let Some(size_refusal) = reason.strip_prefix("plan-size:") {
        println!(
            "**⚠ 5c: publish refused: plan-size guardrail returned {size_refusal}; \
             decompose, override, or retry /design after repair**"
        );
        rows.set("PUBLISH_REFUSE_REASON", size_refusal);
    } else {
        let blocked = reason.strip_prefix("review-provenance:").unwrap_or(reason);
        println!(
            "**⚠ 5c: publish refused: review provenance indicates {blocked}; \
             plan review did not complete; re-run /design**"
        );
        rows.set("PUBLISH_REFUSE_REASON", reason);
    }
    rows.set("VALIDATE_STATUS", "defects-found");
    rows.set("VALIDATE_DEFECT_COUNT", "1");
    refuse(result_env, rows)
}

/// One Gate C assessment refusal: its chat line and its `ARCH_*` row block.
struct AssessmentRefusal<'refusal> {
    message: &'refusal str,
    prefix: &'refusal str,
    status: &'refusal str,
    artifact: &'refusal str,
    present: bool,
    reason: &'refusal str,
}

/// Emit one Gate C assessment refusal with its shared row block.
fn emit_assessment_refusal(
    refusal: &AssessmentRefusal<'_>,
    rows: &mut Rows,
    result_env: &Path,
) -> i32 {
    println!("{}", refusal.message);
    let prefix = refusal.prefix;
    rows.set("VALIDATE_STATUS", "not-run");
    rows.set("VALIDATE_DEFECT_COUNT", "0");
    rows.set("VALIDATE_LOG_FILE", "");
    rows.set(&format!("{prefix}_REQUIRED"), "true");
    rows.set(
        &format!("{prefix}_PRESENT"),
        if refusal.present { "true" } else { "false" },
    );
    rows.set(&format!("{prefix}_STATUS"), refusal.status);
    rows.set(&format!("{prefix}_ARTIFACT"), refusal.artifact);
    rows.set("PUBLISH_REFUSE_REASON", refusal.reason);
    refuse(result_env, rows)
}

/// Run the Gate C assessment ladder and the executable-plan contract gate.
fn refuse_pre_write_gates(
    design_tmpdir: &Path,
    repo_root: &Path,
    plan_text: &str,
    rows: &mut Rows,
    result_env: &Path,
) -> Option<i32> {
    let invariants = check_invariant_assessment_completeness(design_tmpdir, repo_root, "approved");
    if invariants.required && !invariants.present {
        return Some(emit_assessment_refusal(
            &AssessmentRefusal {
                message: "**⚠ 5c: publish refused: missing architectural-invariant-assessment.md; \
                          return to Gate C to persist the architectural-invariant assessment \
                          before publish.**",
                prefix: "ARCH_INVARIANT_ASSESSMENT",
                status: "missing",
                artifact: invariants.artifact,
                present: false,
                reason: "missing-invariant-assessment",
            },
            rows,
            result_env,
        ));
    }
    if invariants.required
        && !persisted_note_publishable(
            &design_tmpdir.join(invariants.artifact),
            AssessmentKind::Invariants,
        )
    {
        return Some(emit_assessment_refusal(
            &AssessmentRefusal {
                message: "**⚠ 5c: publish refused: architectural-invariant-assessment.md records \
                          a violation; return to Gate C to resolve the invariant violation before \
                          publish.**",
                prefix: "ARCH_INVARIANT_ASSESSMENT",
                status: "violation",
                artifact: invariants.artifact,
                present: true,
                reason: "invariant-violation",
            },
            rows,
            result_env,
        ));
    }

    let guidelines = check_guideline_assessment_completeness(design_tmpdir, repo_root, "approved");
    if guidelines.required && !guidelines.present {
        return Some(emit_assessment_refusal(
            &AssessmentRefusal {
                message: "**⚠ 5c: publish refused: missing architectural-guideline-assessment.md; \
                          return to Gate C to persist the architectural-guideline assessment \
                          before publish.**",
                prefix: "ARCH_GUIDE_ASSESSMENT",
                status: "missing",
                artifact: guidelines.artifact,
                present: false,
                reason: "missing-guideline-assessment",
            },
            rows,
            result_env,
        ));
    }
    if guidelines.required
        && !persisted_note_publishable(
            &design_tmpdir.join(guidelines.artifact),
            AssessmentKind::Guidelines,
        )
    {
        return Some(emit_assessment_refusal(
            &AssessmentRefusal {
                message: "**⚠ 5c: publish refused: architectural-guideline-assessment.md records \
                          a guideline deviation without a documented exception; return to Gate C \
                          to fix the plan or record an exception before publish.**",
                prefix: "ARCH_GUIDE_ASSESSMENT",
                status: "deviation",
                artifact: guidelines.artifact,
                present: true,
                reason: "invalid-guideline-deviation",
            },
            rows,
            result_env,
        ));
    }

    let contract = validate_plan_contract(plan_text, repo_root, &tracked_paths(repo_root));
    if !contract.ok() {
        let tokens = contract.defects.join(",");
        println!(
            "**⚠ 5c: publish refused: executable-plan contract defects `{tokens}`; \
             repair plan.txt / composed-plan.md before publish**"
        );
        rows.set("PUBLISH_REFUSE_REASON", &format!("plan-contract:{tokens}"));
        rows.set("VALIDATE_STATUS", "defects-found");
        rows.set("VALIDATE_DEFECT_COUNT", &contract.defects.len().to_string());
        return Some(refuse(result_env, rows));
    }
    None
}

/// Load the tracked-path set the plan-contract M2 checks resolve against.
///
/// An empty set makes every `### UPDATED:` path look missing, so publish reads
/// the live index through `gix` exactly as Preflight does (#7671).
fn tracked_paths(repo_root: &Path) -> HashSet<String> {
    let mut tracked = HashSet::new();
    if let Ok(repository) = GixRepository::open(repo_root)
        && let Ok(paths) = repository.tracked_paths()
    {
        for path in paths {
            tracked.insert(String::from_utf8_lossy(path.as_bytes()).into_owned());
        }
    }
    tracked
}

// ---------------------------------------------------------------------------
// Step 5b.5 diagram sanitize gate
// ---------------------------------------------------------------------------

/// Mark the Step 5b.5 sentinel as completed.
fn touch_step5b5_sentinel(design_tmpdir: &Path) -> std::io::Result<()> {
    let completed = design_tmpdir.join(".completed");
    fs::create_dir_all(&completed)?;
    fs::write(completed.join("step-5b.5"), b"")
}

/// Record a diagram-sanitizer failure in the bounded logs and warning ledger.
fn write_diagram_sanitizer_failure(design_tmpdir: &Path, reason: &str, exit_code: &str) {
    let safe: String = reason
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | ':' | '-') {
                character
            } else {
                '-'
            }
        })
        .collect();
    let safe = safe.trim_matches('-');
    let safe = if safe.is_empty() { "unknown" } else { safe };
    let failure_log = design_tmpdir.join("architecture-diagram-sanitizer.failure.log");
    let _ = fs::write(
        &failure_log,
        format!("reason={safe}\nexit-code={exit_code}\nsite=design Step 5b.5\n"),
    );
    let _ = write_bounded_diagram_failure_log(
        design_tmpdir,
        "design Step 5b.5",
        safe,
        exit_code,
        Some(&failure_log),
    );
    let _ = append_execution_issue(
        &design_tmpdir.join("execution-issues.md"),
        "Warnings",
        &bounded_diagram_warning_body(safe, exit_code),
    );
}

/// Drop the candidate, mark the diagram skipped, and complete Step 5b.5.
fn skip_diagram_candidate(design_tmpdir: &Path, reason: &str, exit_code: &str) -> bool {
    let _ = fs::remove_file(design_tmpdir.join("architecture-diagram.md"));
    let _ = fs::remove_file(design_tmpdir.join("architecture-diagram.candidate.md"));
    if fs::write(design_tmpdir.join("architecture-diagram.skipped"), b"").is_err() {
        return false;
    }
    write_diagram_sanitizer_failure(design_tmpdir, reason, exit_code);
    touch_step5b5_sentinel(design_tmpdir).is_ok()
}

/// Complete the Step 5b.5 diagram sanitize gate before publishing.
fn sanitize_diagram_candidate(runner: &dyn SiblingRunner, design_tmpdir: &Path) -> bool {
    if design_tmpdir.join(".completed").join("step-5b.5").is_file() {
        return true;
    }
    let candidate = design_tmpdir.join("architecture-diagram.candidate.md");
    if !candidate.is_file() || candidate.is_symlink() {
        return skip_diagram_candidate(design_tmpdir, "candidate-missing", "2");
    }
    let sanitizer = runner.run_python(&osargs(&[
        "mermaid",
        "sanitize",
        "--input",
        &candidate.display().to_string(),
        "--from-md",
        "--warnings-step",
        "5b.5",
    ]));
    let combined = format!("{}\n{}", sanitizer.stdout, sanitizer.stderr);
    if sanitizer.rc == 0 && kv_last(&combined, "STATUS") != "rejected" {
        for stale in [
            "architecture-diagram.skipped",
            "architecture-diagram-sanitizer.failure.log",
            "architecture-diagram-generation.failure.log",
        ] {
            let _ = fs::remove_file(design_tmpdir.join(stale));
        }
        if fs::rename(&candidate, design_tmpdir.join("architecture-diagram.md")).is_err() {
            return false;
        }
        return touch_step5b5_sentinel(design_tmpdir).is_ok();
    }
    skip_diagram_candidate(
        design_tmpdir,
        &format!("sanitizer-rejected:{}", sanitizer_reason_token(&combined)),
        &sanitizer.rc.to_string(),
    )
}

// ---------------------------------------------------------------------------
// plan receipt
// ---------------------------------------------------------------------------

/// The plan-receipt write, behind a seam.
///
/// The write is the phase machine's only GitHub mutation, so keeping it behind
/// one method lets the ported phase order stay provable without a network.
pub trait ReceiptWriter {
    /// Write and read-verify the receipt for one published plan.
    ///
    /// # Errors
    /// Returns the reason token publish reports to the operator.
    fn persist(&self, repo: &str, issue: u64, repo_root: &Path) -> Result<(), String>;
}

/// The live writer: the typed issue-mutation owner, never `gh api` (#7672).
struct LiveReceiptWriter;

impl ReceiptWriter for LiveReceiptWriter {
    fn persist(&self, repo: &str, issue: u64, repo_root: &Path) -> Result<(), String> {
        persist_published_plan_receipt(repo, issue, repo_root)
    }
}

/// Whether offline mutation deny is set, as the Python receipt seam read it.
fn mutation_denied() -> bool {
    matches!(
        std::env::var("LARCH_ISSUE_MUTATION_DENY")
            .unwrap_or_default()
            .trim()
            .to_lowercase()
            .as_str(),
        "1" | "true" | "yes" | "on"
    )
}

/// The blocker freshness rows one body's receipt hashes.
///
/// Both the native `blocked_by` edges and the body's documented blocker refs
/// contribute a `(number, state, updated_at)` row, matching the retired Python
/// snapshot loader; an unreadable edge fails the receipt closed.
async fn receipt_blocker_rows(
    service: &OctocrabGitHubService,
    owner: &IssueMutationOwner<'_>,
    repository: &GitHubRepositoryRef,
    issue: u64,
    body: &str,
    cancellation: &dyn ProcessCancellation,
) -> Result<Vec<BlockerSnapshotRow>, String> {
    let native = service
        .list_blocked_by(cancellation, repository.owner(), repository.name(), issue)
        .await
        .map_err(|_error| "blocker-read-unavailable".to_owned())?;
    let mut numbers: BTreeSet<u64> = native
        .iter()
        .map(larch_adapters::github::DependencyRef::issue_number)
        .collect();
    numbers.extend(parse_native_blocker_refs(body));
    let mut rows = Vec::new();
    for number in numbers {
        let snapshot = owner
            .read_snapshot(repository, number, cancellation)
            .await
            .map_err(|_error| "blocker-read-unavailable".to_owned())?;
        rows.push(BlockerSnapshotRow {
            number,
            state: state_token(snapshot.state).to_owned(),
            updated_at: snapshot.updated_at,
        });
    }
    Ok(rows)
}

const fn state_token(state: GitHubIssueState) -> &'static str {
    match state {
        GitHubIssueState::Open => "open",
        _ => "closed",
    }
}

/// Bind a plan named-block write to the active run id, matching
/// `issue_wire_commands::named_block_lease` (`RUN_ID` / `LARCH_RUN_ID` / `SESSION_ID`).
fn plan_named_block_lease() -> Option<IssueMutationLease> {
    for key in ["RUN_ID", "LARCH_RUN_ID", "SESSION_ID"] {
        if let Ok(value) = std::env::var(key) {
            let run_id = value.trim();
            if !run_id.is_empty() {
                return Some(IssueMutationLease {
                    run_id: run_id.to_owned(),
                    marker: PLAN_MARKER.to_owned(),
                });
            }
        }
    }
    None
}

/// True when a named-block apply failure is the protected-mutation class Python
/// caught before falling back to a whole-body write (`ProtectedIssueMutation`).
fn is_protected_named_block_refusal(reason: &str) -> bool {
    matches!(
        reason,
        "missing-lease"
            | "protected-body"
            | "lease-run-mismatch"
            | "foreign-lease-body-change"
            | "foreign-marker-or-body-change"
            | "invalid-lease"
            | "invalid-named-block-request"
    )
}

/// Build the receipt mutation request for one snapshot and field.
fn receipt_mutation(
    repository: &GitHubRepositoryRef,
    snapshot: &IssueMutationSnapshot,
    body: String,
    named_block: bool,
) -> IssueMutationRequest {
    IssueMutationRequest {
        repository: repository.clone(),
        issue: snapshot.issue,
        expected_updated_at: snapshot.updated_at.clone(),
        expected_state: snapshot.state,
        fields: BTreeSet::from([if named_block {
            IssueMutationField::NamedBlock
        } else {
            IssueMutationField::Body
        }]),
        title: None,
        body: Some(body),
        labels: None,
        marker: named_block.then(|| PLAN_MARKER.to_owned()),
        // Named-block receipt refresh needs the plan lease so a still-
        // `[DESIGNING]` issue can update the adjacent receipt marker.
        lease: named_block.then(plan_named_block_lease).flatten(),
    }
}

/// Write and read-verify the plan receipt after a successful plan write.
///
/// Offline unit runs set `LARCH_ISSUE_MUTATION_DENY` and skip the live write,
/// exactly as the retired Python receipt seam did.
fn persist_published_plan_receipt(repo: &str, issue: u64, repo_root: &Path) -> Result<(), String> {
    if mutation_denied() {
        return Ok(());
    }
    let base_sha = resolve_revision_sha(repo_root, "HEAD")?;
    let slug = resolve_repo_for((!repo.is_empty()).then_some(repo))
        .ok_or_else(|| "repository slug required to persist plan receipt".to_owned())?;
    let repository = repository_ref(&slug).map_err(|()| "invalid-repository".to_owned())?;
    let outcome = with_github_service(async |service, cancellation| {
        let owner = IssueMutationOwner::new(service);
        let snapshot = owner
            .read_snapshot(&repository, issue, cancellation)
            .await
            .map_err(|error| error.reason().to_owned())?;
        let Ok(Some(plan_inner)) = parse_named_block(&snapshot.body, PLAN_MARKER) else {
            return Err("plan-block-missing-for-receipt".to_owned());
        };
        let blockers = receipt_blocker_rows(
            service,
            &owner,
            &repository,
            issue,
            &snapshot.body,
            cancellation,
        )
        .await?;
        let receipt = PlanReceipt {
            plan_sha256: hash_plan_block(&plan_inner),
            base_sha: base_sha.clone(),
            blockers_sha256: hash_blocker_rows(&blockers),
            owners_sha256: hash_owner_rows(&parse_owner_block(&snapshot.body).raw_rows),
        };
        let updated = upsert_receipt(&snapshot.body, &receipt)
            .map_err(|defect| defect.reason().to_owned())?;
        if updated == snapshot.body {
            return if parse_receipt(&snapshot.body).as_ref() == Some(&receipt) {
                Ok(())
            } else {
                Err("plan-receipt-readback-mismatch".to_owned())
            };
        }
        // Prefer the plan named-block mutation so a `[DESIGNING]` issue can
        // refresh its adjacent receipt; fall back to the whole-body write the
        // retired owner used when the protected named-block path refuses.
        let authorization = authorization_request("", "", "", true);
        let mutation = match owner
            .apply(
                cancellation,
                &authorization,
                &receipt_mutation(&repository, &snapshot, updated.clone(), true),
            )
            .await
        {
            Ok(mutation) => mutation,
            // Match Python: only ProtectedIssueMutation falls back to body;
            // transient/stale/unreachable NamedBlock failures must not widen
            // into a whole-body overwrite.
            Err(error) => {
                let reason = error.reason();
                if !is_protected_named_block_refusal(reason) {
                    return Err(reason.to_owned());
                }
                let snapshot = owner
                    .read_snapshot(&repository, issue, cancellation)
                    .await
                    .map_err(|error| error.reason().to_owned())?;
                let updated = upsert_receipt(&snapshot.body, &receipt)
                    .map_err(|defect| defect.reason().to_owned())?;
                owner
                    .apply(
                        cancellation,
                        &authorization,
                        &receipt_mutation(&repository, &snapshot, updated, false),
                    )
                    .await
                    .map_err(|error| error.reason().to_owned())?
            }
        };
        if parse_receipt(&mutation.after.body).as_ref() == Some(&receipt) {
            Ok(())
        } else {
            Err("plan-receipt-readback-mismatch".to_owned())
        }
    });
    outcome.map_err(ServiceFailure::into_detail)
}

// ---------------------------------------------------------------------------
// failure staging and log publish
// ---------------------------------------------------------------------------

/// Append the optional publish state a terminal-stage command carries.
fn publish_failure_stage_args(design_tmpdir: &Path, rows: &Rows, detail_log: &Path) -> Vec<String> {
    let mut args = vec![
        "--design-tmpdir".to_owned(),
        design_tmpdir.display().to_string(),
        "--outcome".to_owned(),
        "failed-plan-write".to_owned(),
        "--step".to_owned(),
        "step5c".to_owned(),
        "--phase".to_owned(),
        "plan-write".to_owned(),
        "--site".to_owned(),
        "design-publish".to_owned(),
        "--trigger".to_owned(),
        "plan-write-failed".to_owned(),
        "--bail-reason".to_owned(),
        "plan-write-failed".to_owned(),
        "--exit-code".to_owned(),
        "1".to_owned(),
        "--source-script".to_owned(),
        "design-publish".to_owned(),
        "--summary-outcome".to_owned(),
        "failed-plan-write".to_owned(),
        "--failure-detail-log".to_owned(),
        detail_log.display().to_string(),
    ];
    for (flag, key) in [
        ("--publish-attempt-id", "PUBLISH_ATTEMPT_ID"),
        ("--publish-rc-source", "PUBLISH_RC_SOURCE"),
        ("--latest-phase", "LATEST_PHASE"),
        ("--plan-write-ok", "PLAN_WRITE_OK"),
        ("--publish-ok", "PUBLISH_OK"),
        ("--renamed", "RENAMED"),
        ("--log-publish-attempted", "LOG_PUBLISH_ATTEMPTED"),
        ("--log-publish-completed", "LOG_PUBLISH_COMPLETED"),
        ("--designed-admission-ready", "DESIGNED_ADMISSION_READY"),
        ("--pr-url", "PR_URL"),
        ("--recovery-branch", "RECOVERY_BRANCH"),
    ] {
        let value = rows.get(key);
        if !value.is_empty() {
            args.push(flag.to_owned());
            args.push(value.to_owned());
        }
    }
    args
}

/// Stage the terminal state before failure reporting and log publication.
fn stage_failed_plan_write(design_tmpdir: &Path, rows: &Rows) {
    let detail_log = design_tmpdir.join("design-plan-write.failure.log");
    if !detail_log.is_file() {
        let _ = fs::write(&detail_log, "named-block write failed\n");
    }
    let stdout_log = design_tmpdir.join("design-plan-write-stage.stdout.log");
    let stderr_log = design_tmpdir.join("design-plan-write-stage.stderr.log");
    let rc = stage_terminal_state_bridge(
        &stdout_log,
        &stderr_log,
        &publish_failure_stage_args(design_tmpdir, rows, &detail_log),
    );
    let staged = read_lossy(&stdout_log).contains("STAGED=true");
    if rc != 0 || !staged {
        let _ = append_execution_issue(
            &design_tmpdir.join("execution-issues.md"),
            "Warnings",
            "design Step 5c plan-write terminal-state staging failed; \
             failure report may be unavailable.",
        );
    }
}

/// The transcript-and-log-publish context the log-publish bridge carries.
struct LogPublishContext<'a> {
    design_tmpdir: &'a Path,
    session_id: &'a str,
    issue: &'a str,
    repo: &'a str,
}

/// Publish the design log, appending its result rows.
///
/// Returns the publish exit code when publish must stop, or `None` to continue.
/// Transcript capture stays inside the Rust-owned `design log-publish` verb
/// (#8592).
fn run_log_publish(
    runner: &dyn SiblingRunner,
    context: &LogPublishContext<'_>,
    rows: &mut Rows,
    result_env: &Path,
    outcome: &str,
    write_result_env_on_failure: bool,
) -> Option<i32> {
    let mut args = vec![
        "design".to_owned(),
        "log-publish".to_owned(),
        "--design-tmpdir".to_owned(),
        context.design_tmpdir.display().to_string(),
        "--run-id".to_owned(),
        context.session_id.to_owned(),
        "--issue".to_owned(),
        context.issue.to_owned(),
        "--outcome".to_owned(),
        outcome.to_owned(),
    ];
    if !context.repo.is_empty() {
        args.push("--repo".to_owned());
        args.push(context.repo.to_owned());
    }
    let publish = runner.run_larch(&args.iter().map(OsString::from).collect::<Vec<_>>());
    write_bounded_phase_stderr(context.design_tmpdir, LOG_STDERR_FILE, &publish.stderr);
    let publish_ok = kv_last(&publish.stdout, "PUBLISH_OK");
    rows.push(
        "PUBLISH_OK",
        if publish_ok == "true" {
            "true"
        } else {
            "false"
        },
    );
    for (key, value) in [
        ("PR_NUMBER", kv_last(&publish.stdout, "PR_NUMBER")),
        ("PR_URL", kv_last(&publish.stdout, "PR_URL")),
    ] {
        if !value.is_empty() {
            rows.push(key, &value);
        }
    }
    let recovery = kv_last(&publish.stdout, "RECOVERY_BRANCH");
    if !recovery.is_empty() {
        rows.push("RECOVERY_BRANCH", &recovery);
        rows.push("LOG_RECOVERY_BRANCH", &recovery);
    }
    for (key, value) in [
        ("REMOTE_KEY", kv_last(&publish.stdout, "REMOTE_KEY")),
        ("CACHE_DIR", kv_last(&publish.stdout, "CACHE_DIR")),
    ] {
        if !value.is_empty() {
            rows.push(key, &value);
        }
    }
    if publish.rc != 0 && recovery.is_empty() {
        rows.set("PUBLISH_OK", "false");
        if write_result_env_on_failure {
            rows.emit();
            if let Err(error) = checkpoint(result_env, rows, "log-publish-failed") {
                eprintln!("{error}");
            }
        }
        return Some(RC_FAILED);
    }
    let violations = kv_last(&publish.stdout, "SECRET_SCRUB_VIOLATIONS");
    if violations.parse::<u64>().is_ok_and(|value| value > 0) {
        println!(
            "**⚠ SECURITY: redact scrub-log-secrets redacted {violations} \
             secret-shaped value(s) from this /design run's logs before flush. \
             A credential was almost certainly exposed in the session; ROTATE it now \
             and check chat/PRs for the same value.**"
        );
    }
    if publish.rc == 0 && publish_ok != "true" {
        if !write_result_env_on_failure {
            return Some(0);
        }
        rows.emit();
        return Some(if write_publish_result_env(result_env, rows).is_ok() {
            0
        } else {
            RC_RESULT_ENV
        });
    }
    None
}

/// Stage, report, and finalize a failed plan write; returns its exit code.
fn finalize_failed_plan_write(
    runner: &dyn SiblingRunner,
    context: Option<&LogPublishContext<'_>>,
    design_tmpdir: &Path,
    rows: &mut Rows,
    result_env: &Path,
) -> i32 {
    stage_failed_plan_write(design_tmpdir, rows);
    if let Some(context) = context {
        let _ignored = run_log_publish(
            runner,
            context,
            rows,
            result_env,
            "failed-plan-write",
            false,
        );
    }
    rows.emit();
    if write_publish_result_env(result_env, rows).is_ok() {
        1
    } else {
        RC_RESULT_ENV
    }
}

// ---------------------------------------------------------------------------
// difficulty
// ---------------------------------------------------------------------------

/// Sync the difficulty label, persist the record, and write its run-log batch.
fn publish_difficulty(
    runner: &dyn SiblingRunner,
    design_tmpdir: &Path,
    issue: &str,
    repo_args: &[String],
    rating: &DifficultyRating,
) {
    let mut sync = vec![
        "difficulty".to_owned(),
        "sync-labels".to_owned(),
        "--issue".to_owned(),
        issue.to_owned(),
        "--tier".to_owned(),
        rating.adjusted_tier.clone(),
    ];
    sync.extend(repo_args.iter().cloned());
    let _ = runner.run_larch(&sync.iter().map(OsString::from).collect::<Vec<_>>());

    // `difficulty write-record` owns the record's merge and fallback rules, so
    // publish delegates instead of rebuilding the record map here.
    let record_path = design_tmpdir.join(DIFFICULTY_RECORD_BASENAME);
    let mut record = vec![
        "difficulty".to_owned(),
        "write-record".to_owned(),
        "--output".to_owned(),
        record_path.display().to_string(),
        "--rater".to_owned(),
        "design".to_owned(),
        "--rater-tool".to_owned(),
        "claude".to_owned(),
        "--rater-model".to_owned(),
        "unknown".to_owned(),
        "--design-tier".to_owned(),
        rating.adjusted_tier.clone(),
        "--fallback-tier".to_owned(),
        rating.adjusted_tier.clone(),
        "--fallback-rationale".to_owned(),
        "design plan metadata".to_owned(),
    ];
    let raw_rating = design_tmpdir.join(DESIGN_RAW_RATING_BASENAME);
    if raw_rating.is_file() && !raw_rating.is_symlink() {
        for flag in ["--raw-rating-file", "--design-raw-rating-file"] {
            record.push(flag.to_owned());
            record.push(raw_rating.display().to_string());
        }
    }
    if runner
        .run_larch(&record.iter().map(OsString::from).collect::<Vec<_>>())
        .rc
        != 0
        || !record_path.is_file()
    {
        return;
    }
    let run_id = std::env::var("RUN_ID").unwrap_or_default();
    let run_id = if run_id.is_empty() {
        read_lossy(&design_tmpdir.join("run-id.txt"))
            .trim()
            .to_owned()
    } else {
        run_id
    };
    if run_id.is_empty() {
        return;
    }
    let _ = runner.run_larch(&osargs(&[
        "run-log",
        "write",
        "--skill",
        "design",
        "--run-id",
        &run_id,
        "--batch",
        "difficulty-rating",
        "--input-file",
        &record_path.display().to_string(),
    ]));
}

// ---------------------------------------------------------------------------
// diagram upsert
// ---------------------------------------------------------------------------

/// Upsert the architecture diagram into the shared `larch:diagrams` comment.
///
/// Step 5c consumes post-approval artifacts written by Step 5b.5. It clears
/// Architecture content only when Step 5b.5 wrote an explicit skip marker; a
/// missing tmpdir file after the sentinel is warning-only and must not wipe a
/// valid issue diagram.
fn upsert_architecture_diagram(
    runner: &dyn SiblingRunner,
    design_tmpdir: &Path,
    issue: &str,
    repo_args: &[String],
    rows: &mut Rows,
) {
    let arch_file = design_tmpdir.join("architecture-diagram.md");
    let arch_skipped = design_tmpdir.join("architecture-diagram.skipped");
    let mut args = vec![
        "diagrams".to_owned(),
        "upsert".to_owned(),
        "--issue".to_owned(),
        issue.to_owned(),
    ];
    args.extend(repo_args.iter().cloned());
    if nonempty_file(&arch_file) {
        args.push("--architecture-file".to_owned());
        args.push(arch_file.display().to_string());
    } else if arch_skipped.is_file() {
        args.push("--clear-architecture".to_owned());
    } else {
        let _ = append_execution_issue(
            &design_tmpdir.join("execution-issues.md"),
            "Warnings",
            &bounded_diagram_warning_body("diagram-artifact-missing-after-step5b5", "0"),
        );
        return;
    }
    let upsert = runner.run_python(&args.iter().map(OsString::from).collect::<Vec<_>>());
    let stderr_file = design_tmpdir.join("diagrams-architecture-upsert.stderr");
    let _ = fs::write(&stderr_file, &upsert.stderr);
    let _ = fs::write(
        design_tmpdir.join("diagrams-architecture-upsert.stdout"),
        &upsert.stdout,
    );
    let status = kv_last(&upsert.stdout, "UPSERT_STATUS");
    match status.as_str() {
        "" => {}
        reported => rows.push("UPSERT_STATUS", reported),
    }
    let source = kv_last(&upsert.stdout, "ARCHITECTURE_SOURCE");
    if !source.is_empty() {
        rows.push("ARCHITECTURE_SOURCE", &source);
    }
    if status == "failed" || upsert.rc != 0 {
        let _ = runner.run_larch(&osargs(&[
            "run-log",
            "append-failure",
            "--log",
            &design_tmpdir
                .join("execution-issues.md")
                .display()
                .to_string(),
            "--site",
            "design Step 5c.5",
            "--tool",
            "python/cli.py diagrams upsert architecture",
            "--exit-code",
            &upsert.rc.to_string(),
            "--category",
            "Warnings",
            "--output-file",
            &stderr_file.display().to_string(),
            "--redact",
        ]));
    }
}

/// Build an `OsString` argv from string slices.
fn osargs(parts: &[&str]) -> Vec<OsString> {
    parts.iter().map(OsString::from).collect()
}

// ---------------------------------------------------------------------------
// phase machine
// ---------------------------------------------------------------------------

/// Every path the publish phase machine needs after argv validation.
struct PublishPaths {
    design_tmpdir: PathBuf,
    result_env: PathBuf,
    composed_plan: PathBuf,
    repo_root: PathBuf,
}

/// Run the publish phase machine; returns the publish exit code.
#[expect(
    clippy::too_many_lines,
    reason = "one ported phase order whose steps must stay in one readable sequence"
)]
fn publish_core(
    runner: &dyn SiblingRunner,
    receipt: &dyn ReceiptWriter,
    args: &PublishArgs,
) -> i32 {
    let design_tmpdir = fs::canonicalize(&args.design_tmpdir)
        .unwrap_or_else(|_error| PathBuf::from(&args.design_tmpdir));
    let paths = PublishPaths {
        result_env: design_tmpdir.join(PUBLISH_RESULT_FILE),
        composed_plan: design_tmpdir.join("composed-plan.md"),
        repo_root: consumer_repo_root()
            .or_else(plugin_root_directory)
            .unwrap_or_else(|| PathBuf::from(".")),
        design_tmpdir,
    };
    let Some(attempt_id) = resolve_attempt_id() else {
        return RC_FAILED;
    };
    let mut rows = Rows(
        [
            ("PUBLISH_ATTEMPT_ID", attempt_id.as_str()),
            ("PUBLISH_RC_SOURCE", RC_SOURCE_RETURNED),
            ("LATEST_PHASE", "initialized"),
            ("PLAN_WRITE_OK", "false"),
            ("PUBLISH_OK", "false"),
            ("RENAMED", "false"),
            ("LOG_PUBLISH_ATTEMPTED", "false"),
            ("LOG_PUBLISH_COMPLETED", "false"),
            ("VALIDATE_STATUS", "not-run"),
            ("VALIDATE_DEFECT_COUNT", "0"),
            ("VALIDATE_SKIPPED_COUNT", "0"),
            ("VALIDATE_UNSAFE_TOKEN_COUNT", "0"),
            ("VALIDATE_MISSING_SCRIPT_COUNT", "0"),
            ("VALIDATE_LOG_FILE", ""),
        ]
        .into_iter()
        .map(|(key, value)| (key.to_owned(), value.to_owned()))
        .collect(),
    );
    rows.push(
        "FINAL_SUMMARY_PATH",
        &paths
            .design_tmpdir
            .join("final-summary.md")
            .display()
            .to_string(),
    );
    rows.push("DESIGNED_ADMISSION_READY", "false");
    rows.push("PUBLISH_REFUSE_REASON", "");

    if !paths
        .design_tmpdir
        .join(".completed")
        .join("step-5b")
        .is_file()
    {
        return RC_FAILED;
    }
    if let Err(error) = checkpoint(&paths.result_env, &mut rows, "initialized") {
        eprintln!("{error}");
        return RC_FAILED;
    }

    // Publish recomposes composed-plan.md from plan.txt so a stale composition
    // cannot reach the issue; the compose helper stays with its Step 5c owner.
    let compose = runner.run_python(&osargs(&[
        "design",
        "compose-plan-md",
        "--design-tmpdir",
        &paths.design_tmpdir.display().to_string(),
    ]));
    print!("{}", compose.stdout);
    if !nonempty_file(&paths.composed_plan) {
        rows.set("VALIDATE_STATUS", "defects-found");
        rows.set("VALIDATE_DEFECT_COUNT", "1");
        rows.set(
            "VALIDATE_LOG_FILE",
            &paths
                .design_tmpdir
                .join("validate-plan-commands.log")
                .display()
                .to_string(),
        );
        return refuse(&paths.result_env, &rows);
    }

    let provenance = review_provenance(&paths.design_tmpdir);
    let step3_sentinel = paths
        .design_tmpdir
        .join(".completed")
        .join("step-3")
        .is_file();
    let refusal = publish_refusal_reason(
        runner,
        &paths,
        &blocked_review_reason(&provenance, step3_sentinel),
    );
    if !refusal.is_empty() {
        return emit_publish_refusal(&refusal, &mut rows, &paths.result_env);
    }

    if paths.design_tmpdir.join(".pause-requested").is_file() {
        let mut pause = vec![
            "design".to_owned(),
            "pause-save".to_owned(),
            "--design-tmpdir".to_owned(),
            paths.design_tmpdir.display().to_string(),
            "--issue".to_owned(),
            args.issue.clone(),
        ];
        if !args.repo.is_empty() {
            pause.push("--repo".to_owned());
            pause.push(args.repo.clone());
        }
        return runner
            .run_python(&pause.iter().map(OsString::from).collect::<Vec<_>>())
            .rc;
    }

    if !sanitize_diagram_candidate(runner, &paths.design_tmpdir) {
        return RC_FAILED;
    }

    let plan_text = match stage_plan_text(&paths, &provenance) {
        Ok(text) => text,
        Err(code) => return code,
    };
    let (rating, raw_invalid) = resolve_publish_difficulty_rating(&paths.design_tmpdir, &plan_text);
    if raw_invalid {
        return RC_FAILED;
    }
    let plan_text = match &rating {
        Some(rating) => {
            let rewritten = rewrite_plan_difficulty(&plan_text, &rating.adjusted_tier);
            if rewritten != plan_text {
                let _ = fs::write(&paths.composed_plan, &rewritten);
            }
            rewritten
        }
        None => plan_text,
    };

    if args.skip_validate {
        rows.set("VALIDATE_STATUS", "skipped");
    } else if let Some(code) = validate_composed_plan(runner, &paths, &mut rows) {
        return code;
    }

    if let Some(code) = refuse_pre_write_gates(
        &paths.design_tmpdir,
        &paths.repo_root,
        &plan_text,
        &mut rows,
        &paths.result_env,
    ) {
        return code;
    }

    let repo_args: Vec<String> = if args.repo.is_empty() {
        Vec::new()
    } else {
        vec!["--repo".to_owned(), args.repo.clone()]
    };
    let context = (!args.session_id.is_empty()).then_some(LogPublishContext {
        design_tmpdir: &paths.design_tmpdir,
        session_id: &args.session_id,
        issue: &args.issue,
        repo: &args.repo,
    });

    let redacted_plan = paths.design_tmpdir.join("composed-plan.redacted.md");
    let redacted = redact_secrets_only(&plan_text);
    if redacted.is_empty() || fs::write(&redacted_plan, &redacted).is_err() {
        return RC_FAILED;
    }
    let block = plan_named_block_args(&args.issue, &redacted_plan, &repo_args);
    if runner
        .run_larch(&block.iter().map(OsString::from).collect::<Vec<_>>())
        .rc
        != 0
    {
        return finalize_failed_plan_write(
            runner,
            context.as_ref(),
            &paths.design_tmpdir,
            &mut rows,
            &paths.result_env,
        );
    }
    rows.set("PLAN_WRITE_OK", "true");
    if let Err(error) = checkpoint(&paths.result_env, &mut rows, "plan-write") {
        eprintln!("{error}");
        return 1;
    }
    let issue_number = args.issue.parse::<u64>().unwrap_or_default();
    if let Err(detail) = receipt.persist(&args.repo, issue_number, &paths.repo_root) {
        rows.set("PLAN_WRITE_OK", "false");
        if let Err(error) = checkpoint(&paths.result_env, &mut rows, "plan-receipt") {
            eprintln!("{error}");
            return 1;
        }
        println!("**❌ 5c: plan receipt persistence failed: {detail}**");
        return finalize_failed_plan_write(
            runner,
            context.as_ref(),
            &paths.design_tmpdir,
            &mut rows,
            &paths.result_env,
        );
    }

    if let Some(rating) = &rating {
        publish_difficulty(
            runner,
            &paths.design_tmpdir,
            &args.issue,
            &repo_args,
            rating,
        );
    }
    if let Err(error) = checkpoint(&paths.result_env, &mut rows, "difficulty") {
        eprintln!("{error}");
        return 1;
    }

    upsert_architecture_diagram(
        runner,
        &paths.design_tmpdir,
        &args.issue,
        &repo_args,
        &mut rows,
    );
    if let Err(error) = checkpoint(&paths.result_env, &mut rows, "diagram-upsert") {
        eprintln!("{error}");
        return 1;
    }

    rename_tracking_issue(runner, &paths, &args.issue, &repo_args, &mut rows);
    if let Err(error) = checkpoint(&paths.result_env, &mut rows, "tracking-issue-rename") {
        eprintln!("{error}");
        return 1;
    }

    if let Some(context) = &context {
        rows.set("LOG_PUBLISH_ATTEMPTED", "true");
        if let Err(error) = checkpoint(&paths.result_env, &mut rows, "log-publish") {
            eprintln!("{error}");
            return 1;
        }
        if let Some(code) = run_log_publish(
            runner,
            context,
            &mut rows,
            &paths.result_env,
            "approved",
            true,
        ) {
            return code;
        }
        rows.set("LOG_PUBLISH_COMPLETED", "true");
    }
    if let Err(error) = checkpoint(&paths.result_env, &mut rows, "complete") {
        eprintln!("{error}");
        return 1;
    }
    rows.emit();
    0
}

/// Return the publish refusal reason, or an empty string when publish may run.
fn publish_refusal_reason(
    runner: &dyn SiblingRunner,
    paths: &PublishPaths,
    blocked_reason: &str,
) -> String {
    if !blocked_reason.is_empty() {
        return format!("review-provenance:{blocked_reason}");
    }
    let size = runner.run_larch_env(
        &osargs(&[
            "plan",
            "check-size",
            "--design-tmpdir",
            &paths.design_tmpdir.display().to_string(),
            &format!(
                "--plan-file={}",
                paths.design_tmpdir.join("plan.txt").display()
            ),
        ]),
        &[(ChildEnvironment::LarchQuietDisable, OsString::from("1"))],
    );
    let combined = format!("{}\n{}", size.stdout, size.stderr);
    if size.rc != 0 || kv_last(&combined, "PLAN_SIZE_STATUS") != "ok" {
        return "plan-size:size-check-failed".to_owned();
    }
    match kv_last(&combined, "SIZE_TRIGGER_FIRED").as_str() {
        "false" => String::new(),
        "true" => "plan-size:oversize-no-override".to_owned(),
        _ => "plan-size:size-check-failed".to_owned(),
    }
}

/// Splice review provenance into the composed plan and return its text.
fn stage_plan_text(paths: &PublishPaths, provenance: &ReviewProvenance) -> Result<String, i32> {
    if !provenance.status.is_empty() || provenance.rounds_completed != 0 {
        let original = read_lossy(&paths.composed_plan);
        let spliced =
            splice_plan_provenance(&original, &provenance.status, provenance.rounds_completed);
        if fs::write(&paths.composed_plan, &spliced).is_err() {
            return Err(RC_FAILED);
        }
    }
    Ok(read_lossy(&paths.composed_plan))
}

/// Run `plan validate` and record its rows; `Some(code)` ends publish.
fn validate_composed_plan(
    runner: &dyn SiblingRunner,
    paths: &PublishPaths,
    rows: &mut Rows,
) -> Option<i32> {
    let validate = runner.run_larch_env(
        &osargs(&[
            "plan",
            "validate",
            "--plan-file",
            &paths.composed_plan.display().to_string(),
            "--source-kind",
            "composed",
            "--design-tmpdir",
            &paths.design_tmpdir.display().to_string(),
            "--repo-root",
            &paths.repo_root.display().to_string(),
        ]),
        &[
            (ChildEnvironment::LarchQuietDisable, OsString::from("1")),
            (
                ChildEnvironment::LarchRequirePlanDifficulty,
                OsString::from("1"),
            ),
            (
                ChildEnvironment::DesignTmpdir,
                paths.design_tmpdir.as_os_str().to_owned(),
            ),
        ],
    );
    let combined = format!("{}\n{}", validate.stdout, validate.stderr);
    for (key, fallback) in [
        ("VALIDATE_STATUS", "not-run"),
        ("VALIDATE_DEFECT_COUNT", "0"),
        ("VALIDATE_SKIPPED_COUNT", "0"),
        ("VALIDATE_UNSAFE_TOKEN_COUNT", "0"),
        ("VALIDATE_LOG_FILE", ""),
    ] {
        let value = kv_last(&combined, key);
        rows.set(key, if value.is_empty() { fallback } else { &value });
    }
    rows.set(
        "VALIDATE_MISSING_SCRIPT_COUNT",
        &count_missing_script_defects(&kv_last(&combined, "VALIDATE_LOG_FILE")),
    );
    if rows.get("VALIDATE_STATUS") == "defects-found" {
        return Some(refuse(&paths.result_env, rows));
    }
    if validate.rc != 0 || rows.get("VALIDATE_STATUS") != "ok" {
        return Some(RC_FAILED);
    }
    None
}

/// Rename the tracking issue to `[DESIGNED]` and record the admission rows.
fn rename_tracking_issue(
    runner: &dyn SiblingRunner,
    paths: &PublishPaths,
    issue: &str,
    repo_args: &[String],
    rows: &mut Rows,
) {
    let mut args = vec![
        "tracking-issue".to_owned(),
        "rename".to_owned(),
        "--issue".to_owned(),
        issue.to_owned(),
        "--state".to_owned(),
        "designed".to_owned(),
    ];
    args.extend(repo_args.iter().cloned());
    let rename = runner.run_larch(&args.iter().map(OsString::from).collect::<Vec<_>>());
    write_bounded_phase_stderr(&paths.design_tmpdir, RENAME_STDERR_FILE, &rename.stderr);
    let renamed = kv_last(&rename.stdout, "RENAMED");
    let new_title = kv_last(&rename.stdout, "NEW_TITLE");
    if !renamed.is_empty() {
        rows.push("RENAMED", &renamed);
    }
    if !new_title.is_empty() {
        rows.push("NEW_TITLE", &new_title);
    }
    if renamed == "true" || has_designed_prefix(&new_title) {
        rows.set("DESIGNED_ADMISSION_READY", "true");
    }
}

/// The `design publish` entrypoint.
pub fn design_publish_main(argv: &[OsString]) -> ExitCode {
    let parsed = match parse_publish_args(argv) {
        Ok(parsed) => parsed,
        Err(code) => return exit_from_i32(code),
    };
    let root = plugin_root_directory().unwrap_or_default();
    let cwd = std::env::current_dir().unwrap_or_else(|_error| PathBuf::from("."));
    let runner = LiveRunner::new(cwd, root);
    exit_from_i32(publish_core(&runner, &LiveReceiptWriter, &parsed))
}

#[cfg(test)]
mod tests;
