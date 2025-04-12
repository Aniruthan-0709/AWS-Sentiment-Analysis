import boto3
import os
from fastapi import HTTPException
from dotenv import load_dotenv

# ✅ Load environment variables explicitly from backend folder
load_dotenv(dotenv_path="backend/.env")

# ✅ Get config values
COGNITO_REGION = os.getenv("COGNITO_REGION", "us-east-1")
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")

# 🛑 Ensure environment values are loaded
if not CLIENT_ID:
    raise RuntimeError("❌ COGNITO_CLIENT_ID is not set in the environment.")

client = boto3.client("cognito-idp", region_name=COGNITO_REGION)

def authenticate_user(username: str, password: str) -> dict:
    print("🔐 AUTH DEBUG:")
    print(f"   ▶ Username: {username}")
    print(f"   ▶ Password: {password}")
    print(f"   ▶ Client ID: {CLIENT_ID}")

    try:
        response = client.initiate_auth(
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            },
            ClientId=CLIENT_ID
        )

        auth_result = response["AuthenticationResult"]
        print("✅ Auth successful (token received)")
        return {
            "access_token": auth_result["AccessToken"],
            "id_token": auth_result["IdToken"],
            "refresh_token": auth_result["RefreshToken"]
        }

    except client.exceptions.NotAuthorizedException:
        print("❌ Cognito: Invalid username or password")
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    except client.exceptions.UserNotFoundException:
        print("❌ Cognito: User not found")
        raise HTTPException(status_code=404, detail="User not found.")
    except Exception as e:
        print("❌ Unexpected error during authentication:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
