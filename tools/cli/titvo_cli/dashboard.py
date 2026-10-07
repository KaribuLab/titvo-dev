"""Read-only, loopback-only bridge from the existing dashboard to lab artifacts."""

import hashlib
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError

from titvo_cli.outcome import execution_state
from titvo_cli.storage import BUCKET, TASKS_TABLE


def repository_id(project):
    """Give each project identity a stable local identity."""
    return "local-" + hashlib.sha256(project.encode()).hexdigest()[:16]


class LabAPI:
    """Translate genuine lab tasks into the admin frontend's read contracts."""

    def __init__(self, s3, dynamodb):
        """Use only explicit MiniStack clients supplied by the local launcher."""
        self.s3, self.dynamodb = s3, dynamodb

    def tasks(self):
        """Read every DynamoDB page; do not silently omit older scans."""
        items, options = [], {"TableName": TASKS_TABLE, "ConsistentRead": True}
        decoder = TypeDeserializer()
        while True:
            response = self.dynamodb.scan(**options)
            items.extend(
                {key: decoder.deserialize(value) for key, value in item.items()}
                for item in response.get("Items", [])
            )
            if not response.get("LastEvaluatedKey"):
                break
            options["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)

    def report(self, item):
        """Load persisted coverage to distinguish evaluation from execution."""
        if not item.get("report_key"):
            return None
        return json.loads(
            self.s3.get_object(Bucket=BUCKET, Key=item["report_key"])["Body"].read()
        )

    def summary(self, item, report=None):
        """Preserve evaluation and add independent execution derived from coverage."""
        result = self.report(item) if report is None else report
        return {
            "scan_id": item["scan_id"],
            "repository_id": repository_id(item.get("project_id", item["project"])),
            "status": item["status"],
            "execution_status": execution_state(result) if result is not None else None,
            "source": "cli",
            "branch": "working-tree",
            "created_at": item.get("created_at"),
        }

    def get(self, path):
        """Expose automatic laboratory identity and read routes only."""
        if path == "/api/admin/auth/me":
            return 200, {
                "user_id": "local-lab",
                "email": "laboratorio@titvo.local",
                "role": "member",
            }
        if path in {"/api/admin/api-keys", "/api/admin/users"}:
            return 200, {"items": []}
        tasks = self.tasks()
        if path == "/api/admin/repos":
            repos = {}
            for item in tasks:
                identity = repository_id(item.get("project_id", item["project"]))
                if identity not in repos:
                    repos[identity] = {
                        "repository_id": identity,
                        "name": Path(item["project"]).name,
                        "url": item["project"],
                        "provider": "cli",
                        "last_scan": self.summary(item),
                    }
            return 200, {"items": list(repos.values())}
        parts = path.split("/")
        if (
            len(parts) == 6
            and parts[1:4] == ["api", "admin", "repos"]
            and parts[5] == "scans"
        ):
            return 200, {
                "items": [
                    self.summary(item)
                    for item in tasks
                    if repository_id(item.get("project_id", item["project"]))
                    == parts[4]
                ]
            }
        if len(parts) == 5 and parts[1:4] == ["api", "admin", "scans"]:
            item = next((item for item in tasks if item["scan_id"] == parts[4]), None)
            if item is None:
                return 404, {"error": "not_found"}
            report = self.report(item)
            detail = self.summary(item, report)
            if item.get("report_key"):
                detail["result"] = report
                detail["updated_at"] = (
                    detail["result"].get("metrics", {}).get("finished_at")
                )
            detail["args"] = {
                "project": item["project"],
                "model_mode": item["model"],
                "rag_enabled": False,
            }
            return 200, detail
        return 404, {"error": "not_found"}


def handler_for(api):
    """Restrict browser access to the local proxy and deny all write operations."""

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body):
            """Return uncached JSON without exposing backend exceptions."""
            payload = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            """Validate Host/Origin to keep code evidence local to this browser."""
            hostname = self.headers.get("Host", "").split(":")[0]
            origin = self.headers.get("Origin")
            if hostname not in {"localhost", "127.0.0.1"} or (
                origin and urlparse(origin).hostname not in {"localhost", "127.0.0.1"}
            ):
                self.respond(403, {"error": "local_only"})
                return
            try:
                status, body = api.get(unquote(urlparse(self.path).path))
                self.respond(status, body)
            except ClientError:
                self.respond(503, {"error": "ministack_unavailable"})
            except Exception:
                self.respond(500, {"error": "lab_read_failed"})

        def do_POST(self):
            """Scanning, authentication mutations and admin writes are disabled."""
            self.respond(
                405,
                {
                    "error": "read_only_lab",
                    "message": "Inicia el análisis desde titvo scan.",
                },
            )

        do_PUT = do_PATCH = do_DELETE = do_POST

        def log_message(self, *args):
            """Keep the terminal quiet; never log repository contents."""
            pass

    return Handler


def launch(dev_root, s3, dynamodb, port=5173, api_port=8787):
    """Run the existing Vite frontend and local bridge until Ctrl+C."""
    frontend = dev_root.parent / "titvo-admin-web"
    if not (frontend / "node_modules/vite/bin/vite.js").exists():
        raise ValueError(f"Instala el frontend primero: cd {frontend} && npm ci")
    server = ThreadingHTTPServer(
        ("127.0.0.1", api_port), handler_for(LabAPI(s3, dynamodb))
    )
    process = None
    try:
        process = subprocess.Popen(
            [
                "npm",
                "run",
                "dev",
                "--",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--strictPort",
            ],
            cwd=frontend,
            env={
                **os.environ,
                "VITE_TITVO_LAB": "true",
                "TITVO_DEV_API_URL": f"http://127.0.0.1:{api_port}",
            },
            start_new_session=True,
        )
        server.timeout = 0.5
        while process.poll() is None:
            server.handle_request()
        if process.returncode:
            raise ValueError(
                "El frontend no pudo iniciarse; revisa el puerto y las dependencias."
            )
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if process and process.poll() is None:
            import signal

            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
