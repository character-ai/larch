//! Site → bgjob step/budget mapping and pure argv builders for run-step-checks.

pub const STEP6_CHECKS_STEP: &str = "implement-step6-checks";
pub const CHECKS_TERMINAL_ACTIONS: &[&str] = &["continue", "stall", "checks-failed", "skip-to-7a"];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct StepChecksSite {
    pub step: &'static str,
    pub budget_s: u32,
}

#[must_use]
pub fn checks_step_for_site(site: &str) -> StepChecksSite {
    match site {
        "step3" => StepChecksSite {
            step: "implement-step3-checks",
            budget_s: 15_600,
        },
        "step5-self-review" => StepChecksSite {
            step: "implement-checks-step5-self-review",
            budget_s: 14_700,
        },
        "step6" => StepChecksSite {
            step: STEP6_CHECKS_STEP,
            budget_s: 10_800,
        },
        _ => StepChecksSite {
            step: "",
            budget_s: 10_800,
        },
    }
}

#[must_use]
pub fn public_args_for_site(
    site: &str,
    commit_site: &str,
    forked_target: &str,
    rebase_checkpoint_4r: bool,
) -> Vec<String> {
    let mut args = vec!["--site".to_owned(), site.to_owned()];
    if !commit_site.is_empty() {
        args.extend(["--commit-site".to_owned(), commit_site.to_owned()]);
    }
    args.extend(["--forked-target".to_owned(), forked_target.to_owned()]);
    if rebase_checkpoint_4r {
        args.push("--rebase-checkpoint-4r".to_owned());
    }
    args
}

#[must_use]
pub fn resolve_step_name(site: &str) -> String {
    let mapped = checks_step_for_site(site);
    if mapped.step.is_empty() {
        format!("implement-checks-{site}")
    } else {
        mapped.step.to_owned()
    }
}

#[must_use]
pub fn resolve_step_and_budget(site: &str) -> (String, u32) {
    let mapped = checks_step_for_site(site);
    (resolve_step_name(site), mapped.budget_s)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn preserves_known_site_budgets() {
        assert_eq!(
            resolve_step_and_budget("step3"),
            ("implement-step3-checks".into(), 15_600)
        );
        assert_eq!(
            resolve_step_and_budget("step5-self-review"),
            ("implement-checks-step5-self-review".into(), 14_700)
        );
        assert_eq!(
            resolve_step_and_budget("custom"),
            ("implement-checks-custom".into(), 10_800)
        );
    }
}
