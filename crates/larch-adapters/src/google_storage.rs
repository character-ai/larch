use crate::google_auth::GoogleAdc;
use google_cloud_storage::client::{Storage, StorageControl};
use larch_core::{ObjectPage, ObjectStore, ObjectStoreError, ObjectStoreFuture, RemoteObject};
use std::path::Path;
use tokio::io::AsyncWriteExt as _;
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
    /// Returns a credential-free authentication error when ADC or client construction fails.
    pub async fn new() -> Result<Self, ObjectStoreError> {
        let adc =
            GoogleAdc::load(&[STORAGE_SCOPE]).map_err(|_error| ObjectStoreError::Authentication)?;
        let credentials = adc.credentials().clone();
        let data = Storage::builder()
            .with_credentials(credentials.clone())
            .build()
            .await
            .map_err(|_error| ObjectStoreError::Authentication)?;
        let control = StorageControl::builder()
            .with_credentials(credentials)
            .build()
            .await
            .map_err(|_error| ObjectStoreError::Authentication)?;
        Ok(Self { data, control })
    }

    #[doc(hidden)]
    #[must_use]
    pub const fn from_clients(data: Storage, control: StorageControl) -> Self {
        Self { data, control }
    }
}
impl ObjectStore for GoogleCloudStorage {
    fn preflight_bucket<'a>(&'a self, bucket: &'a str) -> ObjectStoreFuture<'a, ()> {
        Box::pin(async move {
            transport(
                self.control
                    .list_objects()
                    .set_parent(bucket_name(bucket))
                    .set_page_size(1)
                    .send()
                    .await,
            )
            .map(|_| ())
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
            let response = transport(request.send().await)?;
            Ok(ObjectPage {
                objects: response
                    .objects
                    .into_iter()
                    .map(remote_object)
                    .collect::<Result<_, _>>()?,
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
            let file = local(tokio::fs::File::open(source).await)?;
            let object = transport(
                Box::pin(
                    self.data
                        .write_object(bucket_name(bucket), key, file)
                        .set_if_generation_match(0)
                        .send_unbuffered(),
                )
                .await,
            )?;
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
            let mut response =
                transport(self.data.read_object(bucket_name(bucket), key).send().await)?;
            let mut output = local(tokio::fs::File::create(destination).await)?;
            while let Some(chunk) = transport(response.next().await.transpose())? {
                local(output.write_all(&chunk).await)?;
            }
            local(output.flush().await)
        })
    }
    fn metadata<'a>(
        &'a self,
        bucket: &'a str,
        key: &'a str,
    ) -> ObjectStoreFuture<'a, RemoteObject> {
        Box::pin(async move {
            let object = transport(
                self.control
                    .get_object()
                    .set_bucket(bucket_name(bucket))
                    .set_object(key)
                    .send()
                    .await,
            )?;
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
    Ok(RemoteObject {
        key: object.name,
        size: u64::try_from(object.size).map_err(|_error| ObjectStoreError::InvalidResponse)?,
        etag: nonempty(object.etag),
        version: (object.generation != 0).then(|| object.generation.to_string()),
    })
}
fn nonempty(value: String) -> Option<String> {
    (!value.is_empty()).then_some(value)
}
fn local<T>(result: std::io::Result<T>) -> Result<T, ObjectStoreError> {
    result.map_err(|_error| ObjectStoreError::LocalIo)
}
fn transport<T>(result: google_cloud_storage::Result<T>) -> Result<T, ObjectStoreError> {
    result.map_err(|error| classify_error(&error))
}
fn classify_error(error: &google_cloud_storage::Error) -> ObjectStoreError {
    match error.http_status_code() {
        Some(401 | 403) => ObjectStoreError::Authentication,
        Some(404) => ObjectStoreError::NotFound,
        Some(409 | 412) => ObjectStoreError::AlreadyExists,
        _ => ObjectStoreError::Transport,
    }
}
