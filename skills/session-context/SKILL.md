---
name: session-context
description: "Project memory notebook (.codex/session-context.md) for cross-session context continuity. Use for any project task — building features, fixing bugs, implementing changes, analyzing code, creating functionality, developing software, continuing previous work, or any development-related request. Also use when the user asks to recall, resume, remember, save, or checkpoint progress."
metadata:
---

# Session Context

Like a student's memory notebook for a project — captures what matters so no session starts from zero.

## The memory file

`.codex/session-context.md` in the project root. Format is entirely free; write whatever helps a future agent understand the project's current state. The file should naturally convey direction — where things are heading, not just where they've been.

## Lifecycle

### On session start
Read the file. If it exists and has content, briefly tell the user what the project status is: what was being done, what was learned, what's pending. If the file is missing or empty, simply begin.

### During the session
After anything meaningful happens — a decision, a discovery, a completed step, a change in direction — decide whether to update the file. Use one test:

**"If the session dies right now and this is lost, would the next session be worse off?"**

If yes, write. If no, skip.

The update does not need to follow any template. Add a note. Revise an earlier note. Replace a stale section. Whatever makes the file more useful. Prefer brevity — a few lines that capture direction and key knowledge beat paragraphs of narration.

### When the session is ending
Check: is there unfinished work or unrecorded knowledge that a future session would need? If yes, write a final note. Otherwise leave the file as-is.

## What to capture

No checklist. Trust your judgment. Things that typically matter:

- What we're building and why
- What step we're on and what comes next
- Decisions made and the reasoning behind them
- Project conventions and constraints discovered along the way
- Pitfalls, gotchas, and workarounds
- User preferences that affect how work should be done

## What to skip

- Trivial or one-off fixes
- Greetings and small talk
- Information easily reconstructed (e.g., standard library docs)
