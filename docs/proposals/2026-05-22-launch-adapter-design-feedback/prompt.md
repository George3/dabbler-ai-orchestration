# Gemini Pro design review request

Review the attached Dabbler launch-adapter design packet as a critical,
repo-specific design reviewer.

The packet includes:

- the current adapter design document: `coding-assistant-adapter-spec.md`
- the existing related implementation set: Set 036
- the newly authored session-set roadmap: Sets 037 through 043

Please evaluate the design as proposed, not some hypothetical greenfield
alternative.

## What to review

1. Is the split between Set 036 and the new launch-adapter work correct?
2. Is Set 037 the right place to reconcile Set 036 with the new adapter
   roadmap, or should that reconciliation happen differently?
3. Is the session-set DAG sensible, or is it over-split / under-split?
4. Is one discovery session per CLI/provider adapter the right pattern?
5. Is the chat-interface work correctly separated into later sets, or is
   that an architectural mistake?
6. Are there contradictions, hidden prerequisites, or ordering problems
   across the design packet?
7. What concrete edits should be made to the specs before implementation
   begins?

## Output format

Use this exact section structure:

1. `Overall verdict`
2. `What is strong`
3. `Findings` — severity-ordered, concrete, repo-specific
4. `Set 036 reconciliation`
5. `Session-set DAG and sizing`
6. `Chat interface judgement`
7. `Recommended spec edits before implementation`

When you cite a concern, name the file and session number where
possible.

Prefer criticism that changes the plan over generic praise.