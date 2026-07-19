//! Effect-free upgrade state classification.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InstalledVersionState {
    Current,
    Different,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MarketplaceState {
    RuntimeOnly,
    Legacy,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ActiveRootState {
    NonCache,
    CurrentCache,
    OldCache,
}

/// Upgrade path selected from installed metadata and the active plugin root.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum UpgradeDisposition {
    NoOpRepair,
    ActiveOldSession,
    MarketplaceMigration,
    OrdinaryUpgrade,
}

/// Select the observable upgrade path without performing effects.
#[must_use]
pub const fn classify(
    version: InstalledVersionState,
    marketplace: MarketplaceState,
    active_root: ActiveRootState,
) -> UpgradeDisposition {
    match (version, marketplace, active_root) {
        (
            InstalledVersionState::Current,
            MarketplaceState::RuntimeOnly,
            ActiveRootState::NonCache | ActiveRootState::CurrentCache,
        ) => UpgradeDisposition::NoOpRepair,
        (InstalledVersionState::Current, _, ActiveRootState::OldCache) => {
            UpgradeDisposition::ActiveOldSession
        }
        (InstalledVersionState::Current, MarketplaceState::Legacy, _) => {
            UpgradeDisposition::MarketplaceMigration
        }
        (InstalledVersionState::Different, _, _) => UpgradeDisposition::OrdinaryUpgrade,
    }
}

#[cfg(test)]
mod tests {
    use super::{
        ActiveRootState, InstalledVersionState, MarketplaceState, UpgradeDisposition, classify,
    };

    #[test]
    fn classifies_every_upgrade_path() {
        assert_eq!(
            classify(
                InstalledVersionState::Current,
                MarketplaceState::RuntimeOnly,
                ActiveRootState::CurrentCache,
            ),
            UpgradeDisposition::NoOpRepair
        );
        assert_eq!(
            classify(
                InstalledVersionState::Current,
                MarketplaceState::RuntimeOnly,
                ActiveRootState::OldCache,
            ),
            UpgradeDisposition::ActiveOldSession
        );
        assert_eq!(
            classify(
                InstalledVersionState::Current,
                MarketplaceState::Legacy,
                ActiveRootState::CurrentCache,
            ),
            UpgradeDisposition::MarketplaceMigration
        );
        assert_eq!(
            classify(
                InstalledVersionState::Different,
                MarketplaceState::RuntimeOnly,
                ActiveRootState::OldCache,
            ),
            UpgradeDisposition::OrdinaryUpgrade
        );
    }
}
