import os

# The backend reads these at import time. Real values are never needed because
# the tests replace every AWS client with a mock.
os.environ.update(
    {
        "COGNITO_CLIENT_ID": "test-client-id",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "ECS_CLUSTER": "test-cluster",
        "ECS_TASK_DEFINITION_ARN": "test-task-definition",
        "SUBNET_ID": "subnet-test",
        "SECURITY_GROUP_ID": "sg-test",
        "BUCKET_NAME": "test-bucket",
    }
)
