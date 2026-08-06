//! Shared outbound HTTP helpers confined to the adapter layer.

use std::time::Duration;

use reqwest::blocking::Client;

/// Default timeout for outbound webhook POSTs.
const WEBHOOK_TIMEOUT: Duration = Duration::from_secs(10);

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
    let client = Client::builder()
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

#[cfg(test)]
mod tests {
    use super::post_json;
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
}
