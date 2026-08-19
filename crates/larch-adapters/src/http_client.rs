//! Shared outbound HTTP helpers confined to the adapter layer.

use std::time::Duration;

use larch_core::{ConnectivityProbe, ConnectivityProbeFuture, ConnectivityStatus};
use reqwest::{Client as AsyncClient, blocking::Client as BlockingClient};

/// Default timeout for outbound webhook POSTs.
const WEBHOOK_TIMEOUT: Duration = Duration::from_secs(10);
const CONNECTIVITY_REQUEST_TIMEOUT: Duration = Duration::from_secs(15);
const CONNECTIVITY_CONNECT_TIMEOUT: Duration = Duration::from_secs(10);
const CONNECTIVITY_ENDPOINTS: [&str; 2] = ["https://api.anthropic.com/", "https://api.github.com/"];
const CONNECTIVITY_USER_AGENT: &str = "larch-connectivity-probe";

/// Errors from the shared HTTP client. Messages must not embed secrets or URLs
/// the caller intends to keep private; callers still scrub before emission.
#[derive(Debug)]
pub struct HttpClientError {
    message: String,
}

impl HttpClientError {
    /// Return the operator-facing diagnostic.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.message
    }
}

impl std::fmt::Display for HttpClientError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl std::error::Error for HttpClientError {}

/// POST one JSON body to an absolute URL with a fixed timeout.
///
/// # Errors
///
/// Returns [`HttpClientError`] when the client cannot be built, the request
/// fails, or the response status is not success. Callers must scrub secrets
/// from [`HttpClientError::as_str`] before emitting diagnostics.
pub fn post_json(url: &str, body: &[u8]) -> Result<(), HttpClientError> {
    let client = BlockingClient::builder()
        .timeout(WEBHOOK_TIMEOUT)
        .build()
        .map_err(|error| HttpClientError {
            message: format!("http client build failed: {error}"),
        })?;
    let response = client
        .post(url)
        .header(reqwest::header::CONTENT_TYPE, "application/json")
        .body(body.to_vec())
        .send()
        .map_err(|error| HttpClientError {
            message: format!("http post failed: {error}"),
        })?;
    if !response.status().is_success() {
        return Err(HttpClientError {
            message: format!("http post returned status {}", response.status().as_u16()),
        });
    }
    Ok(())
}

/// Fixed, credential-free availability probe for workflow service endpoints.
pub struct FixedConnectivityProbe {
    client: AsyncClient,
    force_offline: bool,
}

impl FixedConnectivityProbe {
    /// Build the fixed HTTPS probe. `force_offline` is reserved for the
    /// environment-gated fault-injection path composed by the CLI.
    ///
    /// # Errors
    ///
    /// Returns a fixed diagnostic if the HTTP client cannot be constructed.
    pub fn new(force_offline: bool) -> Result<Self, HttpClientError> {
        let client = AsyncClient::builder()
            .redirect(reqwest::redirect::Policy::none())
            .connect_timeout(CONNECTIVITY_CONNECT_TIMEOUT)
            .timeout(CONNECTIVITY_REQUEST_TIMEOUT)
            .user_agent(CONNECTIVITY_USER_AGENT)
            .build()
            .map_err(|_error| HttpClientError {
                message: "connectivity probe client build failed".to_owned(),
            })?;
        Ok(Self {
            client,
            force_offline,
        })
    }
}

impl ConnectivityProbe for FixedConnectivityProbe {
    fn probe(&self, timeout: Duration) -> ConnectivityProbeFuture<'_> {
        Box::pin(async move {
            if self.force_offline {
                return ConnectivityStatus::Offline;
            }
            let requests = async {
                for endpoint in CONNECTIVITY_ENDPOINTS {
                    if self.client.head(endpoint).send().await.is_err() {
                        return ConnectivityStatus::Offline;
                    }
                }
                ConnectivityStatus::Online
            };
            tokio::time::timeout(timeout, requests)
                .await
                .unwrap_or(ConnectivityStatus::Offline)
        })
    }
}

#[cfg(test)]
mod tests {
    use super::{FixedConnectivityProbe, post_json};
    use larch_core::{ConnectivityProbe, ConnectivityStatus};
    use std::{
        io::{Read as _, Write as _},
        net::TcpListener,
        sync::mpsc,
        thread,
        time::Duration,
    };

    #[test]
    fn post_json_accepts_2xx_and_rejects_error_status() {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind");
        let addr = listener.local_addr().expect("addr");
        let (tx, rx) = mpsc::channel();
        thread::spawn(move || {
            for status in ["200 OK", "500 Internal Server Error"] {
                let (mut stream, _) = listener.accept().expect("accept");
                let mut buf = [0_u8; 2048];
                let _ = stream.read(&mut buf);
                let response = format!("HTTP/1.1 {status}\r\nContent-Length: 0\r\n\r\n");
                let _ = stream.write_all(response.as_bytes());
                let _ = tx.send(status);
            }
        });
        let url = format!("http://{addr}/hook");
        post_json(&url, b"{\"ok\":true}").expect("2xx");
        assert_eq!(
            rx.recv_timeout(Duration::from_secs(2)).expect("first"),
            "200 OK"
        );
        let error = post_json(&url, b"{}").expect_err("5xx");
        assert!(error.as_str().contains("500"));
        assert!(error.to_string().contains("500"));
        assert_eq!(
            rx.recv_timeout(Duration::from_secs(2)).expect("second"),
            "500 Internal Server Error"
        );
    }

    #[test]
    fn post_json_reports_connection_failures() {
        let error = post_json("http://127.0.0.1:1/no-listener", b"{}").expect_err("connect");
        assert!(error.as_str().contains("http post failed"));
        let _: &dyn std::error::Error = &error;
    }

    #[test]
    fn endpoints_are_fixed_and_forced_offline_never_needs_network_access() {
        assert_eq!(
            super::CONNECTIVITY_ENDPOINTS,
            ["https://api.anthropic.com/", "https://api.github.com/"]
        );
        let runtime = crate::runtime::LarchRuntime::current_thread().expect("test runtime");
        let probe = FixedConnectivityProbe::new(true).expect("probe client");
        let status = runtime.block_on(probe.probe(Duration::from_secs(1)));

        assert_eq!(status, ConnectivityStatus::Offline);
    }
}
