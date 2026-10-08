"""Generate an escaped HTML report without embedding project JavaScript."""

import html
import json

from titvo_cli.usage import summary_rows


def render(result: dict) -> str:
    """Show model mode, coverage and every finding with escaped code evidence."""

    def escape(value):
        """Escape untrusted project text for HTML."""
        return html.escape(str(value))

    cards = []
    for issue in result.get("issues", []):
        cards.append(f"""<article><span class="severity">{escape(issue.get("severity", ""))}</span>
<h2>{escape(issue.get("title", ""))}</h2><p>{escape(issue.get("path", ""))}:{escape(issue.get("line", ""))}</p>
<p>{escape(issue.get("description", ""))}</p><pre>{escape(issue.get("code", ""))}</pre>
<h3>Recomendación</h3><p>{escape(issue.get("recommendation", ""))}</p></article>""")
    summary = "".join(
        f"<p><strong>{escape(label)}:</strong> {escape(value)}</p>"
        for label, value in summary_rows(result)
    )
    remote_report = result.get("report_url")
    remote_link = ""
    if isinstance(remote_report, str) and remote_report.startswith("https://"):
        from titvo_cli.cloud import https_url

        try:
            https_url(remote_report)
            remote_link = f'<p><a href="{escape(remote_report)}" rel="noopener noreferrer">Abrir reporte completo AWS</a></p>'
        except ValueError:
            pass
    mock = result.get("model_mode") == "mock"
    return f"""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Titvo · Reporte</title><style>body{{font:16px system-ui;background:#101722;color:#e5edf7;max-width:960px;margin:40px auto;padding:24px}}article{{background:#1c2636;padding:24px;margin:18px 0;border-radius:12px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}.severity{{color:#ffbf69}}h1{{color:#62d4c5}}</style>
<h1>TITVO · {escape(result.get("project", ""))}</h1><p>{"PRUEBA CON IA SIMULADA · Este reporte no evalúa la seguridad del proyecto." if mock else "Análisis con proveedor de IA real."}</p>
<p>Estado: {escape(result.get("status"))} · Archivos: {escape(result.get("scaned_files", 0))}</p>
<section><h2>Resumen final</h2>{summary}<p>Costo de llamadas IA; no incluye infraestructura ni embeddings.</p></section>
<p>{escape(result.get("error", ""))}</p>{remote_link}{"".join(cards)}
<details><summary>Cobertura y archivos excluidos</summary><pre>{escape(json.dumps({"coverage": result.get("coverage"), "excluded": result.get("excluded"), "truncated_files": result.get("truncated_files")}, ensure_ascii=False, indent=2))}</pre></details></html>"""
