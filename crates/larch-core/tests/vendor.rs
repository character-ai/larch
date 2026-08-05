use larch_core::{
    CLAUDE_DESCRIPTOR, CODEX_DESCRIPTOR, CURSOR_DESCRIPTOR, ClaudeEnvelopeStatus, CodexEnvAuth,
    REQUIRED_CAPABILITIES, VENDOR_DESCRIPTORS, VendorArgvErrorKind, VendorDescriptor,
    VendorDescriptorErrorKind, VendorFamilyHooks, VendorLaunchRequest, VendorProgram,
    VendorSessionErrorKind, VendorSessionHandle, build_claude_argv, build_codex_argv,
    build_codex_resume_argv, build_codex_session_argv, build_cursor_argv,
    build_cursor_create_chat_argv, build_cursor_resume_argv, build_vendor_registry,
    codex_auth_args, codex_env_auth_from_key, extract_model_from_argv, parse_claude_envelope,
    trust_config_arg,
};
use std::collections::BTreeSet;

fn codex_request() -> VendorLaunchRequest {
    let mut request = VendorLaunchRequest::new("/repo", "/tmp/out.txt", "do the thing");
    "codex-review".clone_into(&mut request.timing_task_kind);
    request
}

fn cursor_request() -> VendorLaunchRequest {
    let mut request = VendorLaunchRequest::new("/ws", "/tmp/out", "review please");
    request.model_args = vec!["--model".to_owned(), "cursor-model".to_owned()];
    "cursor-review".clone_into(&mut request.timing_task_kind);
    request
}

fn claude_request() -> VendorLaunchRequest {
    let mut request = VendorLaunchRequest::new("/repo", "/tmp/out", "prompt on stdin");
    "claude-sonnet-4-6".clone_into(&mut request.model);
    "claude-review".clone_into(&mut request.timing_task_kind);
    request
}

#[test]
fn codex_read_only_zero_add_dirs_argv_prompt() {
    let argv = build_codex_argv("read-only", &codex_request(), CodexEnvAuth::Omit)
        .expect("argv")
        .full_argv();
    assert_eq!(
        argv,
        [
            "codex",
            "exec",
            "--sandbox",
            "read-only",
            "-C",
            "/repo",
            "-c",
            &trust_config_arg("/repo"),
            "--output-last-message",
            "/tmp/out.txt",
            "--json",
            "--",
            "do the thing",
        ]
    );
}

#[test]
fn codex_workspace_write_one_add_dir_with_model() {
    let mut request = codex_request();
    request.add_dirs = vec!["/repo".to_owned()];
    request.model_args = vec![
        "-m".to_owned(),
        "gpt-test".to_owned(),
        "-c".to_owned(),
        "model_reasoning_effort=\"high\"".to_owned(),
    ];
    let argv = build_codex_argv("workspace-write", &request, CodexEnvAuth::Omit)
        .expect("argv")
        .full_argv();
    assert_eq!(
        argv,
        [
            "codex",
            "exec",
            "--sandbox",
            "workspace-write",
            "-C",
            "/repo",
            "--add-dir",
            "/repo",
            "-m",
            "gpt-test",
            "-c",
            "model_reasoning_effort=\"high\"",
            "-c",
            &trust_config_arg("/repo"),
            "--output-last-message",
            "/tmp/out.txt",
            "--json",
            "--",
            "do the thing",
        ]
    );
}

#[test]
fn codex_multiple_add_dirs_preserve_order_and_stdin_prompt() {
    let mut request = codex_request();
    request.add_dirs = vec![
        "/tmp/session".to_owned(),
        "/repo".to_owned(),
        "/extra".to_owned(),
    ];
    let argv = build_codex_argv("workspace-write", &request, CodexEnvAuth::Omit)
        .expect("argv")
        .full_argv();
    assert_eq!(
        &argv[6..12],
        [
            "--add-dir",
            "/tmp/session",
            "--add-dir",
            "/repo",
            "--add-dir",
            "/extra",
        ]
    );
    request.prompt_via_stdin = true;
    let stdin = build_codex_argv("workspace-write", &request, CodexEnvAuth::Omit)
        .expect("argv")
        .full_argv();
    assert_eq!(&stdin[stdin.len() - 2..], ["--", "-"]);
}

#[test]
fn codex_auth_args_are_explicit_and_byte_exact() {
    let auth = codex_auth_args(CodexEnvAuth::Include);
    assert!(!auth.is_empty());
    let argv = build_codex_argv("read-only", &codex_request(), CodexEnvAuth::Include)
        .expect("argv")
        .full_argv();
    let trust_idx = argv.iter().position(|token| token == "-c").expect("trust");
    assert_eq!(&argv[trust_idx + 2..trust_idx + 2 + auth.len()], auth);
    let omitted = build_codex_argv("read-only", &codex_request(), CodexEnvAuth::Omit)
        .expect("argv")
        .full_argv();
    assert!(
        !omitted
            .iter()
            .any(|token| token.contains("openai-larch-env"))
    );
    assert_eq!(
        codex_env_auth_from_key(Some("sk-test")),
        CodexEnvAuth::Include
    );
    assert_eq!(codex_env_auth_from_key(Some("  ")), CodexEnvAuth::Omit);
    assert_eq!(codex_env_auth_from_key(None), CodexEnvAuth::Omit);
}

#[test]
fn cursor_profiles_are_byte_exact() {
    let request = cursor_request();
    let cases: &[(&str, &[&str])] = &[
        (
            "review-ask",
            &[
                "cursor",
                "agent",
                "-p",
                "--trust",
                "--mode",
                "ask",
                "--output-format",
                "json",
                "--model",
                "cursor-model",
                "--workspace",
                "/ws",
                "review please",
            ],
        ),
        (
            "ci-write",
            &[
                "cursor",
                "agent",
                "-p",
                "--force",
                "--trust",
                "--model",
                "cursor-model",
                "--output-format",
                "json",
                "--workspace",
                "/ws",
                "review please",
            ],
        ),
        (
            "implement-write",
            &[
                "cursor",
                "agent",
                "-p",
                "--force",
                "--trust",
                "--output-format",
                "json",
                "--model",
                "cursor-model",
                "--workspace",
                "/ws",
                "review please",
            ],
        ),
        (
            "negotiation-write",
            &[
                "cursor",
                "agent",
                "-p",
                "--force",
                "--trust",
                "--model",
                "cursor-model",
                "--workspace",
                "/ws",
                "review please",
            ],
        ),
        (
            "lint-fix-write",
            &[
                "cursor",
                "agent",
                "-p",
                "--trust",
                "--model",
                "cursor-model",
                "--workspace",
                "/ws",
                "review please",
            ],
        ),
    ];
    for (profile, expected) in cases {
        let argv = build_cursor_argv(profile, &request)
            .unwrap_or_else(|error| panic!("{profile}: {error}"))
            .full_argv();
        assert_eq!(argv, *expected, "{profile}");
        if *profile == "lint-fix-write" {
            assert!(!argv.iter().any(|token| token == "--force"));
        }
    }
}

#[test]
fn claude_profiles_are_byte_exact() {
    let mut review = claude_request();
    "/sandbox".clone_into(&mut review.read_tools_add_dir);
    let base = claude_request();
    let cases: &[(&str, &VendorLaunchRequest, &[&str])] = &[
        (
            "review-subprocess",
            &review,
            &[
                "claude",
                "--print",
                "--output-format",
                "json",
                "--model",
                "claude-sonnet-4-6",
                "--add-dir",
                "/sandbox",
                "--allowedTools",
                "Read",
                "--permission-mode",
                "plan",
            ],
        ),
        (
            "review-subprocess-base",
            &base,
            &[
                "claude",
                "--print",
                "--output-format",
                "json",
                "--model",
                "claude-sonnet-4-6",
            ],
        ),
        (
            "drafter-read",
            &base,
            &[
                "claude",
                "--model",
                "claude-sonnet-4-6",
                "--print",
                "--output-format",
                "json",
                "--add-dir",
                "/repo",
                "--allowedTools",
                "Read,Glob,Grep,LS",
                "--permission-mode",
                "plan",
            ],
        ),
        (
            "workspace-write",
            &base,
            &[
                "claude",
                "-p",
                "--output-format",
                "json",
                "--model",
                "claude-sonnet-4-6",
                "--add-dir",
                "/repo",
                "--allowedTools",
                "Read,Edit,Write",
            ],
        ),
    ];
    for (profile, request, expected) in cases {
        let argv = build_claude_argv(profile, request)
            .unwrap_or_else(|error| panic!("{profile}: {error}"))
            .full_argv();
        assert_eq!(argv, *expected, "{profile}");
    }
}

#[test]
fn unknown_profiles_and_missing_fields_are_rejected() {
    assert_eq!(
        build_codex_argv("nope", &codex_request(), CodexEnvAuth::Omit)
            .expect_err("unknown")
            .kind(),
        VendorArgvErrorKind::UnknownProfile
    );
    assert_eq!(
        build_cursor_argv("nope", &cursor_request())
            .expect_err("unknown")
            .kind(),
        VendorArgvErrorKind::UnknownProfile
    );
    assert_eq!(
        build_claude_argv("nope", &claude_request())
            .expect_err("unknown")
            .kind(),
        VendorArgvErrorKind::UnknownProfile
    );
    assert_eq!(
        build_claude_argv("review-subprocess", &claude_request())
            .expect_err("missing")
            .kind(),
        VendorArgvErrorKind::MissingField
    );
}

#[test]
fn model_extraction_prefers_model_flag() {
    assert_eq!(
        extract_model_from_argv(&[
            "codex".into(),
            "exec".into(),
            "-m".into(),
            "gpt-x".into(),
            "--json".into()
        ]),
        "gpt-x"
    );
    assert_eq!(
        extract_model_from_argv(&[
            "cursor".into(),
            "agent".into(),
            "--model".into(),
            "c-model".into(),
            "-p".into()
        ]),
        "c-model"
    );
    assert_eq!(
        extract_model_from_argv(&["-m".into(), "a".into(), "--model".into(), "b".into()]),
        "b"
    );
    assert_eq!(
        extract_model_from_argv(&["codex".into(), "exec".into(), "--json".into()]),
        ""
    );
    assert_eq!(
        extract_model_from_argv(&["cursor".into(), "agent".into(), "--model".into()]),
        ""
    );
}

#[test]
fn session_create_and_resume_argv_are_byte_exact() {
    assert_eq!(
        build_cursor_create_chat_argv().full_argv(),
        ["cursor", "agent", "create-chat"]
    );
    let cursor = VendorSessionHandle::create("cursor", "chat-abc123").expect("cursor");
    let mut request = VendorLaunchRequest::new("/repo", "/tmp/out.txt", "continue the debate");
    request.model_args = vec!["--model".to_owned(), "cursor-grok-4.5-high".to_owned()];
    assert_eq!(
        build_cursor_resume_argv(&cursor, &request)
            .expect("resume")
            .full_argv(),
        [
            "cursor",
            "agent",
            "-p",
            "--resume",
            "chat-abc123",
            "--mode",
            "plan",
            "--trust",
            "--output-format",
            "json",
            "--model",
            "cursor-grok-4.5-high",
            "--workspace",
            "/repo",
            "continue the debate",
        ]
    );
    let session = build_codex_session_argv(&codex_request()).expect("session");
    assert_eq!(
        session.full_argv(),
        build_codex_argv("read-only", &codex_request(), CodexEnvAuth::Omit)
            .expect("read-only")
            .full_argv()
    );
    let codex = VendorSessionHandle::create("codex", "019fc6b3-e6c4-7892-a97a-c80b30a7f5b0")
        .expect("codex");
    let mut resume_request = VendorLaunchRequest::new("/repo", "/tmp/out.txt", "resume please");
    resume_request.model_args = vec!["-m".to_owned(), "gpt-5.6-sol".to_owned()];
    let resume = build_codex_resume_argv(&codex, &resume_request)
        .expect("resume")
        .full_argv();
    assert_eq!(
        &resume[..4],
        [
            "codex",
            "exec",
            "resume",
            "019fc6b3-e6c4-7892-a97a-c80b30a7f5b0"
        ]
    );
    assert!(
        !resume
            .iter()
            .any(|token| token == "--sandbox" || token == "-C")
    );
    assert!(
        resume
            .iter()
            .any(|token| token == "sandbox_mode=\"read-only\"")
    );
    assert!(
        resume
            .iter()
            .any(|token| token == &trust_config_arg("/repo"))
    );
    assert_eq!(resume.last().map(String::as_str), Some("resume please"));
}

#[test]
fn session_handles_and_wrong_vendor_are_rejected() {
    let cursor = VendorSessionHandle::create("cursor", "chat1").expect("cursor");
    let codex = VendorSessionHandle::create("codex", "019fc6b3-e6c4-7892-a97a-c80b30a7f5b0")
        .expect("codex");
    let request = VendorLaunchRequest::new("/repo", "/tmp/out.txt", "p");
    assert_eq!(
        build_cursor_resume_argv(&codex, &request)
            .expect_err("wrong")
            .kind(),
        VendorArgvErrorKind::WrongVendor
    );
    assert_eq!(
        build_codex_resume_argv(&cursor, &request)
            .expect_err("wrong")
            .kind(),
        VendorArgvErrorKind::WrongVendor
    );
    assert_eq!(
        VendorSessionHandle::create("cursor", "")
            .expect_err("empty")
            .kind(),
        VendorSessionErrorKind::InvalidSessionId
    );
    assert_eq!(
        VendorSessionHandle::create("cursor", "-flaglike")
            .expect_err("flag")
            .kind(),
        VendorSessionErrorKind::InvalidSessionId
    );
    assert_eq!(
        VendorSessionHandle::create("codex", "not-a-uuid")
            .expect_err("uuid")
            .kind(),
        VendorSessionErrorKind::InvalidSessionId
    );
    assert_eq!(
        VendorSessionHandle::create("claude", "x")
            .expect_err("vendor")
            .kind(),
        VendorSessionErrorKind::UnsupportedVendor
    );
}

#[test]
fn descriptors_name_vendor_programs_and_reject_invalid_registry() {
    assert_eq!(CODEX_DESCRIPTOR.program(), VendorProgram::Codex);
    assert_eq!(CURSOR_DESCRIPTOR.program(), VendorProgram::Cursor);
    assert_eq!(CLAUDE_DESCRIPTOR.program(), VendorProgram::Claude);
    assert_eq!(VENDOR_DESCRIPTORS.len(), 3);
    for capability in REQUIRED_CAPABILITIES {
        assert!(CODEX_DESCRIPTOR.capabilities().contains(capability));
    }
    let request = codex_request();
    assert_eq!(
        CODEX_DESCRIPTOR
            .build_argv("read-only", &request)
            .expect("dispatch")
            .full_argv(),
        build_codex_argv("read-only", &request, CodexEnvAuth::Omit)
            .expect("direct")
            .full_argv()
    );
    let invalid = VendorDescriptor::new(
        "",
        VendorProgram::Codex,
        BTreeSet::new(),
        BTreeSet::new(),
        VendorFamilyHooks,
    );
    assert_eq!(
        build_vendor_registry([invalid]).expect_err("empty").kind(),
        VendorDescriptorErrorKind::EmptyKey
    );
    let missing = VendorDescriptor::new(
        "codex",
        VendorProgram::Codex,
        BTreeSet::new(),
        std::iter::once("read-only").collect(),
        VendorFamilyHooks,
    );
    assert_eq!(
        build_vendor_registry([missing]).expect_err("caps").kind(),
        VendorDescriptorErrorKind::MissingCapabilities
    );
    let empty_profiles = VendorDescriptor::new(
        "codex",
        VendorProgram::Codex,
        REQUIRED_CAPABILITIES.iter().copied().collect(),
        BTreeSet::new(),
        VendorFamilyHooks,
    );
    assert_eq!(
        build_vendor_registry([empty_profiles])
            .expect_err("profiles")
            .kind(),
        VendorDescriptorErrorKind::EmptyProfiles
    );
    assert_eq!(
        build_vendor_registry([CODEX_DESCRIPTOR.clone(), CODEX_DESCRIPTOR.clone()])
            .expect_err("dup")
            .kind(),
        VendorDescriptorErrorKind::DuplicateKey
    );
}

#[test]
fn claude_envelope_statuses_match_recorded_fixtures() {
    // Raw stdout texts from crates/larch-test-support/fixtures/vendor/claude-*.json.
    let cases = [
        (
            "{\"result\":\"review ok\",\"is_error\":false,\"usage\":{\"input_tokens\":10,\"output_tokens\":4}}\n",
            ClaudeEnvelopeStatus::Ok,
            Some("review ok"),
        ),
        (
            "{\"result\":\"vendor error\",\"is_error\":true}\n",
            ClaudeEnvelopeStatus::IsError,
            None,
        ),
        (
            "{\"result\":\"\"}\n",
            ClaudeEnvelopeStatus::EmptyResult,
            None,
        ),
        (
            "{\"is_error\":false}\n",
            ClaudeEnvelopeStatus::MissingResult,
            None,
        ),
        (
            "{\"result\":42}\n",
            ClaudeEnvelopeStatus::NonStringResult,
            None,
        ),
        ("{not-json\n", ClaudeEnvelopeStatus::MalformedJson, None),
        ("[\"result\"]\n", ClaudeEnvelopeStatus::NonObject, None),
    ];
    for (raw, expected, text) in cases {
        let parsed = parse_claude_envelope(raw);
        assert_eq!(parsed.status, expected);
        if let Some(expected_text) = text {
            assert_eq!(parsed.text, expected_text);
        }
        if expected == ClaudeEnvelopeStatus::IsError {
            assert!(parsed.is_error);
        }
    }
}

#[test]
fn vendor_argv_exposes_process_arguments_without_executable_path() {
    let argv = build_cursor_create_chat_argv();
    assert_eq!(argv.program(), VendorProgram::Cursor);
    assert_eq!(argv.arguments(), ["agent", "create-chat"]);
    assert_eq!(argv.program().executable(), "cursor");
}
