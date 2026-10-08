"""Interactive terminal workspace; credentials and choices live only in this process."""

import json
import os
import webbrowser
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import questionary
import typer
from prompt_toolkit.keys import Keys
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from titvo_cli.outcome import outcome_rows
from titvo_cli.presentation import animation_enabled, identity
from titvo_cli.theme import ACCENT, BORDER, SOFT
from titvo_cli.usage import summary_rows

STYLE = questionary.Style(
    [
        ("qmark", f"fg:{ACCENT} bold"),
        ("question", f"fg:{SOFT} bold"),
        ("answer", f"fg:{ACCENT}"),
        ("pointer", f"fg:{ACCENT} bold"),
        ("highlighted", f"fg:{SOFT} bg:#25233f bold"),
        ("selected", f"fg:{ACCENT}"),
        ("instruction", "fg:#888888"),
    ]
)
AI_ENV = (
    "TITVO_AI_PROVIDER",
    "TITVO_AI_MODEL",
    "TITVO_AI_API_KEY",
    "TITVO_API_KEY",
    "TITVO_API_ENDPOINT",
)


@dataclass
class Session:
    """Retain selection between menu actions without persisting credentials."""

    project: Path | None = None
    include: list[str] = field(default_factory=list)
    mode: str = "mock"
    scope_ready: bool = False
    model_ready: bool = False
    provider: str = "openai"
    model: str = ""
    target: str = "ministack"
    target_ready: bool = True
    api_url: str = ""
    dashboard_url: str = ""
    repository_url: str = ""
    branch: str = ""


@dataclass
class MenuFrame:
    """Keep one terminal workspace while navigating nested menu screens."""

    console: Console
    session: Session
    body: object = None
    tick: int = 0


FRAME: ContextVar[MenuFrame | None] = ContextVar("titvo_menu_frame", default=None)


def redraw(title: str, show_body: bool = True):
    """Replace the current menu screen; command output remains visible until return."""
    frame = FRAME.get()
    if frame is None:
        return
    pose = frame.tick if animation_enabled(frame.console.is_terminal) else 0
    frame.tick += 1
    if frame.console.is_terminal:
        frame.console.clear()
    if show_body and frame.body is not None:
        frame.console.print(
            identity(
                "Resultados del análisis",
                frame.session.project.name if frame.session.project else "",
                frame=pose,
            )
        )
        frame.console.print(frame.body)
    else:
        banner(frame.console, frame.session, mascot_frame=pose)
    frame.console.print()


def ask(factory, message, **options):
    """Redraw before each text/path/secret form without changing typing semantics."""
    redraw(message)
    return factory(message, style=STYLE, **options).ask()


def report_overview(result: dict) -> Panel:
    """Keep the execution outcome and cost visible above the report actions."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    for label, value in outcome_rows(result):
        table.add_row(label, value)
    for label, value in summary_rows(result)[:4]:
        table.add_row(Text(label), Text(value))
    return Panel(table, title="Resultado", border_style=BORDER)


def menu_keys(question):
    """Add Vim enter/back keys to lists only; text and passwords remain literal."""
    bindings = question.application.key_bindings

    @bindings.add("escape", eager=True)
    @bindings.add("h", eager=True)
    def back(event):
        event.app.exit(result=None)

    enter = bindings.get_bindings_for_keys((Keys.ControlM,))
    if enter:
        bindings.add("l", eager=True)(enter[-1].handler)
    return question


def choose(message: str, choices: list[tuple[str, object]]):
    """Select a value with arrows; Ctrl+C returns to the caller."""
    redraw(message)
    # Questionary replaces a None choice value with its title. Preserve our
    # exit/back contract through a private non-null value, distinct from cancel.
    back_value = object()
    answer = menu_keys(
        questionary.select(
            message,
            choices=[
                questionary.Choice(title, value=back_value if value is None else value)
                for title, value in choices
            ],
            style=STYLE,
            pointer="▸",
            use_arrow_keys=True,
            use_jk_keys=True,
            use_search_filter=False,
            erase_when_done=True,
            instruction="↑/k ↓/j · Enter/l elegir · Esc/h volver",
        )
    ).ask()
    return None if answer is back_value else answer


def banner(console: Console, session: Session, mascot_frame: int = 0):
    """Render one compact workspace with completed and pending preparation steps."""
    console.print(
        identity(
            "Seguridad para tu código",
            session.project.name
            if session.project
            else "Elige un proyecto para empezar",
            frame=mascot_frame,
        )
    )
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", no_wrap=True)
    table.add_column()
    table.add_row(
        "Destino",
        "AWS · servicio Titvo" if session.target == "aws" else "MiniStack · local",
    )
    if session.target == "aws":
        table.add_row("API", session.api_url or "Por configurar")
    table.add_row(
        "✓ Proyecto" if session.project else "○ Proyecto",
        str(session.project or "Pendiente"),
    )
    table.add_row(
        "✓ Alcance" if session.scope_ready else "○ Alcance",
        ", ".join(session.include)
        or (
            "Todo el proyecto · respetar exclusiones"
            if session.scope_ready
            else "Por confirmar"
        ),
    )
    model = "IA simulada · prueba del flujo"
    if session.target == "aws":
        model = "Configurado en el servicio Titvo"
    elif session.mode == "real":
        model = f"{os.getenv('TITVO_AI_PROVIDER', 'openai')} / {os.getenv('TITVO_AI_MODEL') or 'pendiente'}"
    table.add_row(
        "✓ Modelo" if session.target == "aws" or session.model_ready else "○ Modelo",
        model if session.target == "aws" or session.model_ready else "Por configurar",
    )
    if session.target == "aws":
        table.add_row(
            "Clave Titvo",
            "Configurada · conexión aún no verificada"
            if os.getenv("TITVO_API_KEY")
            else "Pendiente",
        )
    elif session.mode == "real":
        table.add_row(
            "Credencial",
            "Configurada · conexión aún no verificada"
            if os.getenv("TITVO_AI_API_KEY")
            else "Pendiente · se solicitará al revisar",
        )
    console.print(Panel(table, border_style=BORDER))
    console.print(
        "AWS · agente remoto · modelo del servicio"
        if session.target == "aws"
        else "MiniStack local · agente Docker · RAG desactivado",
        style="dim",
    )


def load_session(path: Path, cwd: Path, dev_root: Path) -> Session:
    """Restore only validated, non-secret choices; stale paths require setup again."""
    session = Session(
        project=cwd.resolve() if cwd.resolve() != dev_root.resolve() else None,
        target_ready=False,
    )
    try:
        data = json.loads(path.read_text())
        if data.get("target") in {"aws", "ministack"}:
            session.target, session.target_ready = data["target"], True
        for name in ("api_url", "dashboard_url"):
            if isinstance(data.get(name), str):
                from titvo_cli.cloud import https_url

                if data[name]:
                    https_url(data[name])
                setattr(session, name, data[name])
        if not data.get("project"):
            return session
        project = Path(data["project"])
        if not project.is_dir():
            return session
        include = data.get("include", [])
        if not isinstance(include, list) or not all(
            isinstance(value, str) for value in include
        ):
            return session
        if any(
            Path(value).is_absolute() or ".." in Path(value).parts for value in include
        ):
            return session
        if cwd.resolve() != dev_root.resolve() and project.resolve() != cwd.resolve():
            return session
        session.repository_url = (
            data.get("repository_url", "")
            if isinstance(data.get("repository_url"), str)
            else ""
        )
        session.branch = (
            data.get("branch", "") if isinstance(data.get("branch"), str) else ""
        )
        session.project = project.resolve()
        session.include = include
        session.scope_ready = bool(data.get("scope_ready")) and all(
            (project / value).is_dir() for value in include
        )
        session.mode = "real" if data.get("mode") == "real" else "mock"
        session.provider = data.get("provider", "openai")
        session.model = data.get("model", "")
        if session.provider not in {
            "openai",
            "openrouter",
            "anthropic",
            "google",
        } or not isinstance(session.model, str):
            session.provider, session.model = "openai", ""
        session.model_ready = bool(data.get("model_ready")) and (
            session.mode == "mock" or bool(session.model)
        )
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return session


def save_session(console: Console, path: Path, session: Session):
    """Persist an explicit allowlist of preferences, never environment or API keys."""
    data = {
        "project": str(session.project) if session.project else None,
        "target": session.target,
        "api_url": session.api_url,
        "dashboard_url": session.dashboard_url,
        "repository_url": session.repository_url,
        "branch": session.branch,
        "include": session.include,
        "mode": session.mode,
        "scope_ready": session.scope_ready,
        "model_ready": session.model_ready,
        "provider": session.provider,
        "model": session.model,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        temporary.replace(path)
    except OSError:
        console.print(
            "No se pudieron guardar preferencias; la sesión sigue disponible.",
            style="yellow",
        )


def pause():
    """Leave results visible until the user explicitly returns to the dashboard."""
    questionary.press_any_key_to_continue("Enter para volver al proyecto…").ask()


def select_project(console: Console, session: Session, dev_root: Path) -> bool:
    """Offer available projects and directory completion for another local path."""
    candidates = [
        ("Demo · prueba pequeña", dev_root / "tools/cli/fixtures/demo"),
        ("Carpeta actual", Path.cwd()),
    ]
    options = [
        (f"{label}  ·  {path.name}", path)
        for label, path in candidates
        if path.is_dir()
    ]
    options += [("Otra carpeta…", "custom"), ("Volver", None)]
    selected = choose("¿Qué proyecto revisamos?", options)
    if selected == "custom":
        value = ask(
            questionary.path,
            "Carpeta del proyecto",
            only_directories=True,
            default=str(session.project or Path.cwd()),
        )
        selected = Path(value).expanduser() if value else None
    if selected is None:
        return False
    root = Path(selected).resolve()
    if not root.is_dir():
        console.print("La carpeta no existe.", style="red")
        return False
    if session.project != root:
        session.project, session.include = root, []
        session.scope_ready = False
        session.repository_url, session.branch = "", ""
    return True


def select_scope(session: Session):
    """Choose top-level folders, while retaining existing ignore rules."""
    assert session.project is not None
    base = session.project / "src"
    if not base.is_dir():
        base = session.project
    folders = [
        path
        for path in sorted(base.iterdir())
        if path.is_dir()
        and not path.name.startswith(".")
        and path.name not in {"node_modules", "build", "dist", "venv"}
    ]
    scope = choose(
        "Alcance del análisis",
        [
            ("Todo el proyecto · respetar exclusiones", "all"),
            ("Seleccionar carpetas", "folders"),
            ("Volver", None),
        ],
    )
    if scope == "all":
        session.include = []
        session.scope_ready = True
        return True
    elif scope == "folders":
        redraw("Carpetas a incluir")
        selected = (
            menu_keys(
                questionary.checkbox(
                    "Carpetas a incluir",
                    choices=[
                        questionary.Choice(
                            str(path.relative_to(session.project)),
                            checked=str(path.relative_to(session.project))
                            in session.include,
                        )
                        for path in folders
                    ],
                    style=STYLE,
                    instruction="↑/k ↓/j · Espacio marcar · Enter/l confirmar · Esc/h volver",
                    use_arrow_keys=True,
                    use_jk_keys=True,
                    erase_when_done=True,
                    validate=lambda values: (
                        bool(values) or "Selecciona al menos una carpeta"
                    ),
                )
            ).ask()
            if folders
            else None
        )
        if selected:
            session.include = selected
            session.scope_ready = True
            return True
    return False


def select_target(console: Console, session: Session) -> bool:
    """Choose a destination explicitly and keep its non-secret connection settings."""
    from titvo_cli.cloud import api_endpoint, https_url

    target = choose(
        "¿Dónde quieres ejecutar el análisis?",
        [
            ("MiniStack · entorno local", "ministack"),
            ("AWS · servicio de Titvo", "aws"),
            ("Volver", None),
        ],
    )
    if target not in {"ministack", "aws"}:
        return False
    if target == "aws":

        def valid_url(value, optional=False):
            """Keep malformed endpoints in the form instead of crashing the menu."""
            if optional and not value.strip():
                return True
            if not value.strip():
                return "Escribe el endpoint HTTPS de tu instancia Titvo"
            try:
                (https_url if optional else api_endpoint)(value.strip())
                return True
            except ValueError as exc:
                return str(exc)

        value = ask(
            questionary.text,
            "Endpoint HTTPS de la API Titvo",
            default=session.api_url or os.getenv("TITVO_API_ENDPOINT", ""),
            validate=valid_url,
        )
        if not value:
            return False
        endpoint = api_endpoint(value.strip())
        dashboard = ask(
            questionary.text,
            "URL del dashboard AWS · opcional",
            default=session.dashboard_url or os.getenv("TITVO_DASHBOARD_URL", ""),
            validate=lambda value: valid_url(value, optional=True),
        )
        if dashboard is None:
            return False
        dashboard = dashboard.strip()
        if dashboard:
            https_url(dashboard)
        if (
            os.getenv("TITVO_API_ENDPOINT")
            and os.environ["TITVO_API_ENDPOINT"].rstrip("/") != endpoint
        ):
            os.environ.pop("TITVO_API_KEY", None)
        session.api_url, session.dashboard_url = endpoint, dashboard
        os.environ["TITVO_API_ENDPOINT"] = endpoint
    session.target, session.target_ready = target, True
    return True


def cloud_credentials(session: Session, replace=False) -> bool:
    """Request only the Titvo key and never persist it or an AI provider key."""
    from titvo_cli.cloud import api_endpoint

    endpoint = api_endpoint(session.api_url or None)
    if (
        os.getenv("TITVO_API_ENDPOINT")
        and os.environ["TITVO_API_ENDPOINT"].rstrip("/") != endpoint
    ):
        os.environ.pop("TITVO_API_KEY", None)
    session.api_url = endpoint
    os.environ["TITVO_API_ENDPOINT"] = endpoint
    if replace or not os.getenv("TITVO_API_KEY"):
        key = ask(questionary.password, "Clave Titvo (tvok…) · solo para esta sesión")
        if not key:
            return False
        os.environ["TITVO_API_KEY"] = key
    return True


def configure(console: Console, session: Session):
    """Configure the mode and remote provider without writing a secret to disk."""
    if session.target == "aws":
        return cloud_credentials(session, replace=True)
    mode = choose(
        "¿Cómo quieres analizar?",
        [
            ("IA simulada · sin llamadas al proveedor", "mock"),
            ("Modelo real · usa créditos del proveedor", "real"),
            ("Volver", None),
        ],
    )
    if mode is None:
        return
    if mode == "mock":
        session.mode = mode
        session.model_ready = True
        return True
    provider = choose(
        "Proveedor del modelo",
        [(name, name) for name in ("openai", "openrouter", "anthropic", "google")],
    )
    if not provider:
        return
    same_provider = provider == os.getenv("TITVO_AI_PROVIDER", "openai")
    model = ask(
        questionary.text,
        "Nombre del modelo",
        default=os.getenv("TITVO_AI_MODEL", "") if same_provider else "",
        validate=lambda value: bool(value.strip()) or "Escribe el modelo",
    )
    if not model:
        return
    key = os.getenv("TITVO_AI_API_KEY", "") if same_provider else ""
    if key:
        keep = ask(
            questionary.confirm, "¿Usar la API key ya configurada?", default=True
        )
        if keep is None:
            return
        if not keep:
            key = ""
    if not key:
        key = ask(questionary.password, "API key del proveedor · solo para esta sesión")
    if not key:
        console.print("Configuración cancelada: falta la API key.", style="yellow")
        return
    os.environ.update(
        TITVO_AI_PROVIDER=provider, TITVO_AI_MODEL=model.strip(), TITVO_AI_API_KEY=key
    )
    session.mode = "real"
    session.provider, session.model = provider, model.strip()
    session.model_ready = True
    console.print(
        "Modelo configurado. La clave no se guarda en archivos.", style="cyan"
    )
    return True


def local_reports(console: Console, output: Path, show_result: Callable):
    """Browse saved reports and optionally open the chosen HTML in the browser."""
    options = []
    for path in sorted(
        output.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        try:
            data = json.loads(path.read_text())
            label = f"{data.get('project', 'Proyecto')} · {data.get('model_mode', '?')} · {path.stem[:8]}"
            options.append((label, path))
        except (OSError, ValueError):
            continue
    if not options:
        console.print(
            "Todavía no hay reportes locales en esta carpeta.", style="yellow"
        )
        return
    path = choose("Reportes recientes", options + [("Volver", None)])
    if path is None:
        return
    show_result(json.loads(path.read_text()), output)
    explore_report(console, json.loads(path.read_text()), path)


def explore_report(console: Console, result: dict, path: Path):
    """Browse evidence and recommendations without rendering report text as markup."""
    issues = result.get("issues", [])
    frame = FRAME.get()
    if frame is not None:
        frame.body = report_overview(result)
    while True:
        options = [
            (
                f"{issue.get('severity', '?')} · {issue.get('path', '?')}:{issue.get('line', '?')} · {issue.get('title', 'Hallazgo')}",
                index,
            )
            for index, issue in enumerate(issues)
        ]
        options.insert(0, ("Ver resumen completo", "summary"))
        html = path.with_suffix(".html")
        remote_url = result.get("report_url")
        if isinstance(remote_url, str) and remote_url.startswith("https://"):
            options.append(("Abrir reporte completo AWS", "remote"))
        if html.is_file():
            options.append(("Abrir reporte HTML", "html"))
        options.append(("Volver al proyecto", None))
        selected = choose("Explorar resultado", options)
        if selected is None:
            if frame is not None:
                frame.body = None
            return
        if selected == "summary":
            redraw("Resumen del análisis", show_body=False)
            console.print(report_overview(result))
            table = Table("Detalle", "Resultado")
            for label, value in summary_rows(result):
                table.add_row(Text(label), Text(value))
            console.print(table)
            pause()
            continue
        if selected == "remote":
            from titvo_cli.cloud import https_url

            webbrowser.open(https_url(remote_url))
            continue
        if selected == "html":
            webbrowser.open(html.resolve().as_uri())
            continue
        issue = issues[selected]
        redraw("Hallazgo seleccionado", show_body=False)
        console.print(
            Panel(
                Text(str(issue.get("title", "Hallazgo"))),
                title=Text(str(issue.get("severity", ""))),
                border_style="yellow",
            )
        )
        console.print(
            f"{issue.get('path', '?')}:{issue.get('line', '?')}",
            style="cyan",
            markup=False,
        )
        for label, key in [
            ("Explicación", "description"),
            ("Resumen", "summary"),
            ("Recomendación", "recommendation"),
        ]:
            if issue.get(key):
                console.print(label, style="bold")
                console.print(str(issue[key]), markup=False)
        if issue.get("code"):
            console.print(Syntax(str(issue["code"]), "text", word_wrap=True))
        pause()


def prepare_review(console: Console, session: Session, dev_root: Path) -> bool:
    """Complete only missing steps; the scan performs final preview and authorization."""
    if not session.target_ready and not select_target(console, session):
        return False
    if session.project is None and not select_project(console, session, dev_root):
        return False
    if not session.scope_ready and not select_scope(session):
        return False
    if session.target == "aws":
        from titvo_cli.cloud import repository_identity

        if not cloud_credentials(session):
            return False
        try:
            session.repository_url, session.branch = repository_identity(
                session.project, session.repository_url or None, session.branch or None
            )
        except ValueError:
            repository_url = ask(
                questionary.text,
                "URL Git del proyecto · identifica el historial",
                default=session.repository_url,
            )
            branch = ask(questionary.text, "Rama del proyecto", default=session.branch)
            if not repository_url or not branch:
                return False
            session.repository_url, session.branch = repository_identity(
                session.project, repository_url, branch
            )
        return True
    if not session.model_ready and not configure(console, session):
        return False
    if session.mode == "real" and not os.getenv("TITVO_AI_API_KEY"):
        key = ask(questionary.password, "API key del proveedor · solo para esta sesión")
        if not key:
            return False
        os.environ["TITVO_AI_API_KEY"] = key
    return True


def adjustments(console: Console, session: Session, dev_root: Path, preview: Callable):
    """Keep advanced setup out of the primary review action."""
    action = choose(
        "Ajustar análisis",
        [
            ("Cambiar destino · MiniStack / AWS", "target"),
            ("Cambiar proyecto", "project"),
            ("Cambiar alcance", "scope"),
            (
                "Clave Titvo" if session.target == "aws" else "Modelo y API key",
                "configure",
            ),
            ("Ver selección de archivos", "preview"),
            ("Volver", None),
        ],
    )
    if action == "target":
        select_target(console, session)
    elif action == "project":
        select_project(console, session, dev_root)
    elif action in {"scope", "preview"}:
        if session.project is None and not select_project(console, session, dev_root):
            return
        if action == "scope":
            select_scope(session)
        else:
            preview(
                session.project,
                json_output=False,
                list_files=False,
                include=session.include or None,
                **({"target": "aws"} if session.target == "aws" else {}),
            )
            pause()
    elif action == "configure":
        configure(console, session)


def _run_session(
    console: Console,
    dev_root: Path,
    preview: Callable,
    scan: Callable,
    status: Callable,
    show_result: Callable,
    dashboard: Callable | None = None,
):
    """Keep the menu alive after commands and restore inherited AI settings on exit."""
    inherited = {key: os.environ.get(key) for key in AI_ENV}
    preference_path = dev_root / ".titvo/ui.json"
    session = load_session(preference_path, Path.cwd(), dev_root)
    output = Path(".titvo/reports")
    token = FRAME.set(MenuFrame(console, session))
    try:
        if not session.target_ready:
            if not select_target(console, session):
                return
            save_session(console, preference_path, session)
        if session.mode == "real" and session.model_ready:
            if session.provider != os.getenv("TITVO_AI_PROVIDER", "openai"):
                os.environ.pop("TITVO_AI_API_KEY", None)
            os.environ.update(
                TITVO_AI_PROVIDER=session.provider, TITVO_AI_MODEL=session.model
            )
        while True:
            action = choose(
                "Tu proyecto",
                [
                    ("Revisar proyecto", "scan"),
                    ("Ajustar análisis", "settings"),
                    ("Reportes anteriores", "reports"),
                    ("Consultar tarea en curso", "status"),
                    ("Abrir dashboard", "dashboard"),
                    ("Salir", None),
                ],
            )
            if action is None:
                return
            try:
                if action == "settings":
                    adjustments(console, session, dev_root, preview)
                elif action == "scan":
                    if not prepare_review(console, session, dev_root):
                        continue
                    save_session(console, preference_path, session)
                    result = None
                    try:
                        result = scan(
                            session.project,
                            endpoint="http://localhost:4566",
                            model="service"
                            if session.target == "aws"
                            else session.mode,
                            yes=False,
                            allow_remote_ai=session.mode == "real",
                            output=output,
                            include=session.include or None,
                            **(
                                {
                                    "target": "aws",
                                    "api_url": session.api_url,
                                    "repository_url": session.repository_url,
                                    "branch": session.branch,
                                }
                                if session.target == "aws"
                                else {}
                            ),
                        )
                    except typer.Exit:
                        pass
                    if isinstance(result, dict) and result.get("task_id"):
                        path = output / f"{result['task_id']}.json"
                        explore_report(console, result, path)
                    else:
                        pause()
                elif action == "reports":
                    local_reports(console, output, show_result)
                    pause()
                elif action == "dashboard":
                    if dashboard is not None:
                        dashboard(
                            target=session.target,
                            dashboard_url=session.dashboard_url or None,
                        )
                        pause()
                elif action == "status":
                    if session.target == "aws" and not cloud_credentials(session):
                        continue
                    task_id = ask(questionary.text, "Identificador de tarea")
                    if task_id:
                        status(
                            task_id.strip(),
                            endpoint="http://localhost:4566",
                            output=output,
                            json_output=False,
                            **(
                                {"target": "aws", "api_url": session.api_url}
                                if session.target == "aws"
                                else {}
                            ),
                        )
                        pause()
            except typer.Exit:
                pause()
            except (OSError, ValueError) as exc:
                console.print(str(exc), style="red", markup=False)
                pause()
            finally:
                FRAME.get().body = None
                save_session(console, preference_path, session)
    finally:
        FRAME.reset(token)
        for key, value in inherited.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_session(
    console: Console,
    dev_root: Path,
    preview: Callable,
    scan: Callable,
    status: Callable,
    show_result: Callable,
    dashboard: Callable | None = None,
):
    """Use an alternate terminal workspace and restore the shell after exit."""
    with console.screen(hide_cursor=False):
        _run_session(console, dev_root, preview, scan, status, show_result, dashboard)
    console.print("¡Hasta pronto! 👋", style=ACCENT)
    console.print("Sesión cerrada. Tus reportes quedan guardados.", style="dim")
