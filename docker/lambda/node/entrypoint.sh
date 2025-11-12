#!/bin/sh

set -e

if [ -z "$CDK_STACK_NAME" ]; then
    echo "CDK_STACK_NAME is not set"
    exit 1
fi

if [ ! -d "cdklocal" ]; then
    echo "No cdk directory found"
    exit 1
fi

echo "Installing dependencies of app"

npm install
npm run build
mkdir -p dist
cd build && zip -r ../dist/lambda.zip . && cd ..

cd cdklocal

echo "Installing dependencies and building cdklocal"

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

echo "Bootstrap completado, esperando para evitar conflictos..."
sleep 3

cd ..

exec "$@"