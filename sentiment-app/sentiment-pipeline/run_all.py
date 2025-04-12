import subprocess
import sys

def run_script(name):
    print(f"🔄 Running: {name}")
    result = subprocess.run(["python", name])

    if result.returncode != 0:
        print(f"❌ {name} failed. Exiting...")
        sys.exit(result.returncode)

if __name__ == "__main__":
    print("🚀 Starting Sentiment Pipeline ECS Job")
    
    run_script("run_clean.py")
    print("✅ Preprocessing complete.")

    run_script("run_infer.py")
    print("✅ Inference complete.")

    print("🎉 All steps completed successfully.")
