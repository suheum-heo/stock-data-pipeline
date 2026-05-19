# Lessons

## 2. Always include requirements.txt for Streamlit Cloud
Streamlit Cloud doesn't use the local `.venv` — it needs a `requirements.txt` to install dependencies. Always create this before deploying.
**Root cause:** Forgot that cloud environments have no access to the local virtualenv.
**Fix:** Generate `requirements.txt` via `pip freeze | grep <deps>` as part of any deployment step.

## 1. Always push after committing
Always `git push` immediately after every commit — do not ask the user if they want to push.
This is specified in CLAUDE.md under Git Workflow.
**Root cause:** Failed to re-read CLAUDE.md before asking a redundant confirmation question.
**Fix:** Re-read CLAUDE.md at the start of each session, especially the Git Workflow section.
