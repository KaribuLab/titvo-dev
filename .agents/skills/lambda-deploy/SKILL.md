---
name: lambda-deploy
description: Deploy a lambda function to AWS Lambda
---

# lambda-deploy

Inside the lambda function directory build and deploy the lambda function to AWS Lambda

## When to use

When you need to build and deploy a lambda function to AWS Lambda.

## Instructions

Load the AWS credentiasl using `dotenv` skill with the file `.env.aws` located in the root of the project (workspace directory), then inside the lambda function directory:

1. Install dependencies using `npm install`.
2. Build the lambda function using the `npm run build` command.
3. Inside the `aws/parameter/lookup` directory execute `terragrunt apply --terragrunt-non-interactive --auto-approve` to lookup parameters.
4. Inside the `aws` directory execute `terragrunt run-all apply --terragrunt-non-interactive --auto-approve` to deploy the lambda function.

## References

- [dotenv](../dotenv/SKILL.md)