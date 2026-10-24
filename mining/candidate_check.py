def check_candidate(pr_node, repo_name) -> str:
    if not pr_node['merged']:
        return "not_merged"
    
    if pr_node['closingIssuesReferences']['totalCount'] == 0:
        return "no_closing_issue"

    if pr_node['closingIssuesReferences']['totalCount'] > 1:
        return "multiple_issues"

    if pr_node['closingIssuesReferences']['nodes'][0]['repository']['nameWithOwner'].lower() != repo_name.lower():
        return "cross_repo_issue"

    return "candidate"