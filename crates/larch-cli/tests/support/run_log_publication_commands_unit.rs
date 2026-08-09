use super::*;
use larch_adapters::run_lifecycle::{CachePublicationStatus, RemotePublicationStatus};
use larch_core::{StorageBase, StorageConfigurationError};
use std::{collections::HashMap, ffi::OsString, fs};
use tempfile::tempdir;
fn arguments(values: &[&str]) -> Vec<OsString> {
    values.iter().map(OsString::from).collect()
}
#[test]
fn parser_and_staging_preparation_fail_closed() {
    let valid = [
        "--repo-root",
        "/repo",
        "--skill",
        "review",
        "--run-id",
        "run",
    ];
    assert!(parse_publish_arguments(&arguments(&valid)).is_ok());
    assert!(parse_publish_arguments(&arguments(&["--unknown"])).is_err());
    let mut conflicting = valid.to_vec();
    conflicting.extend(["--staging-root", "/staging", "--log-root", "/logs"]);
    assert!(parse_publish_arguments(&arguments(&conflicting)).is_err());
    let mut overflow = valid.to_vec();
    overflow.extend(["--pre-scrub-violations", "18446744073709551616"]);
    assert!(parse_publish_arguments(&arguments(&overflow)).is_err());
    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStringExt as _;
        for position in [3, 5] {
            let mut values = arguments(&valid);
            values[position] = OsString::from_vec(vec![0xFF]);
            assert!(parse_publish_arguments(&values).is_err());
        }
    }
    let root = tempdir().expect("temporary root");
    let staging = root.path().join("staging");
    fs::create_dir(&staging).expect("staging");
    fs::write(staging.join("summary.md"), "complete\n").expect("staging file");
    let mut request = PublishArguments {
        repo_root: root.path().to_owned(),
        skill: "review".to_owned(),
        run_id: "run".to_owned(),
        staging_root: Some(staging.clone()),
        log_root: None,
        pre_scrub_violations: 2,
    };
    let prepared =
        prepare_publish_staging(&request, root.path(), &HashMap::new()).expect("staging");
    assert_eq!(prepared, (Some(staging), 2));
    request.staging_root = None;
    request.log_root = Some(root.path().join("missing"));
    assert!(prepare_publish_staging(&request, root.path(), &HashMap::new()).is_err());
    request.log_root = None;
    request.pre_scrub_violations = u64::MAX;
    let prepared =
        prepare_publish_staging(&request, root.path(), &HashMap::new()).expect("empty staging");
    assert_eq!(prepared, (None, u64::MAX));
    let error = PreflightFailure::Configuration(StorageConfigurationError::new("configuration"));
    assert_eq!(preflight_error(&error), "configuration");
}
#[test]
fn result_formatters_cover_success_and_failure_envelopes() {
    let root = tempdir().expect("temporary root");
    let publication = PublicationResult {
        remote_key: "run-logs/review/run.tar.gz".to_owned(),
        archive_sha256: "a".repeat(64),
        cache_dir: root.path().join("cache"),
        remote_status: RemotePublicationStatus::Created,
        cache_status: CachePublicationStatus::Promoted,
    };
    assert!(publish_outcome(Ok(publication), 3).eq(&ExitCode::SUCCESS));
    assert!(publish_outcome(Err("failed".to_owned()), 3).eq(&ExitCode::FAILURE));
    let sync = RepositorySyncResult {
        corpus_root: root.path().join("corpus"),
        inventory_sha256: "a".repeat(64),
        runs: Vec::new(),
    };
    assert!(sync_outcome(Ok(sync)).eq(&ExitCode::SUCCESS));
    assert!(sync_outcome(Err("failed".to_owned())).eq(&ExitCode::FAILURE));
}
#[test]
fn provider_dispatch_rejects_unavailable_and_unsupported_stores() {
    let root = tempdir().expect("temporary root");
    let homes = LifecycleHomes {
        state: root.path().join("state"),
        cache: root.path().join("cache"),
    };
    for scheme in ["invalid", "r2"] {
        let storage = ToolRepositoryStorage::new(StorageBase::new(scheme, "bucket"), "client");
        let request = PublishRunRequest {
            homes: &homes,
            storage: &storage,
            skill: "review",
            run_id: "run",
            staging_root: None,
        };
        assert!(publish_with_store(&request, &HashMap::new()).is_err());
        assert!(sync_with_store(&homes, &storage, &HashMap::new()).is_err());
    }
}
