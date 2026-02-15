"""
RAG Service — FAISS Vector Store for ARGO Data
Embeds float/profile summaries for semantic search using sentence-transformers.
"""
import os
import json
import numpy as np
from typing import List, Dict, Any

# Try importing FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("[WARN] faiss-cpu not installed. RAG search disabled. Install: pip install faiss-cpu")

# Try importing sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False
    print("[WARN] sentence-transformers not installed. Install: pip install sentence-transformers")

INDEX_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "faiss_index")


class RAGService:
    """Retrieval-Augmented Generation service using FAISS vector search"""

    def __init__(self):
        self.model = None
        self.index = None
        self.documents = []  # parallel list of text summaries
        self.metadata = []   # parallel list of metadata dicts
        self.dimension = 384  # all-MiniLM-L6-v2 embedding dimension
        self.ready = False

        if FAISS_AVAILABLE and SBERT_AVAILABLE:
            try:
                print("[INFO] Loading sentence-transformer model...")
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                print("[OK] RAG model loaded")
                self._load_index()
            except Exception as e:
                print(f"[WARN] Failed to initialize RAG: {e}")
        else:
            print("[WARN] RAG disabled - install faiss-cpu and sentence-transformers")

    def _load_index(self):
        """Load existing FAISS index from disk"""
        index_path = os.path.join(INDEX_DIR, "index.faiss")
        docs_path = os.path.join(INDEX_DIR, "documents.json")

        if os.path.exists(index_path) and os.path.exists(docs_path):
            try:
                self.index = faiss.read_index(index_path)
                with open(docs_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.documents = saved.get("documents", [])
                    self.metadata = saved.get("metadata", [])
                self.ready = True
                print(f"[OK] Loaded FAISS index with {self.index.ntotal} vectors")
            except Exception as e:
                print(f"[WARN] Failed to load index: {e}")
                self.index = None
        else:
            print("[INFO] No existing FAISS index found - build one with build_index()")

    def build_index(self, summaries: List[Dict[str, Any]]):
        """
        Build FAISS index from summaries.

        Args:
            summaries: list of dicts with 'text' and optional metadata keys
        """
        if not self.model or not FAISS_AVAILABLE:
            print("[WARN] Cannot build index: dependencies missing")
            return

        if not summaries:
            print("[WARN] No summaries to index")
            return

        print(f"[INFO] Building FAISS index from {len(summaries)} documents...")

        texts = [s["text"] for s in summaries]
        self.documents = texts
        self.metadata = [{k: v for k, v in s.items() if k != "text"} for s in summaries]

        # Generate embeddings
        embeddings = self.model.encode(texts, show_progress_bar=True)
        embeddings = np.array(embeddings, dtype="float32")

        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)

        # Build index
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner Product after normalization = cosine
        self.index.add(embeddings)

        # Save to disk
        os.makedirs(INDEX_DIR, exist_ok=True)
        faiss.write_index(self.index, os.path.join(INDEX_DIR, "index.faiss"))
        with open(os.path.join(INDEX_DIR, "documents.json"), "w", encoding="utf-8") as f:
            json.dump({"documents": self.documents, "metadata": self.metadata}, f, indent=2, default=str)

        self.ready = True
        print(f"[OK] FAISS index built with {self.index.ntotal} vectors, saved to {INDEX_DIR}")

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the vector store for relevant summaries.

        Args:
            query: natural language search query
            k: number of results to return

        Returns:
            List of dicts with 'text', 'score', and metadata
        """
        if not self.ready or not self.model or not self.index:
            return []

        try:
            query_vec = self.model.encode([query])
            query_vec = np.array(query_vec, dtype="float32")
            faiss.normalize_L2(query_vec)

            k = min(k, self.index.ntotal)
            scores, indices = self.index.search(query_vec, k)

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self.documents):
                    continue
                result = {
                    "text": self.documents[idx],
                    "score": float(score),
                }
                if idx < len(self.metadata):
                    result.update(self.metadata[idx])
                results.append(result)

            return results
        except Exception as e:
            print(f"[WARN] RAG search error: {e}")
            return []

    def add_documents(self, new_summaries: List[Dict[str, Any]]):
        """Add new documents to existing index"""
        if not self.ready:
            self.build_index(new_summaries)
            return

        texts = [s["text"] for s in new_summaries]
        embeddings = self.model.encode(texts)
        embeddings = np.array(embeddings, dtype="float32")
        faiss.normalize_L2(embeddings)

        self.index.add(embeddings)
        self.documents.extend(texts)
        self.metadata.extend([{k: v for k, v in s.items() if k != "text"} for s in new_summaries])

        # Save updated index
        faiss.write_index(self.index, os.path.join(INDEX_DIR, "index.faiss"))
        with open(os.path.join(INDEX_DIR, "documents.json"), "w", encoding="utf-8") as f:
            json.dump({"documents": self.documents, "metadata": self.metadata}, f, indent=2, default=str)

        print(f"[OK] Added {len(new_summaries)} documents. Total: {self.index.ntotal}")
