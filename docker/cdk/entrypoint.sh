#!/bin/sh

set -e

if [ ! -d "app" ]; then
    echo "No app directory found"
    exit 1
fi

cd /app

echo "Installing dependencies and building"

npm install
npm run build
rm -rf cdk.out

echo "Bootstrapping CDK"
echo "AWS_ENDPOINT_URL: $AWS_ENDPOINT_URL"
echo "AWS_ENDPOINT_URL_S3: $AWS_ENDPOINT_URL_S3"
echo "AWS_ACCESS_KEY_ID: $AWS_ACCESS_KEY_ID"
echo "AWS_SECRET_ACCESS_KEY: $AWS_SECRET_ACCESS_KEY"
echo "AWS_DEFAULT_REGION: $AWS_DEFAULT_REGION"

# Configurar credenciales AWS para LocalStack
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY_ID
aws_secret_access_key = $AWS_SECRET_ACCESS_KEY
EOF

cat > ~/.aws/config << EOF
[default]
region = $AWS_DEFAULT_REGION
output = json
EOF

# Esperar a que LocalStack esté listo
echo "Esperando a que LocalStack esté listo..."
until curl -s http://localstack:4566/_localstack/health > /dev/null; do
  echo "Esperando LocalStack..."
  sleep 2
done

echo "LocalStack está listo, ejecutando bootstrap..."
cdklocal bootstrap

exec "$@"