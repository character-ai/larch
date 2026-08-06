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
