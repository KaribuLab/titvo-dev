---
name: dotenv
description: Load environment variables using linux commands with dotenv files
---

# dotenv

Execute the following command passing de full file path:

```shell
set -a && source /somedir/.env && set +a
```

## When to use

When you need environment variables from dotenv file.

## Instructions

1. Check if the OS is UNIX or LINUX.
2. Get the full path of file.
3. Execute the shell command.
