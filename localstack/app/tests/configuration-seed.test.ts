/** Verify conditional seeding and propagation of unexpected DynamoDB errors. */
import { strict as assert } from 'node:assert';
import { test } from 'node:test';
import { ConditionalCheckFailedException, DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, PutCommand } from '@aws-sdk/lib-dynamodb';
import { seedRagIndexingTimeout } from '../configuration-seed';

test('seed creates the initial record and preserves a customized existing value', async (t) => {
    const client = DynamoDBDocumentClient.from(new DynamoDBClient({ region: 'us-east-1' }));
    let stored: Record<string, unknown> | undefined;
    t.mock.method(client, 'send', async (command: PutCommand) => {
        assert.equal(command.input.TableName, 'configuration');
        assert.equal(command.input.ConditionExpression, 'attribute_not_exists(parameter_id)');
        if (stored) {
            throw new ConditionalCheckFailedException({ message: 'Already exists', $metadata: {} });
        }
        stored = command.input.Item;
        return {};
    });
    await seedRagIndexingTimeout(client, 'configuration');
    assert.deepEqual(stored, { parameter_id: 'rag_indexing_timeout_seconds', value: '600' });
    stored = { parameter_id: 'rag_indexing_timeout_seconds', value: '1800' };
    await seedRagIndexingTimeout(client, 'configuration');
    assert.equal(stored.value, '1800');
    client.destroy();
});

test('seed propagates service failures rather than treating them as an existing key', async (t) => {
    const client = DynamoDBDocumentClient.from(new DynamoDBClient({ region: 'us-east-1' }));
    const failure = new Error('AccessDenied');
    t.mock.method(client, 'send', async () => { throw failure; });
    await assert.rejects(seedRagIndexingTimeout(client, 'configuration'), (error) => error === failure);
    client.destroy();
});
