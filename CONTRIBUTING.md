# Contributing to Smart Contract Studies

Thank you for your interest in contributing to our smart contract security analysis repository! This document provides guidelines for contributing high-quality security analyses.

## Table of Contents

- [Getting Started](#getting-started)
- [Types of Contributions](#types-of-contributions)
- [Submission Process](#submission-process)
- [Analysis Standards](#analysis-standards)
- [File Structure](#file-structure)
- [Writing Guidelines](#writing-guidelines)
- [Code of Conduct](#code-of-conduct)
- [Recognition](#recognition)

## Getting Started

1. **Fork the Repository**: Start by forking this repository to your GitHub account
2. **Clone Your Fork**: Clone your forked repository to your local machine
3. **Create a Branch**: Create a new branch for your contribution (`git checkout -b analysis/contract-name`)
4. **Make Your Changes**: Add your analysis following our guidelines
5. **Submit a Pull Request**: Push your changes and create a pull request

## Types of Contributions

We welcome the following types of contributions:

### 1. Smart Contract Security Analyses
- In-depth security reviews of deployed smart contracts
- Post-mortem analyses of hacks and exploits
- Comparative analyses of similar protocols
- Novel vulnerability pattern discoveries

### 2. Tools and Scripts
- Security analysis automation tools
- Vulnerability detection scripts
- Gas optimization analyzers
- Testing frameworks and utilities

### 3. Educational Content
- Security best practices guides
- Vulnerability pattern explanations
- Tutorial content for security researchers
- Case study compilations

### 4. Improvements
- Fixing errors in existing analyses
- Updating analyses with new findings
- Improving documentation
- Enhancing repository structure

## Submission Process

### For New Analyses

1. **Check Existing Content**: Ensure the contract hasn't been analyzed already
2. **Verify Contract**: Confirm the contract source matches deployed bytecode
3. **Conduct Analysis**: Perform thorough security review
4. **Document Findings**: Follow our analysis template
5. **Submit PR**: Create a pull request with your analysis

### For Updates

1. **Reference Original**: Link to the analysis being updated
2. **Explain Changes**: Clearly describe what's being updated and why
3. **Maintain History**: Don't delete original findings, add updates with dates

## Analysis Standards

### Required Elements

Every smart contract analysis must include:

1. **Contract Information**
   - Contract name and purpose
   - Deployment address and network
   - Source code verification status
   - Audit history (if any)

2. **Executive Summary**
   - Brief overview of findings
   - Severity breakdown
   - Key recommendations

3. **Detailed Findings**
   - Vulnerability description
   - Severity rating (Critical/High/Medium/Low/Info)
   - Impact assessment
   - Proof of concept (where applicable)
   - Recommended fixes

4. **Technical Details**
   - Contract architecture overview
   - Key functions analysis
   - State variables examination
   - Access control review

### Severity Ratings

- **Critical**: Direct risk of large fund loss
- **High**: Direct risk of fund loss or severe disruption
- **Medium**: Potential for fund loss under specific conditions
- **Low**: Minor risk or inefficiency
- **Informational**: Best practice suggestions

## File Structure

```
smart-contract-studies/
├── tokens/          # ERC20, ERC721, and other token standards
├── defi/           # DeFi protocols (AMMs, Lending, Yield Farming, etc.)
├── nft/            # NFT contracts and marketplaces
├── dao/            # DAO and governance contracts
└── tools/          # Utility contracts and development tools
```

### Directory Organization

Each contract study should be organized as follows:

```
/category/              # One of: tokens, defi, nft, dao, tools
  /ContractName/
    README.md           # Brief overview and key information
    contract.sol        # Original contract source code
    contract_detailed_study.md  # Comprehensive analysis
```

### Naming Convention

- Folder names: Use the contract/protocol name (e.g., `RXS`, `UniswapV3`)
- Contract files: Use lowercase with underscores (e.g., `rxs.sol`, `uniswap_v3_pool.sol`)
- Analysis files: `[contract_name]_detailed_study.md` (e.g., `rxs_detailed_study.md`)

## Writing Guidelines

### Style Guide

1. **Language**: Use clear, technical English
2. **Format**: Markdown with proper headers
3. **Code Blocks**: Use syntax highlighting
4. **References**: Link to transactions, addresses, and sources
5. **Visuals**: Include diagrams where helpful

### Content Requirements

1. **Objective**: Maintain neutral, factual tone
2. **Evidence-Based**: Support claims with code references
3. **Reproducible**: Provide steps to verify findings
4. **Educational**: Explain vulnerabilities clearly
5. **Responsible**: Follow disclosure guidelines

### Template Structure

Based on our existing analyses (see `/tokens/RXS/rxs_detailed_study.md` for reference), each detailed study should include:

1. **Contract Overview**
   - Basic Information (name, symbol, address, version)
   - Project Metadata (website, social links)
   - Token/Contract Specifications

2. **Contract Architecture**
   - Inheritance Structure
   - Contracts and Interfaces breakdown
   - Dependencies analysis

3. **State Variables**
   - Mappings
   - Variables
   - Constants

4. **Functions Analysis**
   - Constructor
   - Core Functions
   - Admin Functions
   - View Functions

5. **Security Analysis**
   - Access Control
   - Reentrancy Guards
   - Integer Overflow/Underflow
   - Other Security Considerations

6. **Gas Optimization**
   - Current gas costs
   - Optimization recommendations

7. **Testing & Verification**
   - Test coverage
   - Verification status

8. **Recommendations & Best Practices**

## Code of Conduct

Please review and follow our [Code of Conduct](CODE_OF_CONDUCT.md). Key points:

- Responsible disclosure practices
- Respectful communication
- Accurate and verified information
- Proper attribution
- Educational focus

## Recognition

Contributors will be:
- Listed in our contributors file
- Credited in analyses
- Eligible for special recognition badges
- Invited to our security researcher community

## Questions?

- Open an issue for clarification
- Join our discussion forum
- Contact maintainers directly

Thank you for helping make smart contracts more secure!