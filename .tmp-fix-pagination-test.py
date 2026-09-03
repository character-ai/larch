#!/usr/bin/env python3
from pathlib import Path

path = Path("/Users/zhupanov/larch1/crates/larch-cli/src/audit_umbrella_commands.rs")
text = path.read_text()

old = """    #[tokio::test]
    async fn remote_snapshot_filters_more_than_one_hundred_raw_search_hits() {
        let junk: Vec<String> = (0..100)
            .map(|offset| {
                let number = 1001 + offset;
                issue_json(
                    number,
                    number,
                    "Unrelated search hit mentioning LEAF OF 10",
                    "noise",
                    "open",
                )
            })
            .collect();
        let leaf = remote_leaf();
        let junk_items: Vec<Value> = junk
            .iter()
            .map(|body| serde_json::from_str(body).expect("junk json"))
            .collect();
        let first_page = search_payload(&junk_items, 101, Some(false));
        let second_page = search_payload(
            &[serde_json::from_str(&leaf).expect("leaf json")],
            101,
            Some(false),
        );
        let (service, server) = service(vec![
            response(200, repository_json("main")),
            response(200, &remote_parent()),
            response(200, refs(&[(11, 111, "open")])),
            paginated_response(200, &first_page, "/search/issues?page=2"),
            response(200, &second_page),
            response(200, &empty_search()),
            response(200, &leaf),
            response(200, &remote_control()),
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
        .expect("paginated search above 100 stays usable");
        assert_eq!(snapshot, audit_snapshot());
        let requests = server.finish().expect("stub completed");
        assert_eq!(requests.len(), 8);
        let title_searches: Vec<_> = requests
            .iter()
            .filter(|request| {
                request.path.starts_with("/search/issues")
                    && decoded_search_query(&request.path)
                        .is_some_and(|query| query.contains("in:title"))
            })
            .collect();
        assert_eq!(title_searches.len(), 2);
        assert!(
            !requests
                .iter()
                .any(|request| is_repo_wide_issue_list(&request.path))
        );
    }"""

new = """    #[tokio::test]
    async fn remote_snapshot_filters_more_than_one_hundred_raw_search_hits() {
        let junk: Vec<String> = (0..100)
            .map(|offset| {
                let number = 1001 + offset;
                issue_json(
                    number,
                    number,
                    "Unrelated search hit mentioning LEAF OF 10",
                    "noise",
                    "open",
                )
            })
            .collect();
        let leaf = remote_leaf();
        let junk_items: Vec<Value> = junk
            .iter()
            .map(|body| serde_json::from_str(body).expect("junk json"))
            .collect();
        let first_page = search_payload(&junk_items, 101, Some(false));
        let second_page = search_payload(
            &[serde_json::from_str(&leaf).expect("leaf json")],
            101,
            Some(false),
        );
        let (service, server) = service(vec![
            response(200, repository_json("main")),
            response(200, &orphan_parent()),
            response(200, refs(&[])),
            paginated_response(200, &first_page, "/search/issues?page=2"),
            response(200, &second_page),
            response(200, &empty_search()),
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
        .expect("paginated search above 100 stays usable");
        assert!(snapshot.historical_leaf_numbers.contains(&11));
        let requests = server.finish().expect("stub completed");
        assert_eq!(requests.len(), 6);
        let title_searches: Vec<_> = requests
            .iter()
            .filter(|request| {
                request.path.starts_with("/search/issues")
                    && decoded_search_query(&request.path)
                        .is_some_and(|query| query.contains("in:title"))
            })
            .collect();
        assert_eq!(title_searches.len(), 2);
        assert!(
            !requests
                .iter()
                .any(|request| is_repo_wide_issue_list(&request.path))
        );
    }"""

if old not in text:
    raise SystemExit("pagination test block not found")
text = text.replace(old, new)
path.write_text(text)
print("ok")
