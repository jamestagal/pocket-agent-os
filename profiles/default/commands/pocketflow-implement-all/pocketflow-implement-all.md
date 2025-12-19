# PocketFlow Automated Implementation

Implement all task groups from a spec by delegating to specialist subagents based on domain headers.

## EXECUTION PROCESS

Execute these steps IN SEQUENCE:

### STEP 1: Load Tasks and Identify Task Groups

Read `agent-os/specs/$ARGUMENTS/tasks.md`

Identify each task group by finding lines starting with `### ` (h3 headers). 
Each `### ` header marks a new task group that continues until the next `### ` header.

Extract:
- The header text (e.g., "Database Layer", "API Layer", "Frontend Components")
- All content under that header until the next `### ` header (tasks, subtasks, acceptance criteria)

### STEP 2: Map Headers to Specialists

Use this routing table to determine which specialist handles each task group:

| If header contains... | Delegate to... |
|----------------------|----------------|
| "Database" | **database-specialist** |
| "API" | **api-specialist** |
| "Frontend" | **frontend-specialist** |
| "UI" | **frontend-specialist** |
| "Component" | **frontend-specialist** |
| "Testing" | **implementer** |
| "Integration" | **implementer** |
| (none of above) | **implementer** |

### STEP 3: Load Context Files

Read these files to include as context for each specialist:
- `agent-os/specs/$ARGUMENTS/spec.md`
- `agent-os/specs/$ARGUMENTS/planning/requirements.md` (if exists)
- `agent-os/product/mission.md`
- `agent-os/product/tech-stack.md`

### STEP 4: Delegate Each Task Group (LOOP)

For EACH task group identified in Step 1, in order:

**A) Announce the delegation:**
```
📋 Task Group: [Header]
🤖 Delegating to: [specialist-name]
```

**B) Delegate to the specialist with this instruction:**

```
Use the [specialist-name] subagent to implement this task group:

## Task Group
[The full ### header and all content under it from tasks.md]

## Specification
[Contents of spec.md]

## Requirements  
[Contents of requirements.md]

## Tech Stack Reference
[Key technologies from tech-stack.md relevant to this domain]

## Instructions
1. Implement ALL tasks listed in this task group
2. Follow existing patterns in the codebase
3. Run tests for this task group
4. Mark each completed task with [x] in agent-os/specs/$ARGUMENTS/tasks.md
```

**C) Wait for specialist to complete**

After the specialist finishes, verify that tasks in this group are marked `[x]` in tasks.md.

**D) Proceed to next task group**

Repeat steps A-C for each remaining task group.

### STEP 5: Final Verification

After ALL task groups show `[x]` for all tasks:

```
Use the implementation-verifier subagent to verify the complete implementation:

Spec path: agent-os/specs/$ARGUMENTS

Instructions:
1. Verify all functionality works end-to-end
2. Run the full test suite for this feature
3. Check for any regressions
4. Produce verification report at agent-os/specs/$ARGUMENTS/verifications/final-verification.md
```

### STEP 6: Report Completion

Output a summary:
```
✅ Implementation Complete: $ARGUMENTS

Task Groups Completed:
- [x] Database Layer (database-specialist)
- [x] API Layer (api-specialist)
- [x] Frontend Components (frontend-specialist)
- [x] Integration & Testing (implementer)

Verification: agent-os/specs/$ARGUMENTS/verifications/final-verification.md
```

## IMPORTANT NOTES

- Execute task groups SEQUENTIALLY (dependencies flow Database → API → Frontend → Testing)
- Each specialist must mark tasks `[x]` before proceeding to next group
- If a specialist encounters an error, report it and ask user whether to retry or skip
- The specialist subagents contain domain expertise for their area (database patterns, API patterns, etc.)
