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
        DebateError, InitInputs, envelope, initialize, parse_args, point_values, run_round_prep,
        strict_bool,
    };
    use larch_core::VendorSessionHandle;
    use larch_core::debate::{ParticipantSlot, PointId, StoredState, decode_state, encode_state};
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
        let env = envelope(true, "init", Some(&state), None);
        assert_eq!(
            env,
            format!(
                "{{\"artifact_path\":null,\"error_class\":null,\"fingerprint\":\"{}\",\"ok\":true,\"operation\":\"init\",\"phase\":\"BLIND_ROUND_1\",\"schema_version\":2,\"slot_result\":null,\"terminal_outcome\":null,\"warning\":\"\"}}",
                state.fingerprint
            )
        );
        // The written state re-decodes and re-encodes byte for byte.
        let written = std::fs::read_to_string(debate.join("debate-state.json")).expect("state file");
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
        let env = envelope(true, "round-prep", Some(&rp_state), None);
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
}
