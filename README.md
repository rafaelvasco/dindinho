# Finance Analysis Application

AI-powered finance analysis application for Brazilian expense tracking using Claude AI to automatically categorize expenses from credit card statements and bank account extracts.

## Features

- **CSV Import**: Parse Brazilian credit card statements and account extracts
- **AI Categorization**: Automatic expense categorization using Claude AI
- **Import Preview**: Review and mark items before importing (subscription, ignore)
- **Subscription Tracking**: Track recurring expenses with historical values
- **Expense Reports**: Visualize expenses by category, month, and more
- **Ignore List**: Skip unwanted items during import
- **Full-Stack Python**: Backend (FastAPI) + Frontend (Streamlit)

## Tech Stack

- **Backend**: FastAPI 0.119.1
- **Frontend**: Streamlit 1.52.2
- **Database**: SQLite + SQLAlchemy 2.0.45
- **AI**: Claude (Anthropic API 0.75.0)
- **Python**: 3.14.2 (or 3.13+)

## Project Structure

```
FinanceIngest/
├── backend/               # FastAPI backend
│   ├── api/              # API endpoints
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── utils/            # Utility functions
├── frontend/             # Streamlit frontend
│   ├── components/       # UI components
│   └── utils/            # Frontend utilities
├── tests/                # Tests
│   └── sample_data/      # Sample CSV files
├── data/                 # SQLite database
└── run.py                # Launcher script
```

## Installation

### 1. Prerequisites

- Python 3.13 or 3.14
- Dependency manager: **uv** (recommended), Poetry, or pip
- Anthropic API key ([Get one here](https://console.anthropic.com/))

### 2. Quick Setup (Recommended: uv)

**Option A: Using uv (Fastest - Recommended)** ⚡
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup project
cd FinanceIngest
uv venv --python 3.14
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Or use Makefile (auto-detects tool)
make setup
```

**Option B: Using Poetry** 📦
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Setup project
cd FinanceIngest
poetry install --with dev
```

**Option C: Using pip** 🐍
```bash
# Traditional approach
python3.14 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> 📖 **See [SETUP.md](SETUP.md) for detailed dependency management guide**

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Anthropic API key
# Required: ANTHROPIC_API_KEY=your_api_key_here
```

### 4. Initialize Database

The database will be created automatically on first run. Tables are created based on SQLAlchemy models.

## Usage

### Running the Application

**Quick Start:**
```bash
# Using run.py
python run.py

# Or using Makefile (easier)
make run
```

**Run Separately:**
```bash
# Backend only
make backend
# OR: uvicorn backend.main:app --reload

# Frontend only
make frontend
# OR: streamlit run frontend/app.py
```

**Access:**
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:8501

### Available Make Commands

```bash
make help              # Show all available commands
make setup             # Full project setup
make install           # Install dependencies (auto-detects tool)
make run               # Run backend + frontend
make test              # Run tests
make lint              # Check code quality
make format            # Format code
make clean             # Clean generated files
make info              # Show project info
```

See all commands: `make help`

### CSV File Formats

#### Credit Card Statement
```csv
"Data","Lançamento","Categoria","Tipo","Valor"
"03/01/2026","APPLE.COM/BILL","COMPRAS","Compra à vista","R$ 119,90"
```

#### Account Extract
```csv
Extrato Conta Corrente
Conta ;31304761
Período ;01/12/2025 a 31/12/2025
Saldo: ;6.866,58

Data Lançamento;Descrição;Valor;Saldo
01/12/2025;Pix enviado: "Cp :90400888-ORGANIZACAO VERDEMAR LTDA";-703,69;1.008,71
```

### Import Workflow

1. **Upload CSV**: Select credit card statement or account extract
2. **Preview**: Review parsed expenses
   - See items already in ignore list (grayed out)
   - See duplicate items (grayed out)
   - Mark new items as:
     - Import normally
     - Ignore this time only
     - Ignore all future items with this name
     - Create subscription
3. **Confirm Import**: AI categorizes and stores expenses
4. **View Dashboard**: Analyze expenses by category, month, etc.

## Expense Categories

Brazilian expense categories:
- Supermercado (Groceries)
- Restaurantes (Restaurants)
- Transporte (Transport)
- Assinaturas (Subscriptions)
- Utilidades (Utilities)
- Saúde (Healthcare)
- Entretenimento (Entertainment)
- Compras (Shopping)
- Educação (Education)
- Moradia (Housing)
- Seguros (Insurance)
- Investimentos (Investments)
- Impostos (Taxes)
- Transferências (Transfers)
- Outros (Other)

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov=frontend --cov-report=html

# Run specific test file
pytest tests/test_csv_parser.py
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy backend/ frontend/
```

### Project Structure Details

**Backend Models:**
- `Expense`: Financial transactions with AI categorization
- `Subscription`: Recurring expenses with historical tracking
- `IgnoredExpense`: Descriptions to skip during import
- `ExpenseCategory`: Brazilian expense categories enum

**Key Services:**
- `CSVParser`: Parse Brazilian CSV formats
- `AICategorizer`: Claude AI integration for categorization
- `ExpenseService`: Import workflow orchestration
- `date_parser`: Brazilian date format parsing (DD/MM/YYYY)
- `currency_parser`: BRL currency parsing (R$ X.XXX,XX)

## Configuration

### Environment Variables

```env
# Database
DATABASE_PATH=./data/finance.db

# Anthropic API
ANTHROPIC_API_KEY=your_api_key_here

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Frontend
FRONTEND_PORT=8501

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation (Swagger UI).

### Key Endpoints

- `POST /api/upload/preview` - Upload CSV and preview items
- `POST /api/upload/import` - Import expenses with user actions
- `GET /api/expenses` - List expenses (with filters)
- `PATCH /api/expenses/{id}` - Update expense category
- `DELETE /api/expenses/{id}` - Delete expense
- `GET /api/subscriptions` - List subscriptions
- `GET /api/ignore-list` - Get ignored descriptions
- `GET /api/reports/*` - Various expense reports

## Troubleshooting

### Database Issues

```bash
# Delete database to start fresh
rm data/finance.db
# Restart application - database will be recreated
```

### API Key Issues

- Ensure `ANTHROPIC_API_KEY` is set in `.env`
- Check API key is valid at https://console.anthropic.com/

### CSV Parsing Issues

- Ensure CSV uses correct format (see examples above)
- Check encoding (UTF-8 or ISO-8859-1)
- Verify delimiter (comma for credit card, semicolon for account extract)

## License

MIT

## Author

Rafael Vasco
