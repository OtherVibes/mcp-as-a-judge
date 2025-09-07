## [1.0.0](https://github.com/OtherVibes/mcp-as-a-judge/compare/v0.1.8...v1.0.0) (2025-08-30)

### ⚠ BREAKING CHANGES

* judge_coding_plan now requires research_urls parameter

Benefits:
- ✅ Forces AI assistants to do actual online research
- ✅ Validates research quality through URL evidence
- ✅ Ensures investigation of existing solutions and best practices
- ✅ Improves implementation approach validation
- ✅ All tests updated and passing (41/41)

* feat: mandate online research with URL validation and backward compatibility

- Make online research MANDATORY in docstring and prompts
- AI assistants MUST perform online research and provide URLs
- research_urls parameter optional for backward compatibility but strongly enforced
- Enhanced prompts to REJECT submissions without research URLs
- Clear instruction that online research is not optional
- URLs should be comma-separated list demonstrating actual research
- Prioritize existing solutions: current repo > well-known libraries > in-house

Key changes:
- ✅ MANDATORY online research requirement in all documentation
- ✅ Backward compatible research_urls parameter (optional with empty default)
- ✅ Enhanced validation to reject missing URLs as research failure
- ✅ Clear guidance that online research is required, not optional
- ✅ Instructs AI to actually DO research, not just ask for URLs
- ✅ All tests passing (41/41)

Fixes validation error while maintaining mandatory research requirement.

* feat: enforce mandatory online research with List[str] URLs and collaborative workflow

- Add mandatory minimum 3 URLs validation for research_urls parameter
- Change research_urls from str to List[str] for proper URL handling
- Add validation that rejects submissions with insufficient research URLs
- Update docstring to emphasize collaborative workflow with user
- Clarify that AI must 'collaborate with the user' and 'perform ONLINE research'
- Restructure workflow order: requirements → online research → repo analysis → design → plan
- Enhanced prompts to properly format URL lists with Jinja templating
- All tests updated to provide minimum 3 URLs and use List[str] format

Breaking changes:
- research_urls parameter now requires List[str] instead of str
- Minimum 3 URLs required (validates and rejects if insufficient)
- Function signature maintains backward compatibility with None default

Benefits:
- ✅ Forces actual online research with evidence (minimum 3 URLs)
- ✅ Prevents AI from working unilaterally - requires collaboration
- ✅ Proper data structure for URL handling (List[str])
- ✅ Clear workflow prioritizing existing solutions over custom development
- ✅ All tests passing with proper URL validation (41/41)

### 🚀 Features

* add CODEOWNERS file to require approval from [@OtherVibes](https://github.com/OtherVibes) ([1bd5b29](https://github.com/OtherVibes/mcp-as-a-judge/commit/1bd5b2961b99519fe9b819363fb56902b21dbb1e))
* configure semantic release with GitHub App token for branch protection bypass ([315cb37](https://github.com/OtherVibes/mcp-as-a-judge/commit/315cb379fb1b50c0e241c5573322a3ead6e0b41a))
* enforce mandatory online research with List[str] URLs and collaborative workflow ([#11](https://github.com/OtherVibes/mcp-as-a-judge/issues/11)) ([3b76dc0](https://github.com/OtherVibes/mcp-as-a-judge/commit/3b76dc0bda287acfbc51ab5aef1586e85eb34b1a))
* separate user and system messages with type-safe Pydantic models ([3f0a688](https://github.com/OtherVibes/mcp-as-a-judge/commit/3f0a688b9c7839efa8302dd54ab13be497f489e2))

### 🐛 Bug Fixes

* correct version to 0.1.9 ([4072bdb](https://github.com/OtherVibes/mcp-as-a-judge/commit/4072bdbfeda715c7affa19613cbed48ff560d402))
* move prompts into package for reliable installation ([3d2fde6](https://github.com/OtherVibes/mcp-as-a-judge/commit/3d2fde6143edb3c0598788e5b370fa30dc6163af))
* resolve prompts directory not found in installed package ([d8f7964](https://github.com/OtherVibes/mcp-as-a-judge/commit/d8f7964f85582fdfe118e70860cee7f988f3d563))

### ♻️ Code Refactoring

* use importlib.resources for prompt loading (standard Python approach) ([f106137](https://github.com/OtherVibes/mcp-as-a-judge/commit/f106137bb69324c6cae9284193a48f734cb8851c))

## [0.1.8](https://github.com/OtherVibes/mcp-as-a-judge/compare/v0.1.7...v0.1.8) (2025-08-30)

### 🐛 Bug Fixes

* use shell environment variable syntax for PYPI_TOKEN ([1452d4e](https://github.com/OtherVibes/mcp-as-a-judge/commit/1452d4e712b62f6c6af412cfa77116bca46a6bb7))

## [0.1.7](https://github.com/OtherVibes/mcp-as-a-judge/compare/v0.1.6...v0.1.7) (2025-08-30)

### 🐛 Bug Fixes

* correct PYPI token environment variable name ([3112ee4](https://github.com/OtherVibes/mcp-as-a-judge/commit/3112ee4ebbca75510a9e2069fe49a84272dbb382))
* use correct PYPI_TOKEN environment variable ([d45a096](https://github.com/OtherVibes/mcp-as-a-judge/commit/d45a096773c28a9edc1e5e393d95c14687de467a))

## [0.1.6](https://github.com/OtherVibes/mcp-as-a-judge/compare/v0.1.5...v0.1.6) (2025-08-30)

### 🐛 Bug Fixes

* add PyPI publication to semantic-release ([bf47cdf](https://github.com/OtherVibes/mcp-as-a-judge/commit/bf47cdf66b177839f3b1bb0137b6b4a0973e98e7))

## [0.1.5](https://github.com/OtherVibes/mcp-as-a-judge/compare/v0.1.4...v0.1.5) (2025-08-30)

### 🐛 Bug Fixes

* test conventional commit format ([e19e40e](https://github.com/OtherVibes/mcp-as-a-judge/commit/e19e40ede5b848f939a41391d06b54fcdeb680b1))

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial release infrastructure with CI/CD pipelines
- Comprehensive GitHub Actions workflows for testing, building, and releasing
- Semantic versioning with automated releases
- Docker image publishing to GitHub Container Registry
- PyPI package publishing automation
- Pre-commit hooks for code quality
- Dependabot configuration for automated dependency updates

### Changed

- Updated project configuration for better packaging and CI/CD integration
- Modernized tooling configuration (ruff, mypy, pytest)

### Fixed

- N/A

### Removed

- N/A

## [0.1.0] - TBD

### Added

- Initial release of MCP as a Judge
- Core MCP server functionality
- AI-powered code evaluation tools
- User-driven decision making system
- Comprehensive test suite
- Docker support
- Documentation and examples
