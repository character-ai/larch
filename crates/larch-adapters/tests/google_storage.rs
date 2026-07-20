use std::{
    io::{Read as _, Write as _},
    net::TcpListener,
    path::Path,
};

use google_cloud_auth::credentials::anonymous::Builder as Anonymous;
use google_cloud_gax::{options::RequestOptions, response::Response};
use google_cloud_storage::{
    client::{Storage, StorageControl},
    model::{GetObjectRequest, ListObjectsRequest, ListObjectsResponse, Object},
    stub::StorageControl as ControlStub,
};
use larch_adapters::google_storage::GoogleCloudStorage;
use larch_core::{ObjectStore, ObjectStoreError};

#[derive(Debug)]
struct Control;

impl ControlStub for Control {
    async fn list_objects(
        &self,
        _request: ListObjectsRequest,
        _options: RequestOptions,
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
        _options: RequestOptions,
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

async fn store() -> GoogleCloudStorage {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind server");
    let endpoint = format!("http://{}", listener.local_addr().expect("address"));
    std::thread::spawn(move || {
        for _ in 0..2 {
            let (mut stream, _) = listener.accept().expect("accept request");
            let mut request = [0_u8; 16_384];
            let size = stream.read(&mut request).expect("read request");
            let download = request[..size].windows(9).any(|text| text == b"alt=media");
            let body = if download {
                "payload"
            } else {
                r#"{"name":"larch/run","size":"7","etag":"tag","generation":"2"}"#
            };
            write!(stream, "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nx-goog-generation: 2\r\nConnection: close\r\n\r\n{body}", body.len()).expect("write response");
        }
    });
    let data = Storage::builder()
        .with_endpoint(endpoint)
        .with_credentials(Anonymous::new().build())
        .build()
        .await
        .expect("data client");
    GoogleCloudStorage::from_clients(data, StorageControl::from_stub(Control))
}

#[tokio::test]
async fn operations_and_failures_preserve_the_neutral_contract() {
    let store = store().await;
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
    assert_eq!(
        store
            .upload_create("bucket", "key", Path::new("missing-source"))
            .await,
        Err(ObjectStoreError::LocalIo)
    );
}
