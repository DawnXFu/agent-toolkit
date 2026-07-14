# Unified Handoff Protocol Schema 1.0

## Frontmatter

Required scalar keys:

```yaml
---
schema_version: "1.0"
handoff_id: "20260713T230000-abc123"
created_at: "2026-07-13T23:00:00-07:00"
updated_at: "2026-07-13T23:00:00-07:00"
source_agent: "claude-code"
target_agent: "any"
mode: "standard"
language: "auto"
status: "draft"
repository: "owner/repository"
working_directory: "."
branch: "feat/example"
head_commit: "0123456789abcdef"
quality_score: null
continues_from: null
---
```

The parser intentionally supports scalar YAML only so Python 3.9 can operate without PyYAML. JSON-quoted strings are valid YAML scalars.

## Stable section identifiers

Section headings remain English and must not be renamed:

1. Objective
2. Current State
3. Codebase Understanding
4. Completed Work
5. Files Changed
6. Decisions
7. Attempts and Failures
8. Evidence and Verification
9. User Requirements and Constraints
10. User Corrections
11. Knowledge Status
12. Important Context
13. Open Questions and Blockers
14. Immediate Next Steps
15. Resume Instructions
16. Environment State
17. References
18. Security Check

Section bodies may use the user's language. Non-applicable non-blocking sections use `N/A - <specific reason>`. Objective, Current State, and Immediate Next Steps may never be N/A.

## Knowledge status

Material claims are classified as:

- Verified Fact: supported by repository state, command output, tests, or authoritative user correction
- Agent Inference: reasoned conclusion with its basis
- Unverified Assumption: unresolved claim with a validation step

## Validation

Minimum scores: compact 70, standard 80, full 85. Secrets and incomplete blocking sections prevent finalization regardless of score. Failed validation leaves the file as a draft and does not update `HANDOFF.md`.

Allowed redaction markers:

- `[REDACTED]`
- `[SECRET_NAME_ONLY]`
