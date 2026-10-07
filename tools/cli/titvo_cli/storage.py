"""AWS-compatible transport for the isolated MiniStack laboratory."""

import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET = "titvo-cli-local"
FILES_TABLE = "titvo-cli-files-local"
TASKS_TABLE = "titvo-cli-tasks-local"


def clients(endpoint: str | None = None):
    """Use explicit emulator credentials, never the user's default AWS profile."""
    options = dict(
        endpoint_url=endpoint or os.getenv("AWS_ENDPOINT", "http://localhost:4566"),
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    return boto3.client(
        "s3", config=Config(s3={"addressing_style": "path"}), **options
    ), boto3.client("dynamodb", **options)


def bootstrap(s3, dynamodb):
    """Idempotently create only the laboratory's bucket and two DynamoDB tables."""
    try:
        s3.head_bucket(Bucket=BUCKET)
    except ClientError as exc:
        if str(exc.response["Error"]["Code"]) not in {
            "404",
            "NoSuchBucket",
            "NotFound",
        }:
            raise
        s3.create_bucket(Bucket=BUCKET)
    for table, key in [(FILES_TABLE, "file_id"), (TASKS_TABLE, "scan_id")]:
        try:
            dynamodb.describe_table(TableName=table)
            continue
        except dynamodb.exceptions.ResourceNotFoundException:
            pass
        options = dict(
            TableName=table,
            KeySchema=[{"AttributeName": key, "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": key, "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        if table == FILES_TABLE:
            options["AttributeDefinitions"].append(
                {"AttributeName": "batch_id", "AttributeType": "S"}
            )
            options["GlobalSecondaryIndexes"] = [
                {
                    "IndexName": "batch_id_gsi",
                    "KeySchema": [{"AttributeName": "batch_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ]
        dynamodb.create_table(**options)
        dynamodb.get_waiter("table_exists").wait(TableName=table)


def upload(s3, dynamodb, archive: bytes, manifest: dict, model: str) -> str:
    """Register a task only after its immutable package has been uploaded."""
    task_id = str(uuid.uuid4())
    key = f"temp/{task_id}/snapshot.tar.gz"
    s3.put_object(Bucket=BUCKET, Key=key, Body=archive, ContentType="application/gzip")
    dynamodb.put_item(
        TableName=FILES_TABLE,
        Item={
            "file_id": {"S": task_id},
            "batch_id": {"S": task_id},
            "file_key": {"S": key},
        },
    )
    s3.put_object(
        Bucket=BUCKET,
        Key=f"manifests/{task_id}.json",
        Body=json.dumps(manifest).encode(),
        ContentType="application/json",
    )
    dynamodb.put_item(
        TableName=TASKS_TABLE,
        Item={
            "scan_id": {"S": task_id},
            "batch_id": {"S": task_id},
            "status": {"S": "PENDING"},
            "project": {"S": manifest["project"]},
            "project_id": {"S": manifest.get("project_id", manifest["project"])},
            "model": {"S": model},
            "created_at": {"S": datetime.now(timezone.utc).isoformat()},
        },
    )
    return task_id
