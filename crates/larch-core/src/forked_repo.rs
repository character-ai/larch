//! Effect-free forked-repository URL and remote-state rules.

/// A recognized GitHub-style URL reduced to host and repository identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NormalizedGitHubUrl {
    pub host: String,
    pub repository: String,
}

/// Raw configuration relevant to classifying one remote.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RemoteDescription {
    pub name: String,
    pub urls: Vec<String>,
    pub push_urls: Vec<String>,
}

/// The only remote layouts setup may safely retain or rewrite.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RemoteClassification {
    AlreadyConfigured,
    OriginUpstreamOnly,
    OriginUpstreamNamedFork(String),
    Ambiguous,
}

/// Normalize the URL shapes accepted by the legacy setup command.
#[must_use]
pub fn normalize_github_url(url: &str) -> Option<NormalizedGitHubUrl> {
    let mut value = url.trim_end_matches('/');
    value = value.strip_suffix(".git").unwrap_or(value);
    let (after, separator) = value
        .strip_prefix("git@")
        .map(|after| (after, ':'))
        .or_else(|| value.strip_prefix("ssh://git@").map(|after| (after, '/')))
        .or_else(|| value.strip_prefix("ssh://").map(|after| (after, '/')))
        .or_else(|| value.strip_prefix("https://").map(|after| (after, '/')))
        .or_else(|| value.strip_prefix("git://").map(|after| (after, '/')))?;
    let (host, rest) = after.split_once(separator)?;
    if !valid_host(host) {
        return None;
    }
    let mut parts = rest.split('/');
    let owner = parts.next()?;
    let repository = parts.next()?;
    if owner.is_empty() || repository.is_empty() {
        return None;
    }
    Some(NormalizedGitHubUrl {
        host: host.to_ascii_lowercase(),
        repository: format!("{owner}/{repository}").to_ascii_lowercase(),
    })
}

fn valid_host(host: &str) -> bool {
    if host.is_empty() || host.contains(['/', '@']) || host.contains("://") {
        return false;
    }
    let (name, port) = host
        .rsplit_once(':')
        .map_or((host, None), |(name, port)| (name, Some(port)));
    !name.is_empty()
        && name
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'-'))
        && port.is_none_or(|value| {
            !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit())
        })
}

/// Classify the configured remotes without performing a network operation.
#[must_use]
pub fn classify_fork_remotes(
    remotes: &[RemoteDescription],
    upstream: &str,
    fork: &str,
    expected_host: &str,
) -> RemoteClassification {
    let mut entries = Vec::new();
    for remote in remotes {
        if remote.urls.len() > 1 || remote.push_urls.len() > 1 {
            return RemoteClassification::Ambiguous;
        }
        let Some(url) = remote.urls.first() else {
            continue;
        };
        let Some(parsed) = normalize_github_url(url) else {
            return RemoteClassification::Ambiguous;
        };
        if !parsed.host.eq_ignore_ascii_case(expected_host)
            || !(parsed.repository.eq_ignore_ascii_case(upstream)
                || parsed.repository.eq_ignore_ascii_case(fork))
        {
            return RemoteClassification::Ambiguous;
        }
        entries.push((remote.name.as_str(), parsed.repository));
    }
    let Some((_, origin)) = entries.iter().find(|(name, _)| *name == "origin") else {
        return RemoteClassification::Ambiguous;
    };
    if entries.len() == 1 && origin.eq_ignore_ascii_case(upstream) {
        return RemoteClassification::OriginUpstreamOnly;
    }
    if entries.len() != 2 {
        return RemoteClassification::Ambiguous;
    }
    if origin.eq_ignore_ascii_case(fork)
        && entries
            .iter()
            .any(|(name, repo)| *name == "upstream" && repo.eq_ignore_ascii_case(upstream))
    {
        return RemoteClassification::AlreadyConfigured;
    }
    if origin.eq_ignore_ascii_case(upstream)
        && !entries.iter().any(|(name, _)| *name == "upstream")
        && let Some((name, _)) = entries
            .iter()
            .find(|(name, repo)| *name != "origin" && repo.eq_ignore_ascii_case(fork))
    {
        return RemoteClassification::OriginUpstreamNamedFork((*name).to_owned());
    }
    RemoteClassification::Ambiguous
}

#[cfg(test)]
mod tests {
    use super::*;

    fn remote(name: &str, url: &str) -> RemoteDescription {
        RemoteDescription {
            name: name.to_owned(),
            urls: vec![url.to_owned()],
            push_urls: vec![],
        }
    }

    fn classify(remotes: &[RemoteDescription]) -> RemoteClassification {
        classify_fork_remotes(remotes, "acme/project", "me/project", "github.com")
    }

    #[test]
    fn normalizes_legacy_github_url_shapes() {
        let expected = Some(NormalizedGitHubUrl {
            host: "github.com".into(),
            repository: "owner/repo".into(),
        });
        for url in [
            "git@GitHub.com:Owner/Repo.git",
            "ssh://git@github.com/Owner/Repo/",
            "ssh://github.com/Owner/Repo",
            "https://github.com/Owner/Repo.git",
            "git://github.com/Owner/Repo",
        ] {
            assert_eq!(normalize_github_url(url), expected);
        }
        for url in ["not-a-url", "ssh://user@github.com/o/r"] {
            assert_eq!(normalize_github_url(url), None);
        }
    }

    #[test]
    fn classifies_only_the_three_safe_remote_layouts() {
        assert_eq!(
            classify(&[remote("origin", "https://github.com/acme/project.git")]),
            RemoteClassification::OriginUpstreamOnly
        );
        assert_eq!(
            classify(&[
                remote("origin", "https://github.com/acme/project.git"),
                remote("mine", "git@github.com:me/project.git"),
            ]),
            RemoteClassification::OriginUpstreamNamedFork("mine".to_owned())
        );
        assert_eq!(
            classify(&[
                remote("origin", "git@github.com:me/project.git"),
                remote("upstream", "https://github.com/acme/project.git"),
            ]),
            RemoteClassification::AlreadyConfigured
        );
    }

    #[test]
    fn rejects_extra_duplicate_and_cross_host_remotes() {
        let mut duplicate = remote("origin", "https://github.com/acme/project.git");
        duplicate
            .urls
            .push("git@github.com:acme/project.git".to_owned());
        for remotes in [
            vec![duplicate],
            vec![remote("origin", "https://example.com/acme/project.git")],
            vec![
                remote("origin", "https://github.com/acme/project.git"),
                remote("extra", "https://github.com/other/project.git"),
            ],
        ] {
            assert_eq!(classify(&remotes), RemoteClassification::Ambiguous);
        }
    }
}
