# Generic Agent Adapter

A compatible agent must be able to read `SKILL.md`, run Python 3.9+, and access the project filesystem. It should use the bundled CLI for deterministic metadata, validation, staleness, and migration, while using the conversation and repository evidence to fill prose sections.

The agent must not rename protocol section headings, fabricate evidence, expose secrets, or update `HANDOFF.md` after failed validation.
