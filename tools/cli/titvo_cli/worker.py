"""Execute Titvo's real LangGraph workflow against a MiniStack CLI snapshot."""

import argparse
import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from types import SimpleNamespace

from code_analysis.infra.adapters.cli_snapshot import CliSnapshotRepository
from code_analysis.infra.adapters.langgraph.nodes.cli_retrieval_node import (
    CliRetrievalNode,
)
from code_analysis.infra.adapters.langgraph.workflow import LangGraphWorkflowBuilder

from titvo_cli.report import render
from titvo_cli.storage import BUCKET, FILES_TABLE, TASKS_TABLE, clients
from titvo_cli.usage import UsageModel


class MockModel:
    """Canned test double recognizes only an explicit synthetic fixture marker."""

    async def ainvoke(self, messages):
        """Validate transport with fixture findings; never claim security detection."""
        issues = []
        content = str(messages[-1].content)
        for header, code in re.findall(
            r"=== FILE: ([^\n]+) ===\n(.*?)=== END FILE ===", content, re.S
        ):
            path = header.split(" [runtime:", 1)[0]
            offset = re.search(r"\[lines (\d+)-", header)
            first_line = int(offset.group(1)) if offset else 1
            lines = code.splitlines()
            if lines and lines[0].startswith("# Chunk "):
                lines = lines[1:]
            if lines and lines[0].startswith("# [context:"):
                end = next(
                    (
                        i
                        for i, line in enumerate(lines)
                        if line.startswith("# [end context]")
                    ),
                    -1,
                )
                lines = lines[end + 1 :] if end >= 0 else lines
            for number, line in enumerate(lines, first_line):
                if "TITVO_TEST_VULNERABILITY" in line:
                    issues.append(
                        {
                            "title": "Hallazgo de prueba sintético",
                            "description": "Respuesta prefijada para verificar el recorrido.",
                            "severity": "HIGH",
                            "category": "test-fixture",
                            "path": path,
                            "line": number,
                            "summary": "No es una evaluación de seguridad.",
                            "code": line,
                            "recommendation": "Ejecutar con modelo real para evaluar seguridad.",
                        }
                    )
        return SimpleNamespace(content=json.dumps({"issues": issues}))

    def invoke(self, messages):
        """Deterministically consolidate identical fixture findings with source IDs."""
        payload = str(messages[-1].content).split("Hallazgos de entrada:", 1)[1].strip()
        groups = {}
        for finding in json.loads(payload):
            key = (
                finding["path"],
                finding["line"],
                finding["code"],
                finding["category"],
            )
            if key not in groups:
                groups[key] = {**finding, "source_ids": []}
            groups[key]["source_ids"].append(finding["id"])
        return SimpleNamespace(content=json.dumps({"issues": list(groups.values())}))


class ProgressHandler(logging.Handler):
    """Emit machine-readable batch progress to the client terminal."""

    def emit(self, record):
        """Forward only batch counters, excluding code and provider credentials."""
        message = record.getMessage()
        if message.startswith(("TITVO_BATCH ", "TITVO_REPAIR ")):
            marker, expert, counter = message.split()
            print(
                "TITVO_EVENT "
                + json.dumps(
                    {
                        "expert": expert,
                        "batch": counter,
                        "kind": "repair" if marker == "TITVO_REPAIR" else "batch",
                    }
                ),
                flush=True,
            )


async def run(task_id: str) -> dict:
    """Run the shared agent graph and persist artifacts plus terminal task state."""
    s3, dynamodb = clients()
    key = {"scan_id": {"S": task_id}}
    item = dynamodb.get_item(TableName=TASKS_TABLE, Key=key, ConsistentRead=True).get(
        "Item"
    )
    if not item:
        raise ValueError("Unknown task")
    mode = item["model"]["S"]
    if mode not in {"mock", "real"}:
        raise ValueError("Unsupported task model mode")
    dynamodb.update_item(
        TableName=TASKS_TABLE,
        Key=key,
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": {"S": "IN_PROGRESS"}},
    )
    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    tracked = None
    try:
        if mode == "mock":
            model = MockModel()
        else:
            from code_analysis.infra.adapters.langchain_agent_adapter import (
                LangchainAgentModelFactory,
            )

            api_key = os.environ["TITVO_AI_API_KEY"]
            if not api_key:
                raise ValueError("TITVO_AI_API_KEY is required for real mode")
            model = LangchainAgentModelFactory(
                ai_provider=os.getenv("TITVO_AI_PROVIDER", "openai"),
                ai_model=os.environ["TITVO_AI_MODEL"],
                ai_api_key=api_key,
                ai_base_url=os.getenv("TITVO_AI_BASE_URL"),
            ).create_model()
        tracked = UsageModel(
            model,
            mode,
            os.getenv("TITVO_AI_PROVIDER", "openai") if mode == "real" else None,
            os.getenv("TITVO_AI_MODEL") if mode == "real" else None,
        )
        node = CliRetrievalNode(
            CliSnapshotRepository(s3, dynamodb, BUCKET, FILES_TABLE)
        )
        graph = LangGraphWorkflowBuilder(None, tracked, retrieval_node=node).build()
        state = await graph.ainvoke(
            {
                "task_id": task_id,
                "repository_url": "local://snapshot",
                "branch": "working-tree",
                "commit_hash": task_id,
                "scan_mode": "full",
                "extra_args": {"batch_id": item["batch_id"]["S"]},
                "files": [],
                "scaned_files": 0,
                "issues": [],
                "expert_errors": [],
            }
        )
        result = state["final_output"]
        result.update(
            {
                "task_id": task_id,
                "project": item["project"]["S"],
                "model_mode": mode,
                "rag_enabled": False,
            }
        )
        result["truncated_files"] = sorted(
            {
                path
                for expert in result.get("coverage", {}).get("experts", {}).values()
                for path in expert.get("truncated_files", [])
            }
        )
        manifest = json.loads(
            s3.get_object(Bucket=BUCKET, Key=f"manifests/{task_id}.json")["Body"].read()
        )
        result["excluded"] = manifest["excluded"]
        result["selected_files"] = manifest["files"]
    except Exception as exc:
        result = {
            "task_id": task_id,
            "project": item["project"]["S"],
            "model_mode": mode,
            "status": "FAILED",
            "error": str(exc),
            "issues": [],
            "scaned_files": 0,
            "coverage": {"complete": False},
        }
    experts = result.get("coverage", {}).get("experts", {}).values()
    result["metrics"] = {
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.monotonic() - started, 3),
        "task_duration_seconds": round(
            (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(item["created_at"]["S"])
            ).total_seconds(),
            3,
        ),
        "total_batches": sum(expert.get("batches_total", 0) for expert in experts),
        "completed_batches": sum(
            expert.get("batches_completed", 0)
            for expert in result.get("coverage", {}).get("experts", {}).values()
        ),
    }
    result["usage"] = (
        tracked.summary()
        if tracked
        else {"cost_usd": None, "cost_status": "unavailable", "complete": False}
    )
    s3.put_object(
        Bucket=BUCKET,
        Key=f"reports/{task_id}.json",
        Body=json.dumps(result, ensure_ascii=False).encode(),
        ContentType="application/json",
    )
    s3.put_object(
        Bucket=BUCKET,
        Key=f"reports/{task_id}.html",
        Body=render(result).encode(),
        ContentType="text/html; charset=utf-8",
    )
    dynamodb.update_item(
        TableName=TASKS_TABLE,
        Key=key,
        UpdateExpression="SET #s = :s, report_key = :r",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": {"S": result["status"]},
            ":r": {"S": f"reports/{task_id}.json"},
        },
    )
    return result


def main():
    """Worker entry point: nonzero exit for incomplete execution, not findings."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    args = parser.parse_args()
    logger = logging.getLogger(
        "code_analysis.infra.adapters.langgraph.nodes.base_expert_node"
    )
    logger.setLevel(logging.INFO)
    logger.addHandler(ProgressHandler())
    result = asyncio.run(run(args.task_id))
    print(
        "TITVO_RESULT "
        + json.dumps(
            {
                "task_id": args.task_id,
                "status": result["status"],
                "complete": result["coverage"]["complete"],
            }
        ),
        flush=True,
    )
    raise SystemExit(0 if result["coverage"]["complete"] else 2)


if __name__ == "__main__":
    main()
