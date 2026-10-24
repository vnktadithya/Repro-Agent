import os
from pathlib import Path
from dotenv import load_dotenv
import requests
import json

base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / '.env'
load_dotenv(dotenv_path=env_path, override=True)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("Missing GITHUB_TOKEN. Get one from GitHub Developer Settings.")

url = "https://api.github.com/graphql"

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "User-Agent": "Python-Requests-GraphQL"
}

query = """
query($owner: String!, $name: String!, $number: Int!) {
    repository(owner: $owner, name: $name) {
        pullRequest(number: $number) {
            number
            merged
            mergedAt
            baseRefName
            mergeCommit {
                oid
            }
            commits {
                totalCount
            }
            closingIssuesReferences(first: 5) {
                totalCount
                nodes {
                    number
                    repository {
                        nameWithOwner
                    }
                } 
            }  
            files(first: 100) {
                totalCount
                nodes {
                    path
                    changeType
                }
            }
        }
    }
    rateLimit {
        cost
        remaining
        resetAt
    }
}
"""

variables = {
    "owner": "OpenHands",
    "name": "software-agent-sdk",
    "number": 4876
}

payload = {
    "query": query,
    "variables": variables
}

response = requests.post(url=url, headers=headers, timeout=10, json=payload)
json_response = response.json()

if response.status_code == 200:
    json_response = response.json()
    if 'errors' in json_response:
        print("Error occured.")
        print(json_response['errors'])
    else:
        file_path = f"{base_dir}/tests/fixtures/pr_4876.json"
        with open(file_path, 'w', encoding='utf8') as f:
            f.write(json.dumps(json_response["data"]["repository"]["pullRequest"], indent=2))
else:
    print(f"Error {response.status_code}: {response.text}")
