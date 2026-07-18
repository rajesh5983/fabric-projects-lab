Check status of any open PRs with queued auto-merge, and reconcile branches 
if anything has merged since last check.

1. List open PRs: gh pr list --state open --json number,title,autoMergeRequest,mergeable

2. For each PR with autoMergeRequest set (auto-merge queued), check its actual 
   state: gh pr view <number> --json state,mergedAt,statusCheckRollup

3. Report plainly for each: still pending (waiting on CodeRabbit), merged (and 
   when), or blocked (CodeRabbit requested changes — show why, and note this 
   needs my attention, not auto-resolution).

4. Check current divergence regardless of the above: 
   git rev-list --left-right --count origin/main...origin/develop
   If this reports anything other than "0 0", reconcile:
   - git checkout develop
   - git fetch origin
   - git rebase origin/main
   - git push --force-with-lease origin develop
   - Re-check divergence, confirm it's now 0 0

5. Summarize: what merged, what's still pending, what's blocked and needs my 
   attention, and whether develop needed (and got) a rebase.
