#!/bin/bash
# Set up local development environment
set -e

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install uv first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install Python dependencies
uv sync --group dev

# Install JavaScript dependencies
npm install

# Install pre-commit hooks
uv run pre-commit install
