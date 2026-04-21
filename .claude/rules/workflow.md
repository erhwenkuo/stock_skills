# Development Workflow Rules

> For coding conventions, dependencies, and test infrastructure, see [development.md](development.md).

## Principles

- All development work is done **on a Worktree** (direct editing of the main branch is prohibited)
- Each issue progresses through 5 phases: **Design → Implementation → Unit Test → Code Review → Integration Test**
- Integration tests are run in parallel using **Teams (agent teams)**

## 1. Create Worktree

```bash
# For Linear issue KIK-NNN
git worktree add -b feature/kik-{NNN}-{short-desc} ~/stock-skills-kik{NNN} main
```

- Working directory: `~/stock-skills-kik{NNN}`
- Branch name: `feature/kik-{NNN}-{short-desc}`
- All subsequent work (implementation, tests, integration tests) is done in this worktree

### Worktree Setup (gitignore-excluded files)

When using portfolio commands in integration tests, copy gitignore-excluded data:

```bash
mkdir -p ~/stock-skills-kik{NNN}/.claude/skills/stock-portfolio/data
cp ~/stock-skills/.claude/skills/stock-portfolio/data/portfolio.csv \
   ~/stock-skills-kik{NNN}/.claude/skills/stock-portfolio/data/
```

## 2. Design Phase

- Use `EnterPlanMode` to investigate the codebase and formulate an implementation plan
- Clearly define the scope of impact, files to change, and testing approach
- Proceed to implementation only after user approval

## 3. Implementation Phase

- Make code changes on the Worktree
- The PostToolUse hook automatically runs `pytest tests/ -q` when `.py` files are edited
- Maintain all tests PASS while implementing

## 4. Unit Tests

- Create corresponding test files for new modules
- Confirm all tests PASS with `python3 -m pytest tests/ -q`
- Run on Worktree: `cd ~/stock-skills-kik{NNN} && python3 -m pytest tests/ -q`

## 5. Code Review (Teams)

After unit tests PASS, **form a review team to verify changes from multiple angles**.

### Team Composition

| Reviewer | Perspective | Check Items |
|-------------|------|-------------|
| arch-reviewer | Design & structure | Module separation, responsibility isolation, consistency with existing patterns, absence of circular dependencies |
| logic-reviewer | Logic & accuracy | Correctness of calculation logic, edge cases, error handling, missing anomaly guards |
| test-reviewer | Test quality | Test coverage, boundary value tests, appropriateness of mocks, test independence |

### Procedure

1. Create team with `TeamCreate` (e.g., `kik{NNN}-code-review`)
2. Create tasks for each reviewer with `TaskCreate` (specify target files and change diffs)
3. Launch 3 reviewers in parallel with `Task` (`subagent_type=Explore`, explicitly state Worktree path)
4. Collect feedback from each reviewer
5. If issues found, fix → re-run unit tests → re-review (as needed)
6. Proceed to integration tests when all reviewers give LGTM
7. Shut down and delete the team

### How to Pass Review Context

Provide reviewers with the following information:

- Worktree path: `~/stock-skills-kik{NNN}`
- Changed file list: result of `git diff --name-only main`
- Change diff: summary of `git diff main`
- Design intent: summary of the approach decided in the design phase

### Reviewer Selection Based on Scope

For small changes (1-2 files, no logic changes), logic-reviewer alone is sufficient.
All reviewers are required for new module additions or large-scale refactoring.

## 6. Integration Tests (Teams)

After implementation is complete, **form an agent team to verify each skill's behavior**.

### Team Composition (Standard)

| Tester | Responsibility | Verification Content |
|-----------|------|---------|
| screener-tester | Screening | Run `run_screen.py` with multiple presets and regions |
| report-tester | Report + Watchlist | CRUD for `generate_report.py` + `manage_watchlist.py` |
| portfolio-tester | Portfolio | All subcommands of `run_portfolio.py` (list/snapshot/analyze/health/forecast) |
| stress-tester | Stress test | Run `run_stress_test.py` with multiple scenarios |

### Procedure

1. Create team with `TeamCreate` (e.g., `kik{NNN}-integration-test`)
2. Create tasks for each tester with `TaskCreate`
3. Launch 4 testers in parallel with `Task` (specify `team_name`, explicitly state Worktree path)
4. Confirm all testers PASS
5. Shut down and delete the team

### Script Execution Paths for Integration Tests

Since tests run on Worktree, explicitly specify paths:

```bash
cd ~/stock-skills-kik{NNN}
python3 .claude/skills/screen-stocks/scripts/run_screen.py --region japan --preset value --top 5
python3 .claude/skills/stock-report/scripts/generate_report.py 7203.T
python3 .claude/skills/watchlist/scripts/manage_watchlist.py list
python3 .claude/skills/stock-portfolio/scripts/run_portfolio.py snapshot
python3 .claude/skills/stress-test/scripts/run_stress_test.py --portfolio 7203.T,AAPL
```

### Tester Selection Based on Scope

When changes are limited to a specific skill, only the relevant tester is needed for integration tests.
However, changes to core modules (`src/core/`) require all testers.

## 7. Documentation & Rule Updates

**After feature implementation and before merging, always verify and update the following.**

### Auto-Generated Documentation (KIK-525)

The following are auto-generated by `scripts/generate_docs.py all` and do not need manual updates:

| Target | Auto-Generated Content |
|:---|:---|
| `docs/api-reference.md` | Signatures of public functions and classes in src/ |
| `CLAUDE.md` Architecture | Layer overview (module list + KIK annotations) |
| `development.md` test count | Update `approximately NNN tests` count |
| `docs/skill-catalog.md` overview | Overview table regenerated from SKILL.md frontmatter |

The pre-commit hook runs automatically when src/ changes. To add KIK annotations to new modules, edit `config/module_annotations.yaml`.

### Manual Update Checklist

| Target | When to Update | What to Update |
|:---|:---|:---|
| `intent-routing.md` | New keywords or intents are added | Domain judgment table, add keywords |
| Relevant `SKILL.md` | A skill's functionality or output changes | description, output items, command examples |
| `rules/portfolio.md` | Portfolio-related features are added or changed | Add section, annotate KIK number |
| `rules/screening.md` | Screening-related features are added or changed | Add rules |
| `docs/data-models.md` | Fields in stock_info/stock_detail change | Update table (fixture consistency check exists) |
| `README.md` | User-facing feature descriptions are needed | Skill descriptions, usage examples |

### Decision Criteria

- **New feature addition**: Manually update intent-routing + SKILL.md + README.md (CLAUDE.md Architecture is auto-generated)
- **Improvement to existing feature**: Update only the relevant SKILL.md + rules
- **Bug fix only**: No documentation update needed (update SKILL.md if behavior changes)

## 8. Completion

```bash
# Merge to main
cd ~/stock-skills
git merge --no-ff feature/kik-{NNN}-{short-desc}
git push

# Remove Worktree
git worktree remove ~/stock-skills-kik{NNN}
git branch -d feature/kik-{NNN}-{short-desc}
```

- Update the Linear issue to Done
