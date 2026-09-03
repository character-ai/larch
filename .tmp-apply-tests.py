#!/usr/bin/env python3
from pathlib import Path

path = Path("/Users/zhupanov/larch1/crates/larch-cli/src/audit_umbrella_commands.rs")
text = path.read_text()

# Fix snapshot_exchanges
old_snap = """    fn snapshot_exchanges(parent: &str, leaf: &str, control: &str) -> Vec<IssueServiceExchange> {
        let search = search_items(&[leaf]);
        vec![
            response(200, repository_json("main")),
            response(200, parent),
            response(200, refs(&[(11, 111, "open")])),
            response(200, &search),
            response(200, &search),
            response(200, control),
        ]
    }"""
new_snap = """    fn snapshot_exchanges(parent: &str, leaf: &str, control: &str) -> Vec<IssueServiceExchange> {
        let search = search_items(&[leaf]);
        vec![
            response(200, repository_json("main")),
            response(200, parent),
            response(200, refs(&[(11, 111, "open")])),
            response(200, &search),
            response(200, &search),
            response(200, leaf),
            response(200, control),
        ]
    }"""
if old_snap not in text:
    raise SystemExit("snapshot_exchanges block not found")
text = text.replace(old_snap, new_snap)

# orphan_parent helper
orphan_fn = Path("/Users/zhupanov/larch1/.tmp-orphan-parent.txt").read_text()
marker = "    fn remote_leaf() -> String {"
if orphan_fn.strip() not in text:
    if marker not in text:
        raise SystemExit("remote_leaf marker not found")
    text = text.replace(marker, orphan_fn + marker, 1)

# bare_title test
old_bare = """        let (service, server) = service(vec![
            response(200, repository_json("main")),
            response(200, &parent),
            response(200, refs(&[(11, 111, "open")])),
            response(200, &search_items(&[&leaf])),
            response(200, &empty_search()),
            response(200, &control),
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
        .expect("title-only leaf");
        assert_eq!(snapshot, audit_snapshot());
        assert_eq!(server.finish().expect("stub completed").len(), 6);"""
new_bare = old_bare.replace(
    "response(200, &empty_search()),\n            response(200, &control),",
    "response(200, &empty_search()),\n            response(200, &leaf),\n            response(200, &control),",
).replace(".len(), 6)", ".len(), 7)")
if old_bare in text:
    text = text.replace(old_bare, new_bare)

# backlink test
old_back = """        let (service, server) = service(vec![
            response(200, repository_json("main")),
            response(200, &parent),
            response(200, refs(&[(11, 111, "open")])),
            response(200, &empty_search()),
            response(200, &search_items(&[&leaf])),
            response(200, &control),
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
        .expect("backlink-only leaf");
        assert!(snapshot.historical_leaf_numbers.contains(&11));
        assert_eq!(server.finish().expect("stub completed").len(), 6);"""
new_back = old_back.replace(
    "response(200, &search_items(&[&leaf])),\n            response(200, &control),",
    "response(200, &search_items(&[&leaf])),\n            response(200, &leaf),\n            response(200, &control),",
).replace(".len(), 6)", ".len(), 7)")
if old_back in text:
    text = text.replace(old_back, new_back)

# discovery test count
text = text.replace(
    "        assert_eq!(requests.len(), 6);\n        assert!(\n            !requests\n                .iter()\n                .any(|request| is_repo_wide_issue_list(&request.path)),\n            \"audit snapshot listed repo-wide issues:",
    "        assert_eq!(requests.len(), 7);\n        assert!(\n            !requests\n                .iter()\n                .any(|request| is_repo_wide_issue_list(&request.path)),\n            \"audit snapshot listed repo-wide issues:",
    1,
)

# merges and lifecycle count fixes
text = text.replace(
    '        .expect("identical search overlap");\n        assert_eq!(snapshot, audit_snapshot());\n        assert_eq!(server.finish().expect("stub completed").len(), 6);',
    '        .expect("identical search overlap");\n        assert_eq!(snapshot, audit_snapshot());\n        assert_eq!(server.finish().expect("stub completed").len(), 7);',
)
text = text.replace(
    '        .expect("lifecycle prefix is stripped for leaf titles");\n        assert!(snapshot.historical_leaf_numbers.contains(&11));\n        assert_eq!(server.finish().expect("stub completed").len(), 6);',
    '        .expect("lifecycle prefix is stripped for leaf titles");\n        assert!(snapshot.historical_leaf_numbers.contains(&11));\n        assert_eq!(server.finish().expect("stub completed").len(), 7);',
)

# insert new tests
new_tests = Path("/Users/zhupanov/larch1/.tmp-new-tests.txt").read_text()
merge_marker = "    #[tokio::test]\n    async fn remote_snapshot_merges_identical_title_and_body_search_copies()"
if "remote_snapshot_discovers_title_only_orphan_without_native_edge" not in text:
    text = text.replace(merge_marker, new_tests + merge_marker, 1)

# replace pagination test
paginated = Path("/Users/zhupanov/larch1/.tmp-paginated-test.txt").read_text()
start = text.index("    #[tokio::test]\n    async fn remote_snapshot_filters_more_than_one_hundred_raw_search_hits()")
end = text.index("    #[tokio::test]\n    async fn remote_snapshot_refuses_incomplete_title_search_results()")
text = text[:start] + paginated + text[end:]

path.write_text(text)
print("ok")
