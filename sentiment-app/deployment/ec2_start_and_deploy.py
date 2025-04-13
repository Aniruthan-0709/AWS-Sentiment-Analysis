import boto3
import time
import paramiko
import os
import requests

# === CONFIGURATION ===
INSTANCE_ID = 'i-0d9483271f7cacc06'
KEY_PATH = os.path.join(os.path.dirname(__file__), 'key.pem')
REPO_NAME = 'AWS-Sentiment-Analysis'
USERNAME = 'ec2-user'
REGION = 'us-east-1'

# === CHECK KEY FILE ===
with open(KEY_PATH, 'r') as f:
    print("✅ Key file loaded successfully!")

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

def run_remote_commands(public_ip):
    print("🔐 Connecting via SSH to deploy app...")
    key = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Wait for SSH connection
    connected = False
    while not connected:
        try:
            ssh.connect(hostname=public_ip, username=USERNAME, pkey=key)
            connected = True
        except Exception:
            print("⏳ Waiting for SSH to be ready...")
            time.sleep(10)

    print("✅ SSH connection established.")

    # === COMMANDS ===
    commands = [
        f"cd ~ && rm -rf {REPO_NAME} && git clone https://github.com/Aniruthan-0709/{REPO_NAME}.git",

        f"cd {REPO_NAME} && python3 -m venv venv && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt",

        f"cd {REPO_NAME}/sentiment-app/backend && nohup ../../venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 &",

        f"cd {REPO_NAME}/sentiment-app/frontend && nohup ../../venv/bin/streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501 &"
    ]

    for cmd in commands:
        print(f"\n⚙️ Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)

        for line in iter(stdout.readline, ""):
            print(line, end="")

        error = stderr.read().decode()
        if error:
            print(f"\n❌ STDERR:\n{error}")

    ssh.close()
    print("\n🚀 App successfully deployed.")

def health_check(public_ip):
    print("\n🧪 Performing health checks...")
    endpoints = {
        "FastAPI": f"http://{public_ip}:8000/docs",
        "Streamlit": f"http://{public_ip}:8501"
    }

    for name, url in endpoints.items():
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                print(f"✅ {name} is live at {url}")
            else:
                print(f"⚠️ {name} responded with status {r.status_code}")
        except Exception as e:
            print(f"❌ {name} not reachable: {e}")

if __name__ == "__main__":
    start_instance()
    time.sleep(30)  # Let EC2 boot fully
    public_ip = get_public_ip()
    run_remote_commands(public_ip)
    time.sleep(15)  # Let services start
    health_check(public_ip)
