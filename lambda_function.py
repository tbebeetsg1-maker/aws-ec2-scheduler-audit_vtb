import boto3
import json
import os
import oracledb

# Hardcoded instance ID for this project's test instance
INSTANCE_ID = 'i-03ead9af6d244e0b4'
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:643603452958:SEP14EC2SchedulerAlerts'

# RDS connection details (pulled from Lambda environment variables)
DB_HOST = os.environ['DB_HOST']
DB_PORT = os.environ.get('DB_PORT', '1521')
DB_SERVICE = os.environ.get('DB_SERVICE', 'ORCL')
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']

def log_to_db(instance_id, action, status):
    try:
        connection = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
        )
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO ec2_activity_log (instance_id, action, status) VALUES (:1, :2, :3)",
            [instance_id, action, status]
        )
        connection.commit()
        cursor.close()
        connection.close()
        print("Successfully logged to database")
    except Exception as e:
        print(f"Database logging failed: {str(e)}")

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    sns = boto3.client('sns')

    action = event.get('action', '')

    if action == 'start':
        response = ec2.start_instances(InstanceIds=[INSTANCE_ID])
        message = f"Started instance {INSTANCE_ID}"
        status = 'SUCCESS'
    elif action == 'stop':
        response = ec2.stop_instances(InstanceIds=[INSTANCE_ID])
        message = f"Stopped instance {INSTANCE_ID}"
        status = 'SUCCESS'
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid action. Use "start" or "stop".')
        }

    print(message)

    # Log to RDS
    log_to_db(INSTANCE_ID, action, status)

    # Publish notification to SNS
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject='EC2 Scheduler Notification',
        Message=message
    )

    return {
        'statusCode': 200,
        'body': json.dumps(message)
    }
