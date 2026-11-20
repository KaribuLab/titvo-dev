/** Seed editable RAG configuration without replacing an operator's chosen value. */
import { ConditionalCheckFailedException } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, PutCommand } from '@aws-sdk/lib-dynamodb';

/** Insert the initial local budget only when the configuration key is absent. */
export async function seedRagIndexingTimeout(
    client: DynamoDBDocumentClient,
    tableName: string,
): Promise<void> {
    try {
        await client.send(new PutCommand({
            TableName: tableName,
            Item: { parameter_id: 'rag_indexing_timeout_seconds', value: '600' },
            ConditionExpression: 'attribute_not_exists(parameter_id)',
        }));
    } catch (error) {
        if (!(error instanceof ConditionalCheckFailedException)) {
            throw error;
        }
        // Existing values (including invalid ones) belong to the operator.
    }
}
