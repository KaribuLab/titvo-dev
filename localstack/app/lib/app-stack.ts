import * as cdk from 'aws-cdk-lib';
import { EventBus, Rule, RuleTargetInput } from 'aws-cdk-lib/aws-events';
import { SqsQueue } from 'aws-cdk-lib/aws-events-targets';
import { Queue } from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';
import { StringParameter } from 'aws-cdk-lib/aws-ssm';
import { AttributeType, Table } from 'aws-cdk-lib/aws-dynamodb';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { Secret } from 'aws-cdk-lib/aws-secretsmanager';

const basePath = '/tvo/security-scan/localstack/infra';
const aesKey = process.env.AES_KEY ?? 'secret_key_aes';

export class AppStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    // SQS

    // Git Commit Files

    const sqsInput = new Queue(this, 'InputQueue', {
      queueName: 'tvo-mcp-git-commit-files-input-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    const sqsOutput = new Queue(this, 'OutputQueue', {
      queueName: 'tvo-mcp-git-commit-files-output-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    // Issue Report

    const sqsInputIssueReport = new Queue(this, 'InputQueueIssueReport', {
      queueName: 'tvo-mcp-issue-report-input-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    const sqsOutputIssueReport = new Queue(this, 'OutputQueueIssueReport', {
      queueName: 'tvo-mcp-issue-report-output-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    // Bitbucket Code Insights

    const sqsInputBitbucketCodeInsights = new Queue(this, 'InputBitbucketCodeInsights', {
      queueName: 'tvo-mcp-bitbucket-code-insights-input-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    const sqsOutputBitbucketCodeInsights = new Queue(this, 'OutputBitbucketCodeInsights', {
      queueName: 'tvo-mcp-bitbucket-code-insights-output-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    // Github Issue

    const sqsInputGithubIssue = new Queue(this, 'InputGithubIssue', {
      queueName: 'tvo-mcp-github-issue-input-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    const sqsOutputGithubIssue = new Queue(this, 'OutputGithubIssue', {
      queueName: 'tvo-mcp-github-issue-output-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    // DynamoDB

    // Task Table

    const dynamoDB = new Table(this, 'DynamoDB', {
      tableName: 'tvo-task-local',
      partitionKey: { name: 'task_id', type: AttributeType.STRING },
      timeToLiveAttribute: 'ttl',
    });

    // Parameter Table

    const dynamoDBParameter = new Table(this, 'DynamoDBParameter', {
      tableName: 'tvo-parameter-configuration-local',
      partitionKey: { name: 'parameter_id', type: AttributeType.STRING },
    });

    // EventBus

    const eventBus = new EventBus(this, 'EventBus', {
      eventBusName: 'tvo-event-bus-local',
    });

    // Git Commit Files

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

    // Issue Report

    const ruleInputIssueReport = new Rule(this, 'RuleInputIssueReport', {
      eventBus: eventBus,
      description: 'Rule to trigger when a issue report input is received',
      ruleName: 'mcp-issue-report-input',
      eventPattern: {
        source: ['mcp.tool.issue.report'],
        detailType: ['input'],
      },
    });

    const ruleOutputIssueReport = new Rule(this, 'RuleOutputIssueReport', {
      eventBus: eventBus,
      description: 'Rule to trigger when a issue report output is received',
      ruleName: 'mcp-issue-report-output',
      eventPattern: {
        source: ['mcp.tool.issue.report'],
        detailType: ['output'],
      },
    });

    ruleInputIssueReport.addTarget(new SqsQueue(sqsInputIssueReport));

    ruleOutputIssueReport.addTarget(new SqsQueue(sqsOutputIssueReport));

    // Bitbucket Code Insights

    const ruleInputBitbucketCodeInsights = new Rule(this, 'RuleInputBitbucketCodeInsights', {
      eventBus: eventBus,
      description: 'Rule to trigger when a bitbucket code insights input is received',
      ruleName: 'mcp-bitbucket-code-insights-input',
      eventPattern: {
        source: ['mcp.tool.bitbucket.code-insights'],
        detailType: ['input'],
      },
    });

    const ruleOutputBitbucketCodeInsights = new Rule(this, 'RuleOutputBitbucketCodeInsights', {
      eventBus: eventBus,
      description: 'Rule to trigger when a bitbucket code insights output is received',
      ruleName: 'mcp-bitbucket-code-insights-output',
      eventPattern: {
        source: ['mcp.tool.bitbucket.code-insights'],
        detailType: ['output'],
      },
    });

    ruleInputBitbucketCodeInsights.addTarget(new SqsQueue(sqsInputBitbucketCodeInsights));

    ruleOutputBitbucketCodeInsights.addTarget(new SqsQueue(sqsOutputBitbucketCodeInsights));

    // Github Issue
    const ruleInputGithubIssue = new Rule(this, 'RuleInputGithubIssue', {
      eventBus: eventBus,
      description: 'Rule to trigger when a github issue input is received',
      ruleName: 'mcp-github-issue-input',
      eventPattern: {
        source: ['mcp.tool.github.issue'],
        detailType: ['input'],
      },
    });

    const ruleOutputGithubIssue = new Rule(this, 'RuleOutputGithubIssue', {
      eventBus: eventBus,
      description: 'Rule to trigger when a github issue output is received',
      ruleName: 'mcp-github-issue-output',
      eventPattern: {
        source: ['mcp.tool.github.issue'],
        detailType: ['output'],
      },
    });

    ruleInputGithubIssue.addTarget(new SqsQueue(sqsInputGithubIssue));

    ruleOutputGithubIssue.addTarget(new SqsQueue(sqsOutputGithubIssue));

    // S3

    // Bucket de reportes de seguridad
    const s3Report = new Bucket(this, 'S3Report', {
      bucketName: 'tvo-security-scan-report-local',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      websiteIndexDocument: 'index.html',
      publicReadAccess: true,
      blockPublicAccess: cdk.aws_s3.BlockPublicAccess.BLOCK_ACLS_ONLY,
    });

    // Parametro de infraestructura

    // Git Commit Files

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

    // Issue Report

    new StringParameter(this, 'SSMParameterInputQueueIssueReportArn', {
      parameterName: `${basePath}/sqs/mcp/issue-report/input/queue_arn`,
      stringValue: sqsInputIssueReport.queueArn,
      description: 'ARN de la cola de entrada de MCP Issue Report'
    });

    new StringParameter(this, 'SSMParameterInputQueueIssueReportName', {
      parameterName: `${basePath}/sqs/mcp/issue-report/input/queue_name`,
      stringValue: sqsInputIssueReport.queueName,
      description: 'Nombre de la cola de entrada de MCP Issue Report'
    });

    new StringParameter(this, 'SSMParameterInputQueueIssueReportUrl', {
      parameterName: `${basePath}/sqs/mcp/issue-report/input/queue_url`,
      stringValue: sqsInputIssueReport.queueUrl,
      description: 'URL de la cola de entrada de MCP Issue Report'
    });

    new StringParameter(this, 'SSMParameterOutputQueueIssueReportArn', {
      parameterName: `${basePath}/sqs/mcp/issue-report/output/queue_arn`,
      stringValue: sqsOutputIssueReport.queueArn,
      description: 'ARN de la cola de salida de MCP Issue Report'
    });

    new StringParameter(this, 'SSMParameterOutputQueueIssueReportName', {
      parameterName: `${basePath}/sqs/mcp/issue-report/output/queue_name`,
      stringValue: sqsOutputIssueReport.queueName,
      description: 'Nombre de la cola de salida de MCP Issue Report'
    });

    new StringParameter(this, 'SSMParameterOutputQueueIssueReportUrl', {
      parameterName: `${basePath}/sqs/mcp/issue-report/output/queue_url`,
      stringValue: sqsOutputIssueReport.queueUrl,
      description: 'URL de la cola de salida de MCP Issue Report'
    });

    // Bitbucket Code Insights

    new StringParameter(this, 'SSMParameterInputQueueBitbucketCodeInsightsArn', {
      parameterName: `${basePath}/sqs/mcp/bitbucket-code-insights/input/queue_arn`,
      stringValue: sqsInputBitbucketCodeInsights.queueArn,
      description: 'ARN de la cola de entrada de MCP Bitbucket Code Insights'
    });

    new StringParameter(this, 'SSMParameterInputQueueBitbucketCodeInsightsName', {
      parameterName: `${basePath}/sqs/mcp/bitbucket-code-insights/input/queue_name`,
      stringValue: sqsInputBitbucketCodeInsights.queueName,
      description: 'Nombre de la cola de entrada de MCP Bitbucket Code Insights'
    });

    new StringParameter(this, 'SSMParameterInputQueueBitbucketCodeInsightsUrl', {
      parameterName: `${basePath}/sqs/mcp/bitbucket-code-insights/input/queue_url`,
      stringValue: sqsInputBitbucketCodeInsights.queueUrl,
      description: 'URL de la cola de entrada de MCP Bitbucket Code Insights'
    });

    new StringParameter(this, 'SSMParameterOutputQueueBitbucketCodeInsightsArn', {
      parameterName: `${basePath}/sqs/mcp/bitbucket-code-insights/output/queue_arn`,
      stringValue: sqsOutputBitbucketCodeInsights.queueArn,
      description: 'ARN de la cola de salida de MCP Bitbucket Code Insights'
    });

    new StringParameter(this, 'SSMParameterOutputQueueBitbucketCodeInsightsName', {
      parameterName: `${basePath}/sqs/mcp/bitbucket-code-insights/output/queue_name`,
      stringValue: sqsOutputBitbucketCodeInsights.queueName,
      description: 'Nombre de la cola de salida de MCP Bitbucket Code Insights'
    });

    new StringParameter(this, 'SSMParameterOutputQueueBitbucketCodeInsightsUrl', {
      parameterName: `${basePath}/sqs/mcp/bitbucket-code-insights/output/queue_url`,
      stringValue: sqsOutputBitbucketCodeInsights.queueUrl,
      description: 'URL de la cola de salida de MCP Bitbucket Code Insights'
    });

    // Github Issue
    new StringParameter(this, 'SSMParameterInputQueueGithubIssueArn', {
      parameterName: `${basePath}/sqs/mcp/github-issue/input/queue_arn`,
      stringValue: sqsInputGithubIssue.queueArn,
      description: 'ARN de la cola de entrada de MCP Github Issue'
    });

    new StringParameter(this, 'SSMParameterInputQueueGithubIssueName', {
      parameterName: `${basePath}/sqs/mcp/github-issue/input/queue_name`,
      stringValue: sqsInputGithubIssue.queueName,
      description: 'Nombre de la cola de entrada de MCP Github Issue'
    });

    new StringParameter(this, 'SSMParameterInputQueueGithubIssueUrl', {
      parameterName: `${basePath}/sqs/mcp/github-issue/input/queue_url`,
      stringValue: sqsInputGithubIssue.queueUrl,
      description: 'URL de la cola de entrada de MCP Github Issue'
    });

    new StringParameter(this, 'SSMParameterOutputQueueGithubIssueArn', {
      parameterName: `${basePath}/sqs/mcp/github-issue/output/queue_arn`,
      stringValue: sqsOutputGithubIssue.queueArn,
      description: 'ARN de la cola de salida de MCP Github Issue'
    });

    new StringParameter(this, 'SSMParameterOutputQueueGithubIssueName', {
      parameterName: `${basePath}/sqs/mcp/github-issue/output/queue_name`,
      stringValue: sqsOutputGithubIssue.queueName,
      description: 'Nombre de la cola de salida de MCP Github Issue'
    });

    new StringParameter(this, 'SSMParameterOutputQueueGithubIssueUrl', {
      parameterName: `${basePath}/sqs/mcp/github-issue/output/queue_url`,
      stringValue: sqsOutputGithubIssue.queueUrl,
      description: 'URL de la cola de salida de MCP Github Issue'
    });

    // EventBus

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

    // Task Table

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

    // Parameter Table

    new StringParameter(this, 'SSMParameterDynamoDBParameterTableArn', {
      parameterName: `${basePath}/dynamodb/parameter/dynamodb_table_arn`,
      stringValue: dynamoDBParameter.tableArn,
      description: 'ARN de la tabla de parametros de configuracion'
    });

    new StringParameter(this, 'SSMParameterDynamoDBParameterTableName', {
      parameterName: `${basePath}/dynamodb/parameter/dynamodb_table_name`,
      stringValue: dynamoDBParameter.tableName,
      description: 'Nombre de la tabla de parametros de configuracion'
    });

    // S3

    new StringParameter(this, 'SSMParameterS3ReportBucketArn', {
      parameterName: `${basePath}/s3/report/bucket_arn`,
      stringValue: s3Report.bucketArn,
      description: 'ARN del bucket de reportes de seguridad'
    });

    new StringParameter(this, 'SSMParameterS3ReportBucketName', {
      parameterName: `${basePath}/s3/report/bucket_name`,
      stringValue: s3Report.bucketName,
      description: 'Nombre del bucket de reportes de seguridad'
    });

    new StringParameter(this, 'SSMParameterS3ReportWebsiteUrl', {
      parameterName: `${basePath}/s3/report/website_url`,
      stringValue: s3Report.bucketWebsiteUrl,
      description: 'URL del sitio web de reportes de seguridad'
    });

    new Secret(this, 'SecretManagerParameter', {
      secretName: '/tvo/security-scan/localstack/aes_secret',
      description: 'Parametro de la secret manager para el AES',
      secretStringValue: cdk.SecretValue.unsafePlainText(aesKey),
    });

  }
}
