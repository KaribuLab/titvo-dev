import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, PutCommand, QueryCommand } from '@aws-sdk/lib-dynamodb';
import { randomBytes, createHash, createCipheriv, randomUUID } from 'crypto';

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
        const bitbucketClientId = process.env.BITBUCKET_CLIENT_ID as string
        const bitbucketClientSecret = process.env.BITBUCKET_CLIENT_SECRET as string
        const bitbucketClientCredentials: Record<string, string> = {
            key: bitbucketClientId,
            secret: bitbucketClientSecret
        }
        console.log('Setting Bitbucket client credentials');
        await configurationPutItem('bitbucket_client_credentials', encrypt(JSON.stringify(bitbucketClientCredentials), aesKey));
        const githubAccessToken = process.env.GITHUB_ACCESS_TOKEN as string
        console.log('Setting Github access token');
        await configurationPutItem('github_access_token', encrypt(githubAccessToken, aesKey));
        const promptResponse = await fetch("https://raw.githubusercontent.com/KaribuLab/titvo-installer/refs/heads/main/system_prompt.md")
        const prompt = await promptResponse.text()
        const contentTemplateResponse = await fetch("https://raw.githubusercontent.com/KaribuLab/titvo-installer/refs/heads/main/content_template.md")
        const contentTemplate = await contentTemplateResponse.text()
        console.log(`Setting mcp server url: ${mcpServerURL}`);
        await configurationPutItem('mcp_server_url', mcpServerURL);
        console.log(`Setting system prompt: ${prompt}`);
        await configurationPutItem('scan_system_prompt', prompt);
        console.log(`Setting content template: ${contentTemplate}`);
        await configurationPutItem('content_template', contentTemplate);
        console.log(`Setting ia provider: ${iaProvider}`);
        await configurationPutItem('ia_provider', iaProvider);
        console.log(`Setting ia model: ${iaModel}`);
        await configurationPutItem('ia_model', iaModel);
        console.log(`Setting ia api key: ${iaAPIKey.substring(0, 10)}...`);
        await configurationPutItem('ia_api_key', encrypt(iaAPIKey, aesKey));
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