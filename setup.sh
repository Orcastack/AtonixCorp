#!/bin/bash

echo "🔧 Setting up Atonix Capital..."
echo ""

API_DIR="api"
VENV_DIR=".venv"
if [ -d "$API_DIR/venv" ] && [ ! -d "$API_DIR/.venv" ]; then
    VENV_DIR="venv"
fi

# Setup API
echo "📦 Setting up Django API..."
cd "$API_DIR"

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "Creating backend .env file..."
    cp .env.example .env
    BANKING_KEY=$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)
    sed -i "s/^BANKING_TOKEN_ENCRYPTION_KEY=.*/BANKING_TOKEN_ENCRYPTION_KEY=${BANKING_KEY}/" .env
fi

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Use the virtual environment without relying on activation scripts.
VENV_PYTHON="$PWD/$VENV_DIR/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "Virtual environment is missing a Python executable. Recreating..."
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
    VENV_PYTHON="$PWD/$VENV_DIR/bin/python"
fi

if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Install dependencies
echo "Installing Python dependencies..."
"$VENV_PYTHON" -m pip install -r requirements.txt
echo "Installing AtonixCorp CLI..."
"$VENV_PYTHON" -m pip install -e ../tools/atonixcorp_cli

# Run migrations
echo "Running database migrations..."
"$VENV_PYTHON" manage.py makemigrations
"$VENV_PYTHON" manage.py migrate

# Create superuser prompt
echo ""
read -p "Do you want to create a superuser for admin panel? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    "$VENV_PYTHON" manage.py createsuperuser
fi

cd ..

# Setup app
echo ""
echo "⚛️  Setting up React app..."
cd app

# Install dependencies
echo "Installing Node dependencies..."
npm install

# Create .env.local file
if [ ! -f ".env.local" ]; then
    echo "Creating .env.local file..."
    cp .env.example .env.local
fi

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application, run:"
echo "  ./start.sh"
echo ""
echo "Banking integration setup:"
echo "  1. Edit api/.env with your Plaid, Yodlee, or Finicity credentials"
echo "  2. Point provider webhooks to /api/banking-integrations/webhooks/<provider_code>/"
echo "  3. Nightly fallback sync runs automatically via start.sh or docker-compose banking-sync"
echo ""
echo "To use the CLI after setup, run:"
echo "  $API_DIR/$VENV_DIR/bin/atonixcorp profiles"
echo ""
echo "Or start manually:"
echo "  API:      cd $API_DIR && $VENV_DIR/bin/python manage.py runserver"
echo "  App:      cd app && npm start"
