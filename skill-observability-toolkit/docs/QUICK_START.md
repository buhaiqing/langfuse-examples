
# Quick Start Guide

> **Time**: 10-15 minutes
> **Level**: Beginner

## Step 1: Installation

Clone repository and install:
```bash
git clone https://github.com/langfuse/langfuse-examples.git
cd skill-observability-toolkit
pip install -e .[dev]
```

Setup Langfuse credentials:
```bash
## Step 2: Configure

cp .env.example .env
```
Add your keys: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY

## Step 3: Run Example

```bash
cd examples/basic-skill
python src/main.py
```

See README.md for full details.
