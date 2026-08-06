//! JSON parsing that preserves the source order of object members.

use std::fmt;

use serde::{
    Deserialize, Deserializer,
    de::{MapAccess, SeqAccess, Visitor},
};
use serde_json::Number;

/// A JSON value that retains the object-member order produced by `json.loads`.
#[derive(Clone, Debug)]
pub enum OrderedJson {
    /// JSON null.
    Null,
    /// A JSON Boolean.
    Bool(bool),
    /// A JSON number.
    Number(Number),
    /// A JSON string.
    String(String),
    /// A JSON array.
    Array(Vec<Self>),
    /// A JSON object, in source-member order.
    Object(Vec<(String, Self)>),
}

impl<'de> Deserialize<'de> for OrderedJson {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(OrderedJsonVisitor)
    }
}

struct OrderedJsonVisitor;

impl<'de> Visitor<'de> for OrderedJsonVisitor {
    type Value = OrderedJson;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a JSON value")
    }

    fn visit_bool<E>(self, value: bool) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(OrderedJson::Bool(value))
    }

    fn visit_i64<E>(self, value: i64) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(OrderedJson::Number(Number::from(value)))
    }

    fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(OrderedJson::Number(Number::from(value)))
    }

    fn visit_f64<E>(self, value: f64) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Number::from_f64(value)
            .map(OrderedJson::Number)
            .ok_or_else(|| E::custom("JSON number must be finite"))
    }

    fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(OrderedJson::String(value.to_owned()))
    }

    fn visit_borrowed_str<E>(self, value: &'de str) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        self.visit_str(value)
    }

    fn visit_string<E>(self, value: String) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(OrderedJson::String(value))
    }

    fn visit_none<E>(self) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(OrderedJson::Null)
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(OrderedJson::Null)
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let mut values = Vec::new();
        while let Some(value) = sequence.next_element()? {
            values.push(value);
        }
        Ok(OrderedJson::Array(values))
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut values = Vec::new();
        while let Some((key, value)) = map.next_entry::<String, OrderedJson>()? {
            if let Some((_, prior)) = values.iter_mut().find(|(prior_key, _)| *prior_key == key) {
                *prior = value;
            } else {
                values.push((key, value));
            }
        }
        if let [(key, OrderedJson::String(raw))] = values.as_slice()
            && key == "$serde_json::private::Number"
            && let Ok(number) = serde_json::from_str::<Number>(raw)
        {
            return Ok(OrderedJson::Number(number));
        }
        Ok(OrderedJson::Object(values))
    }
}

#[cfg(test)]
mod tests {
    use super::OrderedJson;

    #[test]
    fn preserves_object_order_duplicate_keys_and_large_numbers() {
        let value: OrderedJson = serde_json::from_str(
            r#"{"z":1,"z":2,"large":123456789012345678901234567890,"nested":{"first":true}}"#,
        )
        .expect("valid JSON");
        let OrderedJson::Object(values) = value else {
            panic!("root must be an object");
        };
        assert_eq!(
            values
                .iter()
                .map(|(key, _value)| key.as_str())
                .collect::<Vec<_>>(),
            ["z", "large", "nested"]
        );
        assert!(matches!(&values[0].1, OrderedJson::Number(number) if number.to_string() == "2"));
        assert!(
            matches!(&values[1].1, OrderedJson::Number(number) if number.to_string() == "123456789012345678901234567890")
        );
    }
}
