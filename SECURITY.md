# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of Maestro V3 seriously. If you discover a security vulnerability, please follow these steps:

### 1. Do NOT Create a Public Issue

Please do not report security vulnerabilities through public GitHub issues.

### 2. Report Privately

Email your findings to the maintainer or use GitHub's private vulnerability reporting feature:

1. Go to the **Security** tab of this repository
2. Click **Report a vulnerability**
3. Fill in the details of the vulnerability

### 3. What to Include

When reporting a vulnerability, please include:

- **Description**: A clear description of the vulnerability
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Impact**: The potential impact of the vulnerability
- **Suggested Fix**: If you have a suggested fix, please include it

### 4. Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution Target**: Within 30 days (depending on severity)

## Security Best Practices

When using Maestro V3, please follow these security best practices:

### API Keys

- Never commit API keys to the repository
- Use environment variables for `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`
- Rotate keys regularly

### Code Execution

The `code_executor` tool runs code in a sandboxed environment with:
- 30-second timeout
- Restricted Python builtins
- No network access
- Limited file system access

### File Operations

File tools are sandboxed to allowed directories only. Never add sensitive directories to the allowed paths.

### Network Security

- The application runs on `localhost` by default
- Do not expose the API to public networks without authentication

## Security Features

Maestro V3 includes these built-in security features:

- ✅ Path sandboxing for file operations
- ✅ Sandboxed code execution
- ✅ Input validation
- ✅ CORS protection (configurable)
- ✅ No persistent storage of API keys

## Acknowledgments

We appreciate responsible disclosure and will acknowledge security researchers who report valid vulnerabilities.

---

Thank you for helping keep Maestro V3 secure!
