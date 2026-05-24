---
name: Bug Report
about: Something is broken — wrong contracts, missed bids, email failures
title: "[BUG] "
labels: ["bug"]
assignees: []
---

## Describe the Bug
A clear description of what went wrong.

## Expected Behaviour
What you expected to happen.

## Actual Behaviour
What actually happened. Include log output if available.

## Reproduction Steps
1. …
2. …

## Environment
- Deployment method: [ ] Docker  [ ] GitHub Actions  [ ] Local Python
- Python version (if local): 
- Docker image tag:
- OS:

## Logs
```
Paste relevant log lines here (run with LOG_LEVEL=DEBUG if possible)
```

## Checklist
- [ ] I have checked that my `.env` values are correct
- [ ] The site I'm trying to scrape is accessible in a browser
- [ ] I have reviewed `data/contracts.db` to confirm the contract isn't already marked seen
