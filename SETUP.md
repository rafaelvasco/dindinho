# Dependency Management Setup Guide

This project supports multiple dependency management tools. Choose the one that fits your workflow:

- **uv** (Recommended) - Ultra-fast, modern, best for Python 3.14
- **Poetry** - Mature, feature-rich alternative
- **pip** - Traditional approach

---

## Option 1: uv (Recommended) ⚡

**Why uv?**
- 🚀 10-100x faster than pip
- 🎯 Built-in virtual environment management
- 🔒 Automatic lock file generation
- 🆕 Excellent Python 3.14 support
- 🔄 Compatible with pip workflows

### Install uv:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv

# Or with pip
pip install uv
```

### Project Setup with uv:

```bash
# Navigate to project directory
cd /Users/rafaelvasco/Dev/Python/FinanceIngest

# Create virtual environment with Python 3.14
uv venv --python 3.14

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows

# Install dependencies (reads pyproject.toml)
uv pip install -e .

# Install dev dependencies
uv pip install -e ".[dev]"

# Or install everything at once
uv pip install -e ".[dev]"
```

### Daily Workflow with uv:

```bash
# Add a new package
uv pip install package-name

# Update all packages
uv pip install --upgrade -e ".[dev]"

# Sync dependencies (install exact versions from lock file)
uv pip sync requirements.txt

# Generate lock file from pyproject.toml
uv pip compile pyproject.toml -o requirements.txt

# Run the app
source .venv/bin/activate
python run.py
```

### Create Lock File:

```bash
# Generate uv.lock (automatic dependency resolution)
uv pip compile pyproject.toml -o uv.lock

# Install from lock file
uv pip sync uv.lock
```

---

## Option 2: Poetry 📦

**Why Poetry?**
- 🎨 Rich feature set
- 📦 Built-in packaging and publishing
- 🔐 Automatic lock file (poetry.lock)
- 🛠️ Mature ecosystem

### Install Poetry:

```bash
# Official installer
curl -sSL https://install.python-poetry.org | python3 -

# Or with Homebrew
brew install poetry

# Or with pip
pip install poetry
```

### Convert Project to Poetry:

```bash
cd /Users/rafaelvasco/Dev/Python/FinanceIngest

# Initialize Poetry (it will read pyproject.toml)
poetry init --no-interaction

# Configure to create venv in project
poetry config virtualenvs.in-project true

# Create virtual environment with Python 3.14
poetry env use python3.14

# Install dependencies
poetry install

# Install with dev dependencies
poetry install --with dev
```

### Daily Workflow with Poetry:

```bash
# Add a new package
poetry add package-name

# Add dev package
poetry add --group dev package-name

# Update all packages
poetry update

# Update specific package
poetry update package-name

# Run commands in virtual environment
poetry run python run.py
poetry run uvicorn backend.main:app --reload
poetry run streamlit run frontend/app.py

# Activate shell in virtual environment
poetry shell

# Show installed packages
poetry show

# Check for updates
poetry show --outdated
```

### Poetry Configuration (Optional):

Create `poetry.toml` in project root:

```toml
[virtualenvs]
create = true
in-project = true
```

---

## Option 3: Traditional pip + venv 🐍

### Setup:

```bash
cd /Users/rafaelvasco/Dev/Python/FinanceIngest

# Create virtual environment
python3.14 -m venv .venv

# Activate
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows

# Install from requirements.txt
pip install -r requirements.txt

# Or install from pyproject.toml
pip install -e .
pip install -e ".[dev]"
```

### Daily Workflow:

```bash
# Activate environment
source .venv/bin/activate

# Install package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt

# Run app
python run.py
```

---

## Comparison Table

| Feature | uv | Poetry | pip + venv |
|---------|-----|--------|------------|
| Speed | ⚡⚡⚡ | ⚡ | ⚡ |
| Lock files | ✅ | ✅ | Manual |
| Python version management | ✅ | ✅ | Manual |
| Dependency resolution | ✅ Excellent | ✅ Good | ❌ |
| Build/Publish | ❌ | ✅ | Manual |
| Learning curve | Easy | Medium | Easy |
| Maturity | New (2024) | Mature | Very Mature |
| Python 3.14 support | ✅✅✅ | ✅ | ✅ |

---

## Recommended Setup (uv)

### Quick Start:

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Setup project
cd /Users/rafaelvasco/Dev/Python/FinanceIngest
uv venv --python 3.14
source .venv/bin/activate

# 3. Install dependencies
uv pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 5. Run the app
python run.py
```

### IDE Configuration:

**VS Code** (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true
}
```

**PyCharm**:
- File → Settings → Project → Python Interpreter
- Add Interpreter → Existing → Select `.venv/bin/python`

---

## Managing Dependencies

### Adding New Dependencies:

**With uv:**
```bash
# Add to project dependencies
uv pip install package-name
# Then add to pyproject.toml [project.dependencies]

# Or add to pyproject.toml first, then:
uv pip install -e .
```

**With Poetry:**
```bash
# Automatically adds to pyproject.toml
poetry add package-name
```

### Updating Dependencies:

**With uv:**
```bash
# Update all
uv pip install --upgrade -e ".[dev]"

# Update specific package
uv pip install --upgrade package-name
```

**With Poetry:**
```bash
# Update all
poetry update

# Update specific package
poetry update package-name
```

---

## Lock Files for Reproducibility

### With uv:

```bash
# Generate lock file
uv pip compile pyproject.toml -o requirements.lock

# Install from lock file
uv pip sync requirements.lock
```

### With Poetry:

```bash
# Lock file (poetry.lock) is automatic
poetry lock

# Install from lock file
poetry install
```

---

## Best Practices

1. **Always use a virtual environment** - Don't install globally
2. **Commit lock files** - Ensures reproducible builds
3. **Use `.gitignore`** - Don't commit `.venv/` or `__pycache__/`
4. **Pin Python version** - Specify in `pyproject.toml`
5. **Separate dev dependencies** - Keep production lean

---

## Troubleshooting

### uv not found after installation:
```bash
# Add to PATH (add to ~/.zshrc or ~/.bashrc)
export PATH="$HOME/.cargo/bin:$PATH"
```

### Poetry not creating venv in project:
```bash
poetry config virtualenvs.in-project true
```

### Wrong Python version:
```bash
# With uv
uv venv --python 3.14

# With Poetry
poetry env use python3.14
```

### Dependency conflicts:
```bash
# With uv (shows detailed resolution)
uv pip install -e . --verbose

# With Poetry
poetry lock --no-update
poetry install
```

---

## Recommended: uv

For this project, **uv** is recommended because:

✅ Fastest installation and resolution
✅ Simple workflow (similar to pip)
✅ Excellent Python 3.14 support
✅ Active development (Astral/Ruff team)
✅ Works great with existing `pyproject.toml`

**One-line setup:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh && \
cd /Users/rafaelvasco/Dev/Python/FinanceIngest && \
uv venv --python 3.14 && \
source .venv/bin/activate && \
uv pip install -e ".[dev]"
```

Then just:
```bash
python run.py
```

🚀 **You're ready to go!**
