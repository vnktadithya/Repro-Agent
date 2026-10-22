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