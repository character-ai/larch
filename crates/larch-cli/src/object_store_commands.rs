use std::{path::PathBuf, process::ExitCode};

use clap::{Args, ValueEnum};
use larch_core::{ObjectStore, ObjectStoreError, ObjectStoreErrorKind, RemoteObject};
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
    #[arg(long, default_value = "")]
    prefix: String,
    #[arg(long, default_value = "")]
    page_token: String,
    #[arg(long, default_value = "")]
    key: String,
    #[arg(long, default_value = "")]
    source: PathBuf,
    #[arg(long, default_value = "")]
    destination: PathBuf,
}

pub fn run(arguments: &GcsArguments) -> ExitCode {
    if !valid_bucket(&arguments.bucket)
        || !valid_object_text(&arguments.prefix, true)
        || !valid_object_text(&arguments.key, true)
        || arguments.page_token.contains(['\n', '\r', '\0'])
        || (matches!(
            arguments.operation,
            GcsOperation::UploadCreate | GcsOperation::Download | GcsOperation::Metadata
        ) && !valid_object_text(&arguments.key, false))
        || (matches!(arguments.operation, GcsOperation::UploadCreate)
            && arguments.source.as_os_str().is_empty())
        || (matches!(arguments.operation, GcsOperation::Download)
            && arguments.destination.as_os_str().is_empty())
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
    let result = match arguments.operation {
        GcsOperation::Preflight => store
            .preflight_bucket(&arguments.bucket)
            .await
            .map(|()| json!({})),
        GcsOperation::List => store
            .list_page(
                &arguments.bucket,
                &arguments.prefix,
                nonempty(&arguments.page_token),
            )
            .await
            .map(|page| {
                json!({
                    "next_page_token": page.next_page_token,
                    "objects": page.objects.iter().map(object_json).collect::<Vec<_>>(),
                })
            }),
        GcsOperation::UploadCreate => store
            .upload_create(&arguments.bucket, &arguments.key, &arguments.source)
            .await
            .map(|object| object_json(&object)),
        GcsOperation::Download => store
            .download(&arguments.bucket, &arguments.key, &arguments.destination)
            .await
            .map(|()| json!({})),
        GcsOperation::Metadata => store
            .metadata(&arguments.bucket, &arguments.key)
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

fn object_json(object: &RemoteObject) -> Value {
    json!({
        "etag": object.etag,
        "key": object.key,
        "size": object.size,
        "version": object.version,
    })
}

fn nonempty(value: &str) -> Option<&str> {
    (!value.is_empty()).then_some(value)
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

fn report_error(error: ObjectStoreError) -> ExitCode {
    let (label, code) = match error {
        ObjectStoreErrorKind::Authentication => ("authentication", 3),
        ObjectStoreErrorKind::AlreadyExists => ("already-exists", 4),
        ObjectStoreErrorKind::NotFound => ("not-found", 5),
        ObjectStoreErrorKind::LocalIo => ("local-io", 6),
        ObjectStoreErrorKind::InvalidResponse => ("invalid-request-or-response", 2),
        ObjectStoreErrorKind::Transport => ("transport", 1),
    };
    eprintln!("GCS object transport failed: {label}");
    ExitCode::from(code)
}
