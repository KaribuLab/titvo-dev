/** Opt-in smoke against a disposable table on the local DynamoDB emulator. */
import { strict as assert } from 'node:assert';
import { randomUUID } from 'node:crypto';
import { test } from 'node:test';
import { CreateTableCommand, DeleteTableCommand, DynamoDBClient, waitUntilTableExists } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, GetCommand, PutCommand } from '@aws-sdk/lib-dynamodb';
import { seedRagIndexingTimeout } from '../configuration-seed';

const endpoint = process.env.TITVO_TEST_DYNAMODB_ENDPOINT;

test('real conditional seed preserves the configured timeout', { skip: !endpoint }, async () => {
    assert.ok(['localhost', '127.0.0.1'].includes(new URL(endpoint!).hostname));
    const client = new DynamoDBClient({
        endpoint, region: 'us-east-1',
        credentials: { accessKeyId: 'test', secretAccessKey: 'test' },
    });
    const document = DynamoDBDocumentClient.from(client);
    const table = `titvo-rag-seed-smoke-${randomUUID()}`;
    await client.send(new CreateTableCommand({
        TableName: table,
        AttributeDefinitions: [{ AttributeName: 'parameter_id', AttributeType: 'S' }],
        KeySchema: [{ AttributeName: 'parameter_id', KeyType: 'HASH' }],
        BillingMode: 'PAY_PER_REQUEST',
    }));
    try {
        await waitUntilTableExists({ client, maxWaitTime: 30 }, { TableName: table });
        const key = { parameter_id: 'rag_indexing_timeout_seconds' };
        await seedRagIndexingTimeout(document, table);
        const initial = await document.send(new GetCommand({ TableName: table, Key: key, ConsistentRead: true }));
        assert.equal(initial.Item?.value, '600');
        await document.send(new PutCommand({ TableName: table, Item: { ...key, value: '1800' } }));
        await seedRagIndexingTimeout(document, table);
        const updated = await document.send(new GetCommand({ TableName: table, Key: key, ConsistentRead: true }));
        assert.equal(updated.Item?.value, '1800');
    } finally {
        await client.send(new DeleteTableCommand({ TableName: table }));
        client.destroy();
    }
});
