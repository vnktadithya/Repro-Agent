# BUILDLOG

## Wed Oct 21, 2026 — Sprint 0: instance definitions

### Worked example: OpenHands/software-agent-sdk PR #4876 (issue #4863)
- Merge method: squash — evidence: 1) all the file edits exists between the parent commit and the squashed commit on main, 2) the parent is the main commit while the PR is having 13 commits, this is only possible by squash as all the commits in the PR will combined to 1 and squashed on to the main, so it's parent is the one on the tip of the main branch, right before the squash commit lands
- Pre-fix commit: 856d99d… — derived as: 09e8980^
- Split: 3 source, 2 test, 1 other
- Apply check: test patch exit 0, source patch exit 0
- Environment: the pre-fix environment is created through the command `uv sync --dev --frozen`. --frozen means: install exactly the versions pinned in uv.lock at that commit, without re-resolving them

| Run | test_remote_workspace.py | test_cloud_workspace_repos.py |
|---|---|---|
| Pre-fix (baseline) | 68 passed, exit 0 | 64 passed, exit 0 |
| + test patch | 4 failed, 70 passed, exit 1 | 1 failed, 64 passed, exit 1 |
| + test + source patch | 74 passed, exit 0 | 65 passed, exit 0 |

- FAIL_TO_PASS (5): `test_load_skills_from_agent_server_preserves_base_context_when_found`, `test_load_skills_from_agent_server_preserves_base_context_on_fallback`, `test_load_skills_from_agent_server_preserves_current_datetime`, `test_load_skills_from_agent_server_applies_disabled_skills` in `test_remote_workspace.py`
and `test_load_skills_from_agent_server_preserves_base_context` in `test_cloud_workspace_repos.py`
- PASS_TO_PASS: 134, including the 2 new tests that passed pre-fix
- Exit-code drills: 
2 → caused by an import in a test file which is not present in the environment. It is caused by a missing or broken dependency.So it is environment failure.  
5 → caused by searching for the function which doesn't exist in the test file. Ex: `uv run pytest tests/workspace/test_cloud_workspace_repos.py -k zzz_nothing`. here after `-k` it looks for `zzz_nothing` in the functions inside the file `test_cloud_workspace_repos.py` which doesn't exist. This pytest command will be created by our sandbox environment, so it is a harness failure. 
**Note:** when the agent writes a repro test and runs a bad command, that's an agent failure, scored as a failed repro, not a sandbox failure.
4 → occurs when the command includes an unrecognized argument. Ex:  `uv run pytest tests/workspace/test_cloud_workspace_repos.py --not-a-flag`.
Also caused when the test path doesn't exist.

### Definitions
1. **Pre-fix commit:** 
-> For merge-commit: the merge commit has 2 parents. Parent 1 is the  tip of the main branch before the fix landed and Parent 2 is the last commit in the PR branch. The pre-fix commit is the one on the main-branch. <sha>^1
-> For squash-merge: it combines all the commits in a PR and make it as a single commit on the main thread. It's parent is the last commit on main branch. So, the pre-fix commit is the one on the main branch. <sha>^
-> For rebase: it copies each commit from the PR on to the main branch one by one and the pre-fix commit (the commit before the PR on the main branch) lies N commits behind where N is is number of commits in the PR. <sha>~N

-> hot the method is detected:
1) 2 parents: merge-commit
2) 1 parents and commit diff includes all file edits: squash
3) otherwise: rebase

=> For a PR with s single commit, both squash and rebase looks identical, but `^` and `~` gives the same commit. So, it doesn't matter which one we call.
=> A derived pre-fix commit is passed only if both patches (`source patch` and `test patch`) pass `git apply --check`.

2. **Test/source/other split:**
-> Test file: any file under a directory named `test/` or `tests/`, any file whose name starts with `test_` or ends with `_test.py`, and any `conftest.py` (pytest loads fixtures from it automatically, so the test patch can't run without it). Non-`.py` files under test directories (fixture data like `.json`, `.txt`) go in the test patch, because the test patch must run on its own.
-> Source file: everything else the fix needs in order to work — `.py` code, plus config like `pyproject.toml` or `setup.cfg` when the fix changes them.
-> Other: files that pytest doesn't collect, the package doesn't import, and neither patch needs — docs, changelogs, temporary PR artifacts. Example: OpenHands' `.pr/` directory lands on main with the squashed commit and is removed later by an automated cleanup PR (`.github/workflows/pr-artifacts.yml`), so it is in the history but belongs to neither patch.
-> Localization ground truth: only the `.py` files in the source patch. Config files are in the source patch but are not where a bug lives. PR #4876: 3 files.

3. **Valid instance:**
-> Candidate (static checks only — kill criterion 1 counts these):
   1) the PR is merged
   2) the PR closes exactly one issue (PRs closing more than one issue are excluded for now)
   3) the test patch touches at least 1 test `.py` file
   4) the source patch touches at least 1 source `.py` file
   5) the pre-fix commit is derived per definition 1, and both patches pass `git apply --check` at it
-> Validated (needs execution): a candidate where at least 1 FAIL_TO_PASS test is observed — fails with only the test patch applied, passes with both patches applied. PASS_TO_PASS is recorded for every validated instance.
-> Kill criterion 2 samples 20 candidates, fixed before any run.

4. **"The suite runs":**
-> Which tests: the test files touched by the test patch that already exist at the pre-fix commit. If the PR only adds new test files, run all existing tests in the directory the new files go into. If that directory doesn't exist yet, use its nearest existing parent.
-> Pass rule: exit code 0 or 1, AND at least 1 test passed. Exit 1 counts because criterion 2 measures the environment, not the test results — a failing test means the environment ran it.
-> Record for every run: passed / failed / error counts, exit code, and runtime.
-> Failure labels:
   exit 1 with 0 passed → environment (every test errored during setup)
   exit 2 → environment (collection/import failure: missing or broken dependency)
   exit 3 → environment (pytest internal error, usually a plugin/version mismatch)
   exit 4 → harness (unrecognized argument or nonexistent path in the command we built)
   exit 5 → harness (selection matched nothing) or repo (`testpaths` / `python_files` config) — check which
   timeout → environment (usually waiting on network or a service), or harness if the limit itself was too short
-> Denominator is fixed at 20. A failure is never removed after the run. A harness bug gets fixed and all 20 are rerun; both results are reported.

### Open questions
- Hangs: the harness enforces a wall-clock timeout per run, separately for install and for tests, and kills the whole process tree (inside Docker: stops the container). Saturday's sample runs with a generous provisional limit and records every runtime; the final limit = slowest healthy run × 3, recorded here with its data. Timeout label: environment, unless evidence shows the limit was too short (harness).
- Issue linking: how "the PR closes exactly one issue" is detected in code — decided when the mining code is written.
- Partial-error environments (some tests pass, many error): counted as "runs" under the current rule; the error counts recorded Saturday will show whether the rule needs tightening.
- PRs closing more than one issue: excluded for now; revisit if the candidate count runs short.

---

## Fri Oct 23, 2026 — Sprint 0: issue linking + path classifier

### Issue linking (closes the Oct 21 open question)
- Source: The `closingIssuesReferences` field in the response object shows the list of issues closed by the PR which are recorded by GitHub. It covers all the links made in the UI 
- Why not REST / body regex: REST has no linked issue data at all. And for the Regex, it misses the links present in the UI and also, regex cannot find the cross repo issue references. It just check the issue number and returns as if the issue was from that repo.
- Known blind spot: when the test like `Fixes #xxxx` is present only in the commit message and not in the PR body, we will miss those PR's which affects the `recall` metric. I am not patching a fix around this right now. Will look into this in future. 
- Check 2 scope (same repo only?): Yes, we select the PR's which solves the issues in the same repo only. We can confirm this by looking into the returned **JSON** Response. We just compare each closing reference's `repository.nameWithOwner` to the PR's own repo, and reject the PR if they don't match. Cross-Repo PR's are excluded for now.
- Verified on PR #4876: 
   -> closing reference → {'totalCount': 1, 'nodes': [{'number': 4863, 'repository': {'nameWithOwner': 'OpenHands/software-agent-sdk'}}]} (output from GraphQL query)
   -> files → `.pr/verify_base_context_preserved.py`, `openhands-sdk/openhands/sdk/context/agent_context.py`, `openhands-sdk/openhands/sdk/workspace/remote/base.py`, `openhands-workspace/openhands/workspace/cloud/workspace.py`, `tests/sdk/workspace/remote/test_remote_workspace.py`, `tests/workspace/test_cloud_workspace_repos.py`
   -> result: 3 source / 2 test / 1 other matching the same result as Oct 21.
   -> merge commit → `09e8980c37abe4e02e29bb9bbfb869811415cfd5`

### Path classifier
- Dot-folder rule: Considered all the root-folders which start with a `.` to be in the `other` patch. Ex: `.github`, `.example-test-results` etc.
- Excluded directories (their `.py` = other):
   - docs -> The `.py` files present in the docs folder are not imported by any package or not used by test patch, so they are excluded.
   - examples -> These are the scripts user runs. The package never imports them. So they are excluded. 
- Config files counted as source: configuration files are considered under source patch when modified like `pyproject.toml`, `setup.cfg`(as of now). Because, when they change, they matter for testing the bug which was claimed to be solved. `setup.py` wich is also a config file is directly considered as `source` as it is already a `.py` file. 
- Folder matching depth: In the code, folders can be matched at any depth and can be listed under respective patch. **The trade-off:** Because of this, any `examples` or `docs` present inside any packages are considered to be `other`. The `.pyi` files are considered under `other` patch as they contain the structural definition of a package and not the executable code.
- Deleted files and check 3: Usually, the check is when the test_patch is applied, they should fail and they should pass when source_patch is applied on top of it. But, when the change type is `Deleted` and when any of the test files are deleted, we cannot do the Fail_To_Pass test on it. A test file is counted only if the change type is anything other than `DELETED`.
- Tests: 17 paths — `python -m pytest tests/test_classify_path.py` → 17 passed

### Measured
- GraphQL cost: single-PR query = 1 point; 4,997 of 5,000 remaining after the probe

---

## Sun Oct 25, 2026 — Sprint 0: candidate check (checks 1–4)

### Status table (first-failure order)
| # | Status | Field read | Fails when |
|---|---|---|---|
| 1 | not_merged | `merged` | False |
| 2 | no_closing_issue | `closingIssuesReferences.totalCount` | count = 0 |
| 3 | multiple_issues | `closingIssuesReferences.totalCount` | count > 1 |
| 4 | cross_repo_issue | `closingIssuesReferences.nodes[0].repository.nameWithOwner` | The issue and PR are from different repos |
| 5 | files_truncated | `files.totalCount` | count > 100 |
| 6 | no_test_file | `files.nodes.path`, `files.nodes.changeType` | when the test patch contains no `.py` whose `changeType` is not `DELETED`|
| 7 | no_source_file | `files.nodes.path`, `files.nodes.changeType` | when the source patch contains no `.py` whose `changeType` is present in `SOURCE_COUNTED_CHANGE_TYPES` in `utils.py` |
| 8 | candidate | - | - |

- Why `totalCount`, not `len(nodes)`: I fixed `closingIssuesReferences(first: 5)`. So at max, it will show 5. So the `len(nodes)` might be 5 in cases where there are more actual closing issues than 5.
- Repo comparison: repo name is compared after normalizing using `.lower()` as the names are case-insensitive. 
- Why the order is fixed: Each PR which passes through the candidate check exactly get one status which is the first check it fails. If we reorder the checks, the PR's might ge the status as a different failure mode. So, these numbers can't be comparable from different runs if the checks are reordered. Also, for some checks prior checks are important.
- Why `files_truncated` sits before checks 3–4: The checks 3 and 4 are to check if the test patch and the source contain the `.py` files. The truncated files check is before because we set the limit to 100 and if the number of files are above 100, the files which are next to the 100 are not fetched. If the only `.py` file in the test patch is in those above 100, the status for the PR will be `no_test_file` whih is wrong. A misreport will corrupt the funnel.

### Check 4: source change-type allow-list
- What check 4 guarantees: It guarantees that the source patch contain atleast one `.py` file and it's `changeType` is one from the `SOURCE_COUNTED_CHANGE_TYPES` in `utils.py`.

- Link to definition 2: localiczation ground truth is the `.py` files which are present in the source patch and their `changeType` is `MODIFIED`.
- `PatchStatus` values (from GitHub's schema):
   - MODIFIED → changes in existing files
   - DELETED → delete an existing file
   - ADDED → add a new file 
   - COPIED → the content of one file is copied bit by bit to another file, but this new path doesn't exist at pre-fix commit.
   - RENAMED → the file name is renamed and it doesn't contain any previous-path field. so it's pre-fix name can't be confirmed.
   - CHANGED → the file type is changed. Ex: regular file -> symlink.
- Fails closed: added an allow-list which includes the `changeTypes` which are considered. If a deny-list in used instead of an allow-list, it will silently accept cases which I forgot to add
- "At least one" rule and mixed PRs: A PR with `ADDED` and `MODIFIED` `changeType` on different files in the source patch passes on the `MODIFIED` one.
- Verified on PR #4876: 3 source files (all `MODIFIED`), 2 test files (both `MODIFIED`), 1 `ADDED` file under .pr/ → other. Result: `candidate`

### Why `.py` lives in `check_candidate`, not `decide_patch`
- `decide_patch` is just to check which patch the file belongs to. `check_candidate` is responsible for checking whether the candidate has met the eligibility criteria and can become an instance. So the `.py` check is the eligibility criteria that the files has to meet for the candidate to become eligible, so it is in `candidate_check.py`.

### Limitations
- Feature PRs: They are ignored as their previous versions doesn't include the files which are newly added in this PR. So,when a test patch is applied first, it fails with an import error or attribute error which is a trivial `Fail_to_Pass` which inflates the headline rate. In feature implementations, all the files in the source patch's `changeType` is `ADDED` and they are ignored as we dont get a true result of `Fail_to_Pass` output. There's no ground truth localization target
Note: Feature PR's is a POSSIBLE EXTENSION in future.

- Mixed PRs and localization ground truth: For the mixed PR's where it includes the `changeType` as `ADDED` and `MODIFIED` for different files in the source patch, the ground truth must hold the ones whose `changeType` is in allowed-list.

### Bug: `.py` requirement
- What slipped: Initially missed the `.py` check in `candidate_check.py` for the cases `no_test_file` and `no_source_file`. 
- Why the tests missed it: The tests missed them, because my PR #4876 contains `.py` files in the both test and source.  
- Takeaway: A fixture-mutation test only covers a rule if some test feeds in an input where that rule changes the output.

### Measured
- Tests: `python -m pytest` → 31 tests passed

---

## Mon Oct 26, 2026 — Sprint 0: discovery (pagination, state, retries)

### Query shape
- Connection and arguments: connection is `repository(owner, name).pullRequests(...)`. Its arguments are `states: [MERGED]`, `orderBy: {field: CREATED_AT, direction: ASC}`, `first: $first` and `after: $cursor`. 
- Fields per node: totalCount, pageInfo { hasNextPage endCursor }, nodes {number, merged, mergedAt, baseRefName, mergeCommit {oid}, commits {totalCount}, closingIssueRefrences(first: 5){ totalCount, nodes{number, repository {nameWithOwner}}}, files(first: 100) { totalCount, nodes{path, changeType}} }
- Why `CREATED_AT ASC`: The cursor marks a position in the sort order. A PRs creation time never changes, so a cursor's position never changes. So, the pages stay identical across a run and a resume. With `UPDATED_AT` instead of `CREATED_AT ASC`, a PR edited mid-run would jump to a new position and get skipped or fetched twice.
- What a cursor encodes: cursor points to the last PR of the page that is just fetched and it encodes the PR 's sort key. When decoded, it is `cursor:v2:` + the created-at timestamp + an integer id. `after:` cursor then returns the PRs after that position.
- Why `states: [MERGED]`, and what it does to `not_merged`: it ensures that all the PR's which are fetched are merged and for any PR which is fetched, it's status cannot be `not_merged`.
- Completeness denominator: `len(statuses)` = `totalCount`, 2739 = 2739

### State design
- Shape of `state.json`: {"cursor": <pointer to next page>,
                          "next_page": <next page to be fetched>,
                          "total_count": <number of PRs in the repo>,
                          "has_next_page": <bool value defining if next page is present>,
                          "statuses": {"<owner/repo#pr_number>": <status>}
                          }
- Key format: `<Owner>__<Repo_name>#<PR_number>`
- When it is written: once per page, in a single `save_state()` call inside `record_page()` function after the page is fectched, saved and checked.
- Why statuses and cursor reach disk together: They both are the data fetched from each page during pagination. The cursor is a pointer pointing to the next page to fetch. It means, the current page entries should be updated while updating the cursor so that their statuses aren't lost. If cursor is updated before the statuses and if there is a failure in between, we lose the statuses of PR's in a page. If statuses are updated before cursor and if there is a failure in between, the cursor will be pointing to the same page leading to wasted fetch and rewrites the old entries  with the same information. They are written through atomic write where hey both land or neither does.
- Why per-page keys were rejected: we are using PR-level keys, so that when a page is re-processed, the entries are overwritten, that the funnel count will not be doubled.
- Atomic write: `record_page` updates the memory, `save_state` writes the whole new state into a temp file in the same directory. `os.replavce` then swaps it in with the already existing `state.json` file. So, when there is an interruption mid-write, the old `state.json` is left untouched.The temp file has to be in the same directory because os.replace is only atomic within one filesystem.

### Retry policy
| Condition | Retried? | Wait |
|---|---|---|
| Timeout / ConnectionError | yes | wait for the time computed by `compute_backoff` based on the attempt |
| 5xx | yes | wait for the time computed by `compute_backoff` based on the attempt |
| 429 | yes | if `Retry-After`, wait according to it, else if `x-ratelimit-remaining: 0`, wait based on `x-ratelimit-reset` + 1, else computed by `compute_backoff` based on the attempt |
| 403 with `Retry-After` or `x-ratelimit-remaining: 0` | yes | if `Retry-After`, wait according to it, else if `x-ratelimit-remaining: 0`, wait based on `x-ratelimit-reset` |
| 403 without rate-limit headers | no | raises immediately |
| 401 / 404 / other 4xx | no | raises immediately |
| GraphQL `errors` in a 200 | no | raises immediately |
| After `MAX_ATTEMPTS` | no | raises immediately with runtime error right after the `MAX_ATTEMPTS` without any wait |

- Provenance: the funcitons `fetch_with_retry` and `_rate_limit_wait` are written by agent as the same logic is already written by me in my `rca-lora-scaling` project. Reusing the `compute_backoff` to handle wait time from `rca-lora-scaling` project.
- Budget check (points per page × pages vs hourly budget): ! point per page, total of 55 pages which is a total of 55 points per the whole run again GitHub's GraphQL ratelimit of 5000 per hour. Rate limit could't have stopped this run. But, for the production level code, the rate limit handling is required where there can be too many requests.

### Limitations
- Created-order vs merge-time: 
 -> The connection is sorted by creation date and filtered to MERGED.
 -> A PR created before the cursor’s position that merges after that page was fetched lands behind the cursor.
 -> A single run detects this: totalCount on the last page exceeds the PRs processed.
 -> A resume run from the saved cursor misses it silently.
- Snapshot date: 25 October 2026 22:47:50

### Bug: double-encoding risk
- What slipped: the `reponse.text` field from GraphQL response in already in json format. I tried to encode it again before saving it to json file
- Why the tests missed it: because of a missing test which check the round trip `save_raw_page` -> `parse_page` returning a dict.
- Takeaway: `response.text` is already a JSON string, so `json.dump` of it stores a quoted string, and `json.loads` returns a str, not a dict.

### Bug: bare `repo_name`
- What slipped: initially just used `repo_name` for the candidate check instead of `owner/repo_name` which lead to 18 cross_repo_issues which is false.
- Why the tests missed it: every test passed the full name `OpenHands/software-agent-sdk`. So they didn't catch this issue.
- Takeaway: a rule is only covered when some test feeds an input where that rule changes the output.

### Bug: `next_page` saved as the current page
- What slipped: Initially, I saved the current page number as `next_page` instead of `cur_page + 1` in `state.json` file. It won't lead to any issues in the initial run. But, when there is a failure in the mid-run and the pipeline stops, it starts from the stopped page when restarted. As the next_page field is pointing to the current page now, the cursor correctly fetches the next page contents as it is pointing to it, but it rewrites the previous page content as the `page_num` is pointing to it.
- Why the tests missed it: there are no test cases to test this
- Takeaway: always store the `next_page` field as `cur_page + 1` in the `state.jaon` file.

### Measured
- Run: 
repo: `OpenHands/software-agent-sdk`, 2739 merged PRs (`totalCount`), 55 pages with 50 instances per page, coat per page is 1

| Status | Count |
|---|---|
| no_closing_issue | 1782  |
| candidate | 646 |
| no_test_file | 161 |
| no_source_file | 108 |
| cross_repo_issue | 29 |
| multiple_issues | 13 |
| not_merged | 0 |
| files_truncated | 0 |
| **Total** | 2739|

- Sum = `totalCount`: the sum of all the processed PR's is exactly equals to the count retuned by GraphQL API. `2739 = 2739`
- PR #4876: a valid `candidate`
- Resume test: stopped mid-run after fetching 17 pages and reran it. Exactly pickedup the state and fetched the remaining pages. compared the result with no-failure run. 
 -> Result: `True 2739 2739`
- Tests: all 31 tests passed