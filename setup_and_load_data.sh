#!/bin/bash
# Setup and Data Loading Script for Academic Rankings Platform

set -e  # Exit on error

echo "=========================================="
echo "Academic Rankings Platform - Data Setup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << EOF
# Database Configuration
POSTGRES_HOST=db.peawexmwwmkqszcdqwjv.supabase.co
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=REPLACE_WITH_YOUR_SUPABASE_PASSWORD

# OpenAlex API (optional)
OPENALEX_EMAIL=

# Streamlit Configuration
STREAMLIT_SERVER_PORT=8501
EOF
    echo "✅ Created .env file"
    echo "⚠️  IMPORTANT: Edit .env and add your Supabase password!"
    echo ""
    read -p "Press Enter after you've updated .env with your password..."
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip -q

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt
echo "✅ Dependencies installed in venv"
echo ""

# Generate sample data
echo "📊 Generating sample data..."
PYTHONPATH=$(pwd) python scripts/create_sample_data.py
echo "✅ Sample data generated"
echo ""

# Load to database
echo "💾 Loading data to database..."
PYTHONPATH=$(pwd) python scripts/load_to_postgres.py
echo "✅ Data loaded"
echo ""

# Compute rankings
echo "📈 Computing rankings..."
PYTHONPATH=$(pwd) python scripts/ranking_engine.py
echo "✅ Rankings computed"
echo ""

# Advanced analytics
echo "🔬 Running advanced analytics..."
PYTHONPATH=$(pwd) python scripts/advanced_analytics.py
echo "✅ Analytics completed"
echo ""

# Deactivate venv
deactivate
echo ""

echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Make sure you've run the SQL schema in Supabase:"
echo "   - Go to Supabase SQL Editor"
echo "   - Run sql/schema.sql"
echo "   - Run sql/views.sql"
echo ""
echo "2. Test your dashboard:"
echo "   https://academic-ranking-analytics-platform-dx7vmjupnvzrtfgxpznpxt.streamlit.app/"
echo ""
