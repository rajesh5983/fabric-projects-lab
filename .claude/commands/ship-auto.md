Fully autonomous ship: commit, open PR, and loop fixing CodeRabbit's findings 
until approved, then merge — no confirmation prompts, except the exclusion 
list below.

EXCLUSION CHECK: if this diff touches Key Vault/secrets, .coderabbit.yaml, 
branch protection config, docs/ADR/**, or .github/workflows/**, STOP after 
step 3 (PR opened) and report manual review required. Never loop 
autonomously on these.

1. Commit all changes with a message summarizing the diff. No confirmation.

2. Push, open PR via gh pr create with a real summary.

3. Poll for CodeRabbit's review: 30s/60s/90s intervals. If no response after 
   ~3 min, wait once more (up to 5 min total) before treating as a stall.

4. Once a review lands, evaluate each finding:
   - Legitimate: fix it, push a new commit (this reliably triggers a fresh 
     CodeRabbit review — confirmed twice this session). Go back to step 3.
   - False positive (verified against actual code/config): reply on the PR 
     with justification. Do NOT change the code under dispute. THEN: since 
     a comment-only @coderabbitai mention does not reliably produce a fresh 
     formal review (confirmed — two consecutive attempts failed on PR #8), 
     and an empty commit (git commit --allow-empty) is unreliable for the 
     same reason (no file diff for CodeRabbit to review against — the 
     probable root cause of that same stall), force a real re-review with 
     a trivial real-content commit instead:
     - Append a one-line, dated entry to a small tracked review-log file at 
       the root of the repo/subproject being shipped (e.g. .review-log — 
       create it if it doesn't already exist), recording the dispute:
       "YYYY-MM-DD: disputed finding on <file> — <one-line reason>, see PR 
       comment for full justification"
     - git add <that file>
     - git commit -m "chore: log disputed CodeRabbit finding, trigger re-review"
     - git push
     Then return to step 3's polling.
   - Uncertain: treat as legitimate, fix it.

5. STALE-REVIEW-DECISION CHECK: before advancing, check 
   gh pr view <n> --json reviewDecision,statusCheckRollup,reviews
   If reviewDecision is REVIEW_REQUIRED with zero non-dismissed reviews 
   (this specific state, not "CodeRabbit hasn't responded yet"), that 
   means no approving review exists at all — do NOT keep polling or 
   re-triggering as if CodeRabbit were slow. Instead: use the same 
   real-content .review-log commit mechanism from step 4 (with a note like 
   "re-review triggered: stale/dismissed reviews, forcing fresh formal 
   review") to force a fresh formal review that can satisfy the 
   approval-count rule. This is a different failure mode than "review 
   pending" and needs a different response.

6. HARD CAP: after 5 full review cycles without reaching a mergeable state, 
   stop and check whether the block is substantive or structural:
   - If the CodeRabbit status check is passing and every finding from the 
     last real review is either fixed or disputed-with-a-reply (no 
     unaddressed legitimate findings remain): this is the expected 
     self-approval-blocked case, not a real problem — required_approving_
     review_count can never be satisfied by this account approving its own 
     PR (gh pr review --approve structurally fails with "Can not approve 
     your own pull request" for any PR authored under this account, 
     confirmed on PR #8; do not attempt it, ever, as a fallback). Go 
     straight to an admin-bypass merge, documenting the reasoning in the 
     merge commit itself, same pattern as PR #8:
     gh api repos/<owner>/<repo>/pulls/<n>/merge -X PUT \
       -f merge_method=squash \
       -f commit_title="Merge PR #<n> (admin override: self-approval structurally blocked on solo-author repo; CodeRabbit findings independently verified resolved across <N> review cycles)"
     Then confirm via gh pr view <n> --json state,mergedAt.
   - If the status check is still failing or a legitimate finding remains 
     unaddressed: this is a real stall, not the structural self-approval 
     case — do NOT bypass. Stop and report what was tried each round.

7. Once CodeRabbit's own formal review shows APPROVED (satisfies both the 
   status check and the approval-count rule simultaneously — confirmed this 
   is possible with zero human clicks): queue auto-merge 
   (gh pr merge <n> --auto --squash --delete-branch=false). Don't wait 
   around to confirm completion. (If the merge instead happened via the 
   step 6 admin-bypass path, this step is already done.)

8. Final report regardless of outcome.
