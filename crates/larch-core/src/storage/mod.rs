//! Repository-owned storage configuration and derived tool namespace.
//!
//! Port of Python `larch.report.storage_config`: pure configuration
//! resolution, URI parsing, and identity derivation. Process execution
//! (Git remote discovery, provider preflight) stays in `larch-adapters`
//! and `larch-cli`.

mod config;

pub use config::{
    ENV_LARCH_LOGS_URI, ENV_LARCH_R2_ACCOUNT_ID, ENV_LARCH_R2_ENDPOINT, ENV_LARCH_STORAGE_BASE_URI,
    LARCH_TOOL_NAME, LOCAL_NAMESPACE_DOMAIN, RUN_LOGS_DATA_TYPE, RunLogStorageMode,
    RunLogStorageReason, RunLogStorageResolution, STORAGE_BASE_URI_FIELD, STORAGE_CONFIG_RELPATH,
    STORAGE_URI_SCHEMES, StorageBase, StorageConfigurationError, StoragePreflightError,
    ToolRepositoryStorage, format_preflight_stdout, injected_storage_resolution,
    local_namespace_id, parse_storage_base_uri, parse_tool_repository_uri,
    repository_leaf_from_remote, require_enabled_storage, resolve_run_log_storage,
    validate_client_repo,
};
