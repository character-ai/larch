//! Native AWS S3 and Cloudflare R2 object transport.

use std::{collections::HashMap, fs, future::Future, path::Path, time::Duration};

use aws_config::{BehaviorVersion, ConfigLoader, retry::RetryConfig, timeout::TimeoutConfig};
use aws_runtime::env_config::file::{
    EnvConfigFileKind as ProfileFileKind, EnvConfigFiles as ProfileFiles,
};
use aws_sdk_s3::{
    Client,
    config::{Builder, RequestChecksumCalculation, ResponseChecksumValidation},
    primitives::ByteStream,
};
use larch_core::{
    KvDocument, ObjectPage, ObjectStore, ObjectStoreError, ObjectStoreFuture, ParseOptions,
    RemoteObject, WhitespacePolicy,
};
use tokio::io::AsyncWriteExt as _;

/// Validated Cloudflare R2 endpoint tied to one account identifier.
#[derive(Clone, Debug)]
pub struct R2Endpoint(String);

impl R2Endpoint {
    /// Validate the fixed Cloudflare account endpoint grammar.
    ///
    /// # Errors
    /// Returns an opaque invalid-response error without reflecting credential input.
    pub fn parse(account: &str, endpoint: &str) -> Result<Self, ObjectStoreError> {
        let expected = format!("https://{account}.r2.cloudflarestorage.com");
        let account_is_valid = account.len() == 32
            && account
                .bytes()
                .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'));
        if account_is_valid && (endpoint == expected || endpoint == format!("{expected}/")) {
            Ok(Self(endpoint.to_owned()))
        } else {
            Err(ObjectStoreError::InvalidResponse)
        }
    }
}

/// Official AWS SDK transport configured for either AWS S3 or Cloudflare R2.
#[derive(Clone, Debug)]
pub struct S3Storage {
    client: Client,
}

impl S3Storage {
    /// Load the standard non-process AWS credential and region providers for S3.
    ///
    /// # Errors
    /// Returns an opaque configuration error for an unsafe profile or endpoint override.
    pub async fn s3(environment: &HashMap<String, String>) -> Result<Self, ObjectStoreError> {
        let shared = config_loader(environment)?.load().await;
        Ok(Self {
            client: Client::new(&shared),
        })
    }

    /// Load non-process AWS credentials and bind them to one validated R2 endpoint.
    ///
    /// # Errors
    /// Returns an opaque configuration error for an unsafe profile or endpoint override.
    pub async fn r2(
        endpoint: R2Endpoint,
        environment: &HashMap<String, String>,
    ) -> Result<Self, ObjectStoreError> {
        let shared = config_loader(environment)?.region("auto").load().await;
        let config = Builder::from(&shared)
            .endpoint_url(endpoint.0)
            .force_path_style(true)
            // R2 rejects the optional `x-amz-sdk-checksum-algorithm` header.
            // Existing immutable keys are still downloaded and SHA-256 verified.
            .request_checksum_calculation(RequestChecksumCalculation::WhenRequired)
            .response_checksum_validation(ResponseChecksumValidation::WhenRequired)
            .build();
        Ok(Self {
            client: Client::from_conf(config),
        })
    }
}

fn config_loader(environment: &HashMap<String, String>) -> Result<ConfigLoader, ObjectStoreError> {
    reject_endpoint_overrides(environment)?;
    let profile_files = ProfileFiles::builder()
        .with_contents(
            ProfileFileKind::Config,
            read_hardened_profile(environment, "AWS_CONFIG_FILE", ".aws/config")?,
        )
        .with_contents(
            ProfileFileKind::Credentials,
            read_hardened_profile(
                environment,
                "AWS_SHARED_CREDENTIALS_FILE",
                ".aws/credentials",
            )?,
        )
        .build();
    let timeouts = TimeoutConfig::builder()
        .connect_timeout(Duration::from_secs(5))
        .read_timeout(Duration::from_secs(30))
        .operation_attempt_timeout(Duration::from_secs(120))
        .operation_timeout(Duration::from_secs(300))
        .build();
    Ok(aws_config::defaults(BehaviorVersion::v2026_01_12())
        .profile_files(profile_files)
        .retry_config(RetryConfig::standard().with_max_attempts(3))
        .timeout_config(timeouts))
}

fn reject_endpoint_overrides(
    environment: &HashMap<String, String>,
) -> Result<(), ObjectStoreError> {
    if environment
        .keys()
        .any(|key| key == "AWS_ENDPOINT_URL" || key.starts_with("AWS_ENDPOINT_URL_"))
    {
        return Err(ObjectStoreError::InvalidResponse);
    }
    Ok(())
}

fn read_hardened_profile(
    environment: &HashMap<String, String>,
    override_key: &str,
    default_relative: &str,
) -> Result<String, ObjectStoreError> {
    let explicit = environment
        .get(override_key)
        .filter(|value| !value.is_empty());
    let path = explicit.map_or_else(
        || {
            environment
                .get("HOME")
                .filter(|value| !value.is_empty())
                .map(|home| Path::new(home).join(default_relative))
        },
        |value| Some(Path::new(value).to_path_buf()),
    );
    let Some(path) = path else {
        return Ok(String::new());
    };
    let contents = match fs::read_to_string(path) {
        Ok(contents) => contents,
        Err(error) if explicit.is_none() && error.kind() == std::io::ErrorKind::NotFound => {
            String::new()
        }
        Err(_) => return Err(ObjectStoreError::LocalIo),
    };
    reject_unsafe_profile_keys(&contents)?;
    Ok(contents)
}

fn reject_unsafe_profile_keys(contents: &str) -> Result<(), ObjectStoreError> {
    let document = KvDocument::parse(
        contents,
        ParseOptions {
            key_whitespace: WhitespacePolicy::Trim,
            ..ParseOptions::legacy()
        },
    )
    .map_err(|_| ObjectStoreError::InvalidResponse)?;
    for row in document.rows() {
        let key = row.key();
        if key.eq_ignore_ascii_case("credential_process")
            || key.eq_ignore_ascii_case("endpoint_url")
        {
            return Err(ObjectStoreError::InvalidResponse);
        }
    }
    Ok(())
}

impl ObjectStore for S3Storage {
    fn preflight_prefix<'store>(
        &'store self,
        bucket: &'store str,
        prefix: &'store str,
    ) -> ObjectStoreFuture<'store, ()> {
        boxed_store_future(async move {
            self.client
                .list_objects_v2()
                .bucket(bucket)
                .prefix(prefix)
                .max_keys(1)
                .send()
                .await
                .map_err(|error| classify_sdk_error(&error))?;
            Ok(())
        })
    }

    fn list_page<'store>(
        &'store self,
        bucket: &'store str,
        prefix: &'store str,
        page_token: Option<&'store str>,
    ) -> ObjectStoreFuture<'store, ObjectPage> {
        boxed_store_future(async move {
            let mut request = self.client.list_objects_v2().bucket(bucket).prefix(prefix);
            if let Some(token) = page_token {
                request = request.continuation_token(token);
            }
            let response = request
                .send()
                .await
                .map_err(|error| classify_sdk_error(&error))?;
            let objects = response
                .contents()
                .iter()
                .map(|object| remote_from_object(object, prefix))
                .collect::<Result<_, _>>()?;
            Ok(ObjectPage {
                objects,
                next_page_token: response.next_continuation_token().map(str::to_owned),
            })
        })
    }

    fn upload_create<'store>(
        &'store self,
        bucket: &'store str,
        key: &'store str,
        source: &'store Path,
    ) -> ObjectStoreFuture<'store, RemoteObject> {
        boxed_store_future(async move {
            let size = tokio::fs::metadata(source)
                .await
                .map_err(|_| ObjectStoreError::LocalIo)?
                .len();
            let body = ByteStream::from_path(source)
                .await
                .map_err(|_| ObjectStoreError::LocalIo)?;
            let response = self
                .client
                .put_object()
                .bucket(bucket)
                .key(key)
                .if_none_match("*")
                .body(body)
                .send()
                .await
                .map_err(|error| classify_sdk_error(&error))?;
            Ok(RemoteObject {
                key: key.to_owned(),
                size,
                etag: response.e_tag().map(str::to_owned),
                version: response.version_id().map(str::to_owned),
            })
        })
    }

    fn download<'store>(
        &'store self,
        bucket: &'store str,
        key: &'store str,
        destination: &'store Path,
    ) -> ObjectStoreFuture<'store, ()> {
        boxed_store_future(async move {
            let mut response = self
                .client
                .get_object()
                .bucket(bucket)
                .key(key)
                .send()
                .await
                .map_err(|error| classify_sdk_error(&error))?;
            let mut output = tokio::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(destination)
                .await
                .map_err(|_| ObjectStoreError::LocalIo)?;
            let result = async {
                while let Some(chunk) = response
                    .body
                    .try_next()
                    .await
                    .map_err(|_| ObjectStoreError::Transport)?
                {
                    output
                        .write_all(&chunk)
                        .await
                        .map_err(|_| ObjectStoreError::LocalIo)?;
                }
                output
                    .flush()
                    .await
                    .map_err(|_| ObjectStoreError::LocalIo)?;
                output
                    .sync_all()
                    .await
                    .map_err(|_| ObjectStoreError::LocalIo)
            }
            .await;
            drop(output);
            if result.is_err() {
                let _ = tokio::fs::remove_file(destination).await;
            }
            result
        })
    }

    fn metadata<'store>(
        &'store self,
        bucket: &'store str,
        key: &'store str,
    ) -> ObjectStoreFuture<'store, RemoteObject> {
        boxed_store_future(async move {
            let response = self
                .client
                .head_object()
                .bucket(bucket)
                .key(key)
                .send()
                .await
                .map_err(|error| classify_sdk_error(&error))?;
            Ok(RemoteObject {
                key: key.to_owned(),
                size: response
                    .content_length()
                    .and_then(|value| u64::try_from(value).ok())
                    .ok_or(ObjectStoreError::InvalidResponse)?,
                etag: response.e_tag().map(str::to_owned),
                version: response.version_id().map(str::to_owned),
            })
        })
    }
}

fn boxed_store_future<'a, T>(
    future: impl Future<Output = Result<T, ObjectStoreError>> + Send + 'a,
) -> ObjectStoreFuture<'a, T> {
    Box::pin(future)
}

fn remote_from_object(
    object: &aws_sdk_s3::types::Object,
    prefix: &str,
) -> Result<RemoteObject, ObjectStoreError> {
    let key = object
        .key()
        .filter(|key| !key.is_empty() && key.starts_with(prefix))
        .ok_or(ObjectStoreError::InvalidResponse)?;
    Ok(RemoteObject {
        key: key.to_owned(),
        size: object
            .size()
            .and_then(|value| u64::try_from(value).ok())
            .ok_or(ObjectStoreError::InvalidResponse)?,
        etag: object.e_tag().map(str::to_owned),
        version: None,
    })
}

fn classify_sdk_error<E>(error: &aws_sdk_s3::error::SdkError<E>) -> ObjectStoreError {
    match error
        .raw_response()
        .map(|response| response.status().as_u16())
    {
        Some(401 | 403) => ObjectStoreError::Authentication,
        Some(404) => ObjectStoreError::NotFound,
        Some(409 | 412) => ObjectStoreError::AlreadyExists,
        _ => ObjectStoreError::Transport,
    }
}

#[cfg(test)]
mod tests {
    use std::{
        collections::{HashMap, VecDeque},
        fmt, fs,
        sync::{Arc, Mutex},
    };

    use aws_sdk_s3::{
        Client,
        config::{
            BehaviorVersion, Builder, Credentials, Region, RequestChecksumCalculation,
            ResponseChecksumValidation,
        },
    };
    use aws_smithy_runtime_api::{
        client::{
            connector_metadata::ConnectorMetadata,
            http::{
                HttpClient, HttpConnector, HttpConnectorFuture, HttpConnectorSettings,
                SharedHttpClient, SharedHttpConnector,
            },
            orchestrator::{HttpRequest, HttpResponse},
            runtime_components::RuntimeComponents,
        },
        shared::IntoShared,
    };
    use http::{Response, StatusCode};
    use larch_core::{ObjectStore as _, ObjectStoreError};
    use tempfile::tempdir;

    use super::{
        R2Endpoint, S3Storage, config_loader, read_hardened_profile, reject_endpoint_overrides,
        reject_unsafe_profile_keys,
    };

    const LIST_RESPONSE: &str = concat!(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<ListBucketResult xmlns=\"http://s3.amazonaws.com/doc/2006-03-01/\">",
        "<Name>bucket</Name><Prefix>runs/</Prefix><KeyCount>1</KeyCount>",
        "<MaxKeys>1000</MaxKeys><IsTruncated>true</IsTruncated>",
        "<Contents><Key>runs/one.tar.gz</Key>",
        "<LastModified>2026-08-05T00:00:00.000Z</LastModified>",
        "<ETag>&quot;list-etag&quot;</ETag><Size>7</Size>",
        "<StorageClass>STANDARD</StorageClass></Contents>",
        "<NextContinuationToken>token-2</NextContinuationToken>",
        "</ListBucketResult>",
    );

    fn response(status: StatusCode, body: &str) -> Response<String> {
        Response::builder()
            .status(status)
            .header("content-type", "application/xml")
            .body(body.to_owned())
            .expect("test response is valid")
    }

    #[derive(Clone)]
    struct OfflineHttpClient {
        responses: Arc<Mutex<VecDeque<Response<String>>>>,
        requests: Arc<Mutex<Vec<String>>>,
    }

    impl fmt::Debug for OfflineHttpClient {
        fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
            formatter.debug_struct("OfflineHttpClient").finish()
        }
    }

    impl HttpConnector for OfflineHttpClient {
        fn call(&self, request: HttpRequest) -> HttpConnectorFuture {
            self.requests
                .lock()
                .expect("request log lock is available")
                .push(format!("{} {}", request.method(), request.uri()));
            let response = self
                .responses
                .lock()
                .expect("response queue lock is available")
                .pop_front()
                .expect("one response exists for every request");
            let response: HttpResponse = response
                .map(Into::into)
                .try_into()
                .expect("test response converts to the Smithy HTTP model");
            HttpConnectorFuture::ready(Ok(response))
        }
    }

    impl HttpClient for OfflineHttpClient {
        fn http_connector(
            &self,
            _: &HttpConnectorSettings,
            _: &RuntimeComponents,
        ) -> SharedHttpConnector {
            self.clone().into_shared()
        }

        fn connector_metadata(&self) -> Option<ConnectorMetadata> {
            Some(ConnectorMetadata::new("larch-offline-test", None))
        }
    }

    fn test_storage(responses: Vec<Response<String>>) -> (S3Storage, Arc<Mutex<Vec<String>>>) {
        let responses = Arc::new(Mutex::new(VecDeque::from(responses)));
        let requests = Arc::new(Mutex::new(Vec::new()));
        let http_client: SharedHttpClient = OfflineHttpClient {
            responses,
            requests: Arc::clone(&requests),
        }
        .into_shared();
        let config = Builder::new()
            .behavior_version(BehaviorVersion::v2026_01_12())
            .region(Region::new("us-east-1"))
            .credentials_provider(Credentials::new(
                "test-access",
                "test-secret",
                None,
                None,
                "offline-test",
            ))
            .endpoint_url("https://s3.invalid")
            .force_path_style(true)
            .request_checksum_calculation(RequestChecksumCalculation::WhenRequired)
            .response_checksum_validation(ResponseChecksumValidation::WhenRequired)
            .http_client(http_client)
            .build();
        (
            S3Storage {
                client: Client::from_conf(config),
            },
            requests,
        )
    }

    #[test]
    fn r2_endpoint_is_tied_to_a_lowercase_account_identifier() {
        let account = "0123456789abcdef0123456789abcdef";
        assert!(
            R2Endpoint::parse(
                account,
                "https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com/"
            )
            .is_ok()
        );
        assert!(R2Endpoint::parse(account, "https://example.com").is_err());
        assert!(R2Endpoint::parse(&account.to_uppercase(), "https://example.com").is_err());
    }

    #[test]
    fn profile_cannot_launch_a_process_or_replace_the_provider_endpoint() {
        assert!(
            reject_unsafe_profile_keys("[profile work]\ncredential_process = helper --secret\n")
                .is_err()
        );
        assert!(
            reject_unsafe_profile_keys("[profile work]\n  ENDPOINT_URL = https://example.com\n")
                .is_err()
        );
        assert!(
            reject_unsafe_profile_keys(
                "[profile work]\nrole_arn = arn:aws:iam::123456789012:role/work\n"
            )
            .is_ok()
        );
    }

    #[test]
    fn environment_cannot_replace_the_provider_endpoint() {
        let mut environment = HashMap::new();
        environment.insert(
            "AWS_ENDPOINT_URL_S3".to_owned(),
            "https://example.com".to_owned(),
        );
        assert!(reject_endpoint_overrides(&environment).is_err());
        assert!(reject_endpoint_overrides(&HashMap::new()).is_ok());
    }

    #[test]
    fn profile_loading_is_explicit_bounded_and_process_free() {
        let root = tempdir().expect("temporary profile root is available");
        let profile = root.path().join("config");
        fs::write(&profile, "[default]\nregion = us-east-1\n")
            .expect("profile fixture is writable");
        let mut environment = HashMap::new();
        environment.insert(
            "AWS_CONFIG_FILE".to_owned(),
            profile.to_string_lossy().into_owned(),
        );
        assert_eq!(
            read_hardened_profile(&environment, "AWS_CONFIG_FILE", ".aws/config")
                .expect("safe profile is readable"),
            "[default]\nregion = us-east-1\n"
        );
        assert!(config_loader(&environment).is_ok());

        environment.insert(
            "AWS_CONFIG_FILE".to_owned(),
            root.path().to_string_lossy().into_owned(),
        );
        assert_eq!(
            read_hardened_profile(&environment, "AWS_CONFIG_FILE", ".aws/config"),
            Err(ObjectStoreError::LocalIo)
        );
        assert_eq!(
            read_hardened_profile(&HashMap::new(), "AWS_CONFIG_FILE", ".aws/config"),
            Ok(String::new())
        );
    }

    #[tokio::test]
    async fn official_sdk_transport_covers_the_object_store_contract_offline() {
        let upload = Response::builder()
            .status(StatusCode::OK)
            .header("etag", "upload-etag")
            .header("x-amz-version-id", "upload-version")
            .body(String::new())
            .expect("upload response is valid");
        let download = Response::builder()
            .status(StatusCode::OK)
            .header("content-length", "7")
            .body("payload".to_owned())
            .expect("download response is valid");
        let metadata = Response::builder()
            .status(StatusCode::OK)
            .header("content-length", "7")
            .header("etag", "head-etag")
            .header("x-amz-version-id", "head-version")
            .body(String::new())
            .expect("metadata response is valid");
        let (storage, requests) = test_storage(vec![
            response(StatusCode::OK, LIST_RESPONSE),
            response(StatusCode::OK, LIST_RESPONSE),
            upload,
            download,
            metadata,
        ]);
        storage
            .preflight_prefix("bucket", "runs/")
            .await
            .expect("preflight succeeds");
        let page = storage
            .list_page("bucket", "runs/", Some("token-1"))
            .await
            .expect("listing succeeds");
        assert_eq!(page.next_page_token.as_deref(), Some("token-2"));
        assert_eq!(page.objects[0].key, "runs/one.tar.gz");

        let root = tempdir().expect("temporary object root is available");
        let source = root.path().join("source");
        fs::write(&source, "payload").expect("upload fixture is writable");
        let uploaded = storage
            .upload_create("bucket", "runs/one.tar.gz", &source)
            .await
            .expect("create-only upload succeeds");
        assert_eq!(uploaded.version.as_deref(), Some("upload-version"));
        let destination = root.path().join("destination");
        storage
            .download("bucket", "runs/one.tar.gz", &destination)
            .await
            .expect("download succeeds");
        assert_eq!(
            fs::read(&destination).expect("download is readable"),
            b"payload"
        );
        let head = storage
            .metadata("bucket", "runs/one.tar.gz")
            .await
            .expect("metadata succeeds");
        assert_eq!(head.size, 7);
        assert_eq!(head.etag.as_deref(), Some("head-etag"));

        let requests = requests.lock().expect("request log is readable").clone();
        assert_eq!(requests.len(), 5);
        assert!(requests[1].contains("continuation-token=token-1"));
    }

    #[tokio::test]
    async fn sdk_statuses_map_to_the_neutral_error_contract() {
        let (forbidden, _) = test_storage(vec![response(StatusCode::FORBIDDEN, "")]);
        assert_eq!(
            forbidden.preflight_prefix("bucket", "runs/").await,
            Err(ObjectStoreError::Authentication)
        );
        let (missing, _) = test_storage(vec![response(StatusCode::NOT_FOUND, "")]);
        assert_eq!(
            missing.metadata("bucket", "missing").await,
            Err(ObjectStoreError::NotFound)
        );
        let root = tempdir().expect("temporary object root is available");
        let source = root.path().join("source");
        fs::write(&source, "payload").expect("upload fixture is writable");
        let (exists, _) = test_storage(vec![response(StatusCode::PRECONDITION_FAILED, "")]);
        assert_eq!(
            exists.upload_create("bucket", "existing", &source).await,
            Err(ObjectStoreError::AlreadyExists)
        );
        let (invalid, _) = test_storage(vec![response(StatusCode::BAD_REQUEST, "")]);
        assert_eq!(
            invalid.preflight_prefix("bucket", "runs/").await,
            Err(ObjectStoreError::Transport)
        );
    }

    #[tokio::test]
    async fn unsafe_environment_stops_both_constructors_before_provider_loading() {
        let mut environment = HashMap::new();
        environment.insert(
            "AWS_ENDPOINT_URL".to_owned(),
            "https://example.invalid".to_owned(),
        );
        assert!(S3Storage::s3(&environment).await.is_err());
        let endpoint = R2Endpoint::parse(
            "0123456789abcdef0123456789abcdef",
            "https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com",
        )
        .expect("fixed R2 endpoint is valid");
        assert!(S3Storage::r2(endpoint, &environment).await.is_err());
    }
}
