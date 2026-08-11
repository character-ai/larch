#[derive(Clone, Copy)]
pub enum QuoteEscaping {
    Preserve,
    Decimal,
    Hexadecimal,
}

pub fn escape_html(value: &str, quote_escaping: QuoteEscaping) -> String {
    let mut escaped = String::with_capacity(value.len());
    for character in value.chars() {
        match character {
            '&' => escaped.push_str("&amp;"),
            '<' => escaped.push_str("&lt;"),
            '>' => escaped.push_str("&gt;"),
            '"' if !matches!(quote_escaping, QuoteEscaping::Preserve) => {
                escaped.push_str("&quot;");
            }
            '\'' => match quote_escaping {
                QuoteEscaping::Preserve => escaped.push('\''),
                QuoteEscaping::Decimal => escaped.push_str("&#39;"),
                QuoteEscaping::Hexadecimal => escaped.push_str("&#x27;"),
            },
            _ => escaped.push(character),
        }
    }
    escaped
}

#[cfg(test)]
mod tests {
    use super::{QuoteEscaping, escape_html};

    #[test]
    fn escapes_markup_and_optional_attribute_quotes() {
        assert_eq!(
            escape_html("<&>\"'", QuoteEscaping::Decimal),
            "&lt;&amp;&gt;&quot;&#39;"
        );
        assert_eq!(
            escape_html("<&>\"'", QuoteEscaping::Hexadecimal),
            "&lt;&amp;&gt;&quot;&#x27;"
        );
        assert_eq!(
            escape_html("<&>\"'", QuoteEscaping::Preserve),
            "&lt;&amp;&gt;\"'"
        );
    }
}
