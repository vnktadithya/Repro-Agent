import requests
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from collections import Counter

from .candidate_check import check_candidate

BASE_DIR = Path(__file__).resolve().parent.parent

OWNER = "OpenHands"
NAME = "software-agent-sdk"
REPO_NAME = f"{OWNER}/{NAME}"     
REPO_DIR = f"{OWNER}__{NAME}"     
RAW_DIR = BASE_DIR / "mining" / "raw" / REPO_DIR
PAGE_SIZE = 50


env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path, override=True)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("Missing GITHUB_TOKEN. Get one from GitHub Developer Settings.")

url = "https://api.github.com/graphql"

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "User-Agent": "Python-Requests-GraphQL"
}
query = """query($owner: String!, $name: String!, $first: Int!, $cursor: String) {
            repository(owner: $owner, name: $name) {
                pullRequests(states: [MERGED], orderBy: {field: CREATED_AT, direction: ASC}, first: $first, after: $cursor) {
                totalCount
                pageInfo { hasNextPage endCursor }
                nodes {
                    number
                    merged
                    mergedAt
                    baseRefName
                    mergeCommit { oid }
                    commits { totalCount }
                    closingIssuesReferences(first: 5) {
                    totalCount
                    nodes { number repository { nameWithOwner } }
                    }
                    files(first: 100) {
                    totalCount
                    nodes { path changeType }
                    }
                }
                }
            }
            rateLimit { cost remaining resetAt }
            }"""


def fetch_page(owner, name, cursor, first) -> str:

    variables = {
            "owner": owner,
            "name": name,
            "first": first,
            "cursor": cursor,
        }

    payload = {
        "query": query,
        "variables": variables
    }

    response = requests.post(url=url, headers=headers, timeout=30, json=payload)

    if response.status_code == 200:
        json_response = response.json()
        if 'errors' in json_response:
            raise RuntimeError(json_response['errors'])
        else:
            return response.text
    else:
        response.raise_for_status()
        raise RuntimeError(f"Request failed with status code: {response.status_code}")


def save_raw_page(repo_dir, page_num, text):
    dir_path = BASE_DIR / "mining" / "raw" / repo_dir
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = f"{dir_path}/page_{page_num:04d}.json"
    with open(file_path, 'w', encoding='utf8') as f:
        f.write(text)


def parse_page(text)-> tuple:
    text = json.loads(text)
    total_count = text['data']['repository']['pullRequests']['totalCount']
    nodes = text['data']['repository']['pullRequests']['nodes']
    has_next_page = text['data']['repository']['pullRequests']['pageInfo']['hasNextPage']
    end_cursor = text['data']['repository']['pullRequests']['pageInfo']['endCursor']
    rate_limit = text['data']['rateLimit']

    return (total_count, nodes, has_next_page, end_cursor, rate_limit)


def check_page(nodes, repo_name) -> Counter:
    statuses = Counter([check_candidate(node, repo_name) for node in nodes])
    return statuses

# temporary funcitons
def fetch_first_page():
    text = fetch_page(OWNER, NAME, cursor=None, first=PAGE_SIZE)
    save_raw_page(REPO_DIR, 1, text)
    total_count, nodes, has_next_page, end_cursor, rate_limit = parse_page(text)
    print(f"Total merged PRs: {total_count}")
    print(f"Nodes on page:    {len(nodes)}")
    print(f"Has next page:    {has_next_page}")
    print(f"End cursor:       {end_cursor}")
    print(f"Cost:             {rate_limit['cost']}")
    print(f"Remaining:        {rate_limit['remaining']}")


def check_cached_page(page_num):
    file_path = RAW_DIR / f"page_{page_num:04d}.json"
    text = file_path.read_text(encoding="utf-8")
    _, nodes, _, _, _ = parse_page(text)
    statuses = check_page(nodes, REPO_NAME)
    print(f"Page {page_num}: {len(nodes)} nodes")
    for status, count in statuses.most_common():
        print(f"  {status:<18} {count}")
    print(f"  {'total':<18} {sum(statuses.values())}")


def main():
    check_cached_page(1)


if __name__ == '__main__':
    main()