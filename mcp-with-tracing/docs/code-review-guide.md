# Code Review Guide

> **Purpose**: Code review process and standards  
> **Last Updated**: 2026-04-08

---

## Review Checklist

### Functionality
- [ ] Implements intended functionality
- [ ] Edge cases handled
- [ ] Error handling comprehensive
- [ ] No breaking changes

### Code Quality
- [ ] Follows style guide (black, isort, ruff)
- [ ] Complete type annotations
- [ ] All functions have docstrings
- [ ] No code duplication

### Testing
- [ ] Unit tests cover new functionality
- [ ] Coverage meets minimum (90%+)
- [ ] All tests pass locally

### Security
- [ ] No hardcoded secrets
- [ ] Input validation implemented
- [ ] PII handling compliant

## Workflow

1. Create feature branch
2. Implement with tests
3. Run tests & linters
4. Create PR
5. CI/CD passes
6. 2+ reviewers
7. Address comments
8. Tech lead approval
9. Squash & merge

## Turnaround SLA

- Critical: 4 hours
- High: 1 day
- Medium: 2 days
- Low: 3 days

---

**See Full Documentation**: Comment format, reviewer responsibilities, automated checks, post-merge verification.
