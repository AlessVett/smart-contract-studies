# Security Policy

## Supported Versions

This repository contains educational smart contract analyses. While the repository itself doesn't contain active smart contracts, we take security seriously for all contributions and analyses.

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

## Reporting a Vulnerability

We appreciate your efforts to responsibly disclose your findings and will make every effort to acknowledge your contributions.

### For Repository Security Issues

If you discover a security vulnerability in this repository (website, documentation, or analysis tools):

1. **DO NOT** open a public issue
2. Email us at: alessandro.vettor@egloo.it
3. Include the following information:
   - Type of issue (e.g., XSS, SQL injection, authentication bypass)
   - Full paths of source file(s) related to the manifestation of the issue
   - The location of the affected source code (tag/branch/commit or direct URL)
   - Any special configuration required to reproduce the issue
   - Step-by-step instructions to reproduce the issue
   - Proof-of-concept or exploit code (if possible)
   - Impact of the issue

### For Smart Contract Analysis Issues

If you find errors, omissions, or security issues in our smart contract analyses:

1. You may open a public issue if the vulnerability is already publicly known
2. For new vulnerabilities found in analyzed contracts:
   - Follow responsible disclosure practices
   - Contact the original contract owners/developers first
   - After appropriate disclosure period, submit a PR to update our analysis

### Response Timeline

- **Initial Response**: Within 48 hours
- **Issue Triage**: Within 1 week
- **Resolution**: Depends on severity and complexity

### What to Expect

1. **Acknowledgment**: We'll acknowledge receipt of your vulnerability report
2. **Communication**: We'll keep you informed about the progress
3. **Credit**: With your permission, we'll credit you for the discovery
4. **Disclosure**: We'll work with you to understand the issue and develop a fix

## Security Best Practices for Contributors

When contributing smart contract analyses:

1. **Never include private keys or sensitive data**
2. **Verify contract addresses before publishing**
3. **Double-check vulnerability assessments**
4. **Include disclaimers about audit limitations**
5. **Reference official audit reports when available**

## Disclaimer

The analyses in this repository are for educational purposes only. They should not be considered as formal security audits. Always conduct your own research and hire professional auditors before interacting with smart contracts.

## Contact

- Security Email: alessandro.vettor@egloo.it
- PGP Key: [Available upon request]

Thank you for helping keep our community safe!