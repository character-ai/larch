#!/usr/bin/env python3
from pathlib import Path

path = Path("/Users/zhupanov/larch1/crates/larch-cli/src/audit_umbrella_commands.rs")
text = path.read_text()

old = """        let title_searches: Vec<_> = requests
            .iter()
            .filter(|request| {
                request.path.starts_with("/search/issues")
                    && decoded_search_query(&request.path)
                        .is_some_and(|query| query.contains("in:title"))
            })
            .collect();
        assert_eq!(title_searches.len(), 2);"""

new = """        let search_requests: Vec<_> = requests
            .iter()
            .filter(|request| request.path.starts_with("/search/issues"))
            .collect();
        assert_eq!(search_requests.len(), 3);
        assert!(
            search_requests
                .iter()
                .any(|request| request.path.contains("page=2"))
        );
        assert!(
            decoded_search_query(&search_requests[0].path)
                .is_some_and(|query| query.contains("in:title"))
        );"""

if old not in text:
    raise SystemExit("assert block not found")
text = text.replace(old, new)
path.write_text(text)
print("ok")
