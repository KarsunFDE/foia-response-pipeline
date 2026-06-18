---
name: pr-summary
description: Generate and post a PR summary in the repo's pull_request_template.md format onto the current branch's PR. Fires automatically after a git push to a non-main branch (via the pr-summary-on-push hook), or invoke with /pr-summary. Lists every changed file as `path/to/file — what changed`, fills the brownfield-debt + checklist sections, and posts via gh (comments on the open PR, or creates one against main if none exists).
---

# PR Summary

Produce a PR description in **this repo's `.github/pull_request_template.md` format** and post it to the current branch's PR. This is the format that passes the repo's PR-lint jobs: the Summary must name every changed file as a bare `` `path/to/file` `` line.

## When to run

- Automatically: right after a `git push` to a non-`main`/`master` branch (the `pr-summary-on-push` PostToolUse hook injects a reminder).
- Manually: `/pr-summary` (optionally `/pr-summary base=<branch>` to diff against a base other than `main`).

## Steps

1. **Resolve branch + base.**
   - `git rev-parse --abbrev-ref HEAD` → current branch. If it is `main`/`master`, stop — nothing to summarize.
   - Base defaults to `main`. Run `git fetch origin <base> --quiet` so the diff is current.

2. **Collect the diff facts** (do not guess — read them):
   - Changed files + status: `git diff --name-status origin/<base>...HEAD`
   - Size line: `git diff --shortstat origin/<base>...HEAD` → render as `N files, +X/-Y`.
   - Recent commit subjects for context: `git log origin/<base>..HEAD --format='%s'`.

3. **Read `.github/pull_request_template.md`** and mirror its current section headings exactly (it may change over time — do not hardcode). Today it has: `## Summary`, `## Why this change`, `## Touches named brownfield-debt items?`, `## Modernization-week alignment (only fill if YES)`, `## Checklist`.

4. **Brownfield-debt check.** Read `docs/debt-lockfile.yml` (+ `docs/brownfield-debt.md` if needed). If any changed file maps to a `locked: true` item, fill the **YES** branch (list item IDs, note the lockfile flip + `debt-touch-approved` label, add the modernization-week table). Otherwise fill **NO**. Never claim NO without checking.

5. **Compose the body** in exactly this shape:

   ```
   ## Summary

   <1–3 sentence prose: what changed, the shape of why, scope tag (e.g. "Docs-only"), and the size line "N files, +X/-Y".>

   `path/to/first/file` — <what changed here + why, one line>.
   `path/to/second/file` — <what changed here + why, one line>.
   <...one bare-backtick line per changed file...>

   ## Why this change

   <The problem it solves. Link the driving ADR under docs/adrs/ or a ticket, as `path` or #id.>

   ---

   ## Touches named brownfield-debt items?

   - [x] **NO** — this PR does not touch any debt item. (Default.)

   <or, if YES: check the YES boxes, list item IDs, and fill the modernization-week table>

   ## Modernization-week alignment (only fill if YES)

   N/A — no debt items touched.

   ## Checklist

   - [x] Summary above is real (Claude-drafted + human-reviewed), not the empty template
   - [ ] Tests pass locally (`mvn test` / `pytest` / `npm test` as relevant) — <state N/A for docs-only>
   - [ ] `make verify-debt-locks` passes locally — <note if run>
   - [x] If touching debt: ADR added under `docs/adrs/` — <N/A if not touching debt>
   ```

   Rules for the file list: **every** changed file gets its own `` `path/to/file` `` line (this is what the lint job checks). Mark `deleted` / `new file` / `renamed` explicitly. Keep each description to one line.

6. **Write the body to a temp file** (e.g. `.git/PR_SUMMARY_BODY.md`) with the Write tool — do NOT pass the multi-line, backtick-heavy body as a shell argument (it breaks quoting). Then post with `--body-file`.

7. **Post to the PR** (any-branch → its own PR):
   - Find it: `gh pr list --head <branch> --state open --json number --jq '.[0].number'`.
   - If a number comes back → `gh pr comment <number> --body-file .git/PR_SUMMARY_BODY.md`.
   - If empty → create it: `gh pr create --base <base> --head <branch> --title "<derived from commits>" --body-file .git/PR_SUMMARY_BODY.md`.
   - Delete the temp file after posting.

8. **Report** the PR URL/number and whether you commented or created the PR. If `gh` is missing or unauthenticated, print the composed body in the chat instead and say it was not posted.

## Guardrails

- Never invent file paths, sizes, or debt status — derive them from git + the lockfile.
- Docs-only PRs: mark the test checklist line N/A rather than claiming tests ran.
- Do not push, merge, or change branches. This skill only reads the diff and posts text.
- One comment per invocation — don't loop.
