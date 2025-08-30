# Setting up GitHub Secrets for CI/CD

This document guides you through setting up the necessary secrets for automated publishing and CI/CD.

## Required Secrets

### 1. PyPI API Token (`PYPI_API_TOKEN`)

**Purpose**: Allows GitHub Actions to publish packages to PyPI automatically.

**Steps**:

1. Go to [PyPI Account Settings](https://pypi.org/manage/account/)
2. Scroll down to "API tokens" section
3. Click "Add API token"
4. Set the token name (e.g., "GitHub Actions - mcp-as-a-judge")
5. Set scope to "Entire account" (or specific to your project if you prefer)
6. Click "Add token"
7. **IMPORTANT**: Copy the token immediately (it won't be shown again)

**Adding to GitHub**:

1. Go to your GitHub repository
2. Click "Settings" tab
3. Click "Secrets and variables" → "Actions"
4. Click "New repository secret"
5. Name: `PYPI_API_TOKEN`
6. Value: Paste your PyPI token (starts with `pypi-`)
7. Click "Add secret"

### 2. Codecov Token (`CODECOV_TOKEN`) - Optional

**Purpose**: Upload test coverage reports to Codecov.

**Steps**:

1. Go to [Codecov](https://codecov.io/)
2. Sign in with GitHub
3. Add your repository
4. Copy the repository token
5. Add as GitHub secret with name `CODECOV_TOKEN`

## Using GitHub CLI (Alternative Method)

If you have `gh` CLI installed, you can add secrets from command line:

```bash
# Add PyPI token
gh secret set PYPI_API_TOKEN

# Add Codecov token (optional)
gh secret set CODECOV_TOKEN
```

## Verification

After adding the secrets:

1. Go to repository "Settings" → "Secrets and variables" → "Actions"
2. Verify you see:
   - ✅ `PYPI_API_TOKEN`
   - ✅ `CODECOV_TOKEN` (if added)

## Security Notes

- **Never commit secrets to your repository**
- PyPI tokens should be scoped to specific projects when possible
- Regularly rotate your API tokens
- Use environment-specific tokens for different deployment stages

## Troubleshooting

### PyPI Publishing Fails

- Verify the token is correctly set in GitHub secrets
- Ensure the token has the right permissions
- Check that the package name is available on PyPI

### Coverage Upload Fails

- Codecov token is optional - the workflow will continue without it
- Ensure the token matches your repository

## Next Steps

Once secrets are configured:

1. Push your changes to trigger CI
2. Create a release tag to trigger publishing
3. Monitor the Actions tab for workflow status
