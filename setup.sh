#!/bin/bash
# FloatChat-AI Setup Script
# Automated setup for the ARGO ocean data analysis platform

set -e  # Exit on any error

echo "🌊 FloatChat-AI Setup Starting..."
echo "=================================================="

# Check if running in project directory
if [[ ! -f "README.md" || ! -d "backend" ]]; then
    echo "❌ Error: Run this script from the FloatChat-AI project root directory"
    exit 1
fi

# Python environment setup
echo "🐍 Setting up Python environment..."
cd backend

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.10"

if [[ $(echo "$python_version < $required_version" | bc -l 2>/dev/null || echo "1") == "1" ]]; then
    echo "⚠️  Warning: Python 3.10+ recommended (found: $python_version)"
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Create database
echo "🗄️  Setting up database..."
python3 -c "from db.session import engine; from db.models import Base; Base.metadata.create_all(bind=engine)"

# AI Configuration
echo ""
echo "🤖 AI Configuration - Choose Your Option!"
echo "========================================"
echo ""
echo "FloatChat-AI supports TWO great AI options:"
echo ""
echo "🆓 1. Ollama (FREE) - Local AI, no costs, works offline"
echo "💳 2. OpenAI (PAID) - Cloud AI, fast, ~\$0.001 per chat"
echo "📊 3. Basic Mode - No AI, just data tables (always free)"
echo ""
echo "💡 Most users choose Ollama for the zero cost!"
echo ""

read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🆓 Setting up Ollama (FREE Local AI)..."
        echo "======================================"
        if ! command -v ollama &> /dev/null; then
            echo "📥 Installing Ollama..."
            curl -fsSL https://ollama.ai/install.sh | sh
        fi
        
        echo "🚀 Starting Ollama service..."
        ollama serve &
        sleep 3
        
        echo "📦 Downloading Llama 3.2 model (this may take a few minutes)..."
        ollama pull llama3.2
        
        # Update .env for Ollama
        sed -i 's/AI_MODE=.*/AI_MODE=ollama/' .env
        echo ""
        echo "✅ Ollama (FREE AI) is ready!"
        echo "💡 Your AI conversations will be FREE and private!"
        ;;
    2)
        echo ""
        echo "💳 Setting up OpenAI (Cloud AI)..."
        echo "================================="
        echo "You'll need an API key from: https://platform.openai.com/api-keys"
        echo "💰 Typical cost: ~\$0.001 per conversation (very affordable)"
        echo ""
        read -p "Enter your OpenAI API key: " api_key
        if [[ -z "$api_key" ]]; then
            echo "❌ No API key provided. Falling back to Basic Mode."
            echo "💡 You can add your API key to .env file later"
        else
            sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$api_key/" .env
            sed -i 's/AI_MODE=.*/AI_MODE=openai/' .env
            echo "✅ OpenAI configured!"
            echo "💡 Your conversations will use OpenAI credits"
        fi
        ;;
    3)
        echo ""
        echo "📊 Using Basic Mode (No AI)..."
        echo "============================="
        echo "✅ You'll get structured data responses!"
        echo "💡 To add AI later, edit backend/.env file"
        ;;
    *)
        echo ""
        echo "❌ Invalid choice. Using Basic Mode."
        echo "💡 Edit backend/.env to configure AI later"
        ;;
esac

# Data setup
echo ""
echo "🌊 ARGO Data Setup"
echo "=================="
echo "Fetching sample ARGO ocean data..."

if [[ -f "fetch_argovis.py" ]]; then
    python3 fetch_argovis.py
    echo "✅ Sample data loaded!"
else
    echo "⚠️  Data fetcher not found. Using existing sample data."
fi

# Frontend setup
cd ../frontend
echo ""
echo "⚛️  Setting up React frontend..."
echo "Installing Node.js dependencies..."
npm install

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "🚀 To start FloatChat-AI:"
echo ""
echo "1. Backend (Terminal 1):"
echo "   cd backend && python3 app.py"
echo ""
echo "2. Frontend (Terminal 2):"
echo "   cd frontend && npm start"
echo ""
echo "3. Open browser: http://localhost:3000"
echo ""

if [[ $choice == "1" ]]; then
    echo "🎉 Ollama (FREE AI) is running! No usage costs ever!"
    echo "💡 Keep Ollama running in background for AI responses"
elif [[ $choice == "2" ]]; then
    echo "🎉 OpenAI configured! Fast cloud-based AI responses"  
    echo "💰 Usage will consume your OpenAI API credits (~$0.001/chat)"
else
    echo "🎉 Basic Mode active!"
    echo "💡 Get FREE AI by running: ./setup.sh again and choosing Ollama"
    echo "💡 Or edit backend/.env to configure OpenAI/Ollama manually"
fi

echo ""
echo "🌟 Both AI options work equally well - choose based on your preference:"
echo "   🆓 Ollama = FREE forever, runs locally"  
echo "   💳 OpenAI = Small cost, runs in cloud"

echo ""
echo "📚 Documentation: See README.md for detailed usage"
echo "🐛 Issues? Check GitHub discussions or create an issue"
echo ""
echo "Happy ocean data exploring! 🌊🤖"