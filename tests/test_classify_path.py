import pytest

from mining.classify_path import decide_patch

test_cases = [
    ('.pr/verify_base_context_preserved.py', 'other'),
    ('openhands-sdk/openhands/sdk/context/agent_context.py', 'source'),
    ('openhands-sdk/openhands/sdk/workspace/remote/base.py', 'source'),
    ('openhands-workspace/openhands/workspace/cloud/workspace.py', 'source'),
    ('tests/sdk/workspace/remote/test_remote_workspace.py', 'test'),
    ('tests/workspace/test_cloud_workspace_repos.py', 'test'),
    ('pkg/testing_utils.py', 'source'),
    ('tests/data/sample.json', 'test'),
    ('docs/conf.py', 'other'),
    ('openhands-sdk/docs/conf.py', 'other'),
    ('tests/fixtures/pr_merged.json', 'test'),
    ('pyproject.toml', 'source'),
    ('test_classify_path.py', 'test'),
    ('CHANGELOG.md', 'other'),
    ('conftest.py', 'test'),
    ('openhands/sdk/foo_test.py', 'test'),
    ('openhands/sdk/types.pyi', 'other')
]

@pytest.mark.parametrize("file_path, expected_category", test_cases)
def test_path_classification_takes_place_accurately(file_path, expected_category):
    assert decide_patch(file_path) == expected_category
    