---
name: Bug report
about: Something isn't working as expected
title: "[Bug] "
labels: bug
---

**Describe the bug**
A clear description of what went wrong.

**Where**
- [ ] Frontend (Next.js, `:3000`)
- [ ] Backend API (FastAPI, `:8000`)
- [ ] Streamlit debug tool (`:8501`)
- [ ] Retrieval / answer quality (see below)

**Steps to reproduce**
1.
2.
3.

**Expected behavior**


**Screenshots / logs**
If applicable — `logs/app.log` output is especially useful for backend
issues.

**Environment**
- OS:
- Python version:
- Node version:
- `EMBEDDING_MODEL` / `LLM_MODEL` (if relevant):

---

**If this is a retrieval/answer-quality issue**, please also include:
- The exact query you asked
- Which article you expected it to find (law name + article number),
  if known — this is the fastest path to a regression test (see
  [`docs/evaluation.md`](../../docs/evaluation.md))
