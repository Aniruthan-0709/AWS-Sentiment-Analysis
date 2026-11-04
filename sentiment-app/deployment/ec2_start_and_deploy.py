import boto3
import time
import paramiko
import os
import sys
import requests

# === CONFIGURATION ===
INSTANCE_ID = 'i-0d9483271f7cacc06'
KEY_PATH = os.path.join(os.path.dirname(__file__), 'key.pem')
ENV_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
REPO_NAME = 'AWS-Sentiment-Analysis'
USERNAME = 'ec2-user'
REGION = 'us-east-1'
HEALTH_CHECK_ATTEMPTS = 6

# === AWS CLIENT ===
ec2 = boto3.client('ec2', region_name=REGION)

def start_instance():
    print("🔄 Starting EC2 instance...")
    ec2.start_instances(InstanceIds=[INSTANCE_ID])
    ec2.get_waiter('instance_running').wait(InstanceIds=[INSTANCE_ID])
    print("✅ EC2 instance is running.")

def get_public_ip():
    print("🌐 Fetching current public IP...")
    reservations = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    public_ip = reservations['Reservations'][0]['Instances'][0]['PublicIpAddress']
    print(f"📡 Public IP: {public_ip}")
    return public_ip

def upload_env_file(public_ip):
    print("🛂 Uploading .env file to backend folder...")
    if not os.path.exists(ENV_PATH):
        raise FileNotFoundError(f"⚠️ .env file not found at: {ENV_PATH}")

    key = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    transport = paramiko.Transport((public_ip, 22))
    transport.connect(username=USERNAME, pkey=key)
    sftp = paramiko.SFTPClient.from_transport(transport)

    remote_path = f"/home/ec2-user/{REPO_NAME}/sentiment-app/backend/.env"
    sftp.put(ENV_PATH, remote_path)
    sftp.close()
    transport.close()
    print("✅ .env file uploaded to backend.")

def run_remote_commands(public_ip):
    print("🔐 Connecting via SSH to deploy app...")
    key = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connected = False
    while not connected:
        try:
            ssh.connect(hostname=public_ip, username=USERNAME, pkey=key)
            connected = True
        except Exception:
            print("⏳ Waiting for SSH to be ready...")
            time.sleep(10)

    print("✅ SSH connection established.")

    # === SETUP STEPS ===
    setup_commands = [
        # Stop the previous deploy, or it keeps the ports and serves the old code.
        # The [u] and [s] stop pkill from matching this shell's own command line.
        "pkill -f '[u]vicorn backend.main'; pkill -f '[s]treamlit run'; true",
        f"cd ~ && rm -rf {REPO_NAME} && git clone https://github.com/Aniruthan-0709/{REPO_NAME}.git",
        f"cd {REPO_NAME} && python3 -m venv venv && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
    ]

    for cmd in setup_commands:
        print(f"\n⚙️ Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        print(stdout.read().decode())
        print(stderr.read().decode())

    # === CHECK __init__.py ===
    print("\n🔍 Checking __init__.py in backend folder...")
    check_init_cmd = f"""
    if [ ! -f {REPO_NAME}/sentiment-app/backend/__init__.py ]; then
        echo "__init__.py not found, creating it..."
        touch {REPO_NAME}/sentiment-app/backend/__init__.py
    else
        echo "__init__.py already exists ✅"
    fi
    """
    stdin, stdout, stderr = ssh.exec_command(check_init_cmd, get_pty=True)
    print(stdout.read().decode())
    print(stderr.read().decode())

    # === UPLOAD .env FILE ===
    upload_env_file(public_ip)

    # === START BACKEND & FRONTEND ===
    launch_commands = [
        f"""
        cd /home/ec2-user/{REPO_NAME}/sentiment-app && nohup /home/ec2-user/{REPO_NAME}/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > /home/ec2-user/{REPO_NAME}/fastapi.log 2>&1 &
        """,

        f"""
        nohup /home/ec2-user/{REPO_NAME}/venv/bin/streamlit run {REPO_NAME}/sentiment-app/frontend/streamlit_app.py --server.address 0.0.0.0 --server.port 8501 > /home/ec2-user/{REPO_NAME}/streamlit.log 2>&1 &
        """
    ]

    for cmd in launch_commands:
        print(f"\n🚀 Launching: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        print(stdout.read().decode())
        print(stderr.read().decode())

    ssh.close()
    print("\n✅ FastAPI and Streamlit launched successfully.")

def health_check(public_ip):
    print("\n🧪 Performing health checks...")
    endpoints = {
        "FastAPI": f"http://{public_ip}:8000/docs",
        "Streamlit": f"http://{public_ip}:8501"
    }
    failed = []
    for name, url in endpoints.items():
        for attempt in range(HEALTH_CHECK_ATTEMPTS):
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    print(f"✅ {name} is live at {url}")
                    break
                print(f"⚠️ {name} responded with status {r.status_code}")
            except Exception as e:
                print(f"❌ {name} not reachable: {e}")
            if attempt < HEALTH_CHECK_ATTEMPTS - 1:
                time.sleep(10)
        else:
            failed.append(name)

    # A non-zero exit is what marks the GitHub Actions deploy as failed.
    if failed:
        sys.exit(f"❌ Health check failed for: {', '.join(failed)}")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    start_instance()
    time.sleep(30)
    public_ip = get_public_ip()
    run_remote_commands(public_ip)
    time.sleep(15)
    health_check(public_ip)
