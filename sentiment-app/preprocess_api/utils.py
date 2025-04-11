import os
import boto3
import uuid

# 🔧 You can move these to a .env later
ECS_CLUSTER = os.getenv("ECS_CLUSTER", "default")
ECS_TASK_DEFINITION = os.getenv("ECS_TASK_DEFINITION", "sentiment-cleaner-task:1")
SUBNET_ID = os.getenv("SUBNET_ID", "subnet-061495d7090433d6f")
SECURITY_GROUP_ID = os.getenv("SECURITY_GROUP_ID", "sg-0817514159f510735")
BUCKET_NAME = os.getenv("BUCKET_NAME", "mlops-sentiment-app")

ecs_client = boto3.client("ecs")

def trigger_ecs_task(filename: str, user: str):
    raw_key = f"raw/{user}/{filename}"

    response = ecs_client.run_task(
        cluster=ECS_CLUSTER,
        launchType="FARGATE",
        count=1,
        platformVersion="LATEST",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": [SUBNET_ID],
                "securityGroups": [SECURITY_GROUP_ID],
                "assignPublicIp": "ENABLED"
            }
        },
        taskDefinition=ECS_TASK_DEFINITION,
        overrides={
            "containerOverrides": [
                {
                    "name": "sentiment-cleaner",
                    "environment": [
                        {"name": "BUCKET_NAME", "value": BUCKET_NAME},
                        {"name": "RAW_KEY", "value": raw_key},
                        {"name": "USER_NAME", "value": user}
                    ]
                }
            ]
        }
    )

    tasks = response.get("tasks", [])
    if not tasks:
        raise Exception("ECS task failed to launch")

    return tasks[0]["taskArn"]
