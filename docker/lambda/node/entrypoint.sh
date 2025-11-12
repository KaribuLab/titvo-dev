#!/bin/sh

set -e

wait_for_stack_completion() {
  aws cloudformation wait stack-exists --stack-name $CDK_STACK_NAME
  aws cloudformation wait stack-create-complete --stack-name $CDK_STACK_NAME
}

tail_logs() {
  wait_for_stack_completion
  local cloudwatch_logs_group=$(aws cloudformation describe-stacks --stack-name $CDK_STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='CloudWatchLogGroupName'].OutputValue" --output text)
  echo "CloudWatch log group: $cloudwatch_logs_group"
  
  # Usar polling manual más agresivo para Localstack (cada 500ms)
  local last_event_time=$(date +%s)000
  while true; do
    local events=$(aws logs filter-log-events \
      --log-group-name "$cloudwatch_logs_group" \
      --start-time "$last_event_time" \
      --output json 2>/dev/null || echo '{"events":[]}')
    
    local new_events=$(echo "$events" | jq -r '.events[] | "\(.timestamp) \(.message)"')
    
    if [ -n "$new_events" ]; then
      echo "$new_events"
      # Actualizar el timestamp del último evento
      last_event_time=$(echo "$events" | jq -r '.events[-1].timestamp + 1' 2>/dev/null || echo "$last_event_time")
    fi
    
    sleep 0.5
  done
}

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

tail_logs &

exec "$@"