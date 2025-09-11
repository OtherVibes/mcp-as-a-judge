# Task Size Classifications

**XS (Extra Small)**: Simple fixes, typos, minor config changes (< 30 minutes)
- Examples: Fix typo, update version number, small documentation fix
- Workflow: Skip planning → CREATED → IMPLEMENTING → REVIEW_READY → TESTING → COMPLETED

**S (Small)**: Minor features, simple refactoring (30 minutes - 2 hours)  
- Examples: Add simple validation, minor UI change, basic function addition
- Workflow: Skip planning → CREATED → IMPLEMENTING → REVIEW_READY → TESTING → COMPLETED

**M (Medium)**: Standard features, moderate complexity (2-8 hours) - DEFAULT
- Examples: New API endpoint, database schema change, component refactor
- Workflow: Full workflow → CREATED → PLANNING → PLAN_APPROVED → IMPLEMENTING → REVIEW_READY → TESTING → COMPLETED

**L (Large)**: Complex features, multiple components (1-3 days)
- Examples: Authentication system, payment integration, major feature
- Workflow: Full workflow → CREATED → PLANNING → PLAN_APPROVED → IMPLEMENTING → REVIEW_READY → TESTING → COMPLETED

**XL (Extra Large)**: Major system changes, architectural updates (3+ days)
- Examples: Database migration, architecture overhaul, major system redesign
- Workflow: Full workflow → CREATED → PLANNING → PLAN_APPROVED → IMPLEMENTING → REVIEW_READY → TESTING → COMPLETED

## Size-Based Workflow Routing

- **XS/S Tasks**: Skip planning phase, minimal validation, but still require code review, testing, and completion
- **M/L/XL Tasks**: Full workflow with comprehensive planning, validation, and testing
