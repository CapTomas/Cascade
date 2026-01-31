# Contributing to Cascade

We welcome contributions from the community! Cascade is built for professional engineers, and we maintain high standards for code quality and security.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/cascade-ai/cascade.git
   cd cascade
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Contribution Rules

- **Follow conventions**: Every PR must adhere to the conventions defined in `conventions.yaml`.
- **Test everything**: No code is accepted without accompanying unit tests.
- **Security first**: Never add dependencies without a security review. Hard-coded secrets are strictly forbidden.
- **Sign off**: All commits must be signed for the Developer Certificate of Origin (DCO).

## How to Submit a PR

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes with descriptive messages.
4. Open a Pull Request against the `main` branch.
5. Wait for the automated quality gates to pass and for a core maintainer review.

Thank you for helping us build the future of AI orchestration!
