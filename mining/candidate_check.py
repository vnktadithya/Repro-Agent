from .classify_path import decide_patch
from .utils import CHANGE_TYPES

def check_candidate(pr_node, repo_name) -> str:
    if not pr_node['merged']:
        return "not_merged"
    
    if pr_node['closingIssuesReferences']['totalCount'] == 0:
        return "no_closing_issue"

    if pr_node['closingIssuesReferences']['totalCount'] > 1:
        return "multiple_issues"

    if pr_node['closingIssuesReferences']['nodes'][0]['repository']['nameWithOwner'].lower() != repo_name.lower():
        return "cross_repo_issue"

    if pr_node['files']['totalCount'] > 100:
        return "file_count_above_100"

    atleast_one_test_file = False
    atleast_one_source_file = False

    for node in pr_node['files']['nodes']:
        if decide_patch(node['path']) == 'test' and node['changeType'] != 'DELETED':
            atleast_one_test_file = True
        
        if decide_patch(node['path']) == 'source' and node['changeType'] in CHANGE_TYPES:
            atleast_one_source_file = True

    if not atleast_one_test_file:
        return "no_test_file"

    if not atleast_one_source_file:
        return "no_source_file"

    return "candidate"