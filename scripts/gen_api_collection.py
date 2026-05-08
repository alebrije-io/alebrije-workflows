#!/usr/bin/env python3
"""
gen_api_collection.py - Generates API collection JSON from API gateway repository.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime


class APICollectionGenerator:
    """Generates API collection from gateway repository."""

    def __init__(self, repo_path: str):
        """Initialize generator with repository path."""
        self.repo_path = Path(repo_path)
        if not self.repo_path.is_dir():
            raise FileNotFoundError(f"Repository not found: {repo_path}")
        self.collection: Dict[str, Any] = self._init_collection()
        self.endpoints: List[Dict[str, Any]] = []

    def _init_collection(self) -> Dict[str, Any]:
        """Initialize collection structure."""
        return {
            "apiVersion": "1.0.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "repository": str(self.repo_path),
            "endpoints": [],
            "webhooks": [],
            "schemas": {},
            "authentication": {
                "default_method": "JWT",
                "methods": ["JWT", "PAT"],
            },
            "rate_limits": {
                "default_requests_per_minute": 60,
                "premium_requests_per_minute": 300,
            },
        }

    def generate(self) -> Dict[str, Any]:
        """Generate API collection from repository."""
        self._scan_go_routes()
        self.collection["endpoints"] = self.endpoints
        return self.collection

    def _scan_go_routes(self) -> None:
        """Scan for Go route handler definitions."""
        for go_file in self.repo_path.rglob("*.go"):
            self._parse_go_routes(go_file)

    def _parse_go_routes(self, go_file: Path) -> None:
        """Parse Go file for route definitions."""
        try:
            with open(go_file, "r") as f:
                content = f.read()

            # Pattern for common router definitions
            route_pattern = r'(?:router|r)\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*"([^"]+)"\s*,\s*(\w+)\)'

            for match in re.finditer(route_pattern, content):
                method, path, handler = match.groups()

                if any(ep["path"] == path and ep["method"] == method.upper() for ep in self.endpoints):
                    continue

                endpoint = {
                    "path": path,
                    "method": method.upper(),
                    "handler": handler,
                    "description": f"Handler: {handler}",
                    "authentication": "JWT",
                    "rate_limit_requests_per_minute": 60,
                }
                self.endpoints.append(endpoint)
        except Exception as e:
            print(f"Warning: Failed to parse Go routes from {go_file}: {e}", file=sys.stderr)

    def save(self, output_path: str) -> None:
        """Save collection to JSON file."""
        with open(output_path, "w") as f:
            json.dump(self.collection, f, indent=2)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate API collection from API gateway repository"
    )

    parser.add_argument(
        "-r", "--repo",
        default="../api-gateway-go",
        help="Path to API gateway repository (default: ../api-gateway-go)"
    )
    parser.add_argument(
        "-o", "--output",
        default="api-collection.json",
        help="Output file path (default: api-collection.json)"
    )

    args = parser.parse_args()

    try:
        generator = APICollectionGenerator(args.repo)
        collection = generator.generate()

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        generator.save(args.output)
        print(f"Generated API collection: {args.output}", file=sys.stderr)
        print(f"Total endpoints: {len(collection['endpoints'])}", file=sys.stderr)

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
