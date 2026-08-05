//! Shared byte, path, and redaction helpers for semantic snapshot fixtures.

use std::{
    fs, io,
    path::{Path, PathBuf},
};

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;

/// Locate `needle` in `haystack`.
#[must_use]
pub fn find_bytes(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack
        .windows(needle.len())
        .position(|window| window == needle)
}

/// Return whether `haystack` contains `needle`.
#[must_use]
pub fn contains(haystack: &[u8], needle: &[u8]) -> bool {
    find_bytes(haystack, needle).is_some()
}

/// Replace every occurrence of `needle` with `replacement`.
#[must_use]
pub fn replace_all(input: &[u8], needle: &[u8], replacement: &[u8]) -> Vec<u8> {
    if needle.is_empty() {
        return input.to_vec();
    }
    let mut output = Vec::with_capacity(input.len());
    let mut remaining = input;
    while let Some(index) = find_bytes(remaining, needle) {
        output.extend_from_slice(&remaining[..index]);
        output.extend_from_slice(replacement);
        remaining = &remaining[index + needle.len()..];
    }
    output.extend_from_slice(remaining);
    output
}

/// Redact `user:password@` authority segments in URLs.
#[must_use]
pub fn redact_url_userinfo(input: &[u8]) -> Vec<u8> {
    let Some(scheme) = find_bytes(input, b"://") else {
        return input.to_vec();
    };
    let authority = scheme + 3;
    let Some(at_relative) = input[authority..].iter().position(|byte| *byte == b'@') else {
        return input.to_vec();
    };
    let at = authority + at_relative;
    if !input[authority..at].contains(&b':') {
        return input.to_vec();
    }
    let mut output = input[..authority].to_vec();
    output.extend_from_slice(b"<REDACTED>@");
    output.extend_from_slice(&input[at + 1..]);
    output
}

/// Redact whole lines that match any secret needle, then redact URL userinfo.
#[must_use]
pub fn redact_matching_lines(input: &[u8], needles: &[&[u8]]) -> Vec<u8> {
    let mut output = Vec::with_capacity(input.len());
    for line in input.split_inclusive(|byte| *byte == b'\n' || *byte == 0) {
        let lowercase = line.to_ascii_lowercase();
        if needles.iter().any(|needle| contains(&lowercase, needle)) {
            output.extend_from_slice(b"<REDACTED>");
            if let Some(delimiter) = line.last().filter(|byte| **byte == b'\n' || **byte == 0) {
                output.push(*delimiter);
            }
        } else {
            output.extend_from_slice(&redact_url_userinfo(line));
        }
    }
    output
}

/// Encode bytes as lowercase hex.
#[must_use]
pub fn hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        output.push(char::from(DIGITS[usize::from(byte >> 4)]));
        output.push(char::from(DIGITS[usize::from(byte & 0x0f)]));
    }
    output
}

/// FNV-1a 64-bit checksum.
#[must_use]
pub const fn fnv1a(bytes: &[u8]) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    let mut index = 0;
    while index < bytes.len() {
        hash ^= bytes[index] as u64;
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        index += 1;
    }
    hash
}

/// Platform path bytes.
#[must_use]
pub fn path_bytes(path: &Path) -> Vec<u8> {
    path.as_os_str().as_encoded_bytes().to_vec()
}

/// Permission bits for snapshot entries.
#[must_use]
pub fn file_mode(metadata: &fs::Metadata) -> u32 {
    #[cfg(unix)]
    {
        metadata.permissions().mode() & 0o7777
    }
    #[cfg(not(unix))]
    {
        if metadata.is_dir() { 0o755 } else { 0o644 }
    }
}

/// Children of `path` sorted by path bytes.
///
/// # Errors
/// Returns filesystem errors while reading the directory.
pub fn sorted_children(path: &Path) -> io::Result<Vec<PathBuf>> {
    let mut children = fs::read_dir(path)?
        .map(|entry| entry.map(|value| value.path()))
        .collect::<io::Result<Vec<_>>>()?;
    children.sort_by_key(|left| path_bytes(left));
    Ok(children)
}
