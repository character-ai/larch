//! Shared review voting policy primitives.

/// Classify a finding according to the historical one-, two-, and three-voter thresholds.
#[must_use]
pub const fn classify_result(yes: usize, eligible: usize) -> &'static str {
    if eligible == 0 {
        return "rejected";
    }
    let accepted = if eligible == 1 {
        yes == 1
    } else if eligible == 2 {
        yes == 2
    } else {
        yes >= 2
    };
    if accepted {
        "accepted"
    } else if yes > 0 {
        "neutral"
    } else {
        "rejected"
    }
}

/// Classify an OOS item according to its distinct two-voter policy.
#[must_use]
pub const fn classify_oos_result(yes: usize, eligible: usize) -> &'static str {
    if eligible == 0 {
        return "rejected";
    }
    let accepted = if eligible == 1 {
        yes == 1
    } else if eligible == 2 {
        yes >= 1
    } else {
        yes >= 2
    };
    if accepted {
        "accepted"
    } else if yes > 0 {
        "neutral"
    } else {
        "rejected"
    }
}

fn strict_majority_yes_major(votes: &[String], severities: &[String]) -> bool {
    let mut yes = 0_usize;
    let mut major = 0_usize;
    for (index, vote) in votes.iter().enumerate() {
        if vote.trim().eq_ignore_ascii_case("YES") {
            yes += 1;
            if severities
                .get(index)
                .is_some_and(|severity| severity.trim().eq_ignore_ascii_case("major"))
            {
                major += 1;
            }
        }
    }
    yes > 0 && major * 2 > yes
}

/// Whether an accepted OOS item has a strict majority of major YES votes.
#[must_use]
pub fn oos_fileable_from_votes(result: &str, votes: &[String], severities: &[String]) -> bool {
    result == "accepted" && strict_majority_yes_major(votes, severities)
}

/// Whether a neutral item reroutes to OOS due to major YES evidence.
#[must_use]
pub fn neutral_high_severity_rescue_to_oos(
    result: &str,
    votes: &[String],
    severities: &[String],
) -> bool {
    result == "neutral" && strict_majority_yes_major(votes, severities)
}

/// Return the accepted finding weight, counting only YES-vote severities.
#[must_use]
pub fn accepted_finding_points_from_severities(votes: &[String], severities: &[String]) -> u8 {
    if strict_majority_yes_major(votes, severities) {
        2
    } else {
        1
    }
}
