import pytest
from pathlib import Path
import json
from mining.candidate_check import check_candidate
from mining.classify_path import decide_patch

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
    pr_node['closingIssuesReferences']['nodes'].append({
                                                    "number": 4867,
                                                    "repository": {
                                                    "nameWithOwner": "OpenHands/software-agent-sdk"
                                                    }
                                                }
                                            )
    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'multiple_issues'

def test_cross_repo_issue(pr_node):
    pr_node['closingIssuesReferences']['nodes'][0]['repository']['nameWithOwner'] = 'Docling/docling'
    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'cross_repo_issue'

def test_changed_repo_name_case(pr_node):
    assert check_candidate(pr_node, "OpenHAnDs/softWaRe-ageNt-sdK") == 'candidate'

def test_file_count(pr_node):
    pr_node['files']['totalCount'] = 101
    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'files_truncated'

def test_no_test_files(pr_node):
    pr_node['files']['nodes'] = [node for node in pr_node['files']['nodes'] if decide_patch(node['path']) != 'test']
    pr_node['files']['totalCount'] = len(pr_node['files']['nodes']) 
    
    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'no_test_file'

def test_no_source_file(pr_node):
    pr_node['files']['nodes'] = [node for node in pr_node['files']['nodes'] if decide_patch(node['path']) != 'source']
    pr_node['files']['totalCount'] = len(pr_node['files']['nodes'])

    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'no_source_file'

def test_test_file_changeType_Deleted(pr_node):
    for node in pr_node['files']['nodes']:
        if decide_patch(node['path']) == 'test':
            node['changeType'] = 'DELETED'

    print(pr_node['files']['nodes'])
    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'no_test_file'

def test_source_file_changeType_not_in_CHANGE_TYPES(pr_node):
    for node in pr_node['files']['nodes']:
        if decide_patch(node['path']) == 'source':
            node['changeType'] = 'ADDED'

    print(pr_node['files']['nodes'])
    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'no_source_file'

def test_test_patch_contains_no_py_files(pr_node):
    pr_node['files']['nodes'] = [node for node in pr_node['files']['nodes'] if decide_patch(node['path']) != 'test']
    pr_node['files']['nodes'].append({
                                    "path": "tests/data/sample.json",
                                    "changeType": "ADDED"
                                })

    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'no_test_file'

def test_source_patch_contains_no_py_files(pr_node):
    pr_node['files']['nodes'] = [node for node in pr_node['files']['nodes'] if decide_patch(node['path']) != 'source']
    pr_node['files']['nodes'].append({
                                    "path": "pyproject.toml",
                                    "changeType": "MODIFIED"
                                })

    assert check_candidate(pr_node, "OpenHands/software-agent-sdk") == 'no_source_file'
