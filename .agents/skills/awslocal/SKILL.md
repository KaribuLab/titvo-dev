---
name: awslocal
description: Wrapper for AWS CLI v2 to interact with LocalStack
---

# awslocal

This skill is used to interact with LocalStack using the AWS CLI v2.

This wrapper load this environment variables:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_REGION

And append the endpoint url to the command.

Example:

```bash
awslocal s3 ls
```

## When to use

This skill should be used when you need to interact with LocalStack using the AWS CLI v2.

## Instructions

Run the command with the following syntax:
```bash
awslocal <command> <options>
```
