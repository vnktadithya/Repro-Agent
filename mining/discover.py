import requests
import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from collections import Counter

from .candidate_check import check_candidate
from .backoff_utils import compute_backoff
from .pipeline_state import load_state, record_page

BASE_DIR = Path(__file__).resolve().parent.parent

OWNER = "OpenHands"
NAME = "software-agent-sdk"
REPO_NAME = f"{OWNER}/{NAME}"     
REPO_DIR = f"{OWNER}__{NAME}"     
RAW_DIR = BASE_DIR / "mining" / "raw" / REPO_DIR
PAGE_SIZE = 50
MAX_ATTEMPTS = 5


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


def check_page(nodes, repo_name) -> dict:
    statuses = {}
    for node in nodes:
        key = f"{repo_name}#{node['number']}"
        statuses[key] = check_candidate(node, repo_name)

    return statuses

def _rate_limit_wait(response, attempt):
    """Seconds to wait before retrying a 403/429, or None if it is not a rate limit."""
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        return int(retry_after)
    if response.headers.get("x-ratelimit-remaining") == "0":
        reset_at = int(response.headers["x-ratelimit-reset"])
        return max(reset_at - time.time(), 0) + 1
    if response.status_code == 429:
        return compute_backoff(attempt)
    return None  # 403 without rate-limit headers: a permission problem


def fetch_with_retry(owner, name, cursor, first):
    for attempt in range(MAX_ATTEMPTS):
        try:
            return fetch_page(owner, name, cursor, first)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            reason = type(e).__name__
            time_to_wait = compute_backoff(attempt)
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            reason = f"HTTP {status_code}"
            if status_code >= 500:
                time_to_wait = compute_backoff(attempt)
            elif status_code in (403, 429):
                time_to_wait = _rate_limit_wait(e.response, attempt)
                if time_to_wait is None:
                    raise
            else:
                raise

        if attempt == MAX_ATTEMPTS - 1:
            break
        print(f"  retry {attempt + 1}/{MAX_ATTEMPTS - 1}: {reason}, waiting {time_to_wait:.0f}s")
        time.sleep(time_to_wait)

    raise RuntimeError(f"gave up after {MAX_ATTEMPTS} attempts ({reason})")                


def main():
    state_path = RAW_DIR / "state.json"
    state = load_state(state_path)
    cursor = state['cursor']
    page_num = state['next_page']

    while True:
        if not state['has_next_page']:
            break 
        response_text = fetch_with_retry(OWNER, NAME, cursor, PAGE_SIZE)
        save_raw_page(REPO_DIR, page_num, response_text)
        total_count, nodes, has_next_page, end_cursor, rate_limit = parse_page(response_text)
        statuses = check_page(nodes, REPO_NAME)
        record_page(state, statuses, end_cursor, page_num+1, has_next_page, total_count, state_path)

        print(f"Page Number:  {page_num}")
        print(f"Nodes on page:{len(nodes)}")
        print(f"Cost:         {rate_limit['cost']}")
        print(f"Remaining:    {rate_limit['remaining']}")

        cursor = end_cursor
        page_num += 1 


    print(Counter(state["statuses"].values()))
    print(f"Total number of PR's processed: {len(state['statuses'])}")
    print(state['total_count'])
    print(state["statuses"].get("OpenHands/software-agent-sdk#4876"))


if __name__ == '__main__':
    main()
    