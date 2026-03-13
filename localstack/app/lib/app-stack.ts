import * as cdk from 'aws-cdk-lib';
import { EventBus, Rule, RuleTargetInput } from 'aws-cdk-lib/aws-events';
import { SqsQueue } from 'aws-cdk-lib/aws-events-targets';
import { Queue } from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';
import { StringParameter } from 'aws-cdk-lib/aws-ssm';
import { AttributeType, GlobalSecondaryIndexProps, Table } from 'aws-cdk-lib/aws-dynamodb';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { Secret } from 'aws-cdk-lib/aws-secretsmanager';

const basePath = '/tvo/security-scan/localstack/infra';
const aesKey = process.env.AES_KEY ?? 'secret_key_aes';

export class AppStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // SQS

    // Git Commit Files

    const sqsInputGitCommitFiles = new Queue(this, 'InputQueueGitCommitFiles', {
      queueName: 'tvo-mcp-git-commit-files-input-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    const sqsOutput = new Queue(this, 'OutputQueue', {
      queueName: 'tvo-mcp-gateway-output-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    // Issue Report

    const sqsInputIssueReport = new Queue(this, 'InputQueueIssueReport', {
      queueName: 'tvo-mcp-issue-report-input-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    // Bitbucket Code Insights

    const sqsInputBitbucketCodeInsights = new Queue(this, 'InputBitbucketCodeInsights', {
      queueName: 'tvo-mcp-bitbucket-code-insights-input-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    // Github Issue

    const sqsInputGithubIssue = new Queue(this, 'InputGithubIssue', {
      queueName: 'tvo-mcp-github-issue-input-local',
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    // DynamoDB

    // Task Table

    const dynamoDB = new Table(this, 'DynamoDB', {
      tableName: 'tvo-task-local',
      partitionKey: { name: 'task_id', type: AttributeType.STRING },
      timeToLiveAttribute: 'ttl',
    });

    // Security Scan Table

    const dynamoDBScan = new Table(this, 'DynamoDBScan', {
      tableName: 'tvo-security-scan-local',
      partitionKey: { name: 'scan_id', type: AttributeType.STRING },
      timeToLiveAttribute: 'ttl',
    });

    // Parameter Table

    const dynamoDBParameter = new Table(this, 'DynamoDBParameter', {
      tableName: 'tvo-parameter-configuration-local',
      partitionKey: { name: 'parameter_id', type: AttributeType.STRING },
    });

    // Job/Message Table (para el gateway MCP)
    const dynamoDBJobs = new Table(this, 'DynamoDBJobs', {
      tableName: 'tvo-mcp-jobs-local',
      partitionKey: { name: 'id', type: AttributeType.STRING },
      timeToLiveAttribute: 'ttl',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // API Key Table

    const dynamoDBApiKey = new Table(this, 'DynamoDBApiKey', {
      tableName: 'tvo-api-key-local',
      partitionKey: { name: 'key_id', type: AttributeType.STRING },
    });

    dynamoDBApiKey.addGlobalSecondaryIndex({
      indexName: 'api_key_gsi',
      partitionKey: { name: 'api_key', type: AttributeType.STRING },
    });

    dynamoDBApiKey.addGlobalSecondaryIndex({
      indexName: 'user_id_gsi',
      partitionKey: { name: 'user_id', type: AttributeType.STRING },
    });

    // Task CLI Files Table

    const dynamoDBTaskCliFiles = new Table(this, 'DynamoDBTaskCliFiles', {
      tableName: 'tvo-task-cli-files-local',
      partitionKey: { name: 'task_cli_file_id', type: AttributeType.STRING },
    });

    const dynamoDBRepository = new Table(this, 'DynamoDBRepository', {
      tableName: 'tvo-repository-local',
      partitionKey: { name: 'repository_id', type: AttributeType.STRING },
    });

    const dynamoDBPrompt = new Table(this, 'DynamoDBPrompt', {
      tableName: 'tvo-prompt-local',
      partitionKey: { name: 'prompt_id', type: AttributeType.STRING },
    });

    const dynamoDBSession = new Table(this, 'DynamoDBSession', {
      tableName: 'tvo-session-local',
      partitionKey: { name: 'session_id', type: AttributeType.STRING },
    });

    const dynamoDBUser = new Table(this, 'DynamoDBUser', {
      tableName: 'tvo-user-local',
      partitionKey: { name: 'user_id', type: AttributeType.STRING },
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

    ruleInput.addTarget(new SqsQueue(sqsInputGitCommitFiles));

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

    ruleOutputIssueReport.addTarget(new SqsQueue(sqsOutput));

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

    ruleOutputBitbucketCodeInsights.addTarget(new SqsQueue(sqsOutput));

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

    ruleOutputGithubIssue.addTarget(new SqsQueue(sqsOutput));

    // S3

    // Bucket de reportes de seguridad
    const s3Report = new Bucket(this, 'S3Report', {
      bucketName: 'tvo-security-scan-report-local',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      websiteIndexDocument: 'index.html',
      publicReadAccess: true,
      blockPublicAccess: cdk.aws_s3.BlockPublicAccess.BLOCK_ACLS_ONLY,
    });

    // Bucket de archivos de commit de Git
    const s3GitCommitFiles = new Bucket(this, 'S3GitCommitFiles', {
      bucketName: 'tvo-mcp-git-commit-files-input-local',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const s3CliFiles = new Bucket(this, 'S3CliFiles', {
      bucketName: 'tvo-cli-files-local',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const secretBitbucket = new Secret(this, 'SecretBitbucket', {
      secretName: '/tvo/mcp/localstack/bitbucket_credentials',
      description: 'Secret local de credenciales de Bitbucket',
      secretStringValue: cdk.SecretValue.unsafePlainText('{"username":"local","appPassword":"local"}'),
    });

    const secretGithub = new Secret(this, 'SecretGithub', {
      secretName: '/tvo/mcp/localstack/github_token',
      description: 'Secret local de token de GitHub',
      secretStringValue: cdk.SecretValue.unsafePlainText('{"token":"local"}'),
    });

    // Parametros de infraestructura

    // SQS
    new StringParameter(this, 'SSMParameterGatewayOutputQueueArn', {
      parameterName: `${basePath}/sqs/mcp/gateway/output/queue_arn`,
      stringValue: sqsOutput.queueArn,
      description: 'ARN de la cola de salida de MCP Gateway'
    });

    new StringParameter(this, 'SSMParameterGatewayOutputQueueName', {
      parameterName: `${basePath}/sqs/mcp/gateway/output/queue_name`,
      stringValue: sqsOutput.queueName,
      description: 'Nombre de la cola de salida de MCP Gateway'
    });

    new StringParameter(this, 'SSMParameterGatewayOutputQueueUrl', {
      parameterName: `${basePath}/sqs/mcp/gateway/output/queue_url`,
      stringValue: sqsOutput.queueUrl,
      description: 'URL de la cola de salida de MCP Gateway'
    });

    new StringParameter(this, 'SSMParameterGitCommitFilesInputQueueArn', {
      parameterName: `${basePath}/sqs/mcp/git-commit-files/input/queue_arn`,
      stringValue: sqsInputGitCommitFiles.queueArn,
      description: 'ARN de la cola de entrada de MCP Git Commit Files'
    });

    new StringParameter(this, 'SSMParameterGitCommitFilesInputQueueName', {
      parameterName: `${basePath}/sqs/mcp/git-commit-files/input/queue_name`,
      stringValue: sqsInputGitCommitFiles.queueName,
      description: 'Nombre de la cola de entrada de MCP Git Commit Files'
    });

    new StringParameter(this, 'SSMParameterGitCommitFilesInputQueueUrl', {
      parameterName: `${basePath}/sqs/mcp/git-commit-files/input/queue_url`,
      stringValue: sqsInputGitCommitFiles.queueUrl,
      description: 'URL de la cola de entrada de MCP Git Commit Files'
    });

    new StringParameter(this, 'SSMParameterIssueReportInputQueueArn', {
      parameterName: `${basePath}/sqs/mcp/issue-report/input/queue_arn`,
      stringValue: sqsInputIssueReport.queueArn,
      description: 'ARN de la cola de entrada de MCP Issue Report'
    });

    new StringParameter(this, 'SSMParameterIssueReportInputQueueName', {
      parameterName: `${basePath}/sqs/mcp/issue-report/input/queue_name`,
      stringValue: sqsInputIssueReport.queueName,
      description: 'Nombre de la cola de entrada de MCP Issue Report'
    });

    new StringParameter(this, 'SSMParameterIssueReportInputQueueUrl', {
      parameterName: `${basePath}/sqs/mcp/issue-report/input/queue_url`,
      stringValue: sqsInputIssueReport.queueUrl,
      description: 'URL de la cola de entrada de MCP Issue Report'
    });

    new StringParameter(this, 'SSMParameterBitbucketCodeInsightsInputQueueArn', {
      parameterName: `${basePath}/sqs/mcp/bitbucket-code-insights/input/queue_arn`,
      stringValue: sqsInputBitbucketCodeInsights.queueArn,
      description: 'ARN de la cola de entrada de MCP Bitbucket Code Insights'
    });

    new StringParameter(this, 'SSMParameterBitbucketCodeInsightsInputQueueName', {
      parameterName: `${basePath}/sqs/mcp/bitbucket-code-insights/input/queue_name`,
      stringValue: sqsInputBitbucketCodeInsights.queueName,
      description: 'Nombre de la cola de entrada de MCP Bitbucket Code Insights'
    });

    new StringParameter(this, 'SSMParameterBitbucketCodeInsightsInputQueueUrl', {
      parameterName: `${basePath}/sqs/mcp/bitbucket-code-insights/input/queue_url`,
      stringValue: sqsInputBitbucketCodeInsights.queueUrl,
      description: 'URL de la cola de entrada de MCP Bitbucket Code Insights'
    });

    new StringParameter(this, 'SSMParameterGithubIssueInputQueueArn', {
      parameterName: `${basePath}/sqs/mcp/github-issue/input/queue_arn`,
      stringValue: sqsInputGithubIssue.queueArn,
      description: 'ARN de la cola de entrada de MCP Github Issue'
    });

    new StringParameter(this, 'SSMParameterGithubIssueInputQueueName', {
      parameterName: `${basePath}/sqs/mcp/github-issue/input/queue_name`,
      stringValue: sqsInputGithubIssue.queueName,
      description: 'Nombre de la cola de entrada de MCP Github Issue'
    });

    new StringParameter(this, 'SSMParameterGithubIssueInputQueueUrl', {
      parameterName: `${basePath}/sqs/mcp/github-issue/input/queue_url`,
      stringValue: sqsInputGithubIssue.queueUrl,
      description: 'URL de la cola de entrada de MCP Github Issue'
    });

    // Infra base
    new StringParameter(this, 'SSMParameterEcsClusterName', {
      parameterName: `${basePath}/ecs/cluster_name`,
      stringValue: 'tvo-mcp-cluster-local',
      description: 'Nombre del cluster ECS'
    });

    new StringParameter(this, 'SSMParameterVpcPrivateSubnets', {
      parameterName: `${basePath}/vpc/subnet/private/subnets_id`,
      stringValue: '["subnet-local-1","subnet-local-2","subnet-local-3"]',
      description: 'IDs de subnets privadas'
    });

    new StringParameter(this, 'SSMParameterVpcPrivateRouteTables', {
      parameterName: `${basePath}/vpc/subnet/private/routes_table_id`,
      stringValue: '["rtb-local-1"]',
      description: 'IDs de route table privadas'
    });

    new StringParameter(this, 'SSMParameterVpcId', {
      parameterName: `${basePath}/vpc/vpc_id`,
      stringValue: 'vpc-local-1',
      description: 'ID de VPC'
    });

    new StringParameter(this, 'SSMParameterVpcSecurityGroup', {
      parameterName: `${basePath}/vpc/security-group/security_group_id`,
      stringValue: 'sg-local-1',
      description: 'ID de security group'
    });

    new StringParameter(this, 'SSMParameterCloudmapId', {
      parameterName: `${basePath}/cloudmap/cloudmap_id`,
      stringValue: 'ns-local-1',
      description: 'ID de CloudMap'
    });

    new StringParameter(this, 'SSMParameterCloudmapArn', {
      parameterName: `${basePath}/cloudmap/cloudmap_arn`,
      stringValue: 'arn:aws:servicediscovery:us-east-1:000000000000:namespace/ns-local-1',
      description: 'ARN de CloudMap'
    });

    new StringParameter(this, 'SSMParameterEventBusArn', {
      parameterName: `${basePath}/eventbridge/eventbus_arn`,
      stringValue: eventBus.eventBusArn,
      description: 'ARN del bus de eventos'
    });

    new StringParameter(this, 'SSMParameterEventBusName', {
      parameterName: `${basePath}/eventbridge/eventbus_name`,
      stringValue: eventBus.eventBusName,
      description: 'Nombre del bus de eventos'
    });

    // S3
    new StringParameter(this, 'SSMParameterS3CliFilesBucketArn', {
      parameterName: `${basePath}/s3/cli-files/bucket_arn`,
      stringValue: s3CliFiles.bucketArn,
      description: 'ARN del bucket de CLI files'
    });

    new StringParameter(this, 'SSMParameterS3CliFilesBucketName', {
      parameterName: `${basePath}/s3/cli-files/bucket_name`,
      stringValue: s3CliFiles.bucketName,
      description: 'Nombre del bucket de CLI files'
    });

    new StringParameter(this, 'SSMParameterS3ReportsBucketArn', {
      parameterName: `${basePath}/s3/reports/bucket_arn`,
      stringValue: s3Report.bucketArn,
      description: 'ARN del bucket de reportes'
    });

    new StringParameter(this, 'SSMParameterS3ReportsBucketName', {
      parameterName: `${basePath}/s3/reports/bucket_name`,
      stringValue: s3Report.bucketName,
      description: 'Nombre del bucket de reportes'
    });

    new StringParameter(this, 'SSMParameterS3ReportsWebsiteUrl', {
      parameterName: `${basePath}/s3/reports/bucket_website_url`,
      stringValue: s3Report.bucketWebsiteUrl,
      description: 'URL del sitio web de reportes'
    });

    new StringParameter(this, 'SSMParameterS3GitCommitFilesBucketArn', {
      parameterName: `${basePath}/s3/git-commit-files/bucket_arn`,
      stringValue: s3GitCommitFiles.bucketArn,
      description: 'ARN del bucket de git-commit-files'
    });

    new StringParameter(this, 'SSMParameterS3GitCommitFilesBucketName', {
      parameterName: `${basePath}/s3/git-commit-files/bucket_name`,
      stringValue: s3GitCommitFiles.bucketName,
      description: 'Nombre del bucket de git-commit-files'
    });

    // Dynamo
    new StringParameter(this, 'SSMParameterDynamoApikeyTableArn', {
      parameterName: `${basePath}/dynamo/apikey-table-arn`,
      stringValue: dynamoDBApiKey.tableArn,
      description: 'ARN de la tabla DynamoDB apikey'
    });

    new StringParameter(this, 'SSMParameterDynamoApikeyTableName', {
      parameterName: `${basePath}/dynamo/apikey-table-name`,
      stringValue: dynamoDBApiKey.tableName,
      description: 'Nombre de la tabla DynamoDB apikey'
    });

    new StringParameter(this, 'SSMParameterDynamoCliFilesTableArn', {
      parameterName: `${basePath}/dynamo/cli-files-table-arn`,
      stringValue: dynamoDBTaskCliFiles.tableArn,
      description: 'ARN de la tabla DynamoDB cli-files'
    });

    new StringParameter(this, 'SSMParameterDynamoCliFilesTableName', {
      parameterName: `${basePath}/dynamo/cli-files-table-name`,
      stringValue: dynamoDBTaskCliFiles.tableName,
      description: 'Nombre de la tabla DynamoDB cli-files'
    });

    new StringParameter(this, 'SSMParameterDynamoJobsTableArn', {
      parameterName: `${basePath}/dynamo/jobs-table-arn`,
      stringValue: dynamoDBJobs.tableArn,
      description: 'ARN de la tabla DynamoDB jobs'
    });

    new StringParameter(this, 'SSMParameterDynamoJobsTableName', {
      parameterName: `${basePath}/dynamo/jobs-table-name`,
      stringValue: dynamoDBJobs.tableName,
      description: 'Nombre de la tabla DynamoDB jobs'
    });

    new StringParameter(this, 'SSMParameterDynamoParameterTableArn', {
      parameterName: `${basePath}/dynamo/parameter-table-arn`,
      stringValue: dynamoDBParameter.tableArn,
      description: 'ARN de la tabla DynamoDB parameter'
    });

    new StringParameter(this, 'SSMParameterDynamoParameterTableName', {
      parameterName: `${basePath}/dynamo/parameter-table-name`,
      stringValue: dynamoDBParameter.tableName,
      description: 'Nombre de la tabla DynamoDB parameter'
    });

    new StringParameter(this, 'SSMParameterDynamoPromptTableArn', {
      parameterName: `${basePath}/dynamo/prompt-table-arn`,
      stringValue: dynamoDBPrompt.tableArn,
      description: 'ARN de la tabla DynamoDB prompt'
    });

    new StringParameter(this, 'SSMParameterDynamoPromptTableName', {
      parameterName: `${basePath}/dynamo/prompt-table-name`,
      stringValue: dynamoDBPrompt.tableName,
      description: 'Nombre de la tabla DynamoDB prompt'
    });

    new StringParameter(this, 'SSMParameterDynamoRepositoryTableArn', {
      parameterName: `${basePath}/dynamo/repository-table-arn`,
      stringValue: dynamoDBRepository.tableArn,
      description: 'ARN de la tabla DynamoDB repository'
    });

    new StringParameter(this, 'SSMParameterDynamoRepositoryTableName', {
      parameterName: `${basePath}/dynamo/repository-table-name`,
      stringValue: dynamoDBRepository.tableName,
      description: 'Nombre de la tabla DynamoDB repository'
    });

    new StringParameter(this, 'SSMParameterDynamoScanTableArn', {
      parameterName: `${basePath}/dynamo/scan-table-arn`,
      stringValue: dynamoDBScan.tableArn,
      description: 'ARN de la tabla DynamoDB scan'
    });

    new StringParameter(this, 'SSMParameterDynamoScanTableName', {
      parameterName: `${basePath}/dynamo/scan-table-name`,
      stringValue: dynamoDBScan.tableName,
      description: 'Nombre de la tabla DynamoDB scan'
    });

    new StringParameter(this, 'SSMParameterDynamoSessionTableArn', {
      parameterName: `${basePath}/dynamo/session-table-arn`,
      stringValue: dynamoDBSession.tableArn,
      description: 'ARN de la tabla DynamoDB session'
    });

    new StringParameter(this, 'SSMParameterDynamoSessionTableName', {
      parameterName: `${basePath}/dynamo/session-table-name`,
      stringValue: dynamoDBSession.tableName,
      description: 'Nombre de la tabla DynamoDB session'
    });

    new StringParameter(this, 'SSMParameterDynamoTaskTableArn', {
      parameterName: `${basePath}/dynamo/task-table-arn`,
      stringValue: dynamoDB.tableArn,
      description: 'ARN de la tabla DynamoDB task'
    });

    new StringParameter(this, 'SSMParameterDynamoTaskTableName', {
      parameterName: `${basePath}/dynamo/task-table-name`,
      stringValue: dynamoDB.tableName,
      description: 'Nombre de la tabla DynamoDB task'
    });

    new StringParameter(this, 'SSMParameterDynamoUserTableArn', {
      parameterName: `${basePath}/dynamo/user-table-arn`,
      stringValue: dynamoDBUser.tableArn,
      description: 'ARN de la tabla DynamoDB user'
    });

    new StringParameter(this, 'SSMParameterDynamoUserTableName', {
      parameterName: `${basePath}/dynamo/user-table-name`,
      stringValue: dynamoDBUser.tableName,
      description: 'Nombre de la tabla DynamoDB user'
    });

    // API Gateway
    new StringParameter(this, 'SSMParameterApiGatewayTaskId', {
      parameterName: `${basePath}/apigateway/task/api_gateway_id`,
      stringValue: 'api-gateway-task-id-local',
      description: 'ID de API Gateway de task'
    });

    // Parametros auxiliares usados por agentes
    new StringParameter(this, 'SSMParameterAgentArn', {
      parameterName: `${basePath}/agent-arn`,
      stringValue: 'arn:aws:batch:us-east-1:000000000000:job-definition/tvo-security-scan-batch-local',
      description: 'ARN del job definition del agente'
    });

    new StringParameter(this, 'SSMParameterAgentJobQueueArn', {
      parameterName: `${basePath}/agent-job-queue-arn`,
      stringValue: 'arn:aws:batch:us-east-1:000000000000:job-queue/tvo-security-scan-job-queue-local',
      description: 'ARN del job queue del agente'
    });

    new StringParameter(this, 'SSMParameterEncryptionKeyName', {
      parameterName: `${basePath}/encryption-key-name`,
      stringValue: '/tvo/security-scan/localstack/infra/encryption-key',
      description: 'Nombre de secret para clave de encriptacion'
    });

    new StringParameter(this, 'SSMParameterSecretManagerArn', {
      parameterName: `${basePath}/secret-manager-arn`,
      stringValue: 'arn:aws:secretsmanager:us-east-1:000000000000:secret:/tvo/security-scan/localstack',
      description: 'ARN base para acceso a Secrets Manager'
    });

    new StringParameter(this, 'SSMParameterSecretBitbucketArn', {
      parameterName: `${basePath}/secrets/bitbucket/secret_arn`,
      stringValue: secretBitbucket.secretArn,
      description: 'ARN del secret de Bitbucket'
    });

    new StringParameter(this, 'SSMParameterSecretGithubArn', {
      parameterName: `${basePath}/secrets/github/secret_arn`,
      stringValue: secretGithub.secretArn,
      description: 'ARN del secret de GitHub'
    });

    // Secret Manager

    // AES Secret

    // Convertir la clave a base64 para que sea compatible con aes.service.ts
    const aesKeyBase64 = Buffer.from(aesKey, 'utf8').toString('base64');

    new Secret(this, 'SecretManagerParameter', {
      secretName: '/tvo/security-scan/localstack/aes_secret',
      description: 'Parametro de la secret manager para el AES',
      secretStringValue: cdk.SecretValue.unsafePlainText(aesKeyBase64),
    });

  }
}
