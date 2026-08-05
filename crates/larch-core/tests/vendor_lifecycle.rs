use larch_core::{
    CODEX_DESCRIPTOR, CursorStallRecord, LaunchTimingRecord, TimeoutStallRecord, TimingTaskKind,
    VendorCapCheckResult, VendorConfigurationGuard, VendorDescriptor, VendorHookFuture,
    VendorLaunchContext, VendorLaunchError, VendorLaunchOutcome, VendorLaunchRequest,
    VendorLaunchStatus, VendorLifecycleHooks, VendorPostHook, VendorProcessResult, VendorProgram,
    VendorRetryClassification, VendorRetryPolicy, build_record_launch_timing_argv,
    check_token_budget_cap, elapsed_minute_message, render_cursor_stall_json,
    render_timeout_stall_json, run_vendor_launch, run_with_vendor_retries,
};
use std::{
    collections::VecDeque,
    future::Future,
    sync::Mutex,
    task::{Context, Poll, Waker},
    time::Duration,
};

fn block_on<F: Future>(future: F) -> F::Output {
    let waker = Waker::noop();
    let mut context = Context::from_waker(waker);
    let mut future = std::pin::pin!(future);
    match future.as_mut().poll(&mut context) {
        Poll::Ready(value) => value,
        Poll::Pending => panic!("test future unexpectedly yielded"),
    }
}

fn request(cap: &str) -> VendorLaunchRequest {
    let mut request = VendorLaunchRequest::new("/repo", "/tmp/out.txt", "review");
    cap.clone_into(&mut request.token_cap);
    "codex-review".clone_into(&mut request.timing_task_kind);
    request
}

fn result(exit_code: i32, stdout: &str, stderr: &str) -> VendorProcessResult {
    VendorProcessResult {
        exit_code,
        stdout: stdout.to_owned(),
        stderr: stderr.to_owned(),
    }
}

fn ready<'a, T: Send + 'a>(
    value: Result<T, &'static str>,
) -> VendorHookFuture<'a, T, &'static str> {
    Box::pin(std::future::ready(value))
}

struct RecordingHooks {
    events: Mutex<Vec<&'static str>>,
    results: Mutex<VecDeque<VendorProcessResult>>,
    cap_hit: bool,
    preflight: bool,
}

impl RecordingHooks {
    fn new(results: impl IntoIterator<Item = VendorProcessResult>) -> Self {
        Self {
            events: Mutex::new(Vec::new()),
            results: Mutex::new(results.into_iter().collect()),
            cap_hit: false,
            preflight: true,
        }
    }

    fn record(&self, event: &'static str) {
        self.events.lock().expect("events").push(event);
    }

    fn recorded(&self) -> Vec<&'static str> {
        self.events.lock().expect("events").clone()
    }
}

impl VendorLifecycleHooks for RecordingHooks {
    type Error = &'static str;

    fn check_token_budget_cap<'a>(
        &'a self,
        _request: &'a VendorLaunchRequest,
    ) -> VendorHookFuture<'a, VendorCapCheckResult, Self::Error> {
        self.record("cap");
        ready(Ok(VendorCapCheckResult {
            hit: self.cap_hit,
            ..VendorCapCheckResult::default()
        }))
    }

    fn emit_cap_hit_artifact<'a>(
        &'a self,
        _request: &'a VendorLaunchRequest,
        _cap_check: &'a VendorCapCheckResult,
    ) -> VendorHookFuture<'a, (), Self::Error> {
        self.record("cap_artifact");
        ready(Ok(()))
    }

    fn preflight<'a>(
        &'a self,
        _descriptor: &'a VendorDescriptor,
        _request: &'a VendorLaunchRequest,
    ) -> VendorHookFuture<'a, bool, Self::Error> {
        self.record("preflight");
        ready(Ok(self.preflight))
    }

    fn enter_configuration<'a>(
        &'a self,
        _descriptor: &'a VendorDescriptor,
        _request: &'a VendorLaunchRequest,
    ) -> VendorHookFuture<'a, Box<dyn VendorConfigurationGuard>, Self::Error> {
        ready(Ok(Box::new(())))
    }

    fn execute<'a>(
        &'a self,
        _context: VendorLaunchContext<'a>,
    ) -> VendorHookFuture<'a, VendorProcessResult, Self::Error> {
        self.record("execute");
        ready(Ok(self
            .results
            .lock()
            .expect("results")
            .pop_front()
            .expect("scripted result")))
    }

    fn classify_retry(&self, result: &VendorProcessResult) -> VendorRetryClassification {
        VendorRetryClassification {
            auth: result.stderr.contains("auth"),
            transient: result.stderr.contains("transient"),
            empty: result.exit_code == 0 && result.stdout.is_empty(),
        }
    }

    fn retry_delay(&self, _delay: Duration) -> VendorHookFuture<'_, (), Self::Error> {
        self.record("delay");
        ready(Ok(()))
    }

    fn post_execution<'a>(
        &'a self,
        hook: VendorPostHook,
        _context: VendorLaunchContext<'a>,
        _result: &'a VendorProcessResult,
    ) -> VendorHookFuture<'a, (), Self::Error> {
        let event = match hook {
            VendorPostHook::MirrorQuota => "quota",
            VendorPostHook::RecordTiming => "timing",
            VendorPostHook::Postprocess => "postprocess",
            VendorPostHook::RecordUsage => "usage",
            VendorPostHook::PromoteCompletion => "promote",
        };
        self.record(event);
        ready(Ok(()))
    }
}

fn launch(
    hooks: &RecordingHooks,
    cap: &str,
) -> Result<VendorLaunchOutcome, VendorLaunchError<&'static str>> {
    block_on(run_vendor_launch(
        &CODEX_DESCRIPTOR,
        "read-only",
        &request(cap),
        hooks,
        None,
    ))
}

#[test]
fn launch_preserves_cap_to_promotion_order() {
    let hooks = RecordingHooks::new([result(0, "ok", "")]);
    let outcome = launch(&hooks, "10").expect("launch");

    assert_eq!(outcome.status, VendorLaunchStatus::Completed);
    assert_eq!(outcome.argv.first().map(String::as_str), Some("codex"));
    assert_eq!(
        hooks.recorded().join(","),
        "cap,preflight,execute,quota,timing,postprocess,usage,promote"
    );
}

#[test]
fn cap_and_preflight_short_circuit_without_entering_configuration() {
    let mut cap_hooks = RecordingHooks::new([]);
    cap_hooks.cap_hit = true;
    let cap = launch(&cap_hooks, "1").expect("cap outcome");
    assert_eq!(cap.status, VendorLaunchStatus::CapHit);
    assert_eq!(cap_hooks.recorded(), ["cap", "cap_artifact"]);

    let mut preflight_hooks = RecordingHooks::new([]);
    preflight_hooks.preflight = false;
    let refused = launch(&preflight_hooks, "invalid").expect("preflight outcome");
    assert_eq!(refused.status, VendorLaunchStatus::PreflightRefused);
    assert_eq!(preflight_hooks.recorded(), ["preflight"]);
}

#[test]
fn retries_keep_independent_budgets_and_auth_precedence() {
    let success = result(0, "done", "");
    let hooks = RecordingHooks::new([
        result(1, "", "auth transient"),
        result(1, "", "transient"),
        result(0, "", ""),
        success.clone(),
    ]);
    let context_request = request("");
    let argv = vec!["codex".to_owned()];
    let context = VendorLaunchContext {
        descriptor: &CODEX_DESCRIPTOR,
        request: &context_request,
        argv: &argv,
        model: "",
    };

    let result = block_on(run_with_vendor_retries(
        &hooks,
        context,
        VendorRetryPolicy {
            max_auth_retries: 1,
            max_transient_retries: 1,
            max_empty_retries: 1,
            delay: Duration::from_secs(1),
        },
    ))
    .expect("retry result");

    assert_eq!(result, success);
    assert_eq!(
        hooks.recorded(),
        [
            "execute", "delay", "execute", "delay", "execute", "delay", "execute"
        ]
    );
}

#[test]
fn cap_and_timing_argv_preserve_exact_legacy_keys() {
    let checked = check_token_budget_cap(
        "/python",
        "/plugin/python/cli.py",
        "10",
        "codex-review",
        |argv| {
            assert_eq!(
                argv.join(" "),
                "/python /plugin/python/cli.py token check-budget --cap 10 --step codex-review"
            );
            Ok::<_, ()>(result(0, "STATUS=cap_hit TOTAL=99\n", ""))
        },
    )
    .expect("cap check");
    assert!(checked.hit);
    assert_eq!(checked.payload, "STATUS=cap_hit\n");

    let record = LaunchTimingRecord {
        vendor: VendorProgram::Codex,
        task_kind: TimingTaskKind::new("codex-review").expect("known task kind"),
        start_s: 100,
        end_s: 120,
        output: "/tmp/out".to_owned(),
        exit_code: 7,
    };
    assert_eq!(
        build_record_launch_timing_argv("/python", "/plugin/python/cli.py", &record).join(" "),
        "/python /plugin/python/cli.py timing record-vendor-task --vendor codex --task-kind codex-review --start-s 100 --end-s 120 --output /tmp/out --exit-code 7 --status signal"
    );
}

#[test]
fn progress_and_stall_json_preserve_wire_shape_and_redact_transcript() {
    assert_eq!(
        elapsed_minute_message(VendorProgram::Cursor, Duration::from_secs(125), 1),
        Some((2, "⏳ cursor agent: still running (2m elapsed)".to_owned()))
    );
    assert_eq!(
        render_timeout_stall_json(&TimeoutStallRecord {
            tool: "cursor",
            exit_code: 124,
            timeout: 600,
        }),
        "{\"tool\":\"cursor\",\"exit_code\":124,\"timeout\":600}\n"
    );
    let record = CursorStallRecord::new(
        "tree:/repo",
        42,
        Duration::from_secs(91),
        " M src/lib.rs",
        "before\nsk-abcdefghijklmnopqrstuvwxyz0123456789\nafter",
    );
    let value: serde_json::Value =
        serde_json::from_str(&render_cursor_stall_json(&record)).expect("stall JSON");
    assert_eq!(
        value
            .as_object()
            .expect("object")
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>()
            .join(","),
        "capture_phase,channel,git_state,last_transcript_lines,pid,time_since_last_progress,tool"
    );
    assert_eq!(value["capture_phase"], "pre_sigterm");
    assert_eq!(value["time_since_last_progress"], 91);
    assert!(!value.to_string().contains("sk-abcdefghijklmnopqrstuvwxyz"));
}
