---
name: push-ecr
description: Push a Docker image to AWS ECR
---

# push-ecr

Push a Docker image to AWS ECR

## When to use

When you need to push a Docker image to AWS ECR.

## Instructions

First you must push the `agent` or `gateway` change to the remote repository in `main` branch.

1. If you want to push the `agent` image:
   1. Use the github URL (`GIT_URL`): `https://github.com/KaribuLab/titvo-agent-aws.git`
   2. The image repository (`IMAGE_REPO`): `tvo-agent-ecr-prod`
2. If you want to push the `gateway` image:
   1. Use the github URL (`GIT_URL`): `https://github.com/KaribuLab/titvo-mcp-gateway.git`
   2. The image repository (`IMAGE_REPO`): `tvo-mcp-gateway-ecr-prod`
3. Use `--env-file` AWS to set the environment variables with `.env.aws` file located in the root of the project (workspace directory).
4. Run the command: `docker run --rm --privileged --env-file=.env.aws -e GIT_URL=<GIT_URL> -e IMAGE_REPO=<IMAGE_REPO> karibu/titvo-installer-ecr-publisher:latest`.

## Next step (gateway only)

After pushing the **gateway** image, replace the running ECS task (without changing the task definition) with [deploy-image](../deploy-image/SKILL.md). The **agent** uses AWS Batch and does not need this step.