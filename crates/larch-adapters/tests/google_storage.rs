use google_cloud_gax::{options::RequestOptions as ControlOptions, response::Response};
use google_cloud_storage::{
    client::{Storage, StorageControl},
    model::{GetObjectRequest, ListObjectsRequest, ListObjectsResponse, Object, ReadObjectRequest},
    model_ext::{ObjectHighlights, WriteObjectRequest},
    read_object::ReadObjectResponse,
    request_options::RequestOptions as DataOptions,
    streaming_source::{Seek, StreamingSource},
    stub::{Storage as DataStub, StorageControl as ControlStub},
};
use larch_adapters::google_storage::GoogleCloudStorage;
use larch_core::ObjectStore;

#[derive(Debug)]
struct Control;

#[derive(Debug)]
struct Data;

impl DataStub for Data {
    async fn read_object(
        &self,
        _request: ReadObjectRequest,
        _options: DataOptions,
    ) -> google_cloud_storage::Result<ReadObjectResponse> {
        Ok(ReadObjectResponse::from_source(
            ObjectHighlights::default(),
            "payload",
        ))
    }
    async fn write_object_unbuffered<P>(
        &self,
        _payload: P,
        _request: WriteObjectRequest,
        _options: DataOptions,
    ) -> google_cloud_storage::Result<Object>
    where
        P: StreamingSource + Seek + Send + Sync + 'static,
    {
        Ok(object())
    }
}

impl ControlStub for Control {
    async fn list_objects(
        &self,
        _request: ListObjectsRequest,
        _options: ControlOptions,
    ) -> google_cloud_storage::Result<Response<ListObjectsResponse>> {
        Ok(Response::from(
            ListObjectsResponse::new()
                .set_objects([object()])
                .set_next_page_token("next"),
        ))
    }
    async fn get_object(
        &self,
        _request: GetObjectRequest,
        _options: ControlOptions,
    ) -> google_cloud_storage::Result<Response<Object>> {
        Ok(Response::from(object()))
    }
}

fn object() -> Object {
    Object::new()
        .set_name("larch/run")
        .set_size(7)
        .set_etag("tag")
        .set_generation(2)
}

fn store() -> GoogleCloudStorage<Data> {
    GoogleCloudStorage::from_clients(Storage::from_stub(Data), StorageControl::from_stub(Control))
}

#[tokio::test]
async fn operations_and_failures_preserve_the_neutral_contract() {
    let store = store();
    store.preflight_bucket("bucket").await.expect("preflight");
    let page = store
        .list_page("bucket", "larch/", Some("page"))
        .await
        .expect("list");
    assert_eq!(page.objects[0].key, "larch/run");
    assert_eq!(page.next_page_token.as_deref(), Some("next"));
    let directory = tempfile::tempdir().expect("tempdir");
    let source = directory.path().join("source");
    std::fs::write(&source, "content").expect("source");
    assert_eq!(
        store
            .upload_create("bucket", "larch/run", &source)
            .await
            .expect("upload")
            .size,
        7
    );
    let destination = directory.path().join("destination");
    store
        .download("bucket", "larch/run", &destination)
        .await
        .expect("download");
    assert_eq!(
        std::fs::read_to_string(destination).expect("read"),
        "payload"
    );
    assert_eq!(
        store
            .metadata("bucket", "larch/run")
            .await
            .expect("metadata")
            .etag
            .as_deref(),
        Some("tag")
    );
}
