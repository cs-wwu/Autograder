import datetime
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

# Search for TEST_CASES in a number of different folders
TEST_CASES = None
for dirpath, dirnames, filenames in os.walk("."):
    if "autograder.json" in filenames:
        filename = os.path.join(dirpath, "autograder.json")
        with open(filename) as f:
            TEST_CASES = json.load(f)
            break
if TEST_CASES is None:
    print("No autograder.json found")
    sys.exit(1)

# Install pytest and pytest-json-report if not already installed
subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--quiet",
        "--user",
        "pytest",
        "pytest-json-report",
    ],
    check=True,
)


def get_env(s):
    """Get the environment variable, or just return the string s if not in environment"""
    if s in os.environ:
        return os.environ[s]
    else:
        return s


def run_command(command, timeout_mins=10):
    """
    Run the command. Wait for timeout.Print stdout.
    Return true if passed, or false otherwise
    """
    # Check if there is anything to run
    if len(command) == 0:
        return True

    # Split the command into a list of arguments and run it
    command = command.split()
    process = subprocess.Popen(command)
    try:
        process.wait(timeout=timeout_mins * 60)
        return process.returncode == 0
    except:
        print("Command interrupted. Killing process group...")
        # Send SIGKILL to the entire process group
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except:
            pass
        return False


def run_test_case(test_case):
    """Run the test case and return true if passed, or false otherwise"""
    name = test_case["name"]
    setup = test_case["setup"]
    command = test_case["command"]
    timeout = test_case.get("timeout", 10)

    print(f"Running test case: {name}")

    print(f"Running setup: {setup}")
    # Run the setup command
    if not run_command(setup, timeout_mins=timeout):
        print("Setup failed")
        return False

    # Run the test case command
    print(f"Running command: {command}")
    if not run_command(command, timeout_mins=timeout):
        return False
    print(f"Test case passed: {name}")
    return True


# Get environment variables
CLASSROOM = get_env("CLASSROOM")
ASSIGNMENT = get_env("ASSIGNMENT")
USERNAME = get_env("USERNAME")
SUBMISSION_TAG = get_env("SUBMISSION_TAG")
COMMIT_URL = get_env("COMMIT_URL")
RELEASE_URL = get_env("RELEASE_URL")
REVIEW_URL = get_env("COMMIT_URL")

# Score and max score will be updated when the test case is pulled in
result = {
    "schema": "classroom50/result/v1",
    "classroom": CLASSROOM,
    "assignment": ASSIGNMENT,
    "usernames": [USERNAME],
    "submission": SUBMISSION_TAG,
    "commit": COMMIT_URL,
    "release": RELEASE_URL,
    "review": REVIEW_URL,
    "datetime": datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    ),
    "score": 0,
    "max-score": 0,
    "tests": [
        # filled in by reading from the test case list
    ],
}


# Run through all test cases
max_score = 0
for test_case in TEST_CASES:
    name = test_case["name"]
    points = test_case["points"]
    max_score += points

    if run_test_case(test_case):
        # Succeeded
        result["score"] += points
        result["tests"].append(
            {
                "test-name": name,
                "passed": True,
                "score": points,
                "max-score": points,
            }
        )
    else:
        # Failed
        result["tests"].append(
            {
                "test-name": name,
                "passed": False,
                "score": 0,
                "max-score": points,
            }
        )

# Update the max score
result["max-score"] = max_score

print(f"Score: {result['score']}/{result['max-score']}")
Path("result.json").write_text(json.dumps(result, indent=2))
