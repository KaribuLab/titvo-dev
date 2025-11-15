#!/bin/sh

set -e

api_key=$(aws dynamodb query --table-name tvo-api-key-local --index-name user_id_gsi --key-condition-expression "user_id = :userId" --expression-attribute-values '{":userId": {"S": "tvo-user-local"}}' --query 'Items[0].api_key_raw.S' --output text)
echo "API Key: $api_key"