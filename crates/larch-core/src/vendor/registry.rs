//! Vendor descriptor registry and capability validation.

use super::{VendorDescriptor, VendorFamilyHooks};
use crate::VendorProgram;
use std::{collections::BTreeMap, error::Error, fmt};

/// Capabilities every vendor descriptor must declare.
pub const REQUIRED_CAPABILITIES: &[&str] = &[
    "argv",
    "model_extraction",
    "execution",
    "retry",
    "timing",
    "quota_mirroring",
    "usage_recording",
    "postprocessing",
    "cap_hit_artifact",
    "completion_promotion",
];

const CODEX_PROFILES: &[&str] = &["read-only", "workspace-write"];
const CURSOR_PROFILES: &[&str] = &[
    "review-ask",
    "ci-write",
    "implement-write",
    "negotiation-write",
    "lint-fix-write",
];
const CLAUDE_PROFILES: &[&str] = &[
    "review-subprocess",
    "review-subprocess-base",
    "drafter-read",
    "workspace-write",
];

/// Descriptor validation failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VendorDescriptorError {
    kind: VendorDescriptorErrorKind,
    detail: String,
}

impl VendorDescriptorError {
    fn new(kind: VendorDescriptorErrorKind, detail: impl Into<String>) -> Self {
        Self {
            kind,
            detail: detail.into(),
        }
    }

    /// Stable failure category.
    #[must_use]
    pub const fn kind(&self) -> VendorDescriptorErrorKind {
        self.kind
    }
}

/// Categories of descriptor or registry rejection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VendorDescriptorErrorKind {
    /// Empty vendor key.
    EmptyKey,
    /// Missing one or more required capabilities.
    MissingCapabilities,
    /// No argv profiles declared.
    EmptyProfiles,
    /// Duplicate registry key.
    DuplicateKey,
}

impl fmt::Display for VendorDescriptorError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.detail)
    }
}

impl Error for VendorDescriptorError {}

fn required_capability_set() -> std::collections::BTreeSet<&'static str> {
    REQUIRED_CAPABILITIES.iter().copied().collect()
}

fn profile_set(profiles: &[&'static str]) -> std::collections::BTreeSet<&'static str> {
    profiles.iter().copied().collect()
}

fn validate_descriptor(
    descriptor: VendorDescriptor,
) -> Result<VendorDescriptor, VendorDescriptorError> {
    if descriptor.key().is_empty() {
        return Err(VendorDescriptorError::new(
            VendorDescriptorErrorKind::EmptyKey,
            "vendor descriptor key must be non-empty",
        ));
    }
    let missing: Vec<&'static str> = REQUIRED_CAPABILITIES
        .iter()
        .copied()
        .filter(|capability| !descriptor.capabilities().contains(capability))
        .collect();
    if !missing.is_empty() {
        return Err(VendorDescriptorError::new(
            VendorDescriptorErrorKind::MissingCapabilities,
            format!(
                "vendor {:?} missing capabilities: {missing:?}",
                descriptor.key()
            ),
        ));
    }
    if descriptor.argv_profiles().is_empty() {
        return Err(VendorDescriptorError::new(
            VendorDescriptorErrorKind::EmptyProfiles,
            format!("vendor {:?} has no argv profiles", descriptor.key()),
        ));
    }
    Ok(descriptor)
}

/// Register descriptors; fail loudly on duplicate keys or missing capabilities.
///
/// # Errors
/// Rejects empty keys, missing capabilities, empty profile sets, and duplicates.
pub fn build_vendor_registry(
    descriptors: impl IntoIterator<Item = VendorDescriptor>,
) -> Result<BTreeMap<&'static str, VendorDescriptor>, VendorDescriptorError> {
    let mut registry = BTreeMap::new();
    for descriptor in descriptors {
        let validated = validate_descriptor(descriptor)?;
        if registry.contains_key(validated.key()) {
            return Err(VendorDescriptorError::new(
                VendorDescriptorErrorKind::DuplicateKey,
                format!("duplicate vendor key: {:?}", validated.key()),
            ));
        }
        registry.insert(validated.key(), validated);
    }
    Ok(registry)
}

fn built_in(
    key: &'static str,
    program: VendorProgram,
    profiles: &[&'static str],
) -> VendorDescriptor {
    validate_descriptor(VendorDescriptor::new(
        key,
        program,
        required_capability_set(),
        profile_set(profiles),
        VendorFamilyHooks,
    ))
    .expect("built-in vendor descriptor must validate")
}

/// Codex family descriptor.
pub static CODEX_DESCRIPTOR: std::sync::LazyLock<VendorDescriptor> =
    std::sync::LazyLock::new(|| built_in("codex", VendorProgram::Codex, CODEX_PROFILES));

/// Cursor family descriptor.
pub static CURSOR_DESCRIPTOR: std::sync::LazyLock<VendorDescriptor> =
    std::sync::LazyLock::new(|| built_in("cursor", VendorProgram::Cursor, CURSOR_PROFILES));

/// Claude family descriptor.
pub static CLAUDE_DESCRIPTOR: std::sync::LazyLock<VendorDescriptor> =
    std::sync::LazyLock::new(|| built_in("claude", VendorProgram::Claude, CLAUDE_PROFILES));

/// Validated built-in vendor descriptor registry.
pub static VENDOR_DESCRIPTORS: std::sync::LazyLock<BTreeMap<&'static str, VendorDescriptor>> =
    std::sync::LazyLock::new(|| {
        build_vendor_registry([
            CODEX_DESCRIPTOR.clone(),
            CURSOR_DESCRIPTOR.clone(),
            CLAUDE_DESCRIPTOR.clone(),
        ])
        .expect("built-in vendor registry must validate")
    });
