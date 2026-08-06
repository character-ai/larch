//! POSIX shell quoting shared by every larch renderer that emits shell text.
//!
//! The launcher scripts, the `export KEY=value` session-env lines, and the
//! bgjob source lines were all ported from Python writers that quoted through
//! `shlex.quote`, so they share one owner here rather than each carrying a
//! private copy that can drift from the reference semantics.

/// Characters `shlex.quote` leaves bare beyond the ASCII alphanumerics.
///
/// `_` is in the set because Python's safe pattern is `[\w@%+=:,./-]` and `\w`
/// includes the underscore under `re.ASCII`.
const SHELL_SAFE: &str = "_@%+=:,./-";

/// Quote one value for POSIX shell interpolation exactly as `shlex.quote` does.
///
/// A value made entirely of safe characters is returned unchanged, the empty
/// string becomes `''`, and every other value is wrapped in single quotes with
/// each embedded quote spelled `'"'"'`.
#[must_use]
pub fn shell_quote(value: &str) -> String {
    if !value.is_empty()
        && value
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || SHELL_SAFE.contains(character))
    {
        return value.to_owned();
    }
    format!("'{}'", value.replace('\'', "'\"'\"'"))
}

#[cfg(test)]
mod tests {
    use super::shell_quote;

    #[test]
    fn an_underscore_is_safe_in_both_directions() {
        // `python3 -c "import shlex; print(shlex.quote('/Users/x/my_repo'))"`
        // prints the path unquoted, so the Rust owner must too.
        assert_eq!(shell_quote("/Users/x/my_repo"), "/Users/x/my_repo");
        assert_eq!(shell_quote("run_1"), "run_1");
        assert_eq!(shell_quote("my repo"), "'my repo'");
    }

    #[test]
    fn the_remaining_safe_characters_match_the_python_pattern() {
        assert_eq!(shell_quote("plain-1.2/x"), "plain-1.2/x");
        assert_eq!(shell_quote("@%+=:,./-"), "@%+=:,./-");
    }

    #[test]
    fn unsafe_values_take_the_single_quoted_branch() {
        assert_eq!(shell_quote(""), "''");
        assert_eq!(shell_quote("a b'c"), "'a b'\"'\"'c'");
        assert_eq!(shell_quote("it's"), r#"'it'"'"'s'"#);
        assert_eq!(shell_quote("caf\u{e9}"), "'caf\u{e9}'");
    }
}
