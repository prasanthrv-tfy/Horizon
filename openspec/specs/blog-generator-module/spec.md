## ADDED Requirements

### Requirement: Generator subpackage at src/blog/generator/
All blog generation files (`runner.py`, `writer.py`, `scorer.py`, `enricher.py`, `fetcher.py`, `loader.py`, `reporter.py`, `prompts.py`) SHALL be relocated to `src/blog/generator/` as a proper Python subpackage with its own `__init__.py`.

#### Scenario: Generator files importable from new path
- **WHEN** code imports from `src.blog.generator.runner` or `src.blog.generator.writer`
- **THEN** the import SHALL succeed without error

### Requirement: Shared files remain at src/blog/ level
`models.py` and `profiles/` SHALL remain at `src/blog/` and SHALL NOT be moved into `generator/` or `publisher/`.

#### Scenario: BlogConfig importable from original path
- **WHEN** `src/models.py` imports `BlogConfig` from `src.blog.models`
- **THEN** the import SHALL succeed without modification to `src/models.py`

### Requirement: horizon-blog entry point continues to work
After the restructure, `uv run horizon-blog` SHALL function identically to before — same flags, same output, same artefact paths.

#### Scenario: horizon-blog runs successfully post-restructure
- **WHEN** `uv run horizon-blog --rank-only` is executed after the module move
- **THEN** it SHALL complete without ImportError or runtime error

### Requirement: All existing tests pass post-restructure
All tests in `tests/` that import from `src/blog/` SHALL continue to pass after the generator subpackage move, with no test file modifications required beyond import path updates.

#### Scenario: Test suite passes
- **WHEN** `uv run pytest` is executed after the restructure
- **THEN** all previously passing tests SHALL continue to pass
