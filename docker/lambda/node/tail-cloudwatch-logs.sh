#!/bin/sh

set -e

# Manejo de señales para salida limpia
cleanup() {
  echo ""
  echo "Deteniendo monitoreo de logs..."
  exit 0
}

trap cleanup INT TERM

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

tail_logs

