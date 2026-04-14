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
]


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
        tab_name = tabs[0].get("name") or raw["title"].replace("HagiCode Backend ", "")
        source_panels = tabs[0].get("panels", [])
    else:
        tab_name = raw["title"].replace("HagiCode Backend ", "")
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
    args = parser.parse_args()

    auth_header = build_auth_header(args.email, args.password)
    dashboards_dir = Path(__file__).resolve().parent.parent / "dashboards"

    try:
        existing = list_dashboards(args.base_url, args.org, auth_header)
        for file_name in DASHBOARD_FILES:
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
