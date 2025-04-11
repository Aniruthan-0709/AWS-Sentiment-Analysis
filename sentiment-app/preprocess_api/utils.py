import os
import boto3
from dotenv import load_dotenv

# --------------------------------------
# ✅ Load environment variables from .env
# --------------------------------------
load_dotenv()

ECS_CLUSTER = os.getenv("ECS_CLUSTER")
ECS_TASK_DEFINITION = os.getenv("ECS_TASK_DEFINITION")
SUBNET_ID = os.getenv("SUBNET_ID")
SECURITY_GROUP_ID = os.getenv("SECURITY_GROUP_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")

ecs_client = boto3.client("ecs", region_name="us-east-1")

def trigger_ecs_task(filename: str, user: str = "") -> str:
    user_for_env = user.strip() or "default"

    print("🧪 DEBUG:")
    print(f"   ▶ ECS_CLUSTER     = {ECS_CLUSTER}")
    print(f"   ▶ TASK_DEFINITION = {ECS_TASK_DEFINITION}")
    print(f"   ▶ USER_NAME       = {user_for_env}")
    print(f"   ▶ FILENAME        = {filename}")

    try:
        describe = ecs_client.describe_clusters(clusters=[ECS_CLUSTER])
        print(f"   🔍 Cluster status: {describe['clusters'][0]['status']}")
    except Exception as e:
        raise RuntimeError(f"Cluster '{ECS_CLUSTER}' not found: {e}")

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
                        {"name": "USER_NAME", "value": user_for_env},
                        {"name": "FILENAME", "value": filename}
                    ]
                }
            ]
        }
    )

    tasks = response.get("tasks", [])
    if not tasks:
        print("❌ Task launch failed:", response)
        raise Exception("ECS task failed to launch")

    task_arn = tasks[0]["taskArn"]
    print(f"🚀 Task started successfully: {task_arn}")
    return task_arn
