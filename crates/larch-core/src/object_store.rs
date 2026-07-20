use std::{future::Future, path::Path, pin::Pin};

/// Credential-free, stable object transport failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ObjectStoreError {
    Authentication,
    AlreadyExists,
    NotFound,
    LocalIo,
    InvalidResponse,
    Transport,
}

/// Provider-neutral remote object metadata.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RemoteObject {
    pub key: String,
    pub size: u64,
    pub etag: Option<String>,
    pub version: Option<String>,
}

/// One explicit page from a provider listing.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ObjectPage {
    pub objects: Vec<RemoteObject>,
    pub next_page_token: Option<String>,
}

pub type ObjectStoreFuture<'a, T> =
    Pin<Box<dyn Future<Output = Result<T, ObjectStoreError>> + Send + 'a>>;

/// Narrow object transport port. Workflow policy remains outside adapters.
pub trait ObjectStore: Send + Sync {
    fn preflight_bucket<'a>(&'a self, bucket: &'a str) -> ObjectStoreFuture<'a, ()>;
    fn list_page<'a>(
        &'a self,
        bucket: &'a str,
        prefix: &'a str,
        page_token: Option<&'a str>,
    ) -> ObjectStoreFuture<'a, ObjectPage>;
    fn upload_create<'a>(
        &'a self,
        bucket: &'a str,
        key: &'a str,
        source: &'a Path,
    ) -> ObjectStoreFuture<'a, RemoteObject>;
    fn download<'a>(
        &'a self,
        bucket: &'a str,
        key: &'a str,
        destination: &'a Path,
    ) -> ObjectStoreFuture<'a, ()>;
    fn metadata<'a>(&'a self, bucket: &'a str, key: &'a str)
    -> ObjectStoreFuture<'a, RemoteObject>;
}
