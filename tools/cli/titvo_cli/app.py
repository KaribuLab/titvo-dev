"""Rich terminal client for preview, scan and report retrieval in MiniStack."""

import json
import math
import os
import subprocess
import webbrowser
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from titvo_cli.presentation import WorkerProgress
from titvo_cli.snapshot import collect, package
from titvo_cli.storage import BUCKET, TASKS_TABLE, bootstrap, clients, upload
from titvo_cli.theme import ACCENT, BORDER, THEME
from titvo_cli.usage import summary_rows

app = typer.Typer(
    no_args_is_help=False, help="Titvo · Fullscan con MiniStack o servicio AWS"
)
console = Console(theme=THEME)
DEV_ROOT = Path(__file__).resolve().parents[3]


def check_endpoint(endpoint: str):
    """Keep laboratory writes on loopback rather than real AWS endpoints."""
    url = urlparse(endpoint)
    if url.hostname not in {"localhost", "127.0.0.1", "::1"} or url.scheme not in {
        "http",
        "https",
    }:
        raise typer.BadParameter(
            "El laboratorio requiere un endpoint local (localhost)."
        )


def show_preview(root: Path, files: dict, manifest: dict, target="ministack"):
    """Display the selected project and exclusion reasons without showing contents."""
    console.print(
        Panel(
            Text.assemble(
                ("TITVO", f"bold {ACCENT}"),
                f" · {root.resolve().name}\nFullscan del working tree · {'AWS · servicio Titvo' if target == 'aws' else 'MiniStack local'} · RAG desactivado",
            ),
            border_style=BORDER,
        )
    )
    table = Table(
        "Selección",
        "Cantidad",
        "Tamaño",
        header_style=f"bold {ACCENT}",
        border_style=BORDER,
    )
    table.add_row(
        "Archivos UTF-8",
        str(len(files)),
        f"{sum(map(len, files.values())) / 1024:.1f} KiB",
    )
    for reason, count in sorted(
        Counter(item["reason"] for item in manifest["excluded"]).items()
    ):
        table.add_row(reason, str(count), "excluidos")
    console.print(table)
    if manifest["missing_submodules"]:
        console.print(
            "[yellow]Submódulos sin inicializar:[/] "
            + ", ".join(manifest["missing_submodules"]),
            markup=False,
        )


@app.callback(invoke_without_command=True)
def menu(ctx: typer.Context):
    """Guiar una sesión interactiva o mostrar ayuda al usar una tubería."""
    if ctx.invoked_subcommand is not None:
        return
    if not console.is_terminal:
        console.print(ctx.get_help())
        return
    from titvo_cli.interactive import run_session

    run_session(console, DEV_ROOT, preview, guided_scan, status, show_result, dashboard)


@app.command()
def preview(
    project: Path = typer.Argument(Path(".")),
    json_output: bool = typer.Option(False, "--json"),
    list_files: bool = typer.Option(False, "--files"),
    include: list[str] | None = typer.Option(
        None, "--include", help="Ruta relativa a incluir; repetible"
    ),
    target: str = typer.Option("ministack", "--target", envvar="TITVO_TARGET"),
):
    """Inspeccionar archivos sin subirlos ni contactar un proveedor de IA."""
    if target not in {"ministack", "aws"}:
        raise typer.BadParameter("--target debe ser ministack o aws")
    try:
        files, manifest = collect(project, include)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        console.print(str(exc), style="red", markup=False)
        raise typer.Exit(2) from exc
    if json_output:
        typer.echo(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        show_preview(project, files, manifest, target=target)
        if list_files:
            for path in sorted(files):
                console.print(path, markup=False)


def download_report(s3, task_id: str, output: Path) -> dict:
    """Save JSON and HTML artifacts in a local report directory."""
    output.mkdir(parents=True, exist_ok=True)
    result = None
    for extension in ("json", "html"):
        data = s3.get_object(Bucket=BUCKET, Key=f"reports/{task_id}.{extension}")[
            "Body"
        ].read()
        (output / f"{task_id}.{extension}").write_bytes(data)
        if extension == "json":
            result = json.loads(data)
    assert result is not None
    return result


def show_result(result: dict, output: Path, limit: int = 10):
    """Summarize findings, model mode and completeness independently."""
    if result.get("model_mode") == "mock":
        console.print(
            "[yellow]IA SIMULADA: prueba de integración, no evaluación de seguridad.[/]"
        )
    from titvo_cli.outcome import (
        execution_state,
        finding_count,
        outcome_rows,
        technical_errors,
    )

    complete = result.get("coverage", {}).get("complete") is True
    issues = result.get("issues", [])
    count = finding_count(result)
    if execution_state(result) == "UNKNOWN":
        outcome, color = "Estado de ejecución no registrado", "yellow"
    elif execution_state(result) == "FAILED":
        outcome, color = "Análisis fallido · revisar errores", "red"
    elif not complete:
        outcome, color = "Análisis incompleto · revisar errores", "red"
    elif count is None:
        outcome, color = "Análisis completado · hallazgos no registrados", "yellow"
    elif count:
        outcome, color = "Análisis completado · hallazgos detectados", "yellow"
    else:
        outcome, color = "Análisis completado · sin hallazgos reportados", "green"
    console.print(
        Panel(
            f"{outcome}\n"
            + "\n".join(f"{label}: {value}" for label, value in outcome_rows(result))
            + "\n"
            f"Archivos: {result.get('scaned_files', 0)}\n"
            f"Cobertura de ejecución: {'no registrada' if execution_state(result) == 'UNKNOWN' else 'completa' if complete else 'INCOMPLETA'}\n"
            f"Hallazgos: {count if count is not None else 'No registrado'}",
            border_style=color,
        )
    )
    repaired = sum(
        expert.get("batches_repaired", 0)
        for expert in result.get("coverage", {}).get("experts", {}).values()
    )
    if repaired:
        console.print(
            f"Recuperación automática: {repaired} lotes corregidos.", style="cyan"
        )
    for error in technical_errors(result):
        console.print(error, style="red", markup=False)
    if result.get("truncated_files"):
        console.print(
            f"Archivos con contenido truncado: {len(result['truncated_files'])}",
            style="yellow",
        )
    table = Table(
        "Severidad",
        "Ubicación",
        "Hallazgo",
        header_style=f"bold {ACCENT}",
        border_style=BORDER,
    )
    for issue in issues[:limit]:
        severity = issue.get("severity", "")
        table.add_row(
            Text(
                severity,
                style={"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow"}.get(
                    severity, "cyan"
                ),
            ),
            Text(f"{issue.get('path')}:{issue.get('line')}"),
            Text(issue.get("title", "")),
        )
    console.print(table)
    if result.get("report_url"):
        console.print(f"Reporte completo: {result['report_url']}", markup=False)
    if len(issues) > limit:
        console.print(
            f"{len(issues) - limit} hallazgos adicionales disponibles en el reporte.",
            style="dim",
        )
    summary = Table(
        "Resumen final", "Resultado", header_style=f"bold {ACCENT}", border_style=BORDER
    )
    for label, value in summary_rows(result):
        summary.add_row(Text(label), Text(value))
    console.print(summary)
    console.print(
        "Costo de llamadas IA; no incluye infraestructura ni embeddings.", style="dim"
    )
    console.print(f"Reportes: {output.resolve()}", markup=False)


@app.command()
def scan(
    project: Path = typer.Argument(Path(".")),
    endpoint: str = "http://localhost:4566",
    model: str | None = None,
    yes: bool = typer.Option(False, "--yes", "-y"),
    allow_remote_ai: bool = False,
    output: Path = Path(".titvo/reports"),
    include: list[str] | None = typer.Option(
        None, "--include", help="Ruta relativa a incluir; repetible"
    ),
    target: str = typer.Option("ministack", "--target", envvar="TITVO_TARGET"),
    api_url: str | None = typer.Option(
        None, "--api-endpoint", envvar="TITVO_API_ENDPOINT"
    ),
    repository_url: str | None = typer.Option(
        None, "--repository-url", envvar="TITVO_REPOSITORY_URL"
    ),
    branch: str | None = typer.Option(None, "--branch", envvar="TITVO_BRANCH"),
    wait_timeout: float = typer.Option(1800, "--wait-timeout", min=1),
):
    """Preparar un snapshot y ejecutar el análisis en el destino elegido."""
    execute_scan(
        project,
        endpoint,
        model,
        yes,
        allow_remote_ai,
        output,
        include,
        target=target,
        api_url=api_url,
        repository_url=repository_url,
        branch=branch,
        wait_timeout=wait_timeout,
    )


def guided_scan(
    project, endpoint, model, yes, allow_remote_ai, output, include, **options
):
    """Use one final authorization prompt for the interactive review flow."""
    return execute_scan(
        project,
        endpoint,
        model,
        yes,
        allow_remote_ai,
        output,
        include,
        guided=True,
        **options,
    )


def execute_scan(
    project,
    endpoint,
    model,
    yes,
    allow_remote_ai,
    output,
    include,
    guided=False,
    target="ministack",
    api_url=None,
    repository_url=None,
    branch=None,
    wait_timeout=1800,
):
    """Execute an identical snapshot in scripted and guided modes."""
    if target not in {"ministack", "aws"}:
        raise typer.BadParameter("--target debe ser ministack o aws")
    if target == "aws":
        if model not in {None, "service"}:
            raise typer.BadParameter(
                "AWS usa el modelo configurado en el servicio; omite --model."
            )
        return execute_cloud_scan(
            project,
            api_url,
            repository_url,
            branch,
            yes,
            output,
            include,
            guided,
            wait_timeout,
        )
    model = model or "mock"
    check_endpoint(endpoint)
    if model not in {"mock", "real"}:
        raise typer.BadParameter("--model debe ser mock o real")
    if model == "real" and not allow_remote_ai:
        raise typer.BadParameter(
            "El modelo real envía código al proveedor: usa --allow-remote-ai explícitamente."
        )
    try:
        files, manifest = collect(project, include)
        show_preview(project, files, manifest)
        if not files or manifest["missing_submodules"]:
            raise ValueError(
                "No se puede iniciar: selección vacía o submódulos sin inicializar."
            )
        if guided:
            import questionary

            from titvo_cli.interactive import STYLE

            message = "¿Iniciar esta prueba con IA simulada?"
            if model == "real":
                import os

                provider = os.getenv("TITVO_AI_PROVIDER", "openai")
                ai_model = os.getenv("TITVO_AI_MODEL", "")
                if not os.getenv("TITVO_AI_API_KEY") or not ai_model:
                    raise ValueError(
                        "Configura el modelo y la API key antes de analizar."
                    )
                console.print(f"Modelo: {provider} / {ai_model}", markup=False)
                message = f"¿Iniciar y autorizar el envío del código seleccionado a {provider}?"
            if not questionary.confirm(message, default=False, style=STYLE).ask():
                raise typer.Exit()
        elif not yes and not typer.confirm(
            "¿Subir estos archivos al MiniStack local e iniciar?"
        ):
            raise typer.Exit()
        s3, dynamodb = clients(endpoint)
        with console.status("Preparando recursos y subiendo snapshot…"):
            bootstrap(s3, dynamodb)
            task_id = upload(s3, dynamodb, package(files, manifest), manifest, model)
        console.print(f"Tarea: {task_id}", markup=False)
        compose_file = DEV_ROOT / "docker-compose.ministack.yaml"
        if not compose_file.exists():
            raise RuntimeError(
                "Instala la CLI en modo editable desde titvo-dev/tools/cli"
            )
        cmd = [
            "docker",
            "compose",
            "-f",
            str(DEV_ROOT / "docker-compose.ministack.yaml"),
            "run",
            "--rm",
            "--no-deps",
            "worker",
            "--task-id",
            task_id,
        ]
        progress = WorkerProgress(animate=console.is_terminal)
        logs = []
        with Live(progress, console=console, refresh_per_second=4):
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            assert process.stdout is not None
            for line in process.stdout:
                if line.startswith("TITVO_EVENT "):
                    event = json.loads(line[len("TITVO_EVENT ") :])
                    progress.update(event)
                elif not line.startswith("TITVO_RESULT "):
                    logs.append(line)
            code = process.wait()
        console.print()
        import os

        # Keep technical output available without displaying Docker chatter.
        log_text = "".join(logs)
        api_key = os.getenv("TITVO_AI_API_KEY")
        if api_key:
            log_text = log_text.replace(api_key, "[API KEY OCULTA]")
        output.mkdir(parents=True, exist_ok=True)
        log_path = output / f"{task_id}.log"
        log_path.write_text(log_text)
        console.print(f"Detalle técnico: {log_path.resolve()}", markup=False)
        if code not in (0, 2):
            raise RuntimeError(
                f"El contenedor falló (exit {code}); consulta tarea {task_id}."
            )
        result = download_report(s3, task_id, output)
        show_result(result, output, limit=5 if guided else 10)
        if guided:
            return result
        raise typer.Exit(0 if result["coverage"]["complete"] else 2)
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"Error: {exc}", style="red", markup=False)
        raise typer.Exit(2) from exc


@app.command()
def status(
    task_id: str,
    endpoint: str = "http://localhost:4566",
    output: Path = Path(".titvo/reports"),
    json_output: bool = typer.Option(False, "--json"),
    target: str = typer.Option("ministack", "--target", envvar="TITVO_TARGET"),
    api_url: str | None = typer.Option(
        None, "--api-endpoint", envvar="TITVO_API_ENDPOINT"
    ),
):
    """Consultar una tarea en el destino elegido, sin reiniciar el análisis."""
    if target == "aws":
        from titvo_cli.cloud import TERMINAL, CloudClient, save_result

        try:
            response = CloudClient(api_url).status(task_id)
            if json_output:
                typer.echo(json.dumps(response, ensure_ascii=False, indent=2))
            elif response["status"] in TERMINAL:
                show_result(save_result(response, task_id, output), output)
            else:
                console.print(f"AWS · {task_id} · {response['status']}", markup=False)
        except (ValueError, OSError) as exc:
            console.print(str(exc), style="red", markup=False)
            raise typer.Exit(2) from exc
        return
    if target != "ministack":
        raise typer.BadParameter("--target debe ser ministack o aws")
    check_endpoint(endpoint)
    try:
        s3, dynamodb = clients(endpoint)
        item = dynamodb.get_item(
            TableName=TASKS_TABLE, Key={"scan_id": {"S": task_id}}, ConsistentRead=True
        ).get("Item")
        if not item:
            raise ValueError("Tarea no encontrada")
        if "report_key" in item:
            result = download_report(s3, task_id, output)
            if json_output:
                typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                show_result(result, output)
        else:
            data = {"task_id": task_id, "status": item["status"]["S"]}
            typer.echo(json.dumps(data))
    except Exception as exc:
        console.print(str(exc), style="red", markup=False)
        raise typer.Exit(2) from exc


@app.command()
def dashboard(
    endpoint: str = "http://localhost:4566",
    port: int = 5173,
    api_port: int = 8787,
    target: str = typer.Option("ministack", "--target", envvar="TITVO_TARGET"),
    dashboard_url: str | None = typer.Option(
        None, "--dashboard-url", envvar="TITVO_DASHBOARD_URL"
    ),
):
    """Abrir el dashboard existente con resultados locales de MiniStack."""
    if target == "aws":
        from titvo_cli.cloud import https_url

        url = dashboard_url or os.getenv("TITVO_DASHBOARD_URL", "")
        if not url:
            raise typer.BadParameter("Configura TITVO_DASHBOARD_URL o --dashboard-url.")
        try:
            https_url(url)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        console.print(f"Dashboard AWS: {url}", markup=False)
        webbrowser.open(url)
        return
    if target != "ministack":
        raise typer.BadParameter("--target debe ser ministack o aws")
    from titvo_cli.dashboard import launch

    check_endpoint(endpoint)
    s3, dynamodb = clients(endpoint)
    console.print(
        f"Dashboard: http://127.0.0.1:{port} · MiniStack · solo lectura", markup=False
    )
    console.print(
        "Inicia análisis desde otra terminal con titvo scan. Ctrl+C para cerrar."
    )
    try:
        launch(DEV_ROOT, s3, dynamodb, port, api_port)
    except (ValueError, OSError) as exc:
        console.print(str(exc), style="red", markup=False)
        raise typer.Exit(2) from exc


def execute_cloud_scan(
    project, api_url, repository_url, branch, yes, output, include, guided, wait_timeout
):
    """Reuse preview and authorization, then upload and poll the existing AWS API."""
    from titvo_cli.cloud import CloudClient, repository_identity, save_result
    from titvo_cli.outcome import execution_state

    try:
        if not math.isfinite(wait_timeout) or wait_timeout <= 0:
            raise ValueError("El tiempo de espera debe ser positivo y finito.")
        client = CloudClient(api_url)
        repository_url, branch = repository_identity(project, repository_url, branch)
        files, manifest = collect(project, include)
        show_preview(project, files, manifest, target="aws")
        console.print(
            f"Destino: AWS · {client.endpoint}\nRepositorio: {repository_url} · {branch}\nModelo: configurado en el servicio",
            markup=False,
        )
        if not files or manifest["missing_submodules"]:
            raise ValueError(
                "No se puede iniciar: selección vacía o submódulos sin inicializar."
            )
        message = f"¿Subir el código seleccionado a {client.endpoint} e iniciar el análisis AWS con IA del servicio?"
        if guided:
            import questionary

            from titvo_cli.interactive import STYLE

            authorized = questionary.confirm(message, default=False, style=STYLE).ask()
        else:
            authorized = yes or typer.confirm(message)
        if not authorized:
            raise typer.Exit()
        with console.status("AWS · subiendo snapshot y solicitando análisis…"):
            task_id = client.start(package(files, manifest), repository_url, branch)
        console.print(f"Tarea AWS: {task_id}", markup=False)
        console.print(
            f"Para consultar después: titvo status {task_id} --target aws", markup=False
        )
        progress = WorkerProgress(animate=console.is_terminal)
        progress.phase, progress.expert = "AWS · esperando resultado", "Estado remoto"

        def update(response):
            """Display only the state returned by AWS, without invented batch counts."""
            progress.expert = response["status"]

        try:
            with Live(progress, console=console, refresh_per_second=4):
                response = client.wait(task_id, wait_timeout, update=update)
        except KeyboardInterrupt:
            console.print(
                f"Consulta interrumpida; {task_id} sigue en AWS. Usa titvo status {task_id} --target aws.",
                markup=False,
            )
            raise typer.Exit(130) from None
        result = save_result(response, task_id, output, manifest["project"])
        show_result(result, output, limit=5 if guided else 10)
        if guided:
            return result
        state = execution_state(result)
        raise typer.Exit(
            0
            if state == "COMPLETED"
            or state == "UNKNOWN"
            and response["status"] == "COMPLETED"
            else 2
        )
    except typer.Exit:
        raise
    except (ValueError, OSError) as exc:
        console.print(str(exc), style="red", markup=False)
        raise typer.Exit(2) from exc


if __name__ == "__main__":
    app()
