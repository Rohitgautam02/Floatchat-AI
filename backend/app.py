"""
FloatChat-AI Backend Server
Flask API for ARGO ocean data chatbot with visualization endpoints
"""
import os
import io
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

from services.data_service import DataService
from services.ai_service import AIService
from db.session import SessionLocal
from db.models import Base, ArgoRecord

# Try RAG
try:
    from services.rag_service import RAGService
    rag_service = RAGService()
except Exception as e:
    print(f"[WARN] RAG service unavailable: {e}")
    rag_service = None

load_dotenv()

app = Flask(__name__)
CORS(app)

data_service = DataService()
ai_service = AIService(rag_service=rag_service)


# ─── Health Check ──────────────────────────────────────────────

@app.route('/')
def home():
    """Health check with setup guidance"""
    ai_status = "enabled" if (rag_service and rag_service.ready) else "disabled"
    ai_mode = os.getenv('AI_MODE', 'not_configured')
    
    # Check if data exists
    session = SessionLocal()
    try:
        from sqlalchemy import text
        record_count = session.execute(text("SELECT COUNT(*) FROM argo_records")).scalar() or 0
    except:
        record_count = 0
    finally:
        session.close()
    
    setup_needed = []
    if record_count == 0:
        setup_needed.append("Run 'python fetch_argovis.py' to load ARGO data")
    if ai_mode in ['not_configured', 'ollama'] and not ai_status == "enabled":
        setup_needed.append("Configure AI in .env file (see README.md)")
    
    return jsonify({
        "status": "online",
        "service": "FloatChat-AI API",
        "version": "2.0.0",
        "ai_mode": ai_mode,
        "rag_enabled": rag_service.ready if rag_service else False,
        "data_records": record_count,
        "setup_needed": setup_needed,
        "message": "🌊 FloatChat-AI Running! Visit http://localhost:3000 for the dashboard."
    })


# ─── Chat Endpoint ─────────────────────────────────────────────

@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint — returns structured response with optional chart suggestions"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Missing 'message' field"}), 400

        user_message = data['message'].strip()
        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400

        context_data = data_service.get_relevant_context(user_message)
        ai_response = ai_service.generate_response(user_message, context_data)

        # ai_response is now a dict: {reply, chart_type, ...}
        if isinstance(ai_response, dict):
            return jsonify(ai_response)
        else:
            return jsonify({"reply": ai_response})

    except Exception as e:
        print(f"[ERROR] Chat error: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """Streaming chat endpoint — returns tokens via newline-delimited JSON as they arrive from Ollama"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Missing 'message' field"}), 400

        user_message = data['message'].strip()
        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400

        context_data = data_service.get_relevant_context(user_message)

        return Response(
            ai_service.stream_ollama(user_message, context_data),
            mimetype='application/x-ndjson',
            headers={'X-Accel-Buffering': 'no', 'Cache-Control': 'no-cache'}
        )
    except Exception as e:
        print(f"[ERROR] Stream chat error: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


# ─── Dataset Stats ─────────────────────────────────────────────

@app.route('/api/data/stats', methods=['GET'])
def get_stats():
    try:
        return jsonify(data_service.get_dataset_stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Float Endpoints ───────────────────────────────────────────

@app.route('/api/data/floats', methods=['GET'])
def get_floats():
    """Get all float metadata + positions for the map"""
    try:
        return jsonify(data_service.get_all_floats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/data/floats/<wmo_id>', methods=['GET'])
def get_float_detail(wmo_id):
    """Get detailed info for a specific float"""
    try:
        return jsonify(data_service.get_float_detail(wmo_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/data/floats/<wmo_id>/trajectory', methods=['GET'])
def get_float_trajectory(wmo_id):
    """Get trajectory for a float"""
    try:
        return jsonify(data_service.get_float_trajectory(wmo_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Chart Data Endpoints ──────────────────────────────────────

@app.route('/api/data/charts/temp-profile', methods=['GET'])
def chart_temp_profile():
    """Temperature vs depth profile"""
    platform = request.args.get('platform')
    cycle = request.args.get('cycle', type=int)
    try:
        return jsonify(data_service.get_temperature_profile(platform, cycle))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/data/charts/sal-profile', methods=['GET'])
def chart_sal_profile():
    """Salinity vs depth profile"""
    platform = request.args.get('platform')
    cycle = request.args.get('cycle', type=int)
    try:
        return jsonify(data_service.get_salinity_profile(platform, cycle))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/data/charts/ts-diagram', methods=['GET'])
def chart_ts_diagram():
    """Temperature-Salinity diagram"""
    platform = request.args.get('platform')
    try:
        return jsonify(data_service.get_ts_diagram(platform))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/data/charts/depth-time', methods=['GET'])
def chart_depth_time():
    """Depth-time section for a float"""
    platform = request.args.get('platform')
    if not platform:
        return jsonify({"error": "platform parameter required"}), 400
    try:
        return jsonify(data_service.get_depth_time_data(platform))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Data Query & Export ───────────────────────────────────────

@app.route('/api/data/query', methods=['POST'])
def query_data():
    try:
        filters = request.get_json() or {}
        return jsonify({"data": data_service.query_records(filters)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/data/export', methods=['POST'])
def export_data():
    """Export data as CSV"""
    try:
        filters = request.get_json() or {}
        csv_str = data_service.export_data(filters, format="csv")
        if not csv_str:
            return jsonify({"error": "No data matching filters"}), 404
        return Response(
            csv_str,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=argo_export.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Error Handlers ────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


def _auto_build_rag():
    """Auto-build RAG index from existing float data if model loaded but no index."""
    if not rag_service or rag_service.ready or not rag_service.model:
        return
    try:
        session = SessionLocal()
        from db.models import FloatMetadata
        floats = session.query(FloatMetadata).all()

        summaries = []
        if floats:
            for f in floats:
                text = f.summary or f"Float {f.wmo_id} in {f.ocean_region or 'Indian Ocean'}"
                summaries.append({"text": text, "wmo_id": f.wmo_id, "region": f.ocean_region})
        else:
            # Build from ArgoRecord if no metadata table
            from sqlalchemy import func, distinct
            platforms = session.query(
                ArgoRecord.platform,
                func.avg(ArgoRecord.latitude).label("lat"),
                func.avg(ArgoRecord.longitude).label("lon"),
                func.count(ArgoRecord.id).label("cnt"),
                func.avg(ArgoRecord.temperature).label("avg_temp"),
                func.avg(ArgoRecord.salinity).label("avg_sal"),
            ).group_by(ArgoRecord.platform).all()

            for p in platforms:
                if not p.platform:
                    continue
                text = (f"ARGO float {p.platform} located near {p.lat:.1f}N, {p.lon:.1f}E "
                        f"with {p.cnt} measurements. Average temperature: {p.avg_temp:.1f}C, "
                        f"average salinity: {p.avg_sal:.1f} PSU.")
                summaries.append({"text": text, "wmo_id": p.platform})

        session.close()

        if summaries:
            print(f"[FloatChat-AI] Auto-building RAG index from {len(summaries)} float summaries...")
            rag_service.build_index(summaries)
            print(f"[FloatChat-AI] RAG index built successfully")
    except Exception as e:
        print(f"[WARN] Auto-build RAG failed: {e}")


if __name__ == '__main__':
    from db.session import engine
    Base.metadata.create_all(bind=engine)

    # Auto-build RAG index if model loaded but no index exists
    _auto_build_rag()

    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    ai_mode = os.getenv('AI_MODE', 'not_configured')
    rag_status = 'enabled' if (rag_service and rag_service.ready) else 'disabled'
    
    print("=" * 60)
    print("🌊 FloatChat-AI Backend v2.0")
    print("=" * 60)
    print(f"🚀 Server: http://{host}:{port}")
    print(f"🌐 Frontend: http://localhost:3000 (if running)")
    print(f"🤖 AI Mode: {ai_mode}")
    print(f"📊 RAG: {rag_status}")
    
    # Check data status
    session = SessionLocal()
    try:
        from sqlalchemy import text
        record_count = session.execute(text("SELECT COUNT(*) FROM argo_records")).scalar() or 0
        if record_count > 0:
            print(f"🌊 ARGO Data: {record_count:,} records loaded")
        else:
            print("⚠️  No ARGO data found. Run: python fetch_argovis.py")
    except:
        print("⚠️  Database not initialized. Will auto-create.")
    finally:
        session.close()
        
    # AI setup guidance
    if ai_mode == 'not_configured' or rag_status == 'disabled':
        print("\n🤖 Enable AI Conversations - Choose Your Option:")
        print("   🆓 OLLAMA (FREE): ollama pull llama3.2 && ollama serve")
        print("   💳 OPENAI (PAID): Add API key to .env file")
        print("   📚 Setup Guide: See README.md or run ./setup.sh")
        print("   💡 Both options work equally well!")
        
    print("=" * 60)
    
    app.run(host=host, port=port, debug=debug)
