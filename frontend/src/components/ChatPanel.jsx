import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

const API = process.env.REACT_APP_API_URL || "http://localhost:5000";

const SUGGESTED_QUERIES = [
    "Show me temperature profiles in the Indian Ocean",
    "What is the average salinity across all floats?",
    "Where are the active ARGO floats deployed?",
    "Compare temperature in the Arabian Sea vs Bay of Bengal",
    "Tell me about depth coverage of the observation network",
    "What patterns do you see in the T-S data?",
];

function nowTs() { return Date.now(); }

function makeEmptyChat() {
    return {
        id: `chat_${nowTs()}`,
        title: "New chat",
        messages: [
            {
                id: `b-${nowTs()}`,
                role: "bot",
                text: "Welcome to **FloatChat AI** 🌊 — your intelligent assistant for ARGO ocean observation data!\n\nI help you explore temperature, salinity, depth profiles, float locations, and oceanographic trends from the Indian Ocean.\n\n> 🤖 **Want AI conversations?** Choose your option:\n> **🆓 Ollama (FREE)** - No costs, runs locally  \n> **💳 OpenAI (PAID)** - Cloud AI, ~$0.001/chat\n> \n> Both work great! See README.md for setup.",
                ts: nowTs(),
            },
        ],
        updatedAt: nowTs(),
    };
}

const LS_KEY = "floatchat_chats_v2";

// 120-second timeout for AI requests (Ollama can be slow on first call)
const FETCH_TIMEOUT = 120000;

async function fetchWithTimeout(url, options, timeout = FETCH_TIMEOUT) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
        const res = await fetch(url, { ...options, signal: controller.signal });
        clearTimeout(timer);
        return res;
    } catch (err) {
        clearTimeout(timer);
        throw err;
    }
}

export default function ChatPanel() {
    const [chats, setChats] = useState([]);
    const [activeId, setActiveId] = useState(null);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const endRef = useRef(null);

    useEffect(() => {
        try {
            const raw = localStorage.getItem(LS_KEY);
            const parsed = raw ? JSON.parse(raw) : null;
            if (parsed && Array.isArray(parsed) && parsed.length) {
                setChats(parsed);
                setActiveId(parsed[0].id);
            } else {
                const first = makeEmptyChat();
                setChats([first]);
                setActiveId(first.id);
            }
        } catch {
            const first = makeEmptyChat();
            setChats([first]);
            setActiveId(first.id);
        }
    }, []);

    useEffect(() => {
        localStorage.setItem(LS_KEY, JSON.stringify(chats));
    }, [chats]);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }, [activeId, chats, loading]);

    const activeChat = chats.find((c) => c.id === activeId) || null;

    const updateChat = (id, patchFn) =>
        setChats((prev) => prev.map((c) => (c.id === id ? { ...c, ...patchFn(c) } : c)));

    const createNewChat = () => {
        const chat = makeEmptyChat();
        setChats((prev) => [chat, ...prev]);
        setActiveId(chat.id);
    };

    const deleteChat = (id) => {
        setChats((prev) => {
            const next = prev.filter((c) => c.id !== id);
            if (next.length === 0) {
                const n = makeEmptyChat();
                setActiveId(n.id);
                return [n];
            }
            if (id === activeId) setActiveId(next[0].id);
            return next;
        });
    };

    const sendMessage = async (text) => {
        const trimmed = text.trim();
        if (!trimmed || loading || !activeChat) return;

        const userMsg = { id: `u-${nowTs()}`, role: "user", text: trimmed, ts: nowTs() };
        const waitId = `wait-${nowTs()}`;
        const waitMsg = { id: waitId, role: "bot", text: "", ts: nowTs(), loading: true };

        const chatId = activeChat.id;
        updateChat(chatId, (c) => ({
            messages: [...c.messages, userMsg, waitMsg],
            title: c.title === "New chat" ? trimmed.slice(0, 40) : c.title,
            updatedAt: nowTs(),
        }));
        setInput("");
        setLoading(true);

        try {
            // Use streaming endpoint for real-time token delivery
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT);

            const res = await fetch(`${API}/api/chat/stream`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: trimmed }),
                signal: controller.signal,
            });
            clearTimeout(timer);

            if (!res.ok) {
                // Fallback to non-streaming endpoint
                const res2 = await fetchWithTimeout(`${API}/api/chat`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: trimmed }),
                });
                const data = await res2.json();
                const reply = data.reply || data.message || data.text || JSON.stringify(data);
                updateChat(chatId, (c) => ({
                    messages: c.messages.map((m) =>
                        m.id === waitId ? { ...m, text: reply, ts: nowTs(), loading: false, chart_type: data.chart_type || "" } : m
                    ),
                    updatedAt: nowTs(),
                }));
                return;
            }

            // Read streaming response
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let accumulated = "";
            let chartType = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split("\n").filter(Boolean);

                for (const line of lines) {
                    try {
                        const parsed = JSON.parse(line);
                        if (parsed.chart_type) chartType = parsed.chart_type;
                        if (parsed.token) {
                            accumulated += parsed.token;
                            // Update message in real-time
                            updateChat(chatId, (c) => ({
                                messages: c.messages.map((m) =>
                                    m.id === waitId ? { ...m, text: accumulated, ts: nowTs(), loading: !parsed.done, chart_type: chartType } : m
                                ),
                                updatedAt: nowTs(),
                            }));
                        }
                        if (parsed.done) {
                            updateChat(chatId, (c) => ({
                                messages: c.messages.map((m) =>
                                    m.id === waitId ? { ...m, text: accumulated || "No response received.", ts: nowTs(), loading: false, chart_type: chartType } : m
                                ),
                                updatedAt: nowTs(),
                            }));
                        }
                    } catch (e) {
                        // skip unparseable lines
                    }
                }
            }

            // Ensure loading is cleared
            updateChat(chatId, (c) => ({
                messages: c.messages.map((m) =>
                    m.id === waitId ? { ...m, loading: false } : m
                ),
                updatedAt: nowTs(),
            }));

        } catch (err) {
            const errMsg = err.name === 'AbortError'
                ? "Request timed out. The AI service may be slow or unavailable — please try again."
                : "Failed to connect to server. Make sure the backend is running on port 5000.";
            updateChat(chatId, (c) => ({
                messages: c.messages.map((m) =>
                    m.id === waitId ? { ...m, text: errMsg, loading: false } : m
                ),
                updatedAt: nowTs(),
            }));
        } finally {
            setLoading(false);
        }
    };

    const onKeyDown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage(input);
        }
    };

    return (
        <div className="chat-page">
            {/* Chat Sidebar */}
            <aside className="chat-sidebar">
                <div className="sidebar-header">
                    <button className="new-chat-btn" onClick={createNewChat}>+ New Chat</button>
                </div>
                <div className="chat-list">
                    {chats.map((c) => (
                        <div key={c.id} className={`chat-item ${c.id === activeId ? "active" : ""}`}
                            onClick={() => setActiveId(c.id)}>
                            <div className="chat-item-main">
                                <div className="chat-title">{c.title || "Untitled"}</div>
                                <div className="chat-snippet">{c.messages[c.messages.length - 1]?.text?.slice(0, 50) || ""}</div>
                            </div>
                            <button className="del-btn" onClick={(e) => { e.stopPropagation(); deleteChat(c.id); }}>
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12" /></svg>
                            </button>
                        </div>
                    ))}
                </div>
            </aside>

            {/* Chat Main */}
            <main className="chat-main">
                <section className="chat-window">
                    {/* Suggested Queries */}
                    {activeChat && activeChat.messages.length <= 1 && (
                        <div className="chat-suggestions">
                            <h3>Try asking:</h3>
                            <div className="suggestion-pills">
                                {SUGGESTED_QUERIES.map((q, i) => (
                                    <button key={i} className="suggestion-pill" onClick={() => sendMessage(q)}>{q}</button>
                                ))}
                            </div>
                        </div>
                    )}

                    {activeChat && activeChat.messages.map((m) => (
                        <div key={m.id} className={`message-row ${m.role}`}>
                            <div className="msg-avatar">
                                {m.role === "user" ? (
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <circle cx="12" cy="8" r="4" /><path d="M4 21v-1a6 6 0 0112 0v1" />
                                    </svg>
                                ) : (
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M2 12c2-3 4-3 6 0s4 3 6 0 4-3 6 0" /><path d="M2 17c2-3 4-3 6 0s4 3 6 0 4-3 6 0" opacity=".6" />
                                    </svg>
                                )}
                            </div>
                            <div className="bubble">
                                {m.loading ? (
                                    <div className="typing-indicator"><span></span><span></span><span></span></div>
                                ) : m.role === "bot" ? (
                                    <div className="markdown-body"><ReactMarkdown>{m.text}</ReactMarkdown></div>
                                ) : (
                                    <div className="text">{m.text}</div>
                                )}
                                <div className="meta">{new Date(m.ts).toLocaleTimeString()}</div>
                            </div>
                        </div>
                    ))}
                    <div ref={endRef} />
                </section>

                <footer className="composer">
                    <textarea className="chat-input" placeholder="Ask about ocean data... (Enter to send)"
                        value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKeyDown} rows={1} disabled={loading} />
                    <button className="send-btn" onClick={() => sendMessage(input)} disabled={loading || !input.trim()}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" /></svg>
                    </button>
                </footer>
            </main>
        </div>
    );
}
