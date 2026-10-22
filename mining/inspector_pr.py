from dotenv import load_dotenv
from pathlib import Path
import os
import requests
import argparse
import json
import sys

base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / '.env'
load_dotenv(dotenv_path=env_path, override=True)

GITHUB_TOKEN = os.getenv("GitHub_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("Missing GITHUB_TOKEN. Get one from GitHub Developer Settings.")

parser = argparse.ArgumentParser()
parser.add_argument("owner")
parser.add_argument("repo")
parser.add_argument("pr_number")
args = parser.parse_args()

url = f"https://api.github.com/repos/{args.owner}/{args.repo}/pulls/{args.pr_number}"
headers = {
    "X-GitHub-Api-Version": "2022-11-28",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

response = requests.get(url=url, headers=headers, timeout=10)

if response.status_code != 200:
    print(f"status code: {response.status_code}")
    print(f"Body: {response.text}")
    sys.exit(1)

output_dir = base_dir / "mining" / "raw"
output_dir.mkdir(parents=True, exist_ok=True)
file_path = output_dir / f"pr_{args.repo}_{args.pr_number}.json"

with open(file_path, 'w') as f:
    f.write(json.dumps(response.text))

final_response = response.json()
print(f"Merged: {final_response['merged']}")
print(f"merged_at: {final_response['merged_at']}")
print(f"merge_commit_sha: {final_response['merge_commit_sha']}")
print(f"commits: {final_response['commits']}")
print(f"base.ref: {final_response['base']['ref']}")
print(f"base.sha: {final_response['base']['sha']}")
print(f"head.sha: {final_response['head']['sha']}")
print(f"changed_files: {final_response['changed_files']}")
print(f"X-RateLimit-Remaining: {response.headers['X-RateLimit-Remaining']}")