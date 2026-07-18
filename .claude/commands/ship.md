Full commit-to-PR-to-auto-merge flow for the current branch (default: develop, 
confirm with me if I'm on something else).

EXCLUSION CHECK (run first, always):
Before doing anything else, check whether this diff touches any of: Key Vault 
or secret-handling code, .coderabbit.yaml, GitHub branch protection config, 
any file under docs/ADR/, or any CI/CD workflow file (.github/workflows/**). 
If yes, skip the auto-merge step (step 7) entirely — after step 5 (CodeRabbit 
comment shown), stop and explicitly tell me manual merge is required for this 
PR, then wait for my instruction. Do not queue auto-merge on these regardless 
of how clean the review looks.

1. Show me the full diff of all staged/unstaged changes. Wait for my explicit 
   confirmation before proceeding — do not assume approval.

2. Once confirmed, commit with a clear message summarizing the actual changes 
   (derive from the diff, don't ask me to write it unless it's ambiguous).

3. Push the current branch to origin.

4. Open a PR to main via gh pr create, using a real summary of the commit(s) 
   as title/description, not a placeholder. Include a Test plan section if 
   there's anything meaningfully testable. Note if CodeRabbit flags this PR 
   as overlapping with a prior one (branch divergence artifact) — if so, flag 
   it to me before continuing.

5. Poll for CodeRabbit's comment via gh pr view <number> --comments. Use ONE 
   polling loop only — check first whether a monitor is already running for 
   this PR before starting another. Wait 30s, check. If not present, wait 60s, 
   check. If not present, wait 90s, check. If not present after these 3 
   attempts (~3 min total), STOP polling and report: "CodeRabbit hasn't 
   responded after ~3 minutes — check the PR or dashboard directly. I won't 
   keep polling indefinitely." Do not start a 4th attempt or a background loop.
   
   Once found, show me CodeRabbit's full comment plus the PR URL.

6. If the exclusion check flagged this PR, stop here per that instruction.

7. Otherwise, queue auto-merge: 
   gh pr merge <number> --auto --squash --delete-branch=false
   This does NOT merge immediately — GitHub merges automatically once 
   CodeRabbit's review check passes (Approved), and leaves the PR open 
   untouched if CodeRabbit requests changes.

8. Report back plainly: "Auto-merge queued on PR #<n>. Will complete 
   automatically if CodeRabbit approves, stays open if it requests changes. 
   Run /ship-status later to check on it and reconcile develop." Do not poll 
   for the outcome or wait around — end here.
