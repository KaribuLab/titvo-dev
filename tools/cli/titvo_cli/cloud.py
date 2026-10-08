"""Titvo API transport: presigned upload, existing trigger and task status contracts."""

import json
import math
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

TERMINAL = {"COMPLETED", "FAILED", "ERROR", "WARNING", "INCOMPLETE"}
TASK_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")


def https_url(value: str) -> str:
    """Require explicit HTTPS origins without credentials or fragments."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ValueError("AWS requiere una URL HTTPS sin credenciales ni fragmentos.")
    return value


def api_endpoint(value: str | None = None) -> str:
    """Resolve only the Titvo API endpoint, never AWS_ENDPOINT used by MiniStack."""
    endpoint = value or os.getenv("TITVO_API_ENDPOINT", "")
    if not endpoint:
        raise ValueError("Configura TITVO_API_ENDPOINT para usar AWS.")
    https_url(endpoint)
    if urlsplit(endpoint).query:
        raise ValueError(
            "El endpoint de Titvo no debe contener parámetros de consulta."
        )
    return endpoint.rstrip("/")


def repository_identity(project: Path, repository_url: str | None, branch: str | None):
    """Read local Git metadata without contacting or modifying the repository."""

    def git(*args):
        """Return a local Git value when available, including detached-head handling."""
        result = subprocess.run(
            ["git", "-C", str(project), *args],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    repository_url = (
        repository_url
        or os.getenv("TITVO_REPOSITORY_URL")
        or git("remote", "get-url", "origin")
    )
    branch = (
        branch
        or os.getenv("TITVO_BRANCH")
        or git("symbolic-ref", "--quiet", "--short", "HEAD")
    )
    if not repository_url or not branch:
        raise ValueError(
            "AWS requiere --repository-url y --branch, o un repositorio Git con origin y rama activa."
        )
    if repository_url.startswith("git@"):
        if not re.fullmatch(r"git@[^\s:]+:[^\s]+", repository_url):
            raise ValueError("URL Git del proyecto inválida.")
    else:
        parsed = urlsplit(repository_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path in {"", "/"}
        ):
            raise ValueError("URL del repositorio inválida o con credenciales.")
    if not branch.strip():
        raise ValueError("Indica una rama para identificar el análisis en AWS.")
    return repository_url, branch.strip()


class NoRedirect(HTTPRedirectHandler):
    """Do not forward a Titvo credential or project bytes to redirected origins."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Reject redirects instead of silently sending credentials elsewhere."""
        return None


class CloudClient:
    """Keep API credentials scoped to the API; signed S3 requests have no API key."""

    def __init__(
        self, endpoint: str | None = None, api_key: str | None = None, opener=None
    ):
        self.endpoint = api_endpoint(endpoint)
        self.api_key = api_key or os.getenv("TITVO_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Configura TITVO_API_KEY (clave Titvo, no clave del proveedor IA)."
            )
        self.opener = opener or build_opener(NoRedirect())

    def _request(self, url: str, payload: bytes, headers: dict, method="POST") -> bytes:
        """Use bounded requests and redact credentials and signed URLs from failures."""
        try:
            with self.opener.open(
                Request(url, data=payload, headers=headers, method=method), timeout=30
            ) as response:
                data = response.read(10 * 1024 * 1024 + 1)
                if len(data) > 10 * 1024 * 1024:
                    raise ValueError("Respuesta de Titvo demasiado grande.")
                return data
        except HTTPError as exc:
            message = {
                401: "Clave Titvo inválida o sin autorización",
                403: "Acceso rechazado",
                404: "Endpoint o tarea no encontrados",
            }.get(exc.code, "Solicitud rechazada")
            raise ValueError(
                f"{message} (HTTP {exc.code}). No se cambió de destino."
            ) from None
        except (URLError, TimeoutError, OSError):
            raise ValueError(
                "No se pudo conectar al servicio AWS. No se cambió de destino; consulta la tarea si ya fue iniciada."
            ) from None

    def post(self, path: str, payload: dict) -> dict:
        """Authenticate against one configured API using its snake_case contracts."""
        data = self._request(
            self.endpoint + path,
            json.dumps(payload).encode(),
            {"x-api-key": self.api_key, "Content-Type": "application/json"},
        )
        try:
            result = json.loads(data)
        except (ValueError, UnicodeError):
            raise ValueError("Titvo devolvió una respuesta JSON inválida.") from None
        if not isinstance(result, dict):
            raise ValueError("Titvo devolvió una respuesta inesperada.")
        return result

    def start(self, archive: bytes, repository_url: str, branch: str) -> str:
        """Create a fresh batch, PUT the frozen archive, and trigger only after upload."""
        batch_id = str(uuid.uuid4())
        name = "snapshot.tar.gz"
        signed = self.post(
            "/cli-files",
            {
                "source": "cli",
                "args": {
                    "batch_id": batch_id,
                    "files": [{"name": name, "content_type": "application/gzip"}],
                },
            },
        )
        # The deployed use case returns a mapping. Older documented responses use a list.
        urls = signed.get("presigned_urls")
        url = (
            urls.get(name)
            if isinstance(urls, dict)
            else next(
                (
                    item.get("url")
                    for item in urls
                    if isinstance(item, dict) and item.get("name") == name
                ),
                None,
            )
            if isinstance(urls, list)
            else None
        )
        if not isinstance(url, str):
            raise ValueError(
                "Titvo no entregó una URL para el snapshot; no se inició el análisis."
            )
        https_url(url)
        self._request(url, archive, {"Content-Type": "application/gzip"}, "PUT")
        response = self.post(
            "/run-scan",
            {
                "source": "cli",
                "args": {
                    "batch_id": batch_id,
                    "repository_url": repository_url,
                    "branch": branch,
                    "scan_mode": "full",
                },
            },
        )
        task_id = response.get("scan_id")
        validate_task_id(task_id)
        return task_id

    def status(self, task_id: str) -> dict:
        """Read the same /scan-status API used by the current CI integrations."""
        validate_task_id(task_id)
        response = self.post("/scan-status", {"scan_id": task_id})
        if not isinstance(response.get("status"), str):
            raise ValueError("Respuesta sin estado de tarea.")
        return response

    def wait(
        self, task_id: str, timeout: float, update=None, interval: float = 3
    ) -> dict:
        """Poll within a finite deadline; timeout never cancels or restarts the AWS job."""
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("El tiempo de espera debe ser positivo y finito.")
        deadline = time.monotonic() + timeout
        while True:
            response = self.status(task_id)
            if update:
                update(response)
            if response["status"] in TERMINAL:
                return response
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError(
                    f"La tarea {task_id} sigue en AWS. Consulta con titvo status {task_id} --target aws; no vuelvas a subirla para consultar."
                )
            time.sleep(min(interval, remaining))


def validate_task_id(value):
    """Ensure remote IDs cannot escape the local reports directory."""
    if not isinstance(value, str) or not TASK_ID.fullmatch(value):
        raise ValueError(
            "Identificador de tarea inválido; consulta el historial del servicio."
        )


def save_result(
    response: dict, task_id: str, output: Path, project: str | None = None
) -> dict:
    """Save AWS metadata without fabricating inline findings, timestamps or model usage."""
    from titvo_cli.report import render

    validate_task_id(task_id)
    value = response.get("result")
    if value is not None and not isinstance(value, dict):
        raise ValueError("Titvo devolvió un resultado inesperado.")
    result = dict(value or {})
    result.setdefault("status", response["status"])
    result.update(task_id=task_id, target="aws", updated_at=response.get("updated_at"))
    if project:
        result["project"] = project
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{task_id}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)
    )
    (output / f"{task_id}.html").write_text(render(result))
    return result
