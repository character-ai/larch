use std::{
    path::{Path, PathBuf},
    process::ExitCode,
};

use clap::{Args, ValueEnum};
use larch_core::{ObjectPage, ObjectStore, ObjectStoreError, RemoteObject};
use serde_json::{Value, json};

#[derive(Clone, Copy, Debug, ValueEnum)]
pub enum GcsOperation {
    Preflight,
    List,
    UploadCreate,
    Download,
    Metadata,
}

#[derive(Args)]
pub struct GcsArguments {
    #[arg(long, value_enum)]
    operation: GcsOperation,
    #[arg(long)]
    bucket: String,
    #[arg(long)]
    prefix: Option<String>,
    #[arg(long)]
    page_token: Option<String>,
    #[arg(long)]
    key: Option<String>,
    #[arg(long)]
    source: Option<PathBuf>,
    #[arg(long)]
    destination: Option<PathBuf>,
}

#[must_use]
pub fn run(arguments: &GcsArguments) -> ExitCode {
    if !valid_bucket(&arguments.bucket)
        || !valid_object_text(arguments.prefix.as_deref().unwrap_or(""), true)
        || !valid_object_text(arguments.key.as_deref().unwrap_or(""), true)
        || arguments
            .page_token
            .as_deref()
            .is_some_and(|token| token.contains(['\n', '\r', '\0']))
        || (matches!(
            arguments.operation,
            GcsOperation::UploadCreate | GcsOperation::Download | GcsOperation::Metadata
        ) && !valid_object_text(arguments.key.as_deref().unwrap_or(""), false))
        || (matches!(arguments.operation, GcsOperation::UploadCreate) && arguments.source.is_none())
        || (matches!(arguments.operation, GcsOperation::Download)
            && arguments.destination.is_none())
    {
        eprintln!("GCS object transport rejected invalid arguments");
        return ExitCode::from(2);
    }
    let Ok(runtime) = larch_adapters::runtime::LarchRuntime::new() else {
        eprintln!("GCS object transport could not initialize its runtime");
        return ExitCode::FAILURE;
    };
    runtime.block_on(async {
        let store = match larch_adapters::google_storage::GoogleCloudStorage::new().await {
            Ok(store) => store,
            Err(error) => return report_error(error),
        };
        execute(arguments, &store).await
    })
}

async fn execute(arguments: &GcsArguments, store: &dyn ObjectStore) -> ExitCode {
    let key = arguments.key.as_deref().unwrap_or("");
    let source = arguments.source.as_deref().unwrap_or_else(|| Path::new(""));
    let destination = arguments
        .destination
        .as_deref()
        .unwrap_or_else(|| Path::new(""));
    let result = match arguments.operation {
        GcsOperation::Preflight => store
            .preflight_prefix(&arguments.bucket, arguments.prefix.as_deref().unwrap_or(""))
            .await
            .map(|()| json!({})),
        GcsOperation::List => store
            .list_page(
                &arguments.bucket,
                arguments.prefix.as_deref().unwrap_or(""),
                arguments.page_token.as_deref(),
            )
            .await
            .map(|page| page_json(&page)),
        GcsOperation::UploadCreate => store
            .upload_create(&arguments.bucket, key, source)
            .await
            .map(|object| object_json(&object)),
        GcsOperation::Download => store
            .download(&arguments.bucket, key, destination)
            .await
            .map(|()| json!({})),
        GcsOperation::Metadata => store
            .metadata(&arguments.bucket, key)
            .await
            .map(|object| object_json(&object)),
    };
    match result {
        Ok(value) => {
            println!("{value}");
            ExitCode::SUCCESS
        }
        Err(error) => report_error(error),
    }
}

#[doc(hidden)]
pub async fn exercise(operation: GcsOperation, store: &dyn ObjectStore) -> ExitCode {
    execute(
        &GcsArguments {
            operation,
            bucket: "bucket".into(),
            prefix: Some("larch/".into()),
            page_token: Some("page".into()),
            key: Some("larch/run".into()),
            source: Some("source".into()),
            destination: Some("destination".into()),
        },
        store,
    )
    .await
}

#[doc(hidden)]
#[must_use]
pub fn object_json(object: &RemoteObject) -> Value {
    json!({
        "etag": object.etag,
        "key": object.key,
        "size": object.size,
        "version": object.version,
    })
}

#[doc(hidden)]
#[must_use]
pub fn page_json(page: &ObjectPage) -> Value {
    json!({
        "next_page_token": page.next_page_token,
        "objects": page.objects.iter().map(object_json).collect::<Vec<_>>(),
    })
}

fn valid_bucket(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 222
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"-._".contains(&byte))
}

fn valid_object_text(value: &str, allow_empty: bool) -> bool {
    (allow_empty || !value.is_empty())
        && value.len() <= 1024
        && !value.starts_with('/')
        && !value.bytes().any(|byte| byte < 32 || byte == 127)
}

#[doc(hidden)]
#[must_use]
pub fn report_error(error: ObjectStoreError) -> ExitCode {
    let (label, code) = error_contract(error);
    eprintln!("GCS object transport failed: {label}");
    ExitCode::from(code)
}

#[doc(hidden)]
#[must_use]
pub const fn error_contract(error: ObjectStoreError) -> (&'static str, u8) {
    match error {
        ObjectStoreError::Authentication => ("authentication", 3),
        ObjectStoreError::AlreadyExists => ("already-exists", 4),
        ObjectStoreError::NotFound => ("not-found", 5),
        ObjectStoreError::LocalIo => ("local-io", 6),
        ObjectStoreError::InvalidResponse => ("invalid-request-or-response", 2),
        ObjectStoreError::Transport => ("transport", 1),
    }
}
