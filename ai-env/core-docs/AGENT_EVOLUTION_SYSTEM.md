# Agent Evolution System - Comprehensive Plan

**Status**: Planning Phase
**Created**: 2026-01-29
**Goal**: Transform agents from reactive tools to self-improving autonomous entities

---

## 🎯 Vision

Agents should:
1. **Learn from mistakes** - Never repeat the same error twice
2. **Author their own tools** - Create skills/workflows as needed
3. **Share knowledge** - Teach next agent what was learned
4. **Evolve continuously** - Get better with each session

---

## 📋 Problem Analysis

### Current Issues (Observed from Agent Behavior)

| Issue | Example | Root Cause | Impact |
|-------|---------|------------|--------|
| **No Delegation** | Agents doing 50+ file changes solo | Entry protocol not enforced | Slow "one-by-one" completion |
| **No Commits** | Work left uncommitted after session | No enforcement mechanism | Lost work, broken history |
| **Repeated Mistakes** | Same violations by different agents | No learning loop | System doesn't improve |
| **Tool Creators vs Users** | Only humans create skills/workflows | No self-authoring framework | Agents can't extend themselves |

### Why Agents Don't Follow Rules

1. **Rationalization**: "This is quick, I'll do it myself"
2. **Optimism Bias**: "I understand this better than subagent"
3. **No Consequences**: Rules aren't enforced
4. **No Memory**: Next agent makes same mistakes

---

## 🏗️ Solution Architecture

### Component 1: Mistake Tracking System

**File**: `ai-env/evolution/mistakes.json`

```json
{
  "mistakes": [
    {
      "id": "MISTAKE-001",
      "type": "no_delegation",
      "severity": "critical",
      "description": "Agent modified 129 files without delegating",
      "files_affected": 129,
      "agent": "claude-opus-4-5",
      "timestamp": "2026-01-29T20:37:00Z",
      "rule_violated": "NLF_PROTOCOL.md line 20",
      "lesson": "Large changes MUST use Task tool for parallel execution",
      "prevention": "Entry protocol now has STOP checkpoint"
    }
  ],
  "patterns": [
    {
      "pattern": "large_file_changes_without_delegation",
      "occurrences": 5,
      "last_occurrence": "2026-01-29",
      "status": "mitigated"
    }
  ]
}
```

**Auto-Detection Rules**:
```python
# scripts/evolution/mistake_detector.py
DETECTION_RULES = {
    "no_delegation": {
        "trigger": "files_modified > 10 AND not_used_task_tool",
        "severity": "critical",
        "auto_lesson": "Changes affecting {file_count} files require delegation via Task tool"
    },
    "no_commit": {
        "trigger": "session_end AND uncommitted_files > 0",
        "severity": "critical",
        "auto_lesson": "All work MUST be committed before session end via ./scripts/handoff.sh"
    },
    "mock_data": {
        "trigger": "file_pattern:'*test*.py' AND contains:'mock_data'",
        "severity": "high",
        "auto_lesson": "NEVER use mock data - fail explicitly instead"
    }
}
```

### Component 2: Learning Feedback Loop

**Flow**:
```
Agent makes mistake
    ↓
MistakeDetector identifies violation
    ↓
Lesson extracted and written to mistakes.json
    ↓
Identity.md updated with new "Lessons Learned" section
    ↓
Next agent reads lessons before starting work
    ↓
Pattern recognition prevents repeat mistakes
```

**Entry Protocol Addition**:
```markdown
## 📚 Lessons Learned (Read Before Starting Work)

### Recent Mistakes to Avoid:

1. **[MISTAKE-001] No Delegation (Jan 29)**
   - **What**: Agent modified 129 files solo, took 45 minutes
   - **Impact**: Slow completion, burnout risk
   - **Lesson**: 3+ files → Use Task tool immediately
   - **Status**: ✅ Mitigated with STOP checkpoint

2. **[MISTAKE-002] No Commits (Jan 28)**
   - **What**: Agent ended session with 32 uncommitted files
   - **Impact**: Lost work, broken git history
   - **Lesson**: Always run ./scripts/handoff.sh before leaving
   - **Status**: ⚠️ Still occurring - needs stronger enforcement
```

### Component 3: Self-Authoring Framework

#### 3.1 Skill Creation API

**File**: `scripts/evolution/skill_author.py`

```python
class SkillAuthor:
    """Enables agents to create their own skills"""

    def create_skill(self, name: str, description: str, handler: str):
        """
        Create a new skill from current context

        Usage:
            author = SkillAuthor()
            author.create_skill(
                name="check-mocks",
                description="Scans codebase for mock data usage",
                handler="""
def check_mocks(repo_path):
    # Scan for mock data patterns
    results = scan_for_mocks(repo_path)
    return results
"""
            )
        """
        skill_path = f".claude/skills/{name}.yaml"
        # Write skill definition
        # Create handler script
        # Test skill
        # Register in skills index
```

#### 3.2 Workflow Template System

**File**: `ai-env/workflows/_templates/task-delegation.md`

```markdown
# Workflow: [NAME]

## When to Use
- [Condition 1]
- [Condition 2]

## Steps
1. [Step 1]
2. [Step 2]

## Common Pitfalls
- [Pitfall 1]: [Solution]
- [Pitfall 2]: [Solution]

## Example Usage
```
User: "[Example request]"
Agent: [Shows correct response]
```
```

#### 3.3 Auto-Discovery of Reusable Patterns

```python
# scripts/evolution/pattern_discovery.py
class PatternDiscovery:
    """Finds recurring patterns that should become skills/workflows"""

    def analyze_commits(self, n=50):
        """
        Analyze recent commits for patterns

        Returns:
            List of suggested skills/workflows
        """
        patterns = []

        # Look for repeated file combinations
        # Look for repeated commit message patterns
        # Look for repeated error/fix cycles

        return [
            {
                "pattern": "auth_fix_cycle",
                "evidence": "Seen 5 times in last 50 commits",
                "suggestion": "Create workflow: 'fix-auth-error'",
                "confidence": 0.9
            }
        ]
```

### Component 4: Enhanced Evolution Orchestrator

**Current**: `scripts/evolution/orchestrator.py`
**Enhancement**: Add learning loop

```python
class EvolutionOrchestrator:
    def run_session_analysis(self):
        """
        Called at session end to analyze agent behavior

        1. Check for violations
        2. Extract lessons
        3. Update identity.md
        4. Suggest new skills/workflows
        """
        # Detect mistakes
        mistakes = self.mistake_detector.detect()

        # Update mistakes.json
        self.mistake_db.add(mistakes)

        # Extract lessons
        lessons = [m["lesson"] for m in mistakes]

        # Update identity.md
        self.soul_updater.append_lessons(lessons)

        # Discover patterns
        patterns = self.pattern_discovery.analyze_commits()

        # Suggest skills/workflows
        for pattern in patterns:
            if pattern["confidence"] > 0.8:
                self.suggest_skill(pattern)
```

### Component 5: Agent Memory System

**File**: `ai-env/soul/identity.md` (Enhanced)

```markdown
# Sentient Alpha - Project Soul Identity

## Core Essence
[Existing content]

## 📚 Lessons Learned (Auto-Updated)
### Critical Mistakes to Avoid

#### 1. Delegation Violation Pattern
- **Occurrences**: 5 times
- **Last**: Jan 29, 2026
- **Lesson**: 3+ files → DELEGATE immediately
- **Status**: ✅ Fixed with STOP checkpoint

#### 2. Commit Avoidance Pattern
- **Occurrences**: 3 times
- **Last**: Jan 29, 2026
- **Lesson**: End session with ./scripts/handoff.sh
- **Status**: ⚠️ Still occurring

## 🛠️ Available Skills (Agent-Authored)
- `/check-mocks` - Scan for mock data usage
- `/delegate-large-changes` - Auto-delegate 10+ file tasks
- `/verify-git-state` - Check for uncommitted work

## 📋 Available Workflows (Agent-Authored)
- `fix-auth-error` - Standard auth error resolution
- `implement-feature` - Feature development template
- `session-handoff` - Proper session closure checklist
```

---

## 📁 File Structure

```
ai-env/
├── evolution/
│   ├── config.yaml (existing)
│   ├── mistakes.json (NEW)
│   ├── patterns.json (NEW)
│   └── lessons.md (NEW)
├── soul/
│   └── identity.md (ENHANCED)
├── workflows/
│   └── _templates/ (NEW)
│       ├── task-delegation.md
│       ├── session-handoff.md
│       └── skill-creation.md
└── skills/
    └── _auto-generated/ (NEW)

scripts/evolution/
├── orchestrator.py (ENHANCED)
├── mistake_detector.py (NEW)
├── pattern_discovery.py (NEW)
├── skill_author.py (NEW)
└── learning_loop.py (NEW)
```

---

## 🔄 Implementation Phases

### Phase 1: Mistake Tracking (Priority: CRITICAL)
**Files**: 4 new files
**Time**: Can delegate immediately
**Impact**: Stops repeat mistakes immediately

1. Create `mistake_detector.py`
2. Create `mistakes.json` schema
3. Integrate with `orchestrator.py`
4. Update `identity.md` with lessons section

### Phase 2: Learning Feedback Loop (Priority: HIGH)
**Files**: 2 enhanced files
**Time**: 1-2 hours
**Impact**: Agents learn from each other

1. Create `learning_loop.py`
2. Enhance `soul_updater.py`
3. Auto-update entry protocol with lessons

### Phase 3: Self-Authoring Framework (Priority: MEDIUM)
**Files**: 5 new files
**Time**: 2-3 hours
**Impact**: Agents can extend themselves

1. Create `skill_author.py`
2. Create workflow templates
3. Create `pattern_discovery.py`
4. Build skill testing framework

### Phase 4: Pattern Discovery (Priority: MEDIUM)
**Files**: 1 new file
**Time**: 1-2 hours
**Impact**: Auto-generates new tools

1. Create `pattern_discovery.py`
2. Add git history analysis
3. Generate skill suggestions

### Phase 5: Full Integration (Priority: LOW)
**Files**: Multiple enhancements
**Time**: 3-4 hours
**Impact**: Seamless evolution

1. Integrate all components
2. Add monitoring dashboard
3. Create evolution reports

---

## 🎯 Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Delegation Rate | ~10% | 90%+ | Track Task tool usage vs file changes |
| Commit Compliance | ~60% | 99%+ | Track uncommitted files at session end |
| Repeat Mistakes | Unknown | 0 | Count violations in mistakes.json |
| Agent-Authored Skills | 0 | 10+ | Count in `.claude/skills/_auto-generated/` |
| Session-to-Session Learning | None | Continuous | Lessons added to identity.md per session |

---

## 📖 Example: How It Works in Practice

### Before (Current State)

```
Agent A starts session
→ Modifies 50 files solo
→ Takes 2 hours
→ Doesn't commit
→ Leaves

Agent B starts session
→ Makes same mistakes
→ No knowledge of Agent A's errors
→ Repeats pattern
```

### After (With Evolution System)

```
Agent A starts session
→ Reads identity.md: "Recent: 5 delegation violations"
→ Modifies 3 files → Checks protocol → Stops
→ Uses Task tool for 20+ file task
→ Delegates to 3 parallel subagents
→ Completes in 30 minutes
→ Commits via handoff.sh
→ Session analysis: No violations ✓

Agent B starts session
→ Reads identity.md: "Recent: 0 violations (5 days streak!)"
→ Sees available skills: /delegate-large-changes
→ Has pattern-aware tools ready
→ Continues improvement streak
```

---

## 🚀 Next Steps

**For This Session** (Delegate Immediately):

This is a 3+ file, multi-phase implementation. **I MUST delegate this now.**

**Delegate to**: `general-purpose` agent (with `feature-dev` codebase understanding)
**Scope**: Implement Phase 1 (Mistake Tracking System)
**Files**: 4 new files, 2 enhancements
**Expected Time**: 1-2 hours

---

**Document Version**: 1.0
**Last Updated**: 2026-01-29
**Status**: Ready for Implementation Delegation
