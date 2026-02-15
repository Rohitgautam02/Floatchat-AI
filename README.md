# FloatChat-AI 🌊🤖

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Llama_3.2-ff6600?logo=meta&logoColor=white)
![RAG](https://img.shields.io/badge/AI-RAG_Powered-orange)

**The Intelligent Interface for Indian Ocean ARGO Float Data.**

FloatChat-AI explores the depths of the Indian Ocean using real-time data from the **ARGO Float Network**. It combines a modern interactive dashboard with an AI-powered **streaming RAG chatbot** to make oceanographic data accessible, understandable, and actionable.

<p align="center">
  <img src="screenshots/Screenshot (188).png" width="48%" alt="Dashboard" />
  <img src="screenshots/Screenshot (189).png" width="48%" alt="Chat" />
</p>
<p align="center">
  <img src="screenshots/Screenshot (190).png" width="48%" alt="Map" />
  <img src="screenshots/Screenshot (191).png" width="48%" alt="Charts" />
</p>

---

## Table of Contents

- [Key Features](#-key-features)
- [Technology Stack](#-technology-stack)
- [Quick Start](#-quick-start)
- [Dev Container / Codespaces](#-dev-container--github-codespaces)
- [AI Configuration](#-ai-configuration)
- [Project Structure](#-project-structure)
- [API Reference](#-api-reference)
- [Environment Variables](#-environment-variables)
- [Scientific Verification](#-scientific-verification)
- [Contributing](#-contributing)
- [License](#-license)
- [Acknowledgments](#-acknowledgments)

---

## ✨ Key Features

### 🧠 AI-Powered Streaming Chat (RAG)
- **Real-time Streaming** — Tokens arrive word-by-word (like ChatGPT) via Ollama streaming, so you never wait for the full response.
- **Context-Aware RAG** — Uses FAISS vector embeddings + SentenceTransformers to retrieve relevant float data for every query.
- **Local & Cloud AI** — Supports **Ollama (Llama 3.2, FREE)** for local inference or **OpenAI GPT-4o-mini** for cloud-based reasoning.
- **Auto Pre-warming** — Ollama model is pre-loaded into RAM at server startup for instant first responses.
- **Chart Intent Detection** — Automatically detects when a visualization is needed and renders the right chart.

### 📊 Interactive Data Dashboard
- **Scientifically Verified Data** — Only real, confirmed ARGO floats from the Indian Ocean (Arabian Sea, Bay of Bengal, Equatorial, Southern IO).
- **Live Map** — Interactive Leaflet map showing real-time float positions and drift trajectories.
- **Advanced Visualization**:
  - Temperature & Salinity depth profiles
  - T-S Diagrams for water mass analysis
  - Depth-time sections
  - Regional surface statistics (0–10 m)

### 🛡️ Robust Backend
- **Data Pipeline** — Automated fetching and validation of float profiles from the **Argovis 2.0 API**.
- **Vector Search** — Automatic FAISS embedding generation for new float data.
- **SQLite Database** — Efficient local storage for metadata and profiles.
- **Fallback Mode** — Structured data responses even when no AI is configured.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 19, Recharts, React-Leaflet | UI, charts, interactive maps |
| **Backend** | Flask 3.1, SQLAlchemy, Gunicorn | REST API, ORM, production server |
| **AI / RAG** | FAISS, SentenceTransformers (`all-MiniLM-L6-v2`) | Vector search & embeddings |
| **LLM** | Ollama (Llama 3.2) / OpenAI (GPT-4o-mini) | Conversational AI |
| **Data Source** | Argovis 2.0 API | Scientific ARGO float observations |
| **Database** | SQLite | Local persistent storage |
| **DevOps** | Docker, Dev Containers, GitHub Codespaces | Reproducible environments |

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Required |
|------|---------|----------|
| Python | 3.10+ | Yes |
| Node.js | 18+ | Yes |
| Ollama | latest | Recommended (for free AI) |
| Git | any | Yes |

### Option 1: Automated Setup ⚡ (Recommended)

```bash
git clone https://github.com/Rohitgautam02/Floatchat-AI.git
cd Floatchat-AI
chmod +x setup.sh
./setup.sh
```

The interactive script will:
1. Install all Python & Node.js dependencies
2. Let you choose AI mode (Ollama / OpenAI / Basic)
3. Create the SQLite database
4. Fetch sample ARGO data from the Indian Ocean
5. Show you how to start the app

### Option 2: Manual Setup

```bash
# 1. Clone the repository
git clone https://github.com/Rohitgautam02/Floatchat-AI.git
cd Floatchat-AI

# 2. Backend setup
cd backend
pip install -r requirements.txt
cp .env.example .env          # then edit .env with your AI settings

# 3. Initialize database and fetch ocean data
python fetch_argovis.py

# 4. Start the backend (Terminal 1)
python app.py                  # runs on http://localhost:5000

# 5. Frontend setup (Terminal 2)
cd ../frontend
npm install
npm start                      # opens http://localhost:3000
```

### Option 3: Docker Compose

```bash
git clone https://github.com/Rohitgautam02/Floatchat-AI.git
cd Floatchat-AI
cp backend/.env.example backend/.env   # edit .env with your settings
docker compose up --build
```

Open **http://localhost:3000** — the frontend proxies API calls to the backend automatically.

### Windows-Specific Setup

On Windows, the `setup.sh` script requires Git Bash or WSL. Alternatively, follow the manual setup:

```powershell
# PowerShell
git clone https://github.com/Rohitgautam02/Floatchat-AI.git
cd Floatchat-AI

# Backend
cd backend
pip install -r requirements.txt
Copy-Item .env.example .env    # edit .env with notepad
python fetch_argovis.py
python app.py

# Frontend (new PowerShell window)
cd frontend
npm install
npm start
```

---

## 🐳 Dev Container / GitHub Codespaces

This project includes a full **Dev Container** configuration for one-click development.

### GitHub Codespaces (Easiest)

1. Go to [github.com/Rohitgautam02/Floatchat-AI](https://github.com/Rohitgautam02/Floatchat-AI)
2. Click **Code → Codespaces → Create codespace on main**
3. Wait for the container to build (~2–3 minutes)
4. The post-create script auto-installs all dependencies
5. Open two terminals:
   ```bash
   # Terminal 1 — Backend
   cd backend && python app.py

   # Terminal 2 — Frontend
   cd frontend && npm start
   ```
6. Codespaces will auto-forward ports 5000 & 3000

> **Note:** Ollama cannot run inside Codespaces. Use `AI_MODE=openai` with an API key in `backend/.env`, or use Basic Mode.

### VS Code Dev Container (Local)

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
2. Open the repo folder in VS Code
3. Press `Ctrl+Shift+P` → **Dev Containers: Reopen in Container**
4. All dependencies install automatically via `postCreateCommand`
5. For Ollama support, install Ollama on your **host machine** (not in the container) and set:
   ```env
   OLLAMA_URL=http://host.docker.internal:11434
   ```

---

## 🤖 AI Configuration

FloatChat-AI gives you **three options** — choose what fits your needs:

| Option | Cost | Speed | Setup |
|--------|------|-------|-------|
| **🆓 Ollama** | **FREE forever** | ~5 tok/s (CPU) | 5 min local install |
| **💳 OpenAI** | ~$0.001 / chat | Very fast | 2 min (API key) |
| **📊 Basic** | Free | Instant | None |

### 🆓 Ollama — Free Local AI (Recommended)

```bash
# Install Ollama (one-time)
# Linux / macOS:
curl -fsSL https://ollama.ai/install.sh | sh
# Windows: download from https://ollama.com/download

# Pull the model (~2 GB download)
ollama pull llama3.2

# Start Ollama (keep running in background)
ollama serve
```

In `backend/.env`:
```env
AI_MODE=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

> **Performance tip:** The backend pre-warms Ollama at startup (loads model into RAM). The first chat after a cold start may take a few extra seconds, but all subsequent responses stream in real-time.

### 💳 OpenAI — Cloud AI

Get an API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys).

In `backend/.env`:
```env
AI_MODE=openai
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-4o-mini
```

### 📊 Basic Mode — No AI

No configuration needed. You'll get structured data tables, charts, and statistics without AI conversations. Upgrade anytime by editing `.env`.

---

## 📂 Project Structure

```
Floatchat-AI/
├── .devcontainer/
│   ├── devcontainer.json       # Dev Container / Codespaces config
│   └── setup.sh                # Post-create setup for Codespaces
├── .vscode/
│   └── settings.json           # VS Code workspace settings
├── backend/
│   ├── app.py                  # Flask application & API routes
│   ├── fetch_argovis.py        # ARGO data fetcher (Argovis 2.0 API)
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment variable template
│   ├── services/
│   │   ├── ai_service.py       # LLM integration (Ollama streaming / OpenAI)
│   │   ├── rag_service.py      # FAISS vector search & RAG retrieval
│   │   └── data_service.py     # Database queries, stats & chart data
│   ├── db/
│   │   ├── models.py           # SQLAlchemy models (ArgoRecord, FloatMetadata)
│   │   └── session.py          # Database session factory
│   └── data/
│       ├── argo_indian_ocean.csv
│       └── faiss_index/        # FAISS vector index + documents
├── frontend/
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── App.jsx             # Main app with routing
│       ├── App.css             # Ocean-themed dark mode styles
│       ├── index.jsx           # React entry point
│       └── components/
│           ├── ChatPanel.jsx   # AI chat with real-time streaming
│           ├── Dashboard.jsx   # Data dashboard with stats cards
│           ├── Charts.jsx      # Recharts visualizations
│           ├── MapView.jsx     # Leaflet interactive map
│           └── Navbar.jsx      # Navigation bar
├── screenshots/                # App screenshots
├── setup.sh                    # Interactive one-click setup
├── docker-compose.yml          # Docker Compose multi-service
├── Dockerfile                  # Multi-stage Docker build
├── CONTRIBUTING.md             # Contribution guidelines
├── LICENSE                     # MIT License
└── README.md                   # This file
```

---

## 📡 API Reference

All endpoints are served from `http://localhost:5000`.

### Chat Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send message, get full JSON response |
| `POST` | `/api/chat/stream` | Send message, get **streaming** NDJSON tokens |

**Request body:**
```json
{ "message": "What is the average ocean temperature?" }
```

**`/api/chat` response:**
```json
{
  "reply": "Based on 885,570 measurements...",
  "chart_type": "temperature_profile"
}
```

**`/api/chat/stream` response** (newline-delimited JSON):
```
{"token": "Based ", "done": false, "chart_type": "temperature_profile"}
{"token": "on ", "done": false, "chart_type": "temperature_profile"}
...
{"token": "", "done": true, "chart_type": "temperature_profile"}
```

### Data Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check & setup status |
| `GET` | `/api/data/stats` | Dataset statistics overview |
| `GET` | `/api/data/floats` | All float metadata + positions |
| `GET` | `/api/data/floats/<wmo_id>` | Single float details |
| `GET` | `/api/data/floats/<wmo_id>/trajectory` | Float trajectory data |
| `GET` | `/api/data/charts/temp-profile?platform=X` | Temperature vs depth |
| `GET` | `/api/data/charts/sal-profile?platform=X` | Salinity vs depth |
| `GET` | `/api/data/charts/ts-diagram?platform=X` | T-S diagram data |
| `GET` | `/api/data/charts/depth-time?platform=X` | Depth-time section |
| `POST` | `/api/data/query` | Query records with filters |
| `POST` | `/api/data/export` | Export filtered data as CSV |

---

## ⚙️ Environment Variables

All configuration lives in `backend/.env`. Copy from the template:

```bash
cp backend/.env.example backend/.env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_MODE` | `ollama` | AI provider: `ollama`, `openai`, or leave unset for basic |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `OPENAI_API_KEY` | — | OpenAI API key (only for `AI_MODE=openai`) |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `DATABASE_URL` | `sqlite:///./db/argo_data.db` | SQLite database path |
| `FLASK_ENV` | `development` | `development` or `production` |
| `FLASK_SECRET_KEY` | `your-secret-key-here` | Flask session secret |
| `PORT` | `5000` | Backend server port |
| `FRONTEND_URL` | `http://localhost:3000` | Frontend URL for CORS |

---

## 🧪 Scientific Verification

This project adheres to strict oceanographic data quality standards:

- **Boundary Checks** — Floats drifting outside 20°E–120°E longitude are automatically filtered.
- **Surface Statistics** — "Surface Temperature" uses only the top **10 m** of the water column (scientifically accepted mixed-layer definition).
- **Verified Sources** — All data from the [Argovis 2.0 API](https://argovis-api.colorado.edu/), cross-checked against official float indices.
- **No Synthetic Data** — Every record is a real ARGO float profile in the Indian Ocean.

### Tracked Regions

| Region | Latitude | Longitude |
|--------|----------|-----------|
| Arabian Sea | 5°N – 30°N | 45°E – 78°E |
| Bay of Bengal | 5°N – 25°N | 78°E – 100°E |
| Equatorial Indian Ocean | 10°S – 10°N | 40°E – 100°E |
| Southern Indian Ocean | 35°S – 10°S | 20°E – 120°E |

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

**Quick version:**
1. Fork the repo
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **[Argovis](https://argovis.colorado.edu/)** — API for accessing ARGO float data
- **[CSIRO](https://www.csiro.au/) & [INCOIS](https://incois.gov.in/)** — Deploying Indian Ocean ARGO floats
- **[Ollama](https://ollama.com/)** — Democratizing local AI inference
- **[FAISS](https://github.com/facebookresearch/faiss)** — Efficient vector similarity search
- **[SentenceTransformers](https://www.sbert.net/)** — State-of-the-art text embeddings

---

<p align="center">Made with 🌊 for ocean science</p>
