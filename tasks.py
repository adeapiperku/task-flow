import subprocess
import sys

tasks = {
    "dev": ["uvicorn", "adapters.inbound.api.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
    "prod": ["uvicorn", "adapters.inbound.api.main:app", "--host", "0.0.0.0", "--port", "8000"],
    "worker": ["python", "-m", "worker.runner"],
    "test": ["pytest"],
    "lint": ["ruff", "check", "."],
    "format": ["ruff", "format", "."],
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in tasks:
        print("Usage: python tasks.py [task]")
        print("Available tasks:", ", ".join(tasks.keys()))
        return

    task = sys.argv[1]
    print(f"Running task: {task}")
    subprocess.run(tasks[task])

if __name__ == "__main__":
    main()
