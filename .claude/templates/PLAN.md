# Plan: <short title>
Status: in progress
Record: none yet (run records.py new <slug>)
Request: <the user's words, short>
Done when: <what the user sees or can do, and the check that proves it>

## Changes (follow pattern: <closest existing example>)
- [ ] <file>: <change>

## Design
- [ ] architecture: where it lives, layers, boundaries (standards/architecture.md)
- [ ] UX: feedback, errors, empty states, mobile (standards/ux.md)

## Standards
- [ ] <file type> checklist met (.claude/standards/<type>.md)

## Edge cases
- [ ] empty / error / loading states
- [ ] invalid input, mobile, slow network

## Tests
- [ ] lock-in or new test: <name>

## Safety
- [ ] callers updated / nothing else breaks (full suite)
- [ ] security: auth, input validation, secrets (if relevant)
- [ ] database: migration created and tried on dev DB (if schema changes)
- [ ] privacy: data minimised, consent, policy updated (if personal data/cookies/payments)
- [ ] deploy: CI green, rollback path, env vars documented (if deploy/config changes)

## Quality
- [ ] accessibility (labels, alt, keyboard, contrast)
- [ ] performance (images, scripts, queries)

## Undo
- [ ] rollback path: /undo checkpoint or revert commit

## Discipline record
- [ ] checklist record filled for every discipline touched (`records.py new <slug>`; the Stop hook lists gaps) - proof: <record path>

## Review
- [ ] request and Done-when re-checked; code-review run, findings fixed
