import crypto from 'crypto';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, PutCommand } from '@aws-sdk/lib-dynamodb';

const tableName = 'tvo-parameter-configuration-local';
const aesKey = process.env.AES_KEY ?? '12345678901234567890123456789012';

// Configurar cliente para Localstack
const client = new DynamoDBClient({
    endpoint: process.env.AWS_ENDPOINT_URL ?? 'http://localstack:4566', // Endpoint de Localstack
    region: process.env.AWS_DEFAULT_REGION ?? 'us-east-1',
});

// Crear un document client para operaciones más simples
const docClient = DynamoDBDocumentClient.from(client);

async function putItem(id: string, value: string): Promise<void> {
    await docClient.send(new PutCommand({
        TableName: tableName,
        Item: {
            parameter_id: id,
            value: value
        }
    }));
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
        const cipher = crypto.createCipheriv('aes-256-ecb', Buffer.from(key, 'utf8'), null);
        cipher.setAutoPadding(false); // Desactivar padding automático ya que lo hacemos manualmente

        const block = padtext.subarray(i, i + blockSize);
        const encryptedBlock = Buffer.concat([cipher.update(block), cipher.final()]);
        encryptedBlock.copy(encrypted, i);
    }

    // Retornar en formato base64
    return encrypted.toString('base64');
}

(async () => {
    const bitbucketClientId = process.env.BITBUCKET_CLIENT_ID as string
    const bitbucketClientSecret = process.env.BITBUCKET_CLIENT_SECRET as string
    const bitbucketClientCredentials: Record<string, string> = {
        key: bitbucketClientId,
        secret: bitbucketClientSecret
    }
    console.log('Setting Bitbucket client credentials');
    await putItem('bitbucket_client_credentials', encrypt(JSON.stringify(bitbucketClientCredentials), aesKey));
    const githubAccessToken = process.env.GITHUB_ACCESS_TOKEN as string
    console.log('Setting Github access token');
    await putItem('github_access_token', encrypt(githubAccessToken, aesKey));
})()