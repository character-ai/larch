use std::{collections::BTreeMap, error::Error, fmt};

/// A complete in-memory HTTP response for an injected client or loopback stub.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HttpResponse {
    status: u16,
    headers: BTreeMap<String, String>,
    body: Vec<u8>,
}

impl HttpResponse {
    #[must_use]
    pub const fn status(&self) -> u16 {
        self.status
    }

    #[must_use]
    pub const fn headers(&self) -> &BTreeMap<String, String> {
        &self.headers
    }

    #[must_use]
    pub fn body(&self) -> &[u8] {
        &self.body
    }
}

/// Builder for deterministic HTTP response fixtures.
#[derive(Clone, Debug)]
pub struct HttpResponseBuilder {
    status: u16,
    headers: BTreeMap<String, String>,
    body: Vec<u8>,
}

impl HttpResponseBuilder {
    #[must_use]
    pub const fn new(status: u16) -> Self {
        Self {
            status,
            headers: BTreeMap::new(),
            body: Vec::new(),
        }
    }

    /// Add or replace a case-normalized header.
    ///
    /// # Errors
    /// Rejects invalid HTTP token names and line-breaking values.
    pub fn header(mut self, name: &str, value: &str) -> Result<Self, HttpResponseError> {
        if !valid_header_name(name) {
            return Err(HttpResponseError::InvalidHeaderName);
        }
        if value.contains(['\r', '\n']) {
            return Err(HttpResponseError::InvalidHeaderValue);
        }
        self.headers
            .insert(name.to_ascii_lowercase(), value.to_owned());
        Ok(self)
    }

    /// Set raw response body bytes.
    #[must_use]
    pub fn body(mut self, body: impl Into<Vec<u8>>) -> Self {
        self.body = body.into();
        self
    }

    /// Validate and build the response.
    ///
    /// # Errors
    /// Rejects status codes outside the HTTP three-digit range.
    pub fn build(self) -> Result<HttpResponse, HttpResponseError> {
        if !(100..=599).contains(&self.status) {
            return Err(HttpResponseError::InvalidStatus);
        }
        Ok(HttpResponse {
            status: self.status,
            headers: self.headers,
            body: self.body,
        })
    }
}

fn valid_header_name(name: &str) -> bool {
    !name.is_empty()
        && name.bytes().all(|byte| {
            byte.is_ascii_alphanumeric()
                || matches!(
                    byte,
                    b'!' | b'#'
                        | b'$'
                        | b'%'
                        | b'&'
                        | b'\''
                        | b'*'
                        | b'+'
                        | b'-'
                        | b'.'
                        | b'^'
                        | b'_'
                        | b'`'
                        | b'|'
                        | b'~'
                )
        })
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum HttpResponseError {
    InvalidStatus,
    InvalidHeaderName,
    InvalidHeaderValue,
}

impl fmt::Display for HttpResponseError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::InvalidStatus => "HTTP fixture status must be between 100 and 599",
            Self::InvalidHeaderName => "HTTP fixture header name is invalid",
            Self::InvalidHeaderValue => "HTTP fixture header value contains a line break",
        })
    }
}

impl Error for HttpResponseError {}

#[cfg(test)]
mod tests {
    use super::{HttpResponseBuilder, HttpResponseError};

    #[test]
    fn response_builder_normalizes_headers_and_preserves_body_bytes() {
        let response = HttpResponseBuilder::new(429)
            .header("Retry-After", "3")
            .expect("valid header")
            .body(vec![0, 255])
            .build()
            .expect("valid response");

        assert_eq!(response.status(), 429);
        assert_eq!(response.headers()["retry-after"], "3");
        assert_eq!(response.body(), [0, 255]);
    }

    #[test]
    fn response_builder_rejects_forged_headers_and_invalid_status() {
        assert_eq!(
            HttpResponseBuilder::new(200)
                .header("X-Test", "ok\r\nforged: yes")
                .expect_err("line break must fail"),
            HttpResponseError::InvalidHeaderValue
        );
        assert_eq!(
            HttpResponseBuilder::new(99)
                .build()
                .expect_err("invalid status must fail"),
            HttpResponseError::InvalidStatus
        );
    }
}
