#!/usr/bin/env python3
from pathlib import Path

path = Path("/Users/zhupanov/larch1/crates/larch-cli/src/audit_umbrella_commands.rs")
text = path.read_text()

old = """        let leaf_refs: Vec<&str> = leaves.iter().map(String::as_str).collect();
        let search = search_items(&leaf_refs);
        let (service, server) = service(vec![
            response(200, repository_json("main")),
            response(200, &parent),
            response(200, refs(&references)),
            response(200, &search),
            response(200, &search),
        ]);

        let snapshot = collect_snapshot_remote(
            &service,
            &Cancellation::new(),
            &repository(),
            10,
            "main",
            &"a".repeat(40),
        )
        .await
        .expect("direct leaf count does not consume proposal batch capacity");

        assert_eq!(snapshot.historical_leaf_numbers.len(), leaf_count);
        assert_eq!(server.finish().expect("stub completed").len(), 5);"""

new = """        let leaf_refs: Vec<&str> = leaves.iter().map(String::as_str).collect();
        let search = search_items(&leaf_refs);
        let mut exchanges = vec![
            response(200, repository_json("main")),
            response(200, &parent),
            response(200, refs(&references)),
            response(200, &search),
            response(200, &search),
        ];
        for leaf in &leaves {
            exchanges.push(response(200, leaf));
        }
        let (service, server) = service(exchanges);

        let snapshot = collect_snapshot_remote(
            &service,
            &Cancellation::new(),
            &repository(),
            10,
            "main",
            &"a".repeat(40),
        )
        .await
        .expect("direct leaf count does not consume proposal batch capacity");

        assert_eq!(snapshot.historical_leaf_numbers.len(), leaf_count);
        assert_eq!(
            server.finish().expect("stub completed").len(),
            5 + leaf_count
        );"""

if old not in text:
    raise SystemExit("more_direct_leaves block not found")
text = text.replace(old, new)

old_pag = """        let searches: Vec<_> = requests
            .iter()
            .filter(|request| request.path.starts_with("/search/issues"))
            .collect();
        assert_eq!(searches.len(), 2);"""

new_pag = """        let title_searches: Vec<_> = requests
            .iter()
            .filter(|request| {
                request.path.starts_with("/search/issues")
                    && decoded_search_query(&request.path)
                        .is_some_and(|query| query.contains("in:title"))
            })
            .collect();
        assert_eq!(title_searches.len(), 2);"""

if old_pag not in text:
    raise SystemExit("pagination assert not found")
text = text.replace(old_pag, new_pag)

path.write_text(text)
print("ok")
