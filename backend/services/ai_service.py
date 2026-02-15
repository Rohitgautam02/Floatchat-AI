"""
AI Service Module — Enhanced with RAG
Handles AI-powered chat responses with ARGO data context, RAG retrieval, and structured responses.
"""
import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import requests as req_lib
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class AIService:
    """AI service with RAG-enhanced responses"""

    def __init__(self, rag_service=None):
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.ai_mode = os.getenv('AI_MODE', 'openai').lower()
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.2')
        self.rag = rag_service

        self.use_ai = False
        self.client = None
        self._original_ai_mode = self.ai_mode  # Remember the configured mode for retries

        # Try Ollama
        if self.ai_mode == 'ollama' and REQUESTS_AVAILABLE:
            if self._test_ollama():
                self.use_ai = True
                print(f"[OK] Ollama connected - model: {self.ollama_model}")
                # Pre-warm: load model into memory so first chat is fast
                self._warmup_ollama()
            else:
                print("[WARN] Ollama not available yet at startup, will retry on each request...")

        # Try OpenAI (only if not configured for ollama, or as explicit mode)
        if self.ai_mode == 'openai' and not self.use_ai:
            if OPENAI_AVAILABLE and self.api_key and not self.api_key.startswith('your_'):
                try:
                    self.client = OpenAI(api_key=self.api_key)
                    self.use_ai = True
                    print(f"[OK] OpenAI initialized - model: {self.model}")
                except Exception as e:
                    print(f"[ERROR] OpenAI init failed: {e}")

        if not self.use_ai:
            print("[WARNING] No AI service available yet. Will retry Ollama on each request.")
            print("[INFO] Make sure Ollama is running: ollama serve")
            print("[INFO] Using basic data-driven responses until AI is available.")

        self.system_prompt = self._build_system_prompt()

    def _test_ollama(self) -> bool:
        try:
            r = req_lib.get(f"{self.ollama_url}/api/tags", timeout=5)
            if r.status_code == 200:
                # Verify the configured model is available
                models = r.json().get('models', [])
                model_names = [m.get('name', '').split(':')[0] for m in models]
                if self.ollama_model.split(':')[0] in model_names:
                    return True
                # Model not found but Ollama is running
                if models:
                    print(f"[WARN] Model '{self.ollama_model}' not found. Available: {', '.join(m.get('name','') for m in models)}")
                    # Use the first available model as fallback
                    self.ollama_model = models[0].get('name', self.ollama_model)
                    print(f"[INFO] Using model: {self.ollama_model}")
                    return True
                return True
            return False
        except Exception as e:
            print(f"[DEBUG] Ollama test failed: {e}")
            return False

    def _warmup_ollama(self):
        """Pre-load the Ollama model into memory so the first real chat is fast."""
        try:
            print(f"[INFO] Pre-warming Ollama model '{self.ollama_model}' (loading into RAM)...")
            r = req_lib.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.ollama_model, "prompt": "hi", "stream": False,
                      "options": {"num_predict": 1}},
                timeout=180  # Model loading can take a while on first run
            )
            if r.status_code == 200:
                print(f"[OK] Ollama model pre-warmed and ready!")
            else:
                print(f"[WARN] Ollama warmup got status {r.status_code}")
        except Exception as e:
            print(f"[WARN] Ollama warmup failed (model may load on first chat): {e}")

    def _build_system_prompt(self) -> str:
        return """You are FloatChat, an expert oceanographic AI assistant specializing in ARGO float data analysis for the Indian Ocean region.

ARGO floats are autonomous profiling instruments that measure:
- Temperature (°C) — ranges typically 2-30°C
- Salinity (PSU — Practical Salinity Units) — typically 34-36 PSU
- Pressure/Depth (dbar) — surface to 2000m
- Geographic position (lat/lon)

IMPORTANT RESPONSE RULES:
1. When the user asks about data visualization, include a "chart_suggestion" in your response indicating what type of chart would best answer their question.
2. Available chart types: "temperature_profile", "salinity_profile", "ts_diagram", "trajectory", "depth_time"
3. When referencing specific floats, mention them by WMO ID.
4. Explain ocean phenomena clearly — thermocline, halocline, water masses, etc.
5. If the user asks to compare or show data, suggest which chart type fits best.
6. Be concise, scientific, and helpful. Use markdown formatting.
7. Always reference the actual data values from the context provided.

RESPONSE FORMAT:
Your response should be informative markdown text. If a chart would help, mention it naturally like:
"I'd recommend viewing the **temperature depth profile** chart for this float."
"""

    def generate_response(self, user_message: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI response with structured output.

        Returns:
            Dict with 'reply' (text), 'chart_type' (optional), 'chart_data' (optional)
        """
        print(f"[DEBUG] generate_response called. use_ai={self.use_ai}, ai_mode={self.ai_mode}, original_mode={self._original_ai_mode}")
        
        # Get RAG context if available
        rag_context = ""
        if self.rag and self.rag.ready:
            rag_results = self.rag.search(user_message, k=3)
            if rag_results:
                rag_context = "\n\n=== Relevant Float Summaries (from RAG) ===\n"
                for r in rag_results:
                    rag_context += f"• {r['text']} (relevance: {r['score']:.2f})\n"

        # Detect chart intent
        chart_type = self._detect_chart_intent(user_message)

        # If AI is not connected yet but mode is ollama, retry connection
        if not self.use_ai and self._original_ai_mode == 'ollama' and REQUESTS_AVAILABLE:
            if self._test_ollama():
                self.use_ai = True
                self.ai_mode = 'ollama'
                print(f"[OK] Ollama reconnected - model: {self.ollama_model}")

        if not self.use_ai:
            return self._generate_fallback_response(user_message, context_data, chart_type)

        try:
            context_str = self._format_context(context_data) + rag_context
            print(f"[DEBUG] Calling {self.ai_mode}...")
            if self.ai_mode == 'ollama':
                reply = self._call_ollama(user_message, context_str)
            else:
                reply = self._call_openai(user_message, context_str)
            
            print(f"[DEBUG] AI reply received ({len(reply)} chars)")

            return {
                "reply": reply,
                "chart_type": chart_type,
            }
        except Exception as e:
            print(f"[ERROR] AI error: {e}")
            return self._generate_fallback_response(user_message, context_data, chart_type)

    def _detect_chart_intent(self, query: str) -> str:
        """Detect what chart type the user wants"""
        q = query.lower()
        if any(w in q for w in ['temperature profile', 'temp profile', 'temperature vs depth', 'temp depth']):
            return "temperature_profile"
        if any(w in q for w in ['salinity profile', 'sal profile', 'salinity vs depth', 'sal depth']):
            return "salinity_profile"
        if any(w in q for w in ['t-s diagram', 'ts diagram', 'temperature salinity', 'temp sal']):
            return "ts_diagram"
        if any(w in q for w in ['trajectory', 'path', 'track', 'movement', 'drift']):
            return "trajectory"
        if any(w in q for w in ['depth time', 'time series', 'temporal', 'over time']):
            return "depth_time"
        if any(w in q for w in ['show', 'plot', 'chart', 'graph', 'visuali', 'display', 'compare']):
            if any(w in q for w in ['temperature', 'temp']):
                return "temperature_profile"
            if any(w in q for w in ['salinity', 'salt']):
                return "salinity_profile"
            if any(w in q for w in ['map', 'location', 'where', 'position', 'near']):
                return "trajectory"
        if any(w in q for w in ['map', 'location', 'where', 'nearest', 'position', 'float near']):
            return "trajectory"
        return ""

    def _call_openai(self, user_message: str, context_str: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"User Question: {user_message}\n\nData Context:\n{context_str}\n\nProvide an accurate, data-backed response."}
        ]
        # Explicit timeout to avoid frontend hanging
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=0.7, max_tokens=1000, timeout=20.0
        )
        return response.choices[0].message.content.strip()

    def _build_ollama_prompt(self, user_message: str, context_str: str) -> str:
        short_context = context_str[:800]
        return f"""You are FloatChat, an oceanographic AI analyzing ARGO float data.

Data Context: {short_context}

Question: {user_message}

Provide a clear, data-backed response in markdown format (2-3 paragraphs)."""

    def _call_ollama(self, user_message: str, context_str: str) -> str:
        prompt = self._build_ollama_prompt(user_message, context_str)
        try:
            r = req_lib.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.ollama_model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0.7, "num_predict": 200}},
                timeout=120
            )
            if r.status_code == 200:
                resp_text = r.json().get('response', '').strip()
                if resp_text:
                    return resp_text
                raise Exception("Ollama returned empty response")
            raise Exception(f"Ollama HTTP {r.status_code}: {r.text[:200]}")
        except req_lib.exceptions.Timeout:
            raise Exception("Ollama timeout - try again.")
        except Exception as e:
            raise e

    def stream_ollama(self, user_message: str, context_data):
        """Generator that yields tokens from Ollama as they arrive (streaming)."""
        rag_context = ""
        if self.rag and self.rag.ready:
            rag_results = self.rag.search(user_message, k=3)
            if rag_results:
                rag_context = "\n\n=== Relevant Float Summaries (from RAG) ===\n"
                for r in rag_results:
                    rag_context += f"- {r['text']} (relevance: {r['score']:.2f})\n"

        chart_type = self._detect_chart_intent(user_message)

        # Retry connection if needed
        if not self.use_ai and self._original_ai_mode == 'ollama' and REQUESTS_AVAILABLE:
            if self._test_ollama():
                self.use_ai = True
                self.ai_mode = 'ollama'

        if not self.use_ai or self.ai_mode != 'ollama':
            fallback = self._generate_fallback_response(user_message, context_data, chart_type)
            yield json.dumps({"token": fallback["reply"], "done": True, "chart_type": chart_type}) + "\n"
            return

        context_str = self._format_context(context_data) + rag_context
        prompt = self._build_ollama_prompt(user_message, context_str)

        try:
            r = req_lib.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.ollama_model, "prompt": prompt, "stream": True,
                      "options": {"temperature": 0.7, "num_predict": 300}},
                timeout=120,
                stream=True
            )
            if r.status_code != 200:
                fallback = self._generate_fallback_response(user_message, context_data, chart_type)
                yield json.dumps({"token": fallback["reply"], "done": True, "chart_type": chart_type}) + "\n"
                return

            for line in r.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        done = chunk.get("done", False)
                        if token:
                            yield json.dumps({"token": token, "done": False, "chart_type": chart_type}) + "\n"
                        if done:
                            yield json.dumps({"token": "", "done": True, "chart_type": chart_type}) + "\n"
                            return
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[ERROR] Ollama stream error: {e}")
            fallback = self._generate_fallback_response(user_message, context_data, chart_type)
            yield json.dumps({"token": fallback["reply"], "done": True, "chart_type": chart_type}) + "\n"

    def _format_context(self, context_data: Dict[str, Any]) -> str:
        parts = []
        stats = context_data.get('stats', {})

        if stats.get('total_records', 0) == 0:
            return "No ARGO data available. Please ingest data first."

        parts.append("=== ARGO Dataset Overview ===")
        parts.append(f"Total Records: {stats.get('total_records', 0):,}")
        parts.append(f"Floats: {', '.join(stats.get('floats', []))}")

        dr = stats.get('date_range', {})
        parts.append(f"Date Range: {dr.get('min', 'N/A')} to {dr.get('max', 'N/A')}")

        temp = stats.get('temperature', {})
        if temp.get('min') is not None:
            parts.append(f"Temperature: {temp['min']} to {temp['max']}°C (avg: {temp.get('avg', 'N/A')}°C)")

        sal = stats.get('salinity', {})
        if sal.get('min') is not None:
            parts.append(f"Salinity: {sal['min']} to {sal['max']} PSU (avg: {sal.get('avg', 'N/A')} PSU)")

        depth = stats.get('depth_range', {})
        if depth.get('min') is not None:
            parts.append(f"Depth: {depth['min']} to {depth['max']} dbar")

        geo = stats.get('geographic_bounds', {})
        lat = geo.get('latitude', {})
        lon = geo.get('longitude', {})
        if lat.get('min') is not None:
            parts.append(f"Area: Lat {lat['min']}° to {lat['max']}°, Lon {lon['min']}° to {lon['max']}°")

        # Float summaries
        floats = context_data.get('floats', [])
        if floats:
            parts.append(f"\n=== Active Floats ({len(floats)}) ===")
            for f in floats[:10]:
                parts.append(f"• {f['wmo_id']} — {f.get('ocean_region', 'Indian Ocean')} "
                           f"({f.get('latitude', '?')}°N, {f.get('longitude', '?')}°E)")

        # Sample data
        samples = context_data.get('sample_data', [])[:8]
        if samples:
            parts.append("\n=== Sample Measurements ===")
            for s in samples:
                parts.append(f"  [{s.get('platform')}] Depth: {s.get('depth')} dbar, "
                           f"Temp: {s.get('temperature')}°C, Sal: {s.get('salinity')} PSU")

        return "\n".join(parts)

    def _generate_fallback_response(self, user_message: str, context_data: Dict[str, Any],
                                     chart_type: str = "") -> Dict[str, Any]:
        stats = context_data.get('stats', {})

        if stats.get('total_records', 0) == 0:
            return {"reply": "No data loaded yet. Run `python fetch_argovis.py` to ingest ARGO data.", "chart_type": ""}

        q = user_message.lower()
        floats_info = context_data.get('floats', [])
        float_list_str = ", ".join([f.get('wmo_id', '?') for f in floats_info[:10]]) if floats_info else ', '.join(stats.get('floats', []))

        if any(w in q for w in ['temperature', 'temp', 'warm', 'cold']):
            temp = stats.get('temperature', {})
            reply = f"""### Temperature Analysis

Based on **{stats.get('total_records', 0):,}** ARGO measurements from **{stats.get('float_count', 0)}** floats:

| Metric | Value |
|--------|-------|
| **Minimum** | {temp.get('min', 'N/A')}°C |
| **Maximum** | {temp.get('max', 'N/A')}°C |
| **Average** | {temp.get('avg', 'N/A')}°C |

**Active Floats:** {float_list_str}

The temperature profile typically shows a warm mixed layer at the surface (~25-30°C), followed by a steep **thermocline** between 100-500m, and cold deep waters (~2-5°C) below 1000m.

*View the Temperature Profile chart in the Dashboard for a visual depth profile.*"""
            return {"reply": reply, "chart_type": chart_type or "temperature_profile"}

        if any(w in q for w in ['salinity', 'salt', 'saline']):
            sal = stats.get('salinity', {})
            reply = f"""### Salinity Analysis

| Metric | Value |
|--------|-------|
| **Minimum** | {sal.get('min', 'N/A')} PSU |
| **Maximum** | {sal.get('max', 'N/A')} PSU |
| **Average** | {sal.get('avg', 'N/A')} PSU |

Typical Indian Ocean salinity is **34-36 PSU**. The Arabian Sea tends to have higher salinity due to excess evaporation, while the Bay of Bengal has lower salinity due to monsoon freshwater input.

*View the Salinity Profile chart for depth-wise distribution.*"""
            return {"reply": reply, "chart_type": chart_type or "salinity_profile"}

        if any(w in q for w in ['depth', 'deep', 'shallow', 'surface', 'profile']):
            depth = stats.get('depth_range', {})
            reply = f"""### Depth Coverage

| Metric | Value |
|--------|-------|
| **Shallowest** | {depth.get('min', 'N/A')} dbar |
| **Deepest** | {depth.get('max', 'N/A')} dbar |

ARGO floats typically profile from the surface to **2000 meters**, ascending while collecting temperature, salinity, and pressure data at each depth level."""
            return {"reply": reply, "chart_type": chart_type or "temperature_profile"}

        if any(w in q for w in ['float', 'location', 'where', 'map', 'nearest', 'position']):
            reply = f"""### ARGO Float Locations

We are tracking **{stats.get('float_count', 0)}** floats across the Indian Ocean:

"""
            for f in floats_info[:10]:
                reply += f"- **{f['wmo_id']}** — {f.get('ocean_region', 'Indian Ocean')} ({f.get('latitude', '?')}°N, {f.get('longitude', '?')}°E)\n"
            reply += "\n*View the interactive Map tab to see all float positions and trajectories.*"
            return {"reply": reply, "chart_type": "trajectory"}

        # Default overview (AI not configured fallback)
        dr = stats.get('date_range', {})
        reply = f"""### 🤖 AI Assistant Not Configured - Basic Data Mode

> ⚡ **Want intelligent AI conversations?** You have **two great options**:
> 
> **🆓 OLLAMA (FREE)**: `curl -fsSL https://ollama.ai/install.sh | sh && ollama pull llama3.2`
> **💳 OPENAI (PAID)**: Add your API key to `.env` file
>
> Both work equally well - choose based on your preference!

**Current dataset**: **{stats.get('total_records', 0):,}** oceanographic measurements from **{stats.get('float_count', 0)}** ARGO floats:

| Parameter | Range |
|-----------|-------|
| **Temperature** | {stats.get('temperature', {}).get('min', '?')} – {stats.get('temperature', {}).get('max', '?')}°C |
| **Salinity** | {stats.get('salinity', {}).get('min', '?')} – {stats.get('salinity', {}).get('max', '?')} PSU |
| **Depth** | {stats.get('depth_range', {}).get('min', '?')} – {stats.get('depth_range', {}).get('max', '?')} dbar |
| **Date Range** | {dr.get('min', '?')[:10] if dr.get('min') else '?'} to {dr.get('max', '?')[:10] if dr.get('max') else '?'} |

**Available in basic mode:**
- "temperature" - Temperature analysis
- "salinity" - Salinity analysis  
- "depth" - Depth coverage
- "location" or "float" - Float locations

**🚀 Run `./setup.sh` to enable full AI conversations!**
"""
        return {"reply": reply, "chart_type": chart_type}
