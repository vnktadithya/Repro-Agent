import pytest
from pathlib import Path
import json
from mining.candidate_check import check_candidate

@pytest.fixture
def pr_node():
    file_path = Path(__file__).parent / "fixtures" / "pr_4876.json"

    with open(file_path, 'r', encoding='utf8') as f:
        pr_json = json.load(f)

    return pr_json

def test_node_fixture_unchanged(pr_node):
    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'candidate'

def test_not_merged_status(pr_node):
    pr_node['merged'] = False
    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'not_merged'

def test_no_closing_issue(pr_node):
    pr_node['closingIssuesReferences']['totalCount'] = 0
    pr_node['closingIssuesReferences']['nodes'] = []
    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'no_closing_issue'

def test_multiple_issues(pr_node):
    pr_node['closingIssuesReferences']['totalCount'] = 2
    pr_node['closingIssuesReferences']['nodes'].append(pr_node['closingIssuesReferences']['nodes'][0])
    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'multiple_issues'

def test_cross_repo_issue(pr_node):
    pr_node['closingIssuesReferences']['nodes'][0]['repository']['nameWithOwner'] = 'Docling/docling'
    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'cross_repo_issue'

def test_changed_repo_name_case(pr_node):
    assert check_candidate(pr_node, "OpenHAnDs/softWaRe-ageNt-sdK") == 'candidate'
