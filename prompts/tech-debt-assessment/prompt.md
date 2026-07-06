Perform a comprehensive technical-debt assessment of this entire codebase and produce a prioritized, evidence-based report. Your deliverable is the report — **do not modify code, fix issues, or refactor anything** during this task. The goal is an honest, actionable inventory of the debt, ranked so a team knows what to tackle first.

Write the report to `TECH_DEBT_ASSESSMENT.md` at the repository root (and also summarize the top findings in your reply).

## How to work

Be systematic and evidence-based. Ground every finding in something concrete — a file and location, a metric, a tool's output, a count — not a general impression. Where you cannot verify something, say so rather than guessing.

### Phase 1 — Map the codebase
Before judging anything, understand the whole. Establish:
- Size and shape: languages, total files/lines, top-level structure, the main modules/packages and how they relate.
- Entry points and boundaries: executables, services, public APIs, the layers (I/O, domain, storage, UI).
- The build, test, lint, and CI/CD setup, and which tools the project already uses.
- What the code is *supposed* to do, from its README/docs, so you can judge debt against intent.

### Phase 2 — Gather evidence with tooling
Run the tools that are available; use what the project already depends on, and reach for standard ones where present. Prefer measured signal over eyeballing. Examples (use the equivalents for this stack, skip and note any that aren't installed):
- Sizing / hotspots: `cloc` or `tokei`; `git log --format= --name-only | sort | uniq -c | sort -rn` to find the highest-churn files.
- Danger zones: cross-reference **high churn × high complexity** — files changed often *and* hard to change are the highest-leverage debt.
- Complexity / dead code: language-appropriate analyzers (e.g. lizard/radon, eslint complexity rules, gocyclo, clippy, unused-export detectors).
- Duplication: `jscpd` or the project's duplication tooling.
- Dependencies: outdated + vulnerability audits (`npm outdated`/`npm audit`, `pip list --outdated`/`pip-audit`, `cargo outdated`/`cargo audit`, `go list -m -u all`, etc.).
- Secrets / supply chain: `gitleaks` or `trufflehog` if available.
- Tests: run the suite and coverage tooling; record pass/fail, coverage %, and slow or skipped tests.
- Markers: grep for `TODO`, `FIXME`, `HACK`, `XXX`, and count them by area.

If a tool isn't installed, note the gap in the report's limitations section rather than silently skipping the dimension.

### Phase 3 — Assess across every dimension
Inspect the codebase against each dimension below. For each, capture concrete findings with locations and evidence.

1. **Architecture & structural debt** — weak module boundaries, tight coupling, circular dependencies, layering violations, **misplaced code** (logic living in the wrong layer/module/file — e.g. backend or domain logic in the frontend, transport concerns leaking into business logic, catch-all "utils" dumping grounds), god files/classes, orphaned/dead modules, inconsistent architectural patterns across the codebase.
2. **Code quality & complexity** — cyclomatic-complexity hotspots, over-long functions/files, deep nesting, dead code, commented-out code, magic numbers, unclear naming.
3. **Duplication & reinvention** — the same logic implemented in multiple places; functionality reimplemented that already exists in the codebase or in a dependency/standard library.
4. **Testing debt** — coverage gaps on critical paths, missing test types (unit/integration/e2e), flaky or slow tests, skipped/disabled tests, tests that assert nothing, and code that is untestable by design (deep mocking required, hardwired to its production environment).
5. **Dependency & supply-chain debt** — outdated packages, unmaintained/abandoned dependencies, known vulnerabilities, unused or duplicate dependencies, unpinned versions, and license concerns.
6. **Security debt** — hardcoded secrets or credentials, missing validation at trust boundaries, insecure or outdated crypto, injection-prone patterns, known CVEs in dependencies. (This is a debt scan, not a full penetration test — flag what you find and recommend a dedicated review where warranted.)
7. **Performance & scalability debt** — accidental O(n²) or worse, N+1 queries, missing indexes/pagination/caching, unbounded allocations, and resource leaks (file handles, connections, sockets) that will bite under real load.
8. **Documentation & knowledge debt** — missing or stale README/architecture/API docs, undocumented decisions and tribal knowledge, comments that now contradict the code, weak onboarding.
9. **Consistency & convention debt** — divergent styles or patterns for the same task, inconsistent naming, mixed paradigms, configuration sprawl.
10. **Type safety & correctness debt** — untyped or `any`-typed code, suppressed type/lint errors, unchecked nulls, swallowed exceptions, ignored error returns.
11. **Build, tooling & CI/CD debt** — slow or fragile builds, manual release steps, missing or weak CI, absent linters/formatters, flaky pipelines, non-reproducible builds.
12. **Operational & observability debt** — poor error handling, insufficient logging/metrics/tracing, hardcoded configuration, missing health checks, no graceful degradation.
13. **Data & schema debt** — schema drift, missing or ad-hoc migrations, no backup/restore story, data-integrity risks.
14. **Explicit debt markers** — an inventory of `TODO`/`FIXME`/`HACK` markers, temporary workarounds, and feature flags that have quietly become permanent.

## Scoring and prioritization

Rate every finding on a consistent scale so the report is actionable, not just a list:
- **Severity**: Critical / High / Medium / Low — how much this hurts (risk of defects or outage, security/reliability exposure, drag on development velocity, onboarding cost).
- **Effort**: S / M / L — rough cost to remediate.
- **Priority**: derive from impact vs. effort. Surface **quick wins** (high impact, low effort) explicitly, and separate them from **strategic** items (high impact, large effort) that need planning.

Anchor prioritization in the high-churn × high-complexity hotspots from Phase 2 — debt in code nobody touches matters far less than debt in code the team fights weekly.

Be honest and proportionate: distinguish genuine debt from work that simply hasn't been built yet, and don't inflate severity. A short, accurate report beats an exhaustive alarmist one.

## Output — `TECH_DEBT_ASSESSMENT.md`

Structure the report as:

1. **Executive summary** — overall health in a few sentences, the top 3–5 risks, and the headline metrics (size, coverage, dependency/vulnerability counts, hotspot count).
2. **Codebase overview** — size, languages, structure, and what the Phase-2 tooling revealed.
3. **Prioritized findings** — the ranked "fix these first" list, each with severity, effort, priority, location/evidence, the concrete problem, and a recommended remediation. Quick wins called out separately.
4. **Detailed inventory by dimension** — findings grouped under the 14 dimensions above, each with location and evidence.
5. **Remediation roadmap** — a phased plan: quick wins first, then strategic initiatives, sequenced by dependency and leverage.
6. **Coverage & limitations** — what you assessed, what you couldn't (tools missing, areas not reachable), and your confidence level per dimension.

For every individual finding, always give: the **location** (file and, where relevant, line/function), the **problem** stated specifically and concretely, and the **recommended remediation** with a concrete action. Never write vague advice like "improve error handling" — say exactly what is wrong, where, and what to do about it.
