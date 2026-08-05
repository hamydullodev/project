## What does this PR do?

<!-- One or two sentences. -->

## Related issue

Closes #

## Checklist

- [ ] Tests added/updated for the change (`pytest -q` passes)
- [ ] `ruff check` and `ruff format --check` pass
- [ ] No cloud LLM calls introduced in `app/agent` or `app/tools`
- [ ] If a tool can source facts from the web, it's registered so sources
      get attached (`app/agent/nodes.py::_WEB_SOURCED_TOOLS`)
- [ ] Docs updated if this changes setup, env vars, or the tool API
      (`README.md`, `docs/TOOLS.md`)

## Screenshots (UI changes only)

<!-- Before/after if this touches app/ui. -->
