Perform a post-change validation pass on the code that was just modified — by an LLM or a human — in this project. This is a soft code review: your job is to confirm the change meets the standards below, and to fix (or precisely flag) every place it does not.

## Scope: what to review

1. Determine exactly what changed. Prefer the project's version control:
   - Unstaged + staged changes: `git diff HEAD` and `git status --porcelain`
   - Untracked files: `git ls-files --others --exclude-standard`
   - If reviewing a branch or PR, diff against the merge base: `git diff $(git merge-base HEAD main)...HEAD`
2. If no version control is available, ask which files changed, or review the files you were told were modified.
3. Review **every** changed file. Read each one in full, plus the surrounding code it touches — a change is only correct in context.

Do not review files that were not part of the change, except to understand context or to confirm the change integrates correctly.

## What to check

For each of the following dimensions, inspect the changed code and report every issue you find. Where you can fix an issue directly and safely, fix it; where a fix is risky or requires a decision, flag it precisely with a concrete recommendation.

### 1. Robustness (short- and long-term)
Will this hold up? Consider malformed input, empty/null/boundary values, concurrent access, and failure of anything external it depends on. Consider not just today's inputs but how this behaves as the system grows and requirements shift.

### 2. No duplication
The code must not duplicate or reimplement functionality that already exists in the codebase. Search for existing helpers, utilities, constants, and patterns before accepting a new implementation. If the change reinvents something already present, replace it with the existing facility (or, if the existing one is inadequate, extend it rather than forking it).

### 3. Correctness
Does the code do what it claims to do? Hunt for logic errors, off-by-one mistakes, race conditions, inverted conditionals, and unhandled states. Trace the important paths by hand and confirm the actual behavior matches the intended behavior.

### 4. Completeness
Are there gaps — missing validation, unhandled branches, `TODO`s left behind, partial implementations? If a new feature was added, is it wired up end-to-end (not just a function defined but never called)? Are tests updated or added to cover the new behavior?

### 5. Modularity and testability
- Are new functions/classes small, single-purpose, and independently testable?
- Are new dependencies injected rather than hardcoded — no hidden global state, no tight coupling to I/O or external resources (e.g. global file paths)?
- Can this code be unit-tested in isolation without mocking half the system?
- Are side effects (I/O, network, database, filesystem) behind interfaces that can be substituted in tests?
- Are functions pure where possible?

Rule of thumb: if testing this code requires mocking more than two layers deep, the design is likely wrong. Code that cannot be tested without its production environment is untestable code — treat that as an issue.

### 6. Appropriate abstraction
The code should sit at the right level of abstraction — neither too concrete nor too abstract.
- Too concrete: copy-paste duplication; the same decision inlined in many places.
- Too abstract: indirection nobody needs, which is confusing and hard to debug.
- Every abstraction must earn its existence — by being used in more than one place, OR by making a genuinely complex concept significantly easier to reason about.
- Are there concrete implementations that should sit behind an interface because they represent a decision that could change (storage backend, external service, algorithm choice)?
- Are there interfaces with only one implementation and no foreseeable second one? That indirection may not be earning its keep.

### 7. Performance
Look for accidentally introduced O(n²) loops, unbounded allocations, missing pagination, and resource leaks (file handles, connections, sockets). Will the change degrade under realistic load, not just in the demo case?

### 8. Documentation
Are public functions, non-obvious logic, and configuration changes documented? Are the README or inline docs updated to match the new behavior? Stale docs that now contradict the code are a defect.

### 9. Dependency hygiene
If new dependencies were added:
- Are they pinned to exact versions?
- Are they actively maintained?
- Do they duplicate something already in the project?
- Do the names look legitimate — verify this is not typosquatting (a lookalike name for a popular package)?

### 10. Steering compliance
Does the change violate any project or global steering rules, conventions, or constraints — e.g. `CLAUDE.md`, `AGENTS.md`, `.kiro/steering/**`, `.cursor/rules`, `CONTRIBUTING`, `.editorconfig`, or linter/formatter configs? For each violation, identify the specific rule it broke and fix it.

### 11. No hacks or band-aids
Is every fix addressing the root cause, not papering over a symptom? Are there workarounds, special-case conditionals, or temporary patches that should be proper solutions instead? If a fix looks like a hack, identify the underlying problem and propose (or implement) the real fix.

### 12. Readability and maintainability
Could a competent reader of this language understand what the code does without relying on comments, docs, or the function name? They should be able to.
- Reject deeply nested `if`/loops unless there is an exceptionally good, stated reason.
- Prioritize guard clauses and flat control flow. Deep nesting usually signals code that can be flattened by inverting a conditional or extracting a well-named, reusable function.

## Active checks — you must run these, not just read

### Tests
- Run the project's full test suite.
- If any test fails, investigate, identify the **root cause**, and fix the root cause — do not silence, skip, or weaken the test.
- Every new or modified code path MUST have test coverage. If tests are missing, write them.
- Validation is not complete until the suite passes.

### Linting and static analysis
- Run the project's linter, formatter, and static-analysis tools (e.g. eslint/prettier, ruff/pylint/mypy, clippy, checkstyle, go vet — whatever this project uses).
- Fix all errors and warnings introduced or surfaced by the change.
- Validation is not complete until these pass cleanly.

## Output

Report your findings as a list. For **each issue**:

1. **Location** — the file and the precise location (line number, function, or symbol).
2. **Problem** — restate the specific problem directly and concretely. No vague "consider improving"; say exactly what is wrong.
3. **Fix** — the concrete action to take. If you fixed it, say what you changed. If you did not, give the exact change to make and why.

Then a short summary:
- Test suite result (pass/fail, with the command run).
- Lint / static-analysis result (pass/fail, with the command run).
- Overall verdict: whether validation passed, and if not, what remains.

Do not report validation as complete while any test fails, any linter/static-analysis check fails, or any unaddressed issue remains. If a dimension had no issues, you may say so briefly rather than padding the report.
