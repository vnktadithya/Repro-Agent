import requests
import os
import json
from pathlib import Path
from dotenv import load_dotenv

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
    elif 400 <= response.status_code <= 600:
        response.raise_for_status()
        raise RuntimeError(f"Request failed with status code: {response.status_code}")


def save_raw_page(repo_dir, page_num, text):
    dir_path = base_dir / "mining" / "raw" / repo_dir
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


def main():
    owner = "OpenHands"
    name = "software-agent-sdk"
    cursor = None
    first = 50
    page_num = 1
    response_text = fetch_page(owner, name, cursor, first)
    save_raw_page("OpenHands__software-agent-sdk", page_num, response_text)
    total_count, nodes, has_next_page, end_cursor, rate_limit = parse_page(response_text)
    print(f'Total count: {total_count}')
    print(f'Number of Nodes: {len(nodes)}')
    print(f'Has Next Page? {has_next_page}')
    print(f'End cursor: {end_cursor}')
    print(f'cost: {rate_limit["cost"]}')
    print(f'Remaining calls: {rate_limit["remaining"]}')


if __name__ == '__main__':
    main()