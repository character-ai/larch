use std::process::Command;

#[test]
fn plan_review_dispatch_contract() {
    let status = Command::new("bash")
        .arg(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../scripts/test-plan-review-dispatch.sh"
        ))
        .env("LARCH_BINARY", env!("CARGO_BIN_EXE_larch"))
        .status()
        .expect("run plan-review dispatch contract");
    assert!(status.success());
}
