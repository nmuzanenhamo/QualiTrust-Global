# Contribution Guidelines

## Git Workflow

We use GitHub Flow for this project:

1. Create a feature branch from `main` (e.g., `feature/qualification-crud`)
2. Make commits following Conventional Commits format
3. Open a Pull Request to `main`
4. Request code review from at least one team member
5. Merge after approval

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `test:` - Test-related changes
- `docs:` - Documentation changes
- `ci:` - CI/CD changes
- `chore:` - Maintenance tasks
- `refactor:` - Code refactoring

Example: `feat: add qualification registration endpoint`

## Branch Naming

- Feature branches: `feature/<description>`
- Bug fix branches: `fix/<description>`
- Test branches: `test/<description>`

## Code Quality

- All PRs must pass CI checks (linting, security scan, tests)
- Test coverage must be at least 80%
- No critical security issues from Bandit scan
- Code must follow Ruff linting rules

## Code Review

- Review for correctness, security, and maintainability
- Check that tests are included for new features
- Verify that documentation is updated if needed
