#!/bin/sh

set -e

task_api_gateway_endpoint=$(aws cloudformation describe-stacks --stack-name "$CDK_STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayEndpoint'].OutputValue" --output text)
if [ -z "$task_api_gateway_endpoint" ]; then
    echo "Task API Gateway Endpoint not found"
    exit 1
fi

echo "Task API Gateway Endpoint: $task_api_gateway_endpoint"

