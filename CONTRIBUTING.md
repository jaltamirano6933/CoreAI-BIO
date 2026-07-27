# Contributing to CoreAI BIO

Thank you for your interest in contributing to **CoreAI BIO**! We welcome contributions from researchers, bioinformaticians, computer vision engineers, and software developers.

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## How to Contribute

### 1. Reporting Bugs
If you discover a bug or unexpected behavior:
- Open a GitHub Issue detailing:
  1. Your OS and Python version.
  2. Steps to reproduce the issue.
  3. Expected vs. actual behavior.
  4. Full error tracebacks or logs.

### 2. Proposing Features or Profiles
We welcome proposals for new morphology profiles, bioinformatics tools, or analytical features:
- Please open a GitHub Discussion or Issue before starting major development.
- Clearly describe the biological motivation and computational workflow.

### 3. Submitting Pull Requests (PRs)
1. Fork the repository and create your feature branch:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Ensure your code follows PEP 8 style guidelines.
3. Write automated unit tests in `tests/` covering new capabilities.
4. Run the full test suite and confirm 100% pass rate:
   ```bash
   python -m unittest discover tests
   ```
5. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "Add feature: [Description]"
   ```
6. Push to your fork and submit a Pull Request.

---

## Development Setup

```bash
# 1. Clone repository
git clone https://github.com/CoreAI-BIO/CoreAI-BIO.git
cd CoreAI-BIO

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run tests
python -m unittest discover tests

# 5. Launch local server
python backend/app.py
```
