import os
import boto3

# Environment configurations (can be moved to a .env file)
ECS_CLUSTER = os.getenv("ECS_CLUSTER", "default")
ECS_TASK_DEFINITION = os.getenv("ECS_TASK_DEFINITION", "default")
SUBNET_ID = os.getenv("SUBNET_ID", "default")
SECURITY_GROUP_ID = os.getenv("SECURITY_GROUP_ID", "default")
BUCKET_NAME = os.getenv("BUCKET_NAME", "default")

# Initialize ECS client
ecs_client = boto3.client("ecs")

def trigger_ecs_task(filename: str, user: str = ""):
    # Fallback: if user is empty, use raw/test.csv
    if user.strip():
        raw_key = f"raw/{user}/{filename}"
        user_for_env = user
    else:
        raw_key = f"raw/{filename}"
        user_for_env = "default"

    # Launch the ECS Fargate task
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
                        {"name": "USER_NAME", "value": user_for_env},
                        {"name": "FILENAME", "value": filename}
                    ]
                }
            ]
        }
    )

    # Validate task was launched
    tasks = response.get("tasks", [])
    if not tasks:
        raise Exception("❌ ECS task failed to launch")

    return tasks[0]["taskArn"]
