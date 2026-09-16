# AWS EC2 Scheduler & Audit Log

An automated EC2 start/stop scheduler built with Lambda and EventBridge, with email notifications and a persistent audit trail written to an Oracle RDS database.

## Overview

This project automates the start/stop lifecycle of an EC2 instance on a schedule, notifies a subscriber by email whenever an action runs, and logs every action to a relational database for auditability. It combines two areas of my training — AWS cloud architecture and Oracle database administration — into one cohesive system.

**Architecture:**

```
EventBridge Scheduler (cron)
        |
        v
   AWS Lambda  ----->  Amazon SNS (email notification)
        |
        v
  Amazon EC2 (start/stop target instance)
        |
        v
  Oracle RDS (ec2_activity_log audit table)
```

## How it works

1. Two EventBridge schedules trigger the same Lambda function on a cron schedule — one passing `{"action": "start"}`, the other `{"action": "stop"}`.
2. The Lambda function calls the EC2 API to start or stop the target instance.
3. It publishes a notification to an SNS topic, which emails a subscriber confirming the action.
4. It writes a row to an Oracle RDS table (`ec2_activity_log`) recording the instance ID, action, status, and timestamp.

## A note on the live infrastructure

This project was built, tested, and validated end-to-end — but it is **not left running**. The RDS instance in particular bills hourly, and there's no reason for an individual to sustain that cost for a demo project that isn't in active use. After each testing session, the EC2 instance is stopped, the RDS instance is deleted, and a snapshot is kept so the database (schema and data included) can be restored in minutes rather than rebuilt from scratch.

In other words: the code, IAM policies, table schema, and schedule configs in this repo are the real, tested artifacts — but the infrastructure itself is spun up only when it's actually being demonstrated or worked on, and torn down right after. This repo reflects that workflow rather than a permanently running environment.

## Files in this repo

| File | Description |
|---|---|
| `lambda_function.py` | Lambda source code. Credentials are read from environment variables — this is the sanitized version; the version actually deployed to AWS uses the same logic. |
| `iam-role-policy.json` | The IAM role and inline policies attached to the Lambda execution role (EC2 start/stop/describe, SNS publish, CloudWatch logging). |
| `create_table.sql` | DDL for the `ec2_activity_log` audit table in Oracle. |
| `eventbridge-schedules.json` | Configuration for the two EventBridge schedules (start/stop) and their Lambda targets. |

## Validation

The full pipeline was tested end-to-end:
- Lambda `start` and `stop` actions both returned success and correctly changed EC2 instance state
- SNS email notifications were received for both actions
- Both actions were confirmed written to the `ec2_activity_log` table via a live SQL query, with matching timestamps against the SNS notifications

## Troubleshooting: connecting to Oracle RDS

Two issues came up while building this project that are worth documenting, since working through them was as much a part of the learning as the final result.

**Issue 1 — No console query tool for standard Oracle RDS**

The RDS Query Editor only supports Aurora Serverless, not standard Oracle RDS instances, so there was no way to run SQL directly through the AWS console. To work around this, I used **AWS CloudShell** as a lightweight SQL workbench:

- CloudShell doesn't include `sqlplus` by default, so I downloaded the Oracle Instant Client (Basic + SQL*Plus packages) directly from Oracle and set `LD_LIBRARY_PATH`/`PATH` to point at it
- Hit a missing dependency (`libaio.so.1`), resolved with `sudo yum install -y libaio`
- Hit one connection failure that turned out to be a typo in the RDS endpoint (copied by hand from a screenshot rather than copy-pasted from the console) — fixed once I copied the endpoint directly
- Once connected via `sqlplus admin@<endpoint>:1521/ORCL`, ran the `ec2_activity_log` DDL and confirmed the table with `DESCRIBE`

**Issue 2 — Lambda has no built-in Oracle driver**

Lambda's default Python runtime doesn't include the `oracledb` driver needed to talk to Oracle. To fix this, I built a **Lambda Layer**:

- Installed `oracledb` into a local folder via CloudShell, zipped it, and uploaded it to S3
- Created a Lambda Layer from that zip and attached it to the function
- The first attempt failed with what looked like a circular import error — actually a Python version mismatch, since the compiled `oracledb` binary didn't match Lambda's Python 3.14 runtime
- Resolved by downgrading the Lambda runtime to Python 3.13 and rebuilding the layer with `pip install oracledb --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.13`

**Result:** Lambda successfully connects to Oracle RDS and writes a log row on every start/stop action, independently verified via live `SELECT` queries in SQL*Plus.

## Lessons learned / production considerations

- The EC2 and CloudWatch Logs permissions in the IAM policy use `"Resource": "*"`, which is broader than necessary for this single-instance project. In a production environment, I'd scope this down to a specific instance ARN or use a tag-based condition, so the role can only ever act on the intended instance.
- Database credentials are handled via Lambda environment variables rather than hardcoded in source, which is what's reflected in this repo.
- Given the hourly cost of RDS, this project is built around a "spin up, validate, tear down, snapshot" workflow rather than leaving infrastructure running continuously — a deliberate cost-management decision appropriate for a self-funded learning project.

## Tech stack

AWS Lambda (Python) - Amazon EventBridge Scheduler - Amazon SNS - Amazon EC2 - Amazon RDS (Oracle) - IAM
