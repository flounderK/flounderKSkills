# Architecture

How this repo is put together: one canonical prompt per skill, an installer that adapts
it to each AI tool, and an eval harness that lets you tell whether a prompt change
actually helped. The diagrams below render on GitHub (Mermaid) and in most Markdown
viewers.

- [System overview](#system-overview)
- [Directory layout](#directory-layout)
- [Authoring model: one source, many interfaces](#authoring-model-one-source-many-interfaces)
- [The install pipeline](#the-install-pipeline)
- [Prompt logic](#prompt-logic)
  - [post-change-validation](#post-change-validation)
  - [tech-debt-assessment](#tech-debt-assessment)
- [Eval harness](#eval-harness)
- [The improvement workflow](#the-improvement-workflow)

---

## System overview

Two halves. The **prompt side** turns one source file into installable artifacts for
each tool. The **eval side** measures a prompt's quality so changes are driven by
evidence, not vibes.

```mermaid
flowchart TD
    subgraph authoring["Prompt side"]
        SRC["prompts/NAME/prompt.md + meta.yaml<br/>(single source of truth)"]
        INS["install.sh"]
        SRC --> INS
        INS --> CLAUDE["Claude Code<br/>command + subagent"]
        INS --> KIRO["Kiro CLI<br/>agent JSON"]
        INS --> GEN["Generic<br/>raw prompt"]
    end

    subgraph evaluation["Eval side"]
        CASES["evals/cases<br/>(diffs + ground truth)"]
        RUN["run"]
        SCORE["score / compare"]
        CASES --> RUN --> SCORE
        SCORE --> METRICS["recall, false-positive rate,<br/>A/B winner"]
    end

    SRC -. graded by .-> RUN
    METRICS -. informs edits to .-> SRC
```

The dotted edges are the point: the eval side reads the same `prompt.md` the install
side ships, and its metrics feed back into editing that file. Single source of truth
throughout.

---

## Directory layout

```
prompts/
  post-change-validation/
    prompt.md            # canonical, interface-agnostic prompt body
    meta.yaml            # name / title / description / model
  tech-debt-assessment/
    prompt.md
    meta.yaml
install.sh               # wraps each prompt into per-interface artifacts
docs/
  ARCHITECTURE.md        # this file
evals/
  cases/<id>/            # case.yaml (ground truth) + diff.patch (the change)
  harness/               # config, llm, dataset, run, score, compare, harvest
  cli.py                 # python -m evals.cli <command>
  runs/                  # run outputs (gitignored)
```

---

## Authoring model: one source, many interfaces

Every prompt is written once as `prompt.md` (imperative voice, so it reads correctly as
both an on-demand command and an agent system prompt) plus a flat `meta.yaml`.
`install.sh` is the only thing that knows each tool's wrapper format and install path.

```mermaid
flowchart LR
    P["prompts/NAME/prompt.md<br/>canonical body"] --> INS["install.sh"]
    M["prompts/NAME/meta.yaml<br/>metadata"] --> INS
    INS -->|slash command| CC["~/.claude/commands/NAME.md"]
    INS -->|subagent| CA["~/.claude/agents/NAME.md"]
    INS -->|custom agent JSON| KI["~/.kiro/agents/NAME.json"]
    INS -->|raw prompt| GEN["~/.ai-prompts/NAME.md"]
```

Because the body is never duplicated by hand, updating a prompt everywhere is
`git pull && ./install.sh` — the installer overwrites the generated copies idempotently.

| Target | Global path | Becomes |
|--------|-------------|---------|
| `claude` | `~/.claude/commands/NAME.md` | slash command `/NAME` |
| `claude` | `~/.claude/agents/NAME.md` | subagent |
| `kiro` | `~/.kiro/agents/NAME.json` | custom agent |
| `generic` | `~/.ai-prompts/NAME.md` | raw portable prompt |

With `--scope project` the same files land under `./.claude`, `./.kiro`, and
`./.ai-prompts` in the current directory instead of `$HOME`.

---

## The install pipeline

`install.sh` discovers every `prompts/*/` directory, so new prompts install with no code
change. Only the Kiro target needs a tool (`jq` or `python3`) to JSON-encode the prompt
body safely; the Claude and generic targets are pure shell.

```mermaid
flowchart TD
    START["install.sh --target --scope --only --dry-run"] --> LOOP{"for each<br/>prompts/*/"}
    LOOP --> READ["read prompt.md + meta.yaml<br/>(name, description, model)"]

    READ --> WC{"target includes claude?"}
    WC -->|yes| CMD["write commands/NAME.md<br/>(description frontmatter + body)"]
    WC -->|yes| AGT["write agents/NAME.md<br/>(name/description/model + body)"]

    READ --> WK{"target includes kiro?"}
    WK -->|yes| HAS{"jq or python3?"}
    HAS -->|yes| KJSON["write agents/NAME.json<br/>(body JSON-encoded + resources)"]
    HAS -->|no| WARN["skip Kiro, print warning"]

    READ --> WG{"target includes generic?"}
    WG -->|yes| RAW["copy body to ai-prompts/NAME.md"]

    CMD --> LOOP
    AGT --> LOOP
    KJSON --> LOOP
    WARN --> LOOP
    RAW --> LOOP
```

The Claude/generic writers stream the body verbatim (`cat`), so `$` and backticks in a
prompt can't be mangled by shell expansion. The Kiro writer uses `jq --rawfile` (or a
`python3 json.dumps` fallback) so the body is correctly escaped inside JSON.

---

## Prompt logic

### post-change-validation

A soft code-review to run **after** a change. It scopes to the changed files, reviews
them across 14 dimensions, then runs the project's tests and linters — and it isn't
"done" until those pass and every issue is addressed or precisely flagged.

```mermaid
flowchart TD
    C["Code changed (LLM or human)"] --> D["Determine changed files<br/>git diff / status / untracked"]
    D --> R["Review every changed file<br/>across 14 dimensions:<br/>correctness, robustness, completeness,<br/>duplication, testability, abstraction,<br/>placement, performance, docs, deps,<br/>steering, hacks, readability, idioms"]
    R --> AC["Active checks (must run, not just read)"]
    AC --> T["Run the test suite"]
    AC --> L["Run linters / static analysis"]
    R --> G{"All tests pass, analysis clean,<br/>every issue addressed?"}
    T --> G
    L --> G
    G -->|no| FIX["Fix root cause<br/>write missing tests"]
    FIX --> AC
    G -->|yes| O["Output: per issue<br/>location, problem, fix<br/>+ overall verdict"]
```

### tech-debt-assessment

A whole-codebase audit that **reports only** — it never edits code. Three phases feed a
severity/effort scoring model, which feeds a prioritized report.

```mermaid
flowchart LR
    P1["Phase 1<br/>Map the codebase<br/>size, structure, entry points,<br/>build/test/CI, intent"]
    P2["Phase 2<br/>Gather evidence with tooling<br/>churn, complexity, duplication,<br/>dependency/vuln audits, coverage"]
    P3["Phase 3<br/>Assess 15 dimensions<br/>architecture ... TODO markers"]
    SC["Score each finding<br/>severity + effort -&gt; priority<br/>anchored to churn x complexity"]
    RPT["TECH_DEBT_ASSESSMENT.md<br/>exec summary, inventory,<br/>prioritized findings, roadmap,<br/>coverage and limitations"]
    P1 --> P2 --> P3 --> SC --> RPT
```

The two prompts are deliberate opposites: post-change-validation is **narrow + fix-in-place**;
tech-debt-assessment is **whole-repo + read-only report**.

---

## Eval harness

The harness answers one question: *did a prompt edit actually make the review better?*
It runs a prompt over labeled cases (single-shot — the model sees a diff and returns
JSON findings), then an LLM judge grades the output against ground truth.

```mermaid
flowchart TD
    REPO["a git repo the prompt<br/>has run on"] -->|harvest| CASES

    subgraph CASES["evals/cases/ID/"]
        CY["case.yaml<br/>should_flag + expected_findings"]
        DP["diff.patch"]
    end

    PROMPT["prompts/NAME/prompt.md"] --> RUN["cli run RUNID"]
    CASES --> RUN
    RUN -->|runner model| A1["Anthropic API"]
    A1 --> RUNS["evals/runs/RUNID/*.json<br/>findings per case"]

    RUNS --> SCORE["cli score RUNID"]
    CASES --> SCORE
    SCORE -->|judge model| A2["Anthropic API"]
    A2 --> MET["bug-catch recall<br/>false-positive rate"]

    RUNS --> CMP["cli compare A B"]
    RUNS2["a second run"] --> CMP
    CMP -->|judge, positions swapped| A3["Anthropic API"]
    A3 --> WIN["per-case winner + tally"]
```

A single `run` then `score`, as a sequence:

```mermaid
sequenceDiagram
    actor U as You
    participant CLI as evals.cli
    participant R as runner
    participant API as Anthropic
    participant J as judge

    U->>CLI: run baseline
    CLI->>R: load cases + prompt body
    loop each case
        R->>API: system = prompt + diff, schema = findings
        API-->>R: findings JSON
        R->>R: write runs/baseline/CASE.json
    end
    R-->>U: N findings per case

    U->>CLI: score baseline
    CLI->>J: diff + expected findings + review findings
    J->>API: grade coverage (per case)
    API-->>J: covered indexes, false-positive flag
    J-->>U: recall + false-positive rate
```

**Honest scope:** the runner is a single-shot *proxy*. The production prompt runs as a
tool-using agent (reads the repo, runs tests, edits files); the harness exercises only
the review *reasoning*, which is what prompt-tuning targets. A prompt that scores well
here still needs end-to-end testing in a real harness. See [`../evals/README.md`](../evals/README.md).

---

## The improvement workflow

The metric is the bottleneck, not the optimizer. Build a benchmark you trust, tune by
hand while there are obvious gains, and only reach for an automated optimizer (e.g.
DSPy/GEPA) once hand-tuning stalls — scoped to a narrow sub-skill where the ground truth
is clean.

```mermaid
flowchart TD
    H["Harvest real diffs<br/>cli harvest REPO"] --> LBL["Hand-label<br/>should_flag + expected_findings"]
    LBL --> BENCH["Trusted benchmark"]
    BENCH --> RUN["cli run"]
    RUN --> EVAL["cli score / compare"]
    EVAL --> Q{"obvious gains<br/>left by hand?"}
    Q -->|yes| EDIT["edit prompts/NAME/prompt.md"]
    EDIT --> RUN
    Q -->|no| OPT["scope an optimizer to a<br/>leaf sub-skill (e.g. GEPA)"]
    OPT --> RUN
```

The labeling step is where the value is: those labels are the ground truth every later
measurement trusts. Everything upstream (harvesting, running, judging) is mechanical;
the human judgment about what a good review *should* catch is what makes the numbers
mean something.
