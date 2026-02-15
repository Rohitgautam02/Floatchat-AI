# Contributing to FloatChat-AI

Thank you for your interest in contributing to FloatChat-AI! This guide will help you get started.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Floatchat-AI.git
   cd Floatchat-AI
   ```
3. **Create a branch** for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Set up the development environment** — follow the [Quick Start](README.md#-quick-start) instructions

## Development Workflow

### Backend (Python / Flask)

```bash
cd backend
pip install -r requirements.txt
python app.py    # Runs on http://localhost:5000 with auto-reload
```

**Key files:**
- `app.py` — Flask routes and API endpoints
- `services/ai_service.py` — AI/LLM integration (Ollama streaming, OpenAI)
- `services/rag_service.py` — FAISS vector search and RAG retrieval
- `services/data_service.py` — Database queries and chart data generation
- `db/models.py` — SQLAlchemy ORM models

### Frontend (React)

```bash
cd frontend
npm install
npm start        # Runs on http://localhost:3000 with hot reload
```

**Key files:**
- `src/components/ChatPanel.jsx` — AI chat with streaming support
- `src/components/Dashboard.jsx` — Data dashboard
- `src/components/Charts.jsx` — Recharts-based visualizations
- `src/components/MapView.jsx` — Leaflet interactive map

## Code Style

### Python
- Follow **PEP 8** conventions
- Use type hints where practical
- Add docstrings to functions and classes
- Keep functions focused and under ~50 lines

### JavaScript / React
- Use **functional components** with hooks
- Follow standard React naming conventions (PascalCase for components)
- Keep components focused — extract complex logic into helper functions
- Use descriptive variable names

## Making Changes

1. Write clean, readable code with comments for complex logic
2. Test your changes locally — make sure both backend and frontend work
3. Ensure existing functionality isn't broken
4. Update documentation if your change affects the public API or setup steps

## Commit Messages

Use clear, descriptive commit messages:

```
feat: add salinity anomaly visualization
fix: resolve streaming timeout on slow connections
docs: update API reference with new endpoints
refactor: extract chart rendering into shared util
```

**Prefixes:** `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

## Pull Request Process

1. **Update your branch** with the latest main:
   ```bash
   git fetch origin
   git rebase origin/main
   ```
2. **Push** your branch:
   ```bash
   git push origin feature/your-feature-name
   ```
3. **Open a Pull Request** on GitHub with:
   - A clear title describing the change
   - A description of what was changed and why
   - Screenshots if the change affects the UI
4. **Address review feedback** promptly

## Reporting Issues

When reporting bugs, please include:

- **Environment** (OS, Python version, Node version, browser)
- **AI mode** (`ollama`, `openai`, or basic)
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Error messages** or logs (check browser console and Flask terminal)

## Areas for Contribution

Looking for ideas? Here are some areas where help is appreciated:

- 🌊 **New data visualizations** — depth sections, anomaly charts, regional comparisons
- 🤖 **AI improvements** — better prompts, new LLM providers, response quality
- 🗺️ **Map enhancements** — float trajectory animations, region highlighting
- 📊 **Data pipeline** — support more ocean basins, additional float parameters
- 🧪 **Testing** — unit tests, integration tests, E2E tests
- 📖 **Documentation** — tutorials, API examples, deployment guides
- ♿ **Accessibility** — keyboard navigation, screen reader support
- 🌐 **i18n** — internationalization support

## Code of Conduct

Be respectful and constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct. All contributors are expected to be welcoming and inclusive.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

Thank you for helping make FloatChat-AI better! 🌊
