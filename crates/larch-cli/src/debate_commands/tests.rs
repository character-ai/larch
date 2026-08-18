//! Black-box parity tests for `debate init` and `debate round-prep`.
//!
//! The subprocess-slot vendor bootstrap is injected, so these tests never
//! launch a real vendor. They pin the success envelopes, the persisted
//! `debate-state.json` structure, and byte-exact turn-prompt files against the
//! frozen Python fixtures, plus the validation and stale-fingerprint refusals.

#[cfg(test)]
mod debate_commands_tests {
    #![allow(clippy::similar_names, clippy::redundant_clone)]

    use super::super::{
        AdjudicateArgs, AdjudicationBackend, DebateError, InitInputs, SynthesisBackend,
        TurnOutcome, TurnRequest, default_runner, envelope, initialize, input_file_runner,
        one_dispatch_value, parse_args, parse_operator_adjudication_row, point_values,
        proposal_parts, run_abort, run_adjudicate, run_adjudication_preview, run_publish_prepare,
        run_record_turn, run_round_prep, run_synthesize, strict_bool, synthesis_input, voter_paths,
    };
    use larch_adapters::TemporaryRoot;
    use larch_core::VendorSessionHandle;
    use larch_core::debate::{
        NonterminalPhase, ParticipantSlot, PointId, ReasonFingerprint, RoundNumber, RoundState,
        SLOT_ORDER, SlotLedgerBinding, StoredState, TerminalOutcome, TransitionAction,
        decode_state, encode_state, fingerprint_reason, parse_slot, parse_slot_ledger, transition,
    };
    use std::collections::BTreeMap;
    use std::ffi::OsString;
    use std::path::{Path, PathBuf};
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::time::{SystemTime, UNIX_EPOCH};

    const SUBJECT: &str = "Should we adopt approach A?";

    fn unique_dir(label: &str) -> PathBuf {
        static COUNTER: AtomicU64 = AtomicU64::new(0);
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|duration| duration.as_nanos())
            .unwrap_or(0);
        let root = std::env::temp_dir().join(format!(
            "larch-debate-{label}-{}-{nanos}-{n}",
            std::process::id()
        ));
        std::fs::create_dir_all(&root).expect("create dir");
        root
    }

    fn fixture(name: &str) -> String {
        let path = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("tests/fixtures/debate_commands")
            .join(name);
        std::fs::read_to_string(&path).unwrap_or_else(|_| panic!("read fixture {name}"))
    }

    fn fake_bootstrap(
        slot: &ParticipantSlot,
        _context: &larch_core::debate::InitializationContext,
    ) -> Result<VendorSessionHandle, DebateError> {
        match slot.tool.as_str() {
            "cursor" => VendorSessionHandle::create("cursor", "chat-abc123")
                .map_err(|_error| DebateError::runner_failure()),
            "codex" => VendorSessionHandle::create("codex", "123e4567-e89b-12d3-a456-426614174000")
                .map_err(|_error| DebateError::runner_failure()),
            other => panic!("unexpected bootstrap slot {other}"),
        }
    }

    fn init_inputs(debate: &Path, work: &Path, log: &Path) -> InitInputs {
        InitInputs {
            debate_tmpdir: debate.to_string_lossy().into_owned(),
            expected_fingerprint: "ABSENT".to_owned(),
            repo_workdir: work.to_string_lossy().into_owned(),
            log_root: log.to_string_lossy().into_owned(),
            run_id: "run-1".to_owned(),
            point_universe: vec![PointId::new(1).unwrap(), PointId::new(2).unwrap()],
            run_local_values: BTreeMap::from([("needle".to_owned(), "value".to_owned())]),
            cursor: true,
            codex: true,
            claude: true,
            restore_issue_number: "42".to_owned(),
            restore_original_title: "Orig Title".to_owned(),
            restore_title: "[DEBATING] Orig Title".to_owned(),
            subject: SUBJECT.to_owned(),
        }
    }

    fn seed_init() -> (PathBuf, StoredState) {
        let debate = unique_dir("root");
        let work = unique_dir("work");
        let log = unique_dir("log");
        let inputs = init_inputs(&debate, &work, &log);
        let state = initialize(&inputs, &fake_bootstrap).expect("init succeeds");
        (debate, state)
    }

    #[test]
    fn init_produces_blind_round_1_envelope_and_canonical_state() {
        let (debate, state) = seed_init();
        let env = envelope(true, "init", Some(&state), None, None, None);
        assert_eq!(
            env,
            format!(
                "{{\"artifact_path\":null,\"error_class\":null,\"fingerprint\":\"{}\",\"ok\":true,\"operation\":\"init\",\"phase\":\"BLIND_ROUND_1\",\"schema_version\":2,\"slot_result\":null,\"terminal_outcome\":null,\"warning\":\"\"}}",
                state.fingerprint
            )
        );
        // The written state re-decodes and re-encodes byte for byte.
        let written =
            std::fs::read_to_string(debate.join("debate-state.json")).expect("state file");
        let decoded = decode_state(&written).expect("decode");
        assert_eq!(encode_state(&decoded), written);
        assert_eq!(decoded.fingerprint, state.fingerprint);
        assert_eq!(decoded.initialization.slots.len(), 3);
        assert_eq!(decoded.initialization.session_handles.len(), 2);
        assert!(decoded.active_round.is_none());
        assert!(
            decoded
                .initialization
                .run_local_values
                .contains_key("larch.debate.subject-base64")
        );
    }

    #[test]
    fn round_prep_writes_byte_exact_prompts_and_active_round() {
        let (debate, state) = seed_init();
        let parsed = BTreeMap::from([
            (
                "--debate-tmpdir".to_owned(),
                debate.to_string_lossy().into_owned(),
            ),
            (
                "--expected-fingerprint".to_owned(),
                state.fingerprint.clone(),
            ),
            ("--round".to_owned(), "1".to_owned()),
        ]);
        let rp_state = run_round_prep(&parsed).expect("round-prep succeeds");
        let active = rp_state.active_round.as_ref().expect("active round");
        assert_eq!(active.round_number, 1);
        assert!(active.prepared);
        assert_eq!(active.live_slots, vec!["cursor", "codex", "claude"]);
        assert_eq!(active.pending_slots, vec!["cursor", "codex", "claude"]);
        for slot in ["cursor", "codex", "claude"] {
            let path = debate.join(format!("{slot}-round-1-prompt.md"));
            let rendered = std::fs::read_to_string(&path).expect("prompt file");
            assert_eq!(
                rendered,
                fixture(&format!("round1-{slot}-prompt.md")),
                "prompt mismatch for {slot}"
            );
        }
        let env = envelope(true, "round-prep", Some(&rp_state), None, None, None);
        assert!(env.contains("\"operation\":\"round-prep\""));
        assert!(env.contains("\"phase\":\"BLIND_ROUND_1\""));
    }

    #[test]
    fn init_rejects_non_absent_fingerprint() {
        let debate = unique_dir("root");
        let work = unique_dir("work");
        let log = unique_dir("log");
        let mut inputs = init_inputs(&debate, &work, &log);
        inputs.expected_fingerprint = "deadbeef".to_owned();
        let error = initialize(&inputs, &fake_bootstrap).expect_err("must reject");
        assert_eq!(error.error_class, "validation");
        assert_eq!(error.exit_code, 2);
    }

    #[test]
    fn init_rejects_two_unavailable_vendors() {
        let debate = unique_dir("root");
        let work = unique_dir("work");
        let log = unique_dir("log");
        let mut inputs = init_inputs(&debate, &work, &log);
        inputs.cursor = false;
        inputs.codex = false;
        let error = initialize(&inputs, &fake_bootstrap).expect_err("must reject");
        assert_eq!(error.error_class, "validation");
    }

    #[test]
    fn init_warns_on_one_unavailable_vendor() {
        let debate = unique_dir("root");
        let work = unique_dir("work");
        let log = unique_dir("log");
        let mut inputs = init_inputs(&debate, &work, &log);
        inputs.codex = false;
        let state = initialize(&inputs, &fake_bootstrap).expect("init succeeds");
        assert_eq!(state.initialization.warning, "unavailable vendor: codex");
        // Only the available cursor subprocess slot is bootstrapped.
        assert_eq!(state.initialization.session_handles.len(), 1);
        assert!(state.initialization.session_handles.contains_key("cursor"));
    }

    #[test]
    fn init_rejects_state_already_present() {
        let (debate, _state) = seed_init();
        let work = unique_dir("work");
        let log = unique_dir("log");
        let inputs = init_inputs(&debate, &work, &log);
        let error = initialize(&inputs, &fake_bootstrap).expect_err("must reject second init");
        assert_eq!(error.error_class, "validation");
    }

    #[test]
    fn round_prep_rejects_stale_fingerprint_and_double_prep() {
        let (debate, state) = seed_init();
        let stale = BTreeMap::from([
            (
                "--debate-tmpdir".to_owned(),
                debate.to_string_lossy().into_owned(),
            ),
            ("--expected-fingerprint".to_owned(), "0".repeat(64)),
            ("--round".to_owned(), "1".to_owned()),
        ]);
        let error = run_round_prep(&stale).expect_err("stale fingerprint");
        assert_eq!(error.error_class, "stale_fingerprint");
        assert_eq!(error.exit_code, 3);

        let good = BTreeMap::from([
            (
                "--debate-tmpdir".to_owned(),
                debate.to_string_lossy().into_owned(),
            ),
            (
                "--expected-fingerprint".to_owned(),
                state.fingerprint.clone(),
            ),
            ("--round".to_owned(), "1".to_owned()),
        ]);
        let prepared = run_round_prep(&good).expect("first prep");
        // A second round-prep now finds an active round and refuses.
        let again = BTreeMap::from([
            (
                "--debate-tmpdir".to_owned(),
                debate.to_string_lossy().into_owned(),
            ),
            (
                "--expected-fingerprint".to_owned(),
                prepared.fingerprint.clone(),
            ),
            ("--round".to_owned(), "1".to_owned()),
        ]);
        let error = run_round_prep(&again).expect_err("double prep");
        assert_eq!(error.error_class, "validation");
    }

    #[test]
    fn round_prep_rejects_unadmitted_round() {
        let (debate, state) = seed_init();
        let parsed = BTreeMap::from([
            (
                "--debate-tmpdir".to_owned(),
                debate.to_string_lossy().into_owned(),
            ),
            (
                "--expected-fingerprint".to_owned(),
                state.fingerprint.clone(),
            ),
            ("--round".to_owned(), "2".to_owned()),
        ]);
        let error = run_round_prep(&parsed).expect_err("round 2 not admitted before round 1");
        assert_eq!(error.error_class, "validation");
    }

    #[test]
    fn parse_args_rejects_unknown_flag_and_missing_required() {
        let unknown = [OsString::from("--nope"), OsString::from("x")];
        assert!(parse_args(&unknown, &["--round"], &[]).is_err());
        let missing: [OsString; 0] = [];
        assert!(parse_args(&missing, &["--round"], &["--round"]).is_err());
        let ok = [OsString::from("--round"), OsString::from("1")];
        let parsed = parse_args(&ok, &["--round"], &["--round"]).expect("ok");
        assert_eq!(parsed["--round"], "1");
        let inline = [OsString::from("--round=2")];
        let parsed = parse_args(&inline, &["--round"], &["--round"]).expect("inline");
        assert_eq!(parsed["--round"], "2");
    }

    #[test]
    fn point_values_and_strict_bool_validate() {
        assert!(point_values("[]").is_err());
        assert!(point_values("[1,1]").is_err());
        assert!(point_values("[true]").is_err());
        assert!(point_values("not json").is_err());
        let points = point_values("[1,2]").expect("ok");
        assert_eq!(points.len(), 2);
        assert!(strict_bool("true").expect("true"));
        assert!(!strict_bool("false").expect("false"));
        assert!(strict_bool("yes").is_err());
    }

    // -----------------------------------------------------------------------
    // record-turn and abort parity
    // -----------------------------------------------------------------------

    const AGREE_LEDGER: &str =
        "POINT POINT_1 AGREE first reason\nPOINT POINT_2 AGREE second reason";

    /// Seed an initialized, round-1-prepared debate and return its fingerprint.
    ///
    /// `claude` toggles the third (agent-tool) slot; with it unavailable the
    /// live panel is exactly `cursor` and `codex`.
    fn seed_prepared(claude: bool) -> (PathBuf, String) {
        let debate = unique_dir("root");
        let work = unique_dir("work");
        let log = unique_dir("log");
        let mut inputs = init_inputs(&debate, &work, &log);
        inputs.claude = claude;
        let state = initialize(&inputs, &fake_bootstrap).expect("init succeeds");
        let parsed = BTreeMap::from([
            (
                "--debate-tmpdir".to_owned(),
                debate.to_string_lossy().into_owned(),
            ),
            ("--expected-fingerprint".to_owned(), state.fingerprint),
            ("--round".to_owned(), "1".to_owned()),
        ]);
        let prepared = run_round_prep(&parsed).expect("round-prep");
        (debate, prepared.fingerprint)
    }

    fn record_turn_args(
        debate: &Path,
        fingerprint: &str,
        round: i64,
        slot: &str,
    ) -> BTreeMap<String, String> {
        BTreeMap::from([
            (
                "--debate-tmpdir".to_owned(),
                debate.to_string_lossy().into_owned(),
            ),
            ("--expected-fingerprint".to_owned(), fingerprint.to_owned()),
            ("--round".to_owned(), round.to_string()),
            ("--slot".to_owned(), slot.to_owned()),
        ])
    }

    /// A fake runner writing a fixed all-AGREE ledger to the turn output.
    fn agree_runner(request: &TurnRequest) -> TurnOutcome {
        std::fs::write(&request.output, AGREE_LEDGER).expect("write ledger");
        TurnOutcome::success(request.output.clone())
    }

    #[test]
    fn record_turn_drives_round_one_to_converged() {
        let (debate, fingerprint) = seed_prepared(false);
        // First live slot: cursor. The round stays open.
        let first = run_record_turn(
            &record_turn_args(&debate, &fingerprint, 1, "cursor"),
            &agree_runner,
        )
        .expect("cursor turn");
        assert_eq!(first.slot_result, None);
        assert_eq!(first.exit_code, 0);
        assert!(first.state.active_round.is_some());
        assert_ne!(first.state.fingerprint, fingerprint);
        // Second (last) live slot: codex. SUBMIT_ROUND -> CONVERGED.
        let second = run_record_turn(
            &record_turn_args(&debate, &first.state.fingerprint, 1, "codex"),
            &agree_runner,
        )
        .expect("codex turn");
        assert_eq!(second.slot_result, None);
        assert!(second.state.active_round.is_none());
        assert_eq!(second.state.proposal.phase(), None);
        assert_eq!(
            second
                .state
                .proposal
                .terminal_outcome()
                .map(larch_core::debate::TerminalOutcome::as_str),
            Some("CONVERGED")
        );
        let env = envelope(true, "record-turn", Some(&second.state), None, None, None);
        assert!(env.contains("\"terminal_outcome\":\"CONVERGED\""));
        assert!(env.contains("\"ok\":true"));
        assert!(env.contains("\"slot_result\":null"));
    }

    #[test]
    fn record_turn_runner_failure_drops_and_aborts() {
        let (debate, fingerprint) = seed_prepared(false);
        let runner = |_request: &TurnRequest| TurnOutcome::drop("runner_failure");
        let outcome = run_record_turn(
            &record_turn_args(&debate, &fingerprint, 1, "cursor"),
            &runner,
        )
        .expect("drop envelope");
        assert_eq!(outcome.slot_result, Some("runner_failure"));
        assert_eq!(outcome.exit_code, 6);
        // Dropping cursor leaves one live slot (< floor), so the debate aborts.
        assert_eq!(
            outcome
                .state
                .proposal
                .terminal_outcome()
                .map(larch_core::debate::TerminalOutcome::as_str),
            Some("ABORTED")
        );
        assert_eq!(outcome.state.drops.len(), 1);
        assert_eq!(outcome.state.drops[0].slot, "cursor");
        let env = envelope(
            false,
            "record-turn",
            Some(&outcome.state),
            outcome.slot_result,
            outcome.slot_result,
            None,
        );
        assert!(env.contains("\"slot_result\":\"runner_failure\""));
        assert!(env.contains("\"error_class\":\"runner_failure\""));
    }

    #[test]
    fn record_turn_protocol_rejection_on_unparsable_output() {
        let (debate, fingerprint) = seed_prepared(false);
        let runner = |request: &TurnRequest| {
            std::fs::write(&request.output, "not a valid ledger").expect("write");
            TurnOutcome::success(request.output.clone())
        };
        let outcome = run_record_turn(
            &record_turn_args(&debate, &fingerprint, 1, "cursor"),
            &runner,
        )
        .expect("drop envelope");
        assert_eq!(outcome.slot_result, Some("protocol_rejection"));
        assert_eq!(outcome.exit_code, 2);
    }

    #[test]
    fn default_runner_rejects_missing_handle() {
        let request = TurnRequest {
            prompt: String::new(),
            workdir: PathBuf::from("/tmp"),
            output: PathBuf::from("/tmp/turn.out"),
            session_handle: None,
            model: String::new(),
        };
        let outcome = default_runner(&request);
        assert!(!outcome.ok);
        assert_eq!(outcome.error_class, Some("unsupported_transport"));
    }

    #[test]
    fn record_turn_input_file_drives_claude_slot() {
        let (debate, fingerprint) = seed_prepared(true);
        let after_cursor = run_record_turn(
            &record_turn_args(&debate, &fingerprint, 1, "cursor"),
            &agree_runner,
        )
        .expect("cursor turn")
        .state
        .fingerprint;
        let after_codex = run_record_turn(
            &record_turn_args(&debate, &after_cursor, 1, "codex"),
            &agree_runner,
        )
        .expect("codex turn")
        .state
        .fingerprint;
        // claude is the last pending slot, driven through the confined input file.
        let root = TemporaryRoot::resolve(Some(&debate)).expect("root");
        let input = root.path().join("claude-input.txt");
        std::fs::write(&input, AGREE_LEDGER).expect("write input");
        let input_str = input.to_string_lossy().into_owned();
        let runner = |request: &TurnRequest| input_file_runner(&root, &input_str, request);
        let outcome = run_record_turn(
            &record_turn_args(&debate, &after_codex, 1, "claude"),
            &runner,
        )
        .expect("claude turn");
        assert_eq!(outcome.slot_result, None);
        assert!(outcome.state.active_round.is_none());
        assert_eq!(
            outcome
                .state
                .proposal
                .terminal_outcome()
                .map(larch_core::debate::TerminalOutcome::as_str),
            Some("CONVERGED")
        );
    }

    #[test]
    fn record_turn_refuses_stale_and_out_of_order() {
        let (debate, fingerprint) = seed_prepared(true);
        let stale = record_turn_args(&debate, &"0".repeat(64), 1, "cursor");
        let error = run_record_turn(&stale, &agree_runner).expect_err("stale");
        assert_eq!(error.error_class, "stale_fingerprint");
        assert_eq!(error.exit_code, 3);

        // claude is not the first pending slot.
        let out_of_order = record_turn_args(&debate, &fingerprint, 1, "claude");
        let error = run_record_turn(&out_of_order, &agree_runner).expect_err("out of order");
        assert_eq!(error.error_class, "validation");
        assert_eq!(error.exit_code, 2);

        // Round 2 is not the admitted round while round 1 is active.
        let bad_round = record_turn_args(&debate, &fingerprint, 2, "cursor");
        let error = run_record_turn(&bad_round, &agree_runner).expect_err("bad round");
        assert_eq!(error.error_class, "validation");
    }

    fn abort_args(debate: &Path, fingerprint: &str) -> BTreeMap<String, String> {
        BTreeMap::from([
            (
                "--debate-tmpdir".to_owned(),
                debate.to_string_lossy().into_owned(),
            ),
            ("--expected-fingerprint".to_owned(), fingerprint.to_owned()),
        ])
    }

    #[test]
    fn abort_writes_restore_handoff_idempotently() {
        let (debate, fingerprint) = seed_prepared(true);
        let state = run_abort(&abort_args(&debate, &fingerprint)).expect("abort succeeds");
        assert_eq!(
            state
                .proposal
                .terminal_outcome()
                .map(larch_core::debate::TerminalOutcome::as_str),
            Some("ABORTED")
        );
        let handoff = debate.join("abort-restore.env");
        let bytes = std::fs::read_to_string(&handoff).expect("handoff");
        assert_eq!(
            bytes,
            format!(
                "RESTORE_ISSUE_NUMBER=42\nRESTORE_ORIGINAL_TITLE=Orig Title\nRESTORE_TITLE=[DEBATING] Orig Title\nSOURCE_FINGERPRINT={}\n",
                state.fingerprint
            )
        );
        // A second abort with the new fingerprint re-writes identical bytes.
        let again = run_abort(&abort_args(&debate, &state.fingerprint)).expect("second abort");
        assert_eq!(again.fingerprint, state.fingerprint);
        assert_eq!(std::fs::read_to_string(&handoff).expect("handoff2"), bytes);
    }

    #[test]
    fn abort_conflicting_handoff_is_persistence_failure() {
        let (debate, fingerprint) = seed_prepared(true);
        let handoff = debate.join("abort-restore.env");
        std::fs::write(&handoff, "RESTORE_ISSUE_NUMBER=different\n").expect("seed conflict");
        let error = run_abort(&abort_args(&debate, &fingerprint)).expect_err("conflict");
        assert_eq!(error.error_class, "persistence_failure");
        assert_eq!(error.exit_code, 5);
    }

    // -----------------------------------------------------------------------
    // adjudication-preview and adjudicate parity
    // -----------------------------------------------------------------------

    /// Submit one HOLD round directly through the protocol machine (mirrors the
    /// Python `_submit_round` test helper for a two-slot live panel).
    fn submit_hold_round(debate: &Path, round_number: i64) -> StoredState {
        let state = larch_cli::debate_state::load_state(debate).expect("load state");
        let needles: Vec<&str> = state
            .proposal
            .run_local_values()
            .iter()
            .map(String::as_str)
            .collect();
        let positions = [
            ("cursor", "adopt approach cursor"),
            ("codex", "adopt approach codex"),
        ];
        let mut bindings: Vec<SlotLedgerBinding> = Vec::new();
        for slot in SLOT_ORDER {
            if let Some((_, reason)) = positions.iter().find(|(name, _)| *name == slot) {
                let ledger =
                    parse_slot_ledger(&format!("POINT POINT_1 HOLD {reason}")).expect("ledger");
                let fingerprints: Vec<ReasonFingerprint> = ledger
                    .rows
                    .iter()
                    .map(|row| fingerprint_reason(&row.reason, &needles))
                    .collect::<Result<_, _>>()
                    .expect("fingerprints");
                let participant = parse_slot(slot).expect("slot");
                bindings.push(
                    SlotLedgerBinding::new(participant, ledger, fingerprints, &needles)
                        .expect("binding"),
                );
            }
        }
        let number = if round_number == 1 {
            RoundNumber::Round1
        } else {
            RoundNumber::Round2
        };
        let round = RoundState::new(number, bindings).expect("round");
        let proposal = transition(
            &state.proposal,
            TransitionAction::SubmitRound,
            Some(&round),
            None,
        )
        .expect("submit round");
        let stored = StoredState {
            proposal,
            active_round: None,
            fingerprint: String::new(),
            ..state
        };
        larch_cli::debate_state::write_state(debate, &stored).expect("write state")
    }

    /// Seed an initialized debate driven to `AWAITING_ADJUDICATION` over one
    /// unresolved point with two competing HOLD positions.
    fn seed_stalemate() -> (PathBuf, String) {
        let debate = unique_dir("root");
        let work = unique_dir("work");
        let log = unique_dir("log");
        let mut inputs = init_inputs(&debate, &work, &log);
        inputs.claude = false;
        inputs.point_universe = vec![PointId::new(1).unwrap()];
        let _state = initialize(&inputs, &fake_bootstrap).expect("init succeeds");
        let _round_one = submit_hold_round(&debate, 1);
        let state = submit_hold_round(&debate, 2);
        assert_eq!(
            state.proposal.phase(),
            Some(NonterminalPhase::AwaitingAdjudication)
        );
        (debate, state.fingerprint)
    }

    fn adjudicate_args(
        debate: &Path,
        fingerprint: &str,
        decisions_file: Option<&Path>,
        vote_stalemates: bool,
    ) -> AdjudicateArgs {
        AdjudicateArgs {
            debate_tmpdir: debate.to_string_lossy().into_owned(),
            expected_fingerprint: fingerprint.to_owned(),
            decisions_file: decisions_file.map(|path| path.to_string_lossy().into_owned()),
            vote_stalemates,
        }
    }

    fn panic_dispatch(
        _root: &Path,
        _state: &StoredState,
        _ballot: &Path,
    ) -> Result<(Vec<PathBuf>, String), DebateError> {
        panic!("operator adjudication must not dispatch voters");
    }

    fn panic_run_log(_state: &StoredState, _input: &Path) -> Result<(), DebateError> {
        panic!("operator adjudication must not write a run log");
    }

    #[test]
    fn adjudication_preview_writes_canonical_bytes() {
        let (debate, fingerprint) = seed_stalemate();
        let parsed = BTreeMap::from([
            (
                "--debate-tmpdir".to_owned(),
                debate.to_string_lossy().into_owned(),
            ),
            ("--expected-fingerprint".to_owned(), fingerprint.clone()),
        ]);
        let (state, artifact) = run_adjudication_preview(&parsed).expect("preview succeeds");
        // Preview never mutates the debate state.
        assert_eq!(state.fingerprint, fingerprint);
        let bytes = std::fs::read_to_string(&artifact).expect("preview artifact");
        assert_eq!(
            bytes,
            "{\"points\":[{\"point\":\"POINT_1\",\"positions\":[\"adopt approach cursor\",\"adopt approach codex\"]}]}\n"
        );
        let env = envelope(
            true,
            "adjudication-preview",
            Some(&state),
            None,
            None,
            Some(&artifact),
        );
        assert!(env.contains(&format!("\"artifact_path\":\"{}\"", artifact.display())));
        assert!(env.contains("\"operation\":\"adjudication-preview\""));
    }

    /// Write a decisions handoff under the canonical debate root so confinement
    /// accepts it even when the OS temp dir is symlinked (macOS `/var`).
    fn write_decisions(debate: &Path, contents: &str) -> PathBuf {
        let root = TemporaryRoot::resolve(Some(debate)).expect("root");
        let decisions = root.path().join("decisions.tsv");
        std::fs::write(&decisions, contents).expect("decisions");
        decisions
    }

    #[test]
    fn operator_adjudicate_reaches_converged() {
        let (debate, fingerprint) = seed_stalemate();
        let decisions = write_decisions(&debate, "POINT_1\tSELECTED\tadopt approach cursor\n");
        let backend = AdjudicationBackend {
            dispatch: &panic_dispatch,
            run_log: &panic_run_log,
        };
        let (state, tally) = run_adjudicate(
            &adjudicate_args(&debate, &fingerprint, Some(&decisions), false),
            &backend,
        )
        .expect("operator adjudicate");
        assert!(tally.is_none());
        assert_eq!(
            state
                .proposal
                .terminal_outcome()
                .map(TerminalOutcome::as_str),
            Some("CONVERGED")
        );
        // The persisted state advances to the adjudicated proposal.
        let reloaded = larch_cli::debate_state::load_state(&debate).expect("reload");
        assert_eq!(reloaded.fingerprint, state.fingerprint);
        let env = envelope(true, "adjudicate", Some(&state), None, None, None);
        assert!(env.contains("\"artifact_path\":null"));
        assert!(env.contains("\"operation\":\"adjudicate\""));
    }

    #[test]
    fn operator_adjudicate_rejects_malformed_handoff() {
        let (debate, fingerprint) = seed_stalemate();
        let decisions = write_decisions(&debate, "POINT_2\tSELECTED\tforeign\n");
        let backend = AdjudicationBackend {
            dispatch: &panic_dispatch,
            run_log: &panic_run_log,
        };
        let error = run_adjudicate(
            &adjudicate_args(&debate, &fingerprint, Some(&decisions), false),
            &backend,
        )
        .expect_err("must reject");
        assert_eq!(error.error_class, "adjudication_rejected");
        assert_eq!(error.exit_code, 8);
        let reloaded = larch_cli::debate_state::load_state(&debate).expect("reload");
        assert_eq!(reloaded.fingerprint, fingerprint);
    }

    #[test]
    fn autonomous_adjudicate_dispatch_and_tally() {
        let (debate, fingerprint) = seed_stalemate();
        let dispatch = |root_path: &Path,
                        _state: &StoredState,
                        _ballot: &Path|
         -> Result<(Vec<PathBuf>, String), DebateError> {
            let voter_dir = root_path.join("stalemate-voters");
            std::fs::write(
                voter_dir.join("voter-1.txt"),
                "FINDING_1: YES\nFINDING_2: NO\n",
            )
            .expect("voter output");
            Ok((
                vec![PathBuf::from("voter-1.txt")],
                "DISPATCH_OK=true\n".to_owned(),
            ))
        };
        let run_log = |_state: &StoredState, _input: &Path| -> Result<(), DebateError> { Ok(()) };
        let backend = AdjudicationBackend {
            dispatch: &dispatch,
            run_log: &run_log,
        };
        let (state, tally) = run_adjudicate(
            &adjudicate_args(&debate, &fingerprint, None, true),
            &backend,
        )
        .expect("autonomous adjudicate");
        assert_eq!(
            state
                .proposal
                .terminal_outcome()
                .map(TerminalOutcome::as_str),
            Some("CONVERGED")
        );
        let tally_path = tally.expect("tally artifact");
        let tally_text = std::fs::read_to_string(&tally_path).expect("tally file");
        assert!(tally_text.contains("adopt approach cursor"));
        // The tally never leaks the debate tmpdir path.
        assert!(!tally_text.contains(&debate.to_string_lossy().into_owned()));
        let env = envelope(
            true,
            "adjudicate",
            Some(&state),
            None,
            None,
            Some(&tally_path),
        );
        assert!(env.contains(&format!("\"artifact_path\":\"{}\"", tally_path.display())));
    }

    #[test]
    fn autonomous_empty_panel_is_both_viable() {
        let (debate, fingerprint) = seed_stalemate();
        let dispatch = |_root: &Path,
                        _state: &StoredState,
                        _ballot: &Path|
         -> Result<(Vec<PathBuf>, String), DebateError> {
            Ok((Vec::new(), "DISPATCH_OK=true\n".to_owned()))
        };
        let run_log = |_state: &StoredState, _input: &Path| -> Result<(), DebateError> { Ok(()) };
        let backend = AdjudicationBackend {
            dispatch: &dispatch,
            run_log: &run_log,
        };
        let (state, tally) = run_adjudicate(
            &adjudicate_args(&debate, &fingerprint, None, true),
            &backend,
        )
        .expect("autonomous adjudicate");
        assert!(tally.is_some());
        assert_eq!(
            state
                .proposal
                .terminal_outcome()
                .map(TerminalOutcome::as_str),
            Some("BOTH_VIABLE")
        );
    }

    #[test]
    fn autonomous_rejects_dispatch_failure() {
        let (debate, fingerprint) = seed_stalemate();
        let dispatch = |_root: &Path,
                        _state: &StoredState,
                        _ballot: &Path|
         -> Result<(Vec<PathBuf>, String), DebateError> {
            Err(DebateError::adjudication_rejected())
        };
        let run_log = |_state: &StoredState, _input: &Path| -> Result<(), DebateError> {
            panic!("dispatch failure must abort before the run log")
        };
        let backend = AdjudicationBackend {
            dispatch: &dispatch,
            run_log: &run_log,
        };
        let error = run_adjudicate(
            &adjudicate_args(&debate, &fingerprint, None, true),
            &backend,
        )
        .expect_err("must reject");
        assert_eq!(error.error_class, "adjudication_rejected");
        let reloaded = larch_cli::debate_state::load_state(&debate).expect("reload");
        assert_eq!(reloaded.fingerprint, fingerprint);
    }

    #[test]
    fn adjudicate_rejects_mutually_exclusive_modes() {
        let (debate, fingerprint) = seed_stalemate();
        let decisions = write_decisions(&debate, "POINT_1\tSELECTED\tadopt approach cursor\n");
        let backend = AdjudicationBackend {
            dispatch: &panic_dispatch,
            run_log: &panic_run_log,
        };
        let error = run_adjudicate(
            &adjudicate_args(&debate, &fingerprint, Some(&decisions), true),
            &backend,
        )
        .expect_err("mutually exclusive");
        assert_eq!(error.error_class, "adjudication_rejected");
    }

    #[test]
    fn operator_row_and_dispatch_kv_parse() {
        assert!(parse_operator_adjudication_row("POINT_1\tSELECTED").is_err());
        assert!(parse_operator_adjudication_row("POINT_1\tSPLIT\tfirst\tsecond").is_ok());
        assert!(parse_operator_adjudication_row("POINT_0\tSELECTED\tx").is_err());
        assert_eq!(one_dispatch_value("K=v\n", "K"), Some("v".to_owned()));
        assert_eq!(one_dispatch_value("K=v\nK=w\n", "K"), None);
        assert_eq!(one_dispatch_value("", "K"), None);
    }

    #[test]
    fn voter_paths_requires_paths_file_key() {
        let dir = unique_dir("voters");
        let root = TemporaryRoot::resolve(Some(&dir)).expect("root");
        let error = voter_paths(&root, "DISPATCH_OK=true\n").expect_err("missing key");
        assert_eq!(error.error_class, "adjudication_rejected");
    }

    /// Seed a debate driven to a terminal `CONVERGED` outcome with the subject
    /// bound, ready for synthesis. Returns the debate root and its fingerprint.
    fn seed_converged() -> (PathBuf, String) {
        let (debate, fingerprint) = seed_stalemate();
        let decisions = write_decisions(&debate, "POINT_1\tSELECTED\tadopt approach cursor\n");
        let backend = AdjudicationBackend {
            dispatch: &panic_dispatch,
            run_log: &panic_run_log,
        };
        let (state, _tally) = run_adjudicate(
            &adjudicate_args(&debate, &fingerprint, Some(&decisions), false),
            &backend,
        )
        .expect("operator adjudicate");
        assert_eq!(
            state
                .proposal
                .terminal_outcome()
                .map(TerminalOutcome::as_str),
            Some("CONVERGED")
        );
        (debate, state.fingerprint)
    }

    fn synthesize_parsed(debate: &Path, fingerprint: &str) -> BTreeMap<String, String> {
        BTreeMap::from([
            (
                "--debate-tmpdir".to_owned(),
                debate.to_string_lossy().into_owned(),
            ),
            ("--expected-fingerprint".to_owned(), fingerprint.to_owned()),
        ])
    }

    /// A synthesizer that writes `body` under the debate root and reports the
    /// single output path through the dispatcher stdout contract.
    fn writing_dispatch(
        body: &'static str,
    ) -> impl Fn(&Path, &StoredState, &Path) -> Result<(bool, String), DebateError> {
        move |root_path: &Path, _state: &StoredState, _manifest: &Path| {
            std::fs::write(root_path.join("synthesizer-output.md"), body).expect("output");
            std::fs::write(root_path.join("all-outputs.txt"), "synthesizer-output.md\n")
                .expect("paths");
            Ok((
                true,
                "ALL_OUTPUT_FILES_PATH=all-outputs.txt\nDISPATCH_OK=true\n".to_owned(),
            ))
        }
    }

    fn ok_run_log(_state: &StoredState, _input: &Path) -> Result<(), DebateError> {
        Ok(())
    }

    fn panic_synthesis_dispatch(
        _root: &Path,
        _state: &StoredState,
        _manifest: &Path,
    ) -> Result<(bool, String), DebateError> {
        panic!("a completed synthesis must not re-dispatch the synthesizer");
    }

    #[test]
    fn synthesis_input_binds_subject_and_terminal() {
        let (debate, _fingerprint) = seed_converged();
        let state = larch_cli::debate_state::load_state(&debate).expect("load");
        let input = synthesis_input(&state).expect("synthesis input");
        assert!(input.contains("\"subject\":\"Should we adopt approach A?\""));
        assert!(input.contains("\"terminal_outcome\":\"CONVERGED\""));
        assert!(input.contains("\"selected_position\":\"adopt approach cursor\""));
    }

    #[test]
    fn synthesize_writes_redacted_artifacts_and_is_idempotent() {
        let (debate, fingerprint) = seed_converged();
        let dispatch = writing_dispatch("# My Title\n\nBody text here.\n");
        let backend = SynthesisBackend {
            dispatch: &dispatch,
            run_log: &ok_run_log,
        };
        let parsed = synthesize_parsed(&debate, &fingerprint);
        let (state, body_path) = run_synthesize(&parsed, &backend).expect("synthesize");
        // Synthesize never mutates the debate state or its fingerprint.
        assert_eq!(state.fingerprint, fingerprint);
        let root = TemporaryRoot::resolve(Some(&debate)).expect("root");
        assert_eq!(body_path, root.path().join("proposal-body.md"));
        assert_eq!(
            std::fs::read_to_string(root.path().join("proposal-title.txt")).expect("title"),
            "[PROPOSAL] My Title\n"
        );
        assert_eq!(
            std::fs::read_to_string(&body_path).expect("body"),
            "Body text here.\n"
        );
        let marker =
            std::fs::read_to_string(root.path().join("synthesis-complete.json")).expect("marker");
        assert!(marker.contains(&format!("\"source_fingerprint\":\"{fingerprint}\"")));
        assert!(marker.ends_with("}\n"));
        // A machine envelope on the success path pins the shape reviewers read.
        let env = envelope(
            true,
            "synthesize",
            Some(&state),
            None,
            None,
            Some(&body_path),
        );
        assert!(env.contains("\"ok\":true"));
        assert!(env.contains(&format!("\"fingerprint\":\"{fingerprint}\"")));
        assert!(env.contains("\"terminal_outcome\":\"CONVERGED\""));
        assert!(env.contains(&format!("\"artifact_path\":\"{}\"", body_path.display())));
        assert!(env.contains("\"operation\":\"synthesize\""));

        // The second call must hit the marker without re-dispatching.
        let backend = SynthesisBackend {
            dispatch: &panic_synthesis_dispatch,
            run_log: &ok_run_log,
        };
        let (again, again_path) = run_synthesize(&parsed, &backend).expect("idempotent synthesize");
        assert_eq!(again.fingerprint, fingerprint);
        assert_eq!(again_path, body_path);
    }

    #[test]
    fn synthesize_normalizes_case_variant_prefix() {
        let (debate, fingerprint) = seed_converged();
        let dispatch = writing_dispatch("# [proposal] Real Title\n\nProposal body.\n");
        let backend = SynthesisBackend {
            dispatch: &dispatch,
            run_log: &ok_run_log,
        };
        let (_state, body_path) =
            run_synthesize(&synthesize_parsed(&debate, &fingerprint), &backend)
                .expect("synthesize");
        let root = TemporaryRoot::resolve(Some(&debate)).expect("root");
        assert_eq!(
            std::fs::read_to_string(root.path().join("proposal-title.txt")).expect("title"),
            "[PROPOSAL] Real Title\n"
        );
        assert_eq!(
            std::fs::read_to_string(&body_path).expect("body"),
            "Proposal body.\n"
        );
    }

    #[test]
    fn synthesize_rejects_plan_grammar_retriably() {
        let (debate, fingerprint) = seed_converged();
        let dispatch = writing_dispatch("# Title\n\n### NEW: something\ndiff_lines: 3\n");
        let backend = SynthesisBackend {
            dispatch: &dispatch,
            run_log: &ok_run_log,
        };
        let error = run_synthesize(&synthesize_parsed(&debate, &fingerprint), &backend)
            .expect_err("plan grammar rejected");
        assert_eq!(error.error_class, "synthesis_exhausted");
        assert_eq!(error.exit_code, 9);
        // No marker is written, so the operation stays retriable.
        let root = TemporaryRoot::resolve(Some(&debate)).expect("root");
        assert!(!root.path().join("synthesis-complete.json").exists());
        let reloaded = larch_cli::debate_state::load_state(&debate).expect("reload");
        assert_eq!(reloaded.fingerprint, fingerprint);
    }

    #[test]
    fn synthesize_rejects_option_shaped_title() {
        let (debate, fingerprint) = seed_converged();
        let dispatch = writing_dispatch("# - dashed title\n\nbody\n");
        let backend = SynthesisBackend {
            dispatch: &dispatch,
            run_log: &ok_run_log,
        };
        let error = run_synthesize(&synthesize_parsed(&debate, &fingerprint), &backend)
            .expect_err("option-shaped title rejected");
        assert_eq!(error.error_class, "synthesis_exhausted");
        assert_eq!(error.exit_code, 9);
    }

    #[test]
    fn synthesize_waterfall_exhaustion_is_retriable() {
        let (debate, fingerprint) = seed_converged();
        let dispatch = |_root: &Path,
                        _state: &StoredState,
                        _manifest: &Path|
         -> Result<(bool, String), DebateError> {
            Ok((false, "DISPATCH_OK=false\n".to_owned()))
        };
        let backend = SynthesisBackend {
            dispatch: &dispatch,
            run_log: &ok_run_log,
        };
        let error = run_synthesize(&synthesize_parsed(&debate, &fingerprint), &backend)
            .expect_err("waterfall exhausted");
        assert_eq!(error.error_class, "synthesis_exhausted");
        assert_eq!(error.exit_code, 9);
        let reloaded = larch_cli::debate_state::load_state(&debate).expect("reload");
        assert_eq!(reloaded.fingerprint, fingerprint);
    }

    #[test]
    fn publish_prepare_writes_handoff_and_is_idempotent() {
        let (debate, fingerprint) = seed_converged();
        let dispatch = writing_dispatch("# My Title\n\nBody text here.\n");
        let backend = SynthesisBackend {
            dispatch: &dispatch,
            run_log: &ok_run_log,
        };
        let parsed = synthesize_parsed(&debate, &fingerprint);
        let (_state, body_path) = run_synthesize(&parsed, &backend).expect("synthesize");
        let (state, handoff_path) = run_publish_prepare(&parsed).expect("publish-prepare");
        assert_eq!(state.fingerprint, fingerprint);
        let root = TemporaryRoot::resolve(Some(&debate)).expect("root");
        assert_eq!(handoff_path, root.path().join("publish-prepare.env"));
        let handoff = std::fs::read_to_string(&handoff_path).expect("handoff");
        assert!(handoff.contains(&format!("BODY_FILE={}\n", body_path.display())));
        assert!(handoff.contains(&format!(
            "TITLE_FILE={}\n",
            root.path().join("proposal-title.txt").display()
        )));
        assert!(handoff.contains("SOURCE_ISSUE_NUMBER=42\n"));
        assert!(handoff.contains("CROSS_LINK_ISSUE_NUMBER=42\n"));
        assert!(handoff.ends_with(&format!("SOURCE_FINGERPRINT={fingerprint}\n")));
        // A second call reproduces the same handoff idempotently.
        let (_again, again_path) =
            run_publish_prepare(&parsed).expect("idempotent publish-prepare");
        assert_eq!(again_path, handoff_path);
    }

    #[test]
    fn publish_prepare_without_synthesis_is_publication_failure() {
        let (debate, fingerprint) = seed_converged();
        let error = run_publish_prepare(&synthesize_parsed(&debate, &fingerprint))
            .expect_err("no synthesized proposal");
        assert_eq!(error.error_class, "publication_failure");
        assert_eq!(error.exit_code, 10);
    }

    #[test]
    fn proposal_parts_rejects_missing_title() {
        let error = proposal_parts("no title line\n").expect_err("missing title");
        assert_eq!(error.error_class, "synthesis_exhausted");
        let (title, body) = proposal_parts("# Clean Title\n\nClean body.\n").expect("valid");
        assert_eq!(title, "Clean Title");
        assert_eq!(body, "Clean body.");
    }
}
