use std::{
    collections::BTreeMap,
    ffi::{OsStr, OsString},
};

use crate::TestWorkspace;

/// A complete child environment that never mutates the test process.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct TestEnvironment {
    values: BTreeMap<OsString, OsString>,
}

impl TestEnvironment {
    /// Build a minimal offline environment rooted in an owned workspace.
    ///
    /// # Errors
    /// Returns fixture-path creation errors.
    pub fn isolated(workspace: &TestWorkspace) -> std::io::Result<Self> {
        let home = workspace.create_dir("home")?;
        let temp = workspace.create_dir("tmp")?;
        let bin = workspace.create_dir("bin")?;
        Ok(Self::default()
            .set("HOME", home)
            .set("TMPDIR", &temp)
            .set("TEMP", &temp)
            .set("TMP", temp)
            .set("PATH", bin)
            .set("LANG", "C")
            .set("NO_PROXY", "")
            .set("LARCH_LIVE_SERVICES", "disabled"))
    }

    /// Set or replace one owned value.
    #[must_use]
    pub fn set(mut self, key: impl Into<OsString>, value: impl Into<OsString>) -> Self {
        self.values.insert(key.into(), value.into());
        self
    }

    /// Return one value without consulting the ambient environment.
    #[must_use]
    pub fn get(&self, key: impl AsRef<OsStr>) -> Option<&OsStr> {
        self.values.get(key.as_ref()).map(OsString::as_os_str)
    }

    /// Iterate over the complete environment for `Command::envs` after `env_clear`.
    pub fn iter(&self) -> impl Iterator<Item = (&OsStr, &OsStr)> {
        self.values
            .iter()
            .map(|(key, value)| (key.as_os_str(), value.as_os_str()))
    }
}

#[cfg(test)]
mod tests {
    use super::TestEnvironment;
    use crate::TestWorkspace;

    #[test]
    fn isolated_environment_is_owned_and_credential_free() {
        let workspace = TestWorkspace::new().expect("test workspace");
        let environment = TestEnvironment::isolated(&workspace).expect("test environment");

        assert_eq!(environment.get("LANG"), Some(std::ffi::OsStr::new("C")));
        assert_eq!(environment.get("GH_TOKEN"), None);
        assert!(
            environment
                .get("HOME")
                .is_some_and(|home| workspace.root().join("home") == home)
        );
    }

    #[test]
    fn setting_a_key_replaces_its_prior_value() {
        let environment = TestEnvironment::default()
            .set("FIXTURE", "first")
            .set("FIXTURE", "second");

        assert_eq!(
            environment.iter().collect::<Vec<_>>(),
            [(
                std::ffi::OsStr::new("FIXTURE"),
                std::ffi::OsStr::new("second")
            )]
        );
    }
}
