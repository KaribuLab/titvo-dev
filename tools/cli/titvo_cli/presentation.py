"""Compact robot identity and truthful worker progress for the terminal UI."""

import os
from time import monotonic

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from titvo_cli.theme import ACCENT, BORDER, SOFT

ROBOT = (" ▄▟██▙▄", " ▐ ▪▪ ▌", "  ▀██▀", "  ▘  ▝")
ROBOT_FRAMES = (
    ROBOT,
    (" ▄▟██▙▄", " ▐ ▪▪ ▌", "  ▀██▀", " ▝  ▘ "),
    (" ▄▟██▙▄", " ▐ ── ▌", "  ▀██▀", "  ▘  ▝"),
    (" ▄▟██▙▄", " ▐ ▪▪ ▌", "  ▀██▀", " ▝  ▘ "),
)
EXPERTS = {
    "prompt_hardening": "Prompt Hardening",
    "owasp_api": "OWASP API",
    "owasp_web": "OWASP Web",
    "owasp_mobile": "OWASP Mobile",
    "devsecops": "DevSecOps",
    "code_vulnerabilities": "Vulnerabilidades de código",
}


def animation_enabled(enabled: bool = True) -> bool:
    """Honor static output and the terminal's explicit reduced-motion settings."""
    return (
        enabled
        and not os.getenv("TITVO_NO_ANIMATION")
        and not os.getenv("NO_COLOR")
        and os.getenv("TERM") != "dumb"
    )


def identity(
    title: str = "Seguridad para tu código", detail: str = "", frame: int = 0
) -> Table:
    """Render a four-line block mascot without emoji or a large frame."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style=ACCENT, no_wrap=True)
    table.add_column()
    for robot, message in zip(
        ROBOT_FRAMES[frame % len(ROBOT_FRAMES)], ["TITVO", title, detail, ""]
    ):
        table.add_row(
            Text(robot, style=ACCENT),
            Text(message, style=f"bold {SOFT}" if message == "TITVO" else ""),
        )
    return table


class WorkerProgress:
    """Display phases and real batch counters; never estimate unknown percentages."""

    def __init__(self, animate: bool = True):
        self.started = monotonic()
        self.animate = animation_enabled(animate)
        self.expert = "Preparando el agente"
        self.counter = ""
        self.phase = "Análisis y consolidación"

    def update(self, event: dict):
        """Apply counters emitted by the existing worker without inventing completion."""
        self.expert = EXPERTS.get(event["expert"], event["expert"])
        self.counter = event["batch"]
        self.phase = (
            "Corrigiendo respuesta"
            if event.get("kind") == "repair"
            else "Análisis y consolidación"
        )

    def render(self):
        """Build an elapsed-time panel for Rich Live refreshes."""
        duration = monotonic() - self.started
        elapsed = int(duration)
        frame = int(duration * 2) if self.animate else 0
        content = Text("✓ Archivos preparados\n✓ Snapshot subido\n", style="green")
        content.append(f"→ {self.phase} · {self.expert}", style=ACCENT)
        if self.counter:
            content.append(f" · lote {self.counter}", style=ACCENT)
        content.append("\n  Reporte · disponible al finalizar", style="dim")
        content.append(
            f"\n\nTiempo transcurrido: {elapsed // 60:02d}:{elapsed % 60:02d}"
        )
        return Group(
            identity("Revisando tu proyecto", frame=frame),
            Panel(content, border_style=BORDER),
        )

    def __rich__(self):
        """Let Rich refresh elapsed time while waiting for worker output."""
        return self.render()
