//! Google Cloud Storage adapter using hardened ADC and the official client.

use std::path::Path;

use google_cloud_storage::client::{Storage, StorageControl};
use larch_core::{
    ObjectPage, ObjectStore, ObjectStoreError, ObjectStoreErrorKind, ObjectStoreFuture,
    RemoteObject,
};
use tokio::io::AsyncWriteExt as _;

use crate::google_auth::GoogleAdc;

const STORAGE_SCOPE: &str = "https://www.googleapis.com/auth/devstorage.read_write";

#[derive(Clone)]
pub struct GoogleCloudStorage {
    data: Storage,
    control: StorageControl,
}

impl GoogleCloudStorage {
    /// Build the official clients through larch's validated ADC boundary.
    ///
    /// # Errors
    ///
    /// Returns a credential-free authentication error when ADC or client
    /// construction fails.
    pub async fn new() -> Result<Self, ObjectStoreError> {
        let adc = GoogleAdc::load(&[STORAGE_SCOPE]).map_err(|_error| authentication_error())?;
        let credentials = adc.credentials().clone();
        let data = Storage::builder()
            .with_credentials(credentials.clone())
            .build()
            .await
            .map_err(|_error| authentication_error())?;
        let control = StorageControl::builder()
            .with_credentials(credentials)
            .build()
            .await
            .map_err(|_error| authentication_error())?;
        Ok(Self { data, control })
    }
}

impl ObjectStore for GoogleCloudStorage {
    fn preflight_bucket<'a>(&'a self, bucket: &'a str) -> ObjectStoreFuture<'a, ()> {
        Box::pin(async move {
            self.control
                .list_objects()
                .set_parent(bucket_name(bucket))
                .set_page_size(1)
                .send()
                .await
                .map(|_response| ())
                .map_err(|error| classify_error(&error))
        })
    }

    fn list_page<'a>(
        &'a self,
        bucket: &'a str,
        prefix: &'a str,
        page_token: Option<&'a str>,
    ) -> ObjectStoreFuture<'a, ObjectPage> {
        Box::pin(async move {
            let mut request = self
                .control
                .list_objects()
                .set_parent(bucket_name(bucket))
                .set_prefix(prefix);
            if let Some(token) = page_token {
                request = request.set_page_token(token);
            }
            let response = request
                .send()
                .await
                .map_err(|error| classify_error(&error))?;
            let objects = response
                .objects
                .into_iter()
                .map(remote_object)
                .collect::<Result<Vec<_>, _>>()?;
            Ok(ObjectPage {
                objects,
                next_page_token: nonempty(response.next_page_token),
            })
        })
    }

    fn upload_create<'a>(
        &'a self,
        bucket: &'a str,
        key: &'a str,
        source: &'a Path,
    ) -> ObjectStoreFuture<'a, RemoteObject> {
        Box::pin(async move {
            let file = tokio::fs::File::open(source)
                .await
                .map_err(|_error| local_io_error())?;
            let object = Box::pin(
                self.data
                    .write_object(bucket_name(bucket), key, file)
                    .set_if_generation_match(0)
                    .send_unbuffered(),
            )
            .await
            .map_err(|error| classify_error(&error))?;
            remote_object(object)
        })
    }

    fn download<'a>(
        &'a self,
        bucket: &'a str,
        key: &'a str,
        destination: &'a Path,
    ) -> ObjectStoreFuture<'a, ()> {
        Box::pin(async move {
            let mut response = self
                .data
                .read_object(bucket_name(bucket), key)
                .send()
                .await
                .map_err(|error| classify_error(&error))?;
            let mut output = tokio::fs::File::create(destination)
                .await
                .map_err(|_error| local_io_error())?;
            while let Some(chunk) = response
                .next()
                .await
                .transpose()
                .map_err(|error| classify_error(&error))?
            {
                output
                    .write_all(&chunk)
                    .await
                    .map_err(|_error| local_io_error())?;
            }
            output.flush().await.map_err(|_error| local_io_error())
        })
    }

    fn metadata<'a>(
        &'a self,
        bucket: &'a str,
        key: &'a str,
    ) -> ObjectStoreFuture<'a, RemoteObject> {
        Box::pin(async move {
            let object = self
                .control
                .get_object()
                .set_bucket(bucket_name(bucket))
                .set_object(key)
                .send()
                .await
                .map_err(|error| classify_error(&error))?;
            remote_object(object)
        })
    }
}

fn bucket_name(bucket: &str) -> String {
    format!("projects/_/buckets/{bucket}")
}

fn remote_object(
    object: google_cloud_storage::model::Object,
) -> Result<RemoteObject, ObjectStoreError> {
    let size = u64::try_from(object.size).map_err(|_error| ObjectStoreError::InvalidResponse)?;
    Ok(RemoteObject {
        key: object.name,
        size,
        etag: nonempty(object.etag),
        version: (object.generation != 0).then(|| object.generation.to_string()),
    })
}

fn nonempty(value: String) -> Option<String> {
    (!value.is_empty()).then_some(value)
}

fn classify_error(error: &google_cloud_storage::Error) -> ObjectStoreError {
    match error.http_status_code() {
        Some(401 | 403) => ObjectStoreErrorKind::Authentication,
        Some(404) => ObjectStoreErrorKind::NotFound,
        Some(409 | 412) => ObjectStoreErrorKind::AlreadyExists,
        _ => ObjectStoreErrorKind::Transport,
    }
}

const fn authentication_error() -> ObjectStoreError {
    ObjectStoreError::Authentication
}

const fn local_io_error() -> ObjectStoreError {
    ObjectStoreError::LocalIo
}
