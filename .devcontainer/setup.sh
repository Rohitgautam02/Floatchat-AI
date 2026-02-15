#!/bin/bash
set -e

echo "🚀 Setting up FloatChat-AI..."
echo ""

# ---- Backend ----
echo "📦 Installing Python dependencies..."
cd backend
pip install -r requirements.txt

# Create .env from template if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        cat > .env << 'EOL'
# AI Configuration — choose one:
#   ollama   = Free local AI (requires Ollama installed)
#   openai   = Cloud AI (requires API key)
#   (blank)  = Basic data mode, no AI chat
AI_MODE=

# Ollama settings (if AI_MODE=ollama)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# OpenAI settings (if AI_MODE=openai)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# Database
DATABASE_URL=sqlite:///./db/argo_data.db

# Flask
FLASK_ENV=development
FLASK_SECRET_KEY=dev-secret-change-in-production
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=True

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000
EOL
    fi
    echo "⚠️  Edit backend/.env to configure your AI provider!"
fi

# Fetch ARGO data if database doesn't exist
if [ ! -f db/argo_data.db ]; then
    echo "📊 Fetching ARGO float data from Indian Ocean..."
    python fetch_argovis.py
else
    echo "✅ Database already exists, skipping data fetch."
fi

cd ..

# ---- Frontend ----
echo ""
echo "📦 Installing Node.js dependencies..."
cd frontend
npm install
cd ..

echo ""
echo "════════════════════════════════════════════"
echo "  ✅ FloatChat-AI setup complete!"
echo "════════════════════════════════════════════"
echo ""
echo "  🎯 To run the project:"
echo "     Terminal 1: cd backend && python app.py"
echo "     Terminal 2: cd frontend && npm start"
echo ""
echo "  🌐 URLs:"
echo "     Backend:  http://localhost:5000"
echo "     Frontend: http://localhost:3000"
echo ""
echo "  🤖 AI Setup:"
echo "     Edit backend/.env to configure Ollama or OpenAI"
echo "     See README.md for detailed AI configuration guide"
echo "════════════════════════════════════════════"
