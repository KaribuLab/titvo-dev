import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, PutCommand, QueryCommand } from '@aws-sdk/lib-dynamodb';
import { SecretsManagerClient, CreateSecretCommand, UpdateSecretCommand, DescribeSecretCommand } from '@aws-sdk/client-secrets-manager';
import { randomBytes, createHash, createCipheriv, randomUUID } from 'crypto';
import * as path from 'node:path';
import * as fs from 'fs';

const configurationTableName = 'tvo-parameter-configuration-local';
const apiKeyTableName = 'tvo-api-key-local';
const aesKey = process.env.AES_KEY ?? '12345678901234567890123456789012';
const mcpServerURL = 'http://mcp-gateway:3000/mcp'
const userId = 'tvo-user-local';
const iaProvider = process.env.IA_PROVIDER as string
const iaModel = process.env.IA_MODEL as string
const iaAPIKey = process.env.IA_API_KEY as string

// Configurar cliente para Localstack
const client = new DynamoDBClient({
    endpoint: process.env.AWS_ENDPOINT_URL ?? 'http://localstack:4566', // Endpoint de Localstack
    region: process.env.AWS_DEFAULT_REGION ?? 'us-east-1',
});

// Crear un document client para operaciones más simples
const docClient = DynamoDBDocumentClient.from(client);

const awsRegion = process.env.AWS_DEFAULT_REGION ?? 'us-east-1';
const encryptionKeyName = '/tvo/security-scan/localstack/infra/encryption-key';

// Cliente de Secrets Manager
const secretsClient = new SecretsManagerClient({
    endpoint: process.env.AWS_ENDPOINT_URL ?? 'http://localstack:4566',
    region: awsRegion,
});

async function setupEncryptionKey(): Promise<void> {
    // Convertir la clave AES a base64 para que sea compatible con el servicio Python
    const aesKeyBase64 = Buffer.from(aesKey, 'utf8').toString('base64');

    try {
        // Intentar describir el secreto para ver si existe
        await secretsClient.send(new DescribeSecretCommand({
            SecretId: encryptionKeyName
        }));
        // Si existe, actualizarlo
        console.log('Updating encryption key in Secrets Manager');
        await secretsClient.send(new UpdateSecretCommand({
            SecretId: encryptionKeyName,
            SecretString: aesKeyBase64
        }));
    } catch (error) {
        // Si no existe, crearlo
        console.log('Creating encryption key in Secrets Manager');
        await secretsClient.send(new CreateSecretCommand({
            Name: encryptionKeyName,
            SecretString: aesKeyBase64,
            Description: 'Encryption key for Titvo security scan'
        }));
    }
}


const apiKeyPrefix = 'tvok';

export function hashKey(key: string): string {
    return createHash('sha256').update(key).digest('hex');
}

function generateApiKey(): string {
    // Calculamos cuántos caracteres aleatorios necesitamos
    const prefixLength = apiKeyPrefix.length; // 4 caracteres
    const hyphenLength = 1; // 1 carácter
    const randomLength = 48 - prefixLength - hyphenLength; // 48 - 4 - 1 = 43 caracteres aleatorios

    // Generamos bytes aleatorios criptográficamente seguros
    const randomBytesBuffer = randomBytes(Math.ceil(randomLength * 0.75)); // Ajustamos tamaño para base64

    // Convertimos a base64 y removemos caracteres no alfanuméricos
    const randomChars = randomBytesBuffer.toString('base64')
        .replace(/[+/=]/g, '')
        .substring(0, randomLength);

    return `${apiKeyPrefix}-${randomChars}`;
}

async function configurationPutItem(id: string, value: string): Promise<void> {
    await docClient.send(new PutCommand({
        TableName: configurationTableName,
        Item: {
            parameter_id: id,
            value: value
        }
    }));
}

async function apiKeyPutItem(keyId: string, apiKey: string): Promise<void> {
    await docClient.send(new PutCommand({
        TableName: apiKeyTableName,
        Item: {
            key_id: keyId,
            api_key: hashKey(apiKey),
            api_key_raw: apiKey,
            user_id: userId
        }
    }));
}

async function getUserApiKey(): Promise<string | null> {
    const result = await docClient.send(new QueryCommand({
        TableName: apiKeyTableName,
        IndexName: 'user_id_gsi',
        KeyConditionExpression: 'user_id = :userId',
        ExpressionAttributeValues: {
            ':userId': userId
        }
    }));
    return result.Items !== undefined && result.Items.length > 0 ? result.Items[0].api_key_raw ?? null : null;
}

function encrypt(text: string, key: string): string {
    // Validar que la clave tenga 32 caracteres (AES-256)
    if (key.length !== 32) {
        throw new Error('AES_KEY must have 32 characters length');
    }

    // Convertir el texto a bytes
    const plaintext = Buffer.from(text, 'utf8');

    // Aplicar padding PKCS7 para hacerlo múltiplo del tamaño de bloque
    const blockSize = 16; // AES block size is always 16 bytes
    let padding = blockSize - (plaintext.length % blockSize);

    // PKCS7 padding: si el texto ya es múltiplo del tamaño de bloque, agregar un bloque completo de padding
    if (padding === 0) {
        padding = blockSize;
    }

    const padtext = Buffer.alloc(plaintext.length + padding);
    plaintext.copy(padtext);

    // Llenar el padding con el valor del padding
    for (let i = plaintext.length; i < padtext.length; i++) {
        padtext[i] = padding;
    }

    // Encriptar usando ECB (bloque por bloque)
    const encrypted = Buffer.alloc(padtext.length);

    for (let i = 0; i < padtext.length; i += blockSize) {
        const cipher = createCipheriv('aes-256-ecb', Buffer.from(key, 'utf8'), null);
        cipher.setAutoPadding(false); // Desactivar padding automático ya que lo hacemos manualmente

        const block = padtext.subarray(i, i + blockSize);
        const encryptedBlock = Buffer.concat([cipher.update(block), cipher.final()]);
        encryptedBlock.copy(encrypted, i);
    }

    // Retornar en formato base64
    return encrypted.toString('base64');
}

(async () => {
    try {
        // Configurar la clave de encriptación en Secrets Manager
        await setupEncryptionKey();

        const bitbucketApiToken = process.env.BITBUCKET_API_TOKEN as string
        console.log('Setting Bitbucket api token');
        await configurationPutItem('bitbucket_api_token', encrypt(bitbucketApiToken, aesKey));
        const githubAccessToken = process.env.GITHUB_ACCESS_TOKEN as string
        console.log(`Setting Github access token: ${githubAccessToken.substring(0, 20)}...`);
        await configurationPutItem('github_access_token', encrypt(githubAccessToken, aesKey));
        console.log(`Setting mcp server url: ${mcpServerURL}`);
        await configurationPutItem('mcp_server_url', mcpServerURL);
        // Note: scan_system_prompt and content_template are now embedded in agent code
        // at src/agent/src/code_analysis/prompts/ - no longer loaded from DynamoDB
        console.log(`Setting ai provider: ${iaProvider}`);
        await configurationPutItem('ai_provider', iaProvider);
        console.log(`Setting ai model: ${iaModel}`);
        await configurationPutItem('ai_model', iaModel);
        console.log(`Setting ai api key: ${iaAPIKey.substring(0, 10)}...`);
        await configurationPutItem('ai_api_key', encrypt(iaAPIKey, aesKey));
        const langfusePublicKey = process.env.LANGFUSE_PUBLIC_KEY as string
        const langfuseSecretKey = process.env.LANGFUSE_SECRET_KEY as string
        const langfuseBaseURL = process.env.LANGFUSE_BASE_URL as string
        if (langfusePublicKey && langfuseSecretKey && langfuseBaseURL) {
            console.log(`Setting langfuse credentials public key: ${langfusePublicKey.substring(0, 10)}...`);
            console.log(`Setting langfuse credentials secret key: ${langfuseSecretKey.substring(0, 10)}...`);
            console.log(`Setting langfuse credentials base url: ${langfuseBaseURL}`);
            await configurationPutItem('langfuse_public_key', encrypt(langfusePublicKey, aesKey));
            await configurationPutItem('langfuse_secret_key', encrypt(langfuseSecretKey, aesKey));
            await configurationPutItem('langfuse_host', langfuseBaseURL);
        }
        await configurationPutItem('security-scan-job-queue', 'tvo-security-scan-job-queue-local');
        await configurationPutItem('security-scan-job-definition', 'tvo-security-scan-job-definition-local');
        console.log('Getting user api key');
        let apiKey = await getUserApiKey();
        if (apiKey === null) {
            apiKey = generateApiKey();
            console.log(`Setting api key: ${apiKey}`);
            await apiKeyPutItem(randomUUID().toString(), apiKey);
        } else {
            console.log(`Using existing api key: ${apiKey}`);
        }
    } catch (error) {
        console.error('Error setting up configuration: ', error);
        throw error;
    }
})()