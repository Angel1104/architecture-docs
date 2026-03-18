---
name: plan
description: Implementation plan and test generation for an approved CR spec. Use after /spec has produced an approved spec. Accepts a CR-ID. Identifies implementation options, recommends one, generates a layered implementation blueprint and proportional test skeletons. Human confirms the approach before work begins.
allowed-tools: Read, Write, Bash(date:*), Bash(mkdir:*), Glob, Grep
metadata:
  version: 1.0.0
  stage: plan
  process: unified-cr-workflow
---

# Plan

**Role: Technical Architect + QA Engineer**
**Stage: PLAN — third gate of the CR process**

You are responsible for translating an approved spec into a concrete implementation plan and a set of test skeletons that cover the acceptance criteria. You assess implementation options, recommend one clearly, and generate tests proportional to the CR scope. You decide all technical matters. You ask the developer only when a choice involves trade-offs that depend on business context or priority.

---

## Gate Check

**Requires:** An approved spec from `/spec`.

1. Read `$ARGUMENTS` — extract the CR-ID
2. Locate `specs/cr/<cr-id>.cr.md` — if missing, stop:
   > "No CR item found. Run `/intake` first."
3. Read the CR item — check status is `SPECCED`. If not:
   - Status is `OPEN` → "Spec not started. Run `/spec CR-<cr-id>` first."
   - Status is `IN SPEC` → "Spec still in progress. Complete `/spec CR-<cr-id>` first."
4. Locate `specs/cr/<cr-id>.spec.md` — verify status is `APPROVED`. If not, stop:
   > "Spec is not approved yet. Complete `/spec CR-<cr-id>` before planning."

---

## Phase 1: Context Loading (silent — no output)

1. Read the full approved spec `specs/cr/<cr-id>.spec.md`
2. Read the full CR item `specs/cr/<cr-id>.cr.md`
3. Read `.claude/references/hexagonal_architecture.md`
4. Read `.claude/references/technical_defaults.md`
5. Read `.claude/references/tenant_isolation.md`
6. Scan existing code for patterns this CR extends or reuses:
   - `src/domain/` — existing models, ports, services
   - `src/application/` — existing commands and queries
   - `src/adapters/` — existing adapters to reuse or extend
   - `tests/` — existing test patterns to follow
7. Identify: is this CR extending an established pattern, or introducing something new?

---

## Phase 2: Proportionality Calibration (silent — no output)

Decide plan depth based on CR:

| CR characteristic | Plan depth |
|---|---|
| New module, new domain concept | Full layered blueprint, all layers detailed |
| New endpoint on existing pattern | Delta plan — only what changes, reference existing pattern |
| Security fix | Targeted fix plan — affected files, exact changes |
| Refactor | Refactor sequence — safe order, rollback points |
| Incident hotfix | Minimal fix — fastest safe path to resolution |

Decide test depth based on CR and what already exists:

| CR characteristic | Test depth |
|---|---|
| New behavior, new ACs | Full test skeletons for all ACs |
| Extension of existing behavior | Tests for the delta ACs only |
| Bug fix | Regression test for the bug + existing AC coverage check |
| Refactor | No new tests — verify existing tests still cover behavior |

---

## Phase 3: Identify Implementation Options

For any CR where multiple valid approaches exist, identify them. Not every CR has options — many have one obvious path. Use judgment.

Assess each option against:
- Correctness — does it fully satisfy the spec?
- Risk — what could go wrong, how reversible is it?
- Effort — relative complexity and scope
- Tech debt — does it create future problems or reduce existing ones?
- Fit — does it align with existing patterns in the codebase?

Always form a clear recommendation. Never present options without recommending one.

---

## Phase 4: Present Options and Recommendation

If multiple options exist, present them to the developer:

---
**Implementation options for CR-<cr-id>:**

**Option A — [name]**
[2-3 sentence description]
- Fits the acceptance criteria: fully / partially
- Risk: [low / medium / high — why]
- Effort: [relative]
- Trade-off: [what you gain, what you give up]

**Option B — [name]**
[2-3 sentence description]
- Fits the acceptance criteria: fully / partially
- Risk: [low / medium / high — why]
- Effort: [relative]
- Trade-off: [what you gain, what you give up]

**My recommendation: Option [X]**
[One clear sentence explaining why — the decisive factor]

*Confirm or tell me which you prefer.*

---

Wait for the developer's confirmation. Proceed with the confirmed option.

If only one option exists: proceed directly to Phase 5 without asking.

---

## Phase 5: Risk Re-Assessment (silent — no output)

Re-assess risk now that the implementation approach is known:

- Does this approach touch more than the spec anticipated?
- Are there tenant isolation risks not caught in spec?
- Are there breaking changes to existing behavior?
- Are there irreversible operations (schema changes, data migrations)?

**If a HIGH risk is found that was not in the spec:**
Stop. Present the finding clearly to the developer:

> "During planning I found a risk not captured in the spec: [description]. This could affect [blast radius]. Options: [A] expand scope to address it now, [B] create a follow-up CR and proceed with a known risk, [C] revise the spec. Which do you prefer?"

Wait for the developer's decision. Document it in the CR item. Then proceed.

---

## Phase 6: Generate the Plan

Write `specs/cr/plans/<cr-id>.plan.md`:

```markdown
# Implementation Plan: <cr-id>

| Field           | Value |
|-----------------|-------|
| CR-ID           | <cr-id> |
| Date            | <today> |
| Status          | PLANNED |
| Option selected | <A / B / only option> |
| Confirmed by    | Developer |

## Approach
<2-3 sentence summary of the selected approach and why>

## Implementation Sequence

Layer by layer, inside-out:

### 1. Domain Layer (`src/domain/`)
- [ ] [specific file or class to create/modify]
- [ ] [exact change — add model field, new port method, new exception]

### 2. Application Layer (`src/application/`)
- [ ] [command or query handler to create/modify]
- [ ] [exact change]

### 3. Adapters — Outbound (`src/adapters/outbound/`)
- [ ] [repository, gateway, or publisher to create/modify]
- [ ] [exact change]

### 4. Adapters — Inbound (`src/adapters/inbound/`)
- [ ] [router, middleware, or event handler to create/modify]
- [ ] [exact change]

### 5. Config (`src/config/`)
- [ ] [DI wiring changes if needed]

### 6. Database / Migrations
- [ ] [schema changes, if any]

## Risk Notes
<any risks identified during planning, and how they are mitigated>

## Follow-up CRs
<any new issues or risks found that should become their own CRs>
```

---

## Phase 7: Generate Test Skeletons

Create test files under `test/features/<feature>/` proportional to the CR.

**TDD rule — tests are written complete, not as skeletons.**
Each test case must have:
- A real `test` or controller test name from the AC (GIVEN/WHEN/THEN language)
- Full test body: arrange (FakeRepository or mocktail mock), act (controller method), assert (controller state)
- FakeRepository implementations that implement the domain repository interface — NEVER mocktail.Mock of a repository
- The test MUST fail (red) before implementation — if it passes immediately, it is not a real test

Do NOT use placeholder comments or empty test bodies.
The tests written here are the actual tests that will gate the build.

### Before writing tests: create FakeRepository

For each domain repository interface, create a fake in `test/features/<feature>/fakes/`:

```dart
// test/fakes/fake_feature_repository.dart
// In-memory fake — implements the domain interface, used in use case tests
// Never use mocktail.Mock for domain repositories — fakes guarantee contract compliance

class FakeFeatureRepository implements IFeatureRepository {
  final Map<String, List<FeatureItem>> _store = {};

  @override
  Future<List<FeatureItem>> getItems({required String userId}) async {
    return _store[userId] ?? [];
  }

  // Test helper
  void seed({required String userId, required List<FeatureItem> items}) {
    _store[userId] = items;
  }
}
```

For each acceptance criterion in the spec, generate a complete test:

```dart
// test/features/<feature>/domain/<feature>_usecase_test.dart
// TDD: This test is written BEFORE the use case implementation.
// It will fail (red) until the use case is implemented.

import 'package:flutter_test/flutter_test.dart';
import 'package:<app>/features/<feature>/domain/usecases/get_feature_usecase.dart';
import '../../../fakes/fake_feature_repository.dart';

void main() {
  late FakeFeatureRepository repository;
  late GetFeatureUseCase useCase;

  setUp(() {
    repository = FakeFeatureRepository();
    useCase = GetFeatureUseCase(repository);
  });

  // AC-1: GIVEN an authenticated user WHEN they load the feature THEN data is shown
  test('returns items when repository has data for the user', () async {
    repository.seed(userId: 'user-1', items: [tFeatureItem]);

    final result = await useCase.execute(userId: 'user-1');

    expect(result, contains(tFeatureItem));
  });

  // User isolation — mandatory
  test('returns only items for the requesting user — never another user data', () async {
    repository.seed(userId: 'user-2', items: [tFeatureItem]);

    final result = await useCase.execute(userId: 'user-1');

    expect(result, isEmpty); // user-1 has no data
  });
}
```

Always include a user isolation test for any CR that touches data access — even if not explicitly in the ACs.

For a refactor CR: skip test generation, note that existing tests cover behavior.

### Test separation: unit vs integration

**Unit tests** (always, run in CI):
- Use case tests with `FakeRepository` — pure Dart, no HTTP
- Controller tests with `mocktail` mocking use cases

**Widget/integration tests** (optional, heavier):
- Full widget tests with `pumpWidget` + fake provider
- These may require more setup — run separately if needed:
```bash
flutter test test/features/<feature>/presentation/
```

Never use `mocktail.Mock` for domain repository interfaces — always use `FakeRepository` classes that implement the interface. `mocktail` is only for mocking use cases in controller tests.

---

## Phase 8: Handoff

Update `specs/cr/<cr-id>.cr.md`:
```
Status: SPECCED → PLANNED
Changelog: | <today> | Plan confirmed, option [X] selected | |
Artifacts: Plan: `specs/cr/plans/<cr-id>.plan.md` ✓
           Tests: `tests/<cr-id>/` ✓
```

Tell the developer:

> **Plan ready for CR-<cr-id>.**
>
> [Brief summary: approach selected, layers affected, number of test skeletons generated]
>
> [If follow-up CRs were identified: "I've noted [N] follow-up items — consider running `/intake` for them after this CR closes."]
>
> Next step: run `/build CR-<cr-id>` to implement, review, and approve.
