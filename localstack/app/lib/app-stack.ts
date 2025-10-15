import * as cdk from 'aws-cdk-lib';
import { EventBus, Rule, RuleTargetInput } from 'aws-cdk-lib/aws-events';
import { SqsQueue } from 'aws-cdk-lib/aws-events-targets';
import { Queue } from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';
import { StringParameter } from 'aws-cdk-lib/aws-ssm';
import { AttributeType, Table } from 'aws-cdk-lib/aws-dynamodb';

const basePath = '/tvo/security-scan/localstack/infra';

export class AppStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    // SQS

    const sqsInput = new Queue(this, 'InputQueue', {
      queueName: 'tvo-mcp-git-commit-files-input-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    const sqsOutput = new Queue(this, 'OutputQueue', {
      queueName: 'tvo-mcp-git-commit-files-output-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    // DynamoDB

    const dynamoDB = new Table(this, 'DynamoDB', {
      tableName: 'tvo-task-local',
      partitionKey: { name: 'task_id', type: AttributeType.STRING },
      timeToLiveAttribute: 'ttl',
    });

    // EventBus

    const eventBus = new EventBus(this, 'EventBus', {
      eventBusName: 'tvo-event-bus-local',
    });

    const ruleInput = new Rule(this, 'Rule', {
      eventBus: eventBus,
      description: 'Rule to trigger when a git commit files input is received',
      ruleName: 'mcp-git-commit-files-input',
      eventPattern: {
        source: ['mcp.tool.git.commit-files'],
        detailType: ['input'],
      },
    });

    const ruleOutput = new Rule(this, 'RuleOutput', {
      eventBus: eventBus,
      ruleName: 'mcp-git-commit-files-output',
      description: 'Rule to trigger when a git commit files output is received',
      eventPattern: {
        source: ['mcp.tool.git.commit-files'],
        detailType: ['output'],
      },
    });

    ruleInput.addTarget(new SqsQueue(sqsInput));

    ruleOutput.addTarget(new SqsQueue(sqsOutput));

    // Parametro de infraestructura

    new StringParameter(this, 'SSMParameterInputQueueArn', {
      parameterName: `${basePath}/sqs/mcp/git-commit-files/input/queue_arn`,
      stringValue: sqsInput.queueArn,
      description: 'ARN de la cola de entrada de MCP Git Commit Files'
    });

    new StringParameter(this, 'SSMParameterInputQueueName', {
      parameterName: `${basePath}/sqs/mcp/git-commit-files/input/queue_name`,
      stringValue: sqsInput.queueName,
      description: 'Nombre de la cola de entrada de MCP Git Commit Files'
    });

    new StringParameter(this, 'SSMParameterInputQueueUrl', {
      parameterName: `${basePath}/sqs/mcp/git-commit-files/input/queue_url`,
      stringValue: sqsInput.queueUrl,
      description: 'URL de la cola de entrada de MCP Git Commit Files'
    });

    new StringParameter(this, 'SSMParameterOutputQueueUrl', {
      parameterName: `${basePath}/sqs/mcp/git-commit-files/output/queue_url`,
      stringValue: sqsOutput.queueUrl,
      description: 'URL de la cola de salida de MCP Git Commit Files'
    });

    new StringParameter(this, 'SSMParameterOutputQueueArn', {
      parameterName: `${basePath}/sqs/mcp/git-commit-files/output/queue_arn`,
      stringValue: sqsOutput.queueArn,
      description: 'ARN de la cola de salida de MCP Git Commit Files'
    });

    new StringParameter(this, 'SSMParameterOutputQueueName', {
      parameterName: `${basePath}/sqs/mcp/git-commit-files/output/queue_name`,
      stringValue: sqsOutput.queueName,
      description: 'Nombre de la cola de salida de MCP Git Commit Files'
    });

    new StringParameter(this, 'SSMParameterEventBusArn', {
      parameterName: `${basePath}/eventbridge/eventbus_arn`,
      stringValue: eventBus.eventBusArn,
      description: 'ARN del bus de eventos de MCP Git Commit Files'
    });

    new StringParameter(this, 'SSMParameterEventBusName', {
      parameterName: `${basePath}/eventbridge/eventbus_name`,
      stringValue: eventBus.eventBusName,
      description: 'Nombre del bus de eventos de MCP Git Commit Files'
    });

    new StringParameter(this, 'SSMParameterDynamoDBTableArn', {
      parameterName: `${basePath}/dynamodb/process/dynamodb_table_arn`,
      stringValue: dynamoDB.tableArn,
      description: 'ARN de la tabla de MCP Git Commit Files'
    });

    new StringParameter(this, 'SSMParameterDynamoDBTableName', {
      parameterName: `${basePath}/dynamodb/process/dynamodb_table_name`,
      stringValue: dynamoDB.tableName,
      description: 'Nombre de la tabla de MCP Git Commit Files'
    });

  }
}
