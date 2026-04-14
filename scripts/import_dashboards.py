#!/usr/bin/env python3
import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any
from urllib import error, parse, request

DEFAULT_BASE_URL = "http://127.0.0.1:37652"
DEFAULT_ORG = "default"
DEFAULT_EMAIL = "root@example.com"
DEFAULT_PASSWORD = "Complexpass#123"
DASHBOARD_FILES = [
    "hagicode-backend-overview.dashboard.json",
    "hagicode-backend-runtime.dashboard.json",
    "hagicode-backend-database.dashboard.json",
    "hagicode-ai-overview.dashboard.json",
    "hagicode-agent-runtime.dashboard.json",
]
KNOWN_STREAM_NAMES = {
    "http_server_request_duration",
    "dotnet_process_memory_working_set",
    "dotnet_gc_last_collection_heap_size",
    "dotnet_gc_last_collection_memory_committed_size",
    "dotnet_thread_pool_queue_length",
    "dotnet_thread_pool_thread_count",
    "dotnet_gc_collections",
    "pcode_orleans_grain_duration",
    "pcode_database_command_duration",
    "pcode_ai_request",
    "pcode_ai_request_duration",
    "pcode_ai_token_usage",
    "pcode_ai_error",
    "pcode_agent_lifecycle",
    "pcode_agent_duration",
    "pcode_agent_tool_outcome",
    "hagicode_cli_acp_session_pool_hit",
    "hagicode_cli_acp_session_pool_miss",
    "hagicode_cli_acp_session_pool_evict",
    "hagicode_cli_acp_session_pool_fault",
    "hagicode_cli_acp_session_pool_active_entries",
    "hagicode_cli_acp_session_pool_leased_entries",
    "hagicode_cli_acp_session_pool_indexed_keys",
}


def build_auth_header(email: str, password: str) -> str:
    token = base64.b64encode(f"{email}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def http_json(method: str, url: str, auth_header: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method=method)
    req.add_header("Authorization", auth_header)
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=20) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else None


def load_dashboard(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    tabs = raw.get("tabs")
    if tabs:
        tab_name = tabs[0].get("name") or derive_tab_name(raw["title"])
        source_panels = tabs[0].get("panels", [])
    else:
        tab_name = derive_tab_name(raw["title"])
        source_panels = raw["panels"]

    panels = []
    for panel in source_panels:
        normalized_queries = []
        for query in panel["queries"]:
            normalized_queries.append(
                {
                    "query": query["query"],
                    "customQuery": True,
                    "fields": {
                        "stream": query["fields"]["stream"],
                        "stream_type": query["fields"]["stream_type"],
                        "x": [],
                        "y": [],
                        "z": [],
                        "filter": {
                            "type": "list",
                            "values": [],
                            "logicalOperator": "AND",
                            "filterType": "list",
                        },
                    },
                    "config": query["config"],
                }
            )
        panels.append(
            {
                "id": str(panel["id"]),
                "type": panel["type"],
                "title": panel["title"],
                "description": panel["description"],
                "config": panel["config"],
                "queryType": panel["queryType"],
                "queries": normalized_queries,
                "layout": panel["layout"],
            }
        )

    return {
        "version": 8,
        "title": raw["title"],
        "description": raw.get("description", ""),
        "defaultDatetimeDuration": raw.get(
            "defaultDatetimeDuration",
            {"type": "relative", "relativeTimePeriod": "1h"},
        ),
        "tabs": [{"tabId": "default", "name": tab_name, "panels": panels}],
        "variables": {"list": []},
    }


def derive_tab_name(title: str) -> str:
    if title.startswith("HagiCode "):
        return title.removeprefix("HagiCode ")

    return title


def discover_dashboard_files(dashboards_dir: Path) -> list[str]:
    return sorted(path.name for path in dashboards_dir.glob("*.dashboard.json"))


def validate_dashboard_files(
    dashboards_dir: Path,
    selected_files: list[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    discovered_files = discover_dashboard_files(dashboards_dir)

    if sorted(DASHBOARD_FILES) != discovered_files:
        missing_in_script = sorted(set(discovered_files) - set(DASHBOARD_FILES))
        missing_on_disk = sorted(set(DASHBOARD_FILES) - set(discovered_files))
        if missing_in_script:
            errors.append(
                "DASHBOARD_FILES is missing: " + ", ".join(missing_in_script)
            )
        if missing_on_disk:
            errors.append(
                "Dashboard files listed in script but not found on disk: "
                + ", ".join(missing_on_disk)
            )

    targets = selected_files or DASHBOARD_FILES
    for file_name in targets:
        path = dashboards_dir / file_name
        if not path.exists():
            errors.append(f"{file_name}: file does not exist")
            continue

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{file_name}: invalid JSON ({exc})")
            continue

        panels = []
        tabs = raw.get("tabs")
        if tabs:
            panels = tabs[0].get("panels", [])
        else:
            panels = raw.get("panels", [])

        if not raw.get("title"):
            errors.append(f"{file_name}: missing dashboard title")

        if not panels:
            errors.append(f"{file_name}: no panels found")
            continue

        seen_panel_ids: set[str] = set()
        for panel in panels:
            panel_id = str(panel.get("id", ""))
            if not panel_id:
                errors.append(f"{file_name}: panel without id")
            elif panel_id in seen_panel_ids:
                errors.append(f"{file_name}: duplicate panel id {panel_id}")
            else:
                seen_panel_ids.add(panel_id)

            title = panel.get("title") or f"panel {panel_id}"
            queries = panel.get("queries", [])
            if not queries:
                errors.append(f"{file_name} / {title}: no queries configured")
                continue

            for query in queries:
                fields = query.get("fields", {})
                stream = fields.get("stream")
                promql = query.get("query", "")
                if not stream:
                    errors.append(f"{file_name} / {title}: query missing fields.stream")
                    continue

                if stream not in KNOWN_STREAM_NAMES:
                    errors.append(
                        f"{file_name} / {title}: unknown normalized metric stream {stream}"
                    )

                if stream not in promql:
                    errors.append(
                        f"{file_name} / {title}: query does not reference fields.stream {stream}"
                    )

    return errors


def list_dashboards(base_url: str, org: str, auth_header: str) -> list[dict[str, Any]]:
    response = http_json("GET", f"{base_url}/api/{org}/dashboards", auth_header)
    return response.get("dashboards", [])


def delete_dashboard(base_url: str, org: str, auth_header: str, dashboard_id: str, folder: str) -> None:
    url = f"{base_url}/api/{org}/dashboards/{dashboard_id}?{parse.urlencode({'folder': folder})}"
    http_json("DELETE", url, auth_header)


def find_dashboard_id(existing: list[dict[str, Any]], title: str) -> str | None:
    for item in existing:
        if item.get("title") == title:
            return item.get("dashboard_id") or item.get("dashboardId")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Import ob4dev dashboards into local OpenObserve.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--org", default=DEFAULT_ORG)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--folder", default="default")
    parser.add_argument("--dashboard", action="append", help="Import or validate only the given dashboard file name. Repeatable.")
    parser.add_argument("--validate-only", action="store_true", help="Validate local dashboard JSON, metric-name alignment, and import coverage without contacting OpenObserve.")
    args = parser.parse_args()

    auth_header = build_auth_header(args.email, args.password)
    dashboards_dir = Path(__file__).resolve().parent.parent / "dashboards"
    selected_files = args.dashboard or DASHBOARD_FILES
    validation_errors = validate_dashboard_files(dashboards_dir, selected_files)

    if validation_errors:
        for validation_error in validation_errors:
            print(f"validation error: {validation_error}", file=sys.stderr)
        return 1

    if args.validate_only:
        print(f"validated {len(selected_files)} dashboard file(s): {', '.join(selected_files)}")
        return 0

    try:
        existing = list_dashboards(args.base_url, args.org, auth_header)
        for file_name in selected_files:
            path = dashboards_dir / file_name
            payload = load_dashboard(path)
            dashboard_id = find_dashboard_id(existing, payload["title"])
            if dashboard_id:
                delete_dashboard(args.base_url, args.org, auth_header, dashboard_id, args.folder)
                print(f"replaced: {payload['title']} ({dashboard_id})")
            url = f"{args.base_url}/api/{args.org}/dashboards?{parse.urlencode({'folder': args.folder})}"
            response = http_json("POST", url, auth_header, payload)
            created_id = response.get("dashboard_id") or response.get("v8", {}).get("dashboardId") or "unknown"
            print(f"created: {payload['title']} ({created_id})")
            existing = list_dashboards(args.base_url, args.org, auth_header)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {body}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Failed to import dashboards: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
