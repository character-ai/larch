use std::process::Command;

#[test]
fn dispatch_panel_contract() {
    let status = Command::new("bash")
        .arg(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../scripts/test-review-dispatch-panel.sh"
        ))
        .env("LARCH_BINARY", env!("CARGO_BIN_EXE_larch"))
        .status()
        .expect("run dispatch-panel contract");
    assert!(status.success());
}
