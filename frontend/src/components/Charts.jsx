import React, { useEffect, useState, useMemo } from "react";
import {
    ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

const API = process.env.REACT_APP_API_URL || "http://localhost:5000";

const tooltipCs = {
    background: "#1e293b",
    border: "1px solid rgba(255,255,255,0.15)",
    borderRadius: 10,
    color: "#e2e8f0",
    fontSize: 13,
    padding: "10px 14px",
    boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
};

export default function Charts() {
    const [floats, setFloats] = useState([]);
    const [selectedFloat, setSelectedFloat] = useState("");
    const [activeTab, setActiveTab] = useState("temp");
    const [tempData, setTempData] = useState([]);
    const [salData, setSalData] = useState([]);
    const [tsData, setTsData] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetch(`${API}/api/data/floats`)
            .then((r) => r.json())
            .then((data) => {
                const list = Array.isArray(data) ? data : [];
                setFloats(list);
                if (list.length > 0) setSelectedFloat(list[0].wmo_id);
            })
            .catch(console.error);
    }, []);

    useEffect(() => {
        if (!selectedFloat) return;
        setLoading(true);
        const params = `?platform=${selectedFloat}`;
        Promise.all([
            fetch(`${API}/api/data/charts/temp-profile${params}`).then(r => r.json()),
            fetch(`${API}/api/data/charts/sal-profile${params}`).then(r => r.json()),
            fetch(`${API}/api/data/charts/ts-diagram${params}`).then(r => r.json()),
        ])
            .then(([t, s, ts]) => {
                setTempData(Array.isArray(t) ? t : []);
                setSalData(Array.isArray(s) ? s : []);
                setTsData(Array.isArray(ts) ? ts : []);
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [selectedFloat]);

    // Auto-compute domains from data ranges
    const tempDomain = useMemo(() => {
        if (!tempData.length) return { x: [0, 30], y: [0, 2000] };
        const temps = tempData.map(d => d.temperature).filter(v => v != null);
        const depths = tempData.map(d => d.depth).filter(v => v != null);
        return {
            x: [Math.floor(Math.min(...temps) - 1), Math.ceil(Math.max(...temps) + 1)],
            y: [0, Math.ceil(Math.max(...depths) / 100) * 100 + 100],
        };
    }, [tempData]);

    const salDomain = useMemo(() => {
        if (!salData.length) return { x: [33, 37], y: [0, 2000] };
        const sals = salData.map(d => d.salinity).filter(v => v != null);
        const depths = salData.map(d => d.depth).filter(v => v != null);
        return {
            x: [Math.floor(Math.min(...sals) * 10) / 10 - 0.5, Math.ceil(Math.max(...sals) * 10) / 10 + 0.5],
            y: [0, Math.ceil(Math.max(...depths) / 100) * 100 + 100],
        };
    }, [salData]);

    const tsDomain = useMemo(() => {
        if (!tsData.length) return { x: [33, 37], y: [0, 30] };
        const sals = tsData.map(d => d.salinity).filter(v => v != null);
        const temps = tsData.map(d => d.temperature).filter(v => v != null);
        return {
            x: [Math.floor(Math.min(...sals) * 10) / 10 - 0.5, Math.ceil(Math.max(...sals) * 10) / 10 + 0.5],
            y: [Math.floor(Math.min(...temps) - 1), Math.ceil(Math.max(...temps) + 1)],
        };
    }, [tsData]);

    const floatInfo = floats.find(f => f.wmo_id === selectedFloat);
    const floatLabel = floatInfo ? `${selectedFloat} — ${floatInfo.ocean_region}` : selectedFloat;
    const dataCount = activeTab === "temp" ? tempData.length : activeTab === "sal" ? salData.length : tsData.length;

    const TABS = [
        { key: "temp", label: "Temperature Profile" },
        { key: "sal", label: "Salinity Profile" },
        { key: "ts", label: "T-S Diagram" },
    ];

    return (
        <div className="page-container">
            <div className="page-header">
                <h1>Data Explorer</h1>
                <p className="page-subtitle">Analyze ARGO float profiles and ocean properties</p>
            </div>

            {/* Controls */}
            <div className="explorer-controls">
                <div className="control-group">
                    <label>Select Float:</label>
                    <select value={selectedFloat} onChange={e => setSelectedFloat(e.target.value)} className="select-input">
                        {floats.map((f, i) => (
                            <option key={i} value={f.wmo_id}>{f.wmo_id} — {f.ocean_region}</option>
                        ))}
                    </select>
                </div>
                <div className="tab-bar">
                    {TABS.map(tab => (
                        <button key={tab.key} className={`tab-btn ${activeTab === tab.key ? "active" : ""}`}
                            onClick={() => setActiveTab(tab.key)}>{tab.label}</button>
                    ))}
                </div>
            </div>

            {loading ? (
                <div className="loading-state"><div className="loading-spinner"></div><p>Loading profile data...</p></div>
            ) : (
                <div className="chart-display">
                    {/* Temperature */}
                    {activeTab === "temp" && (
                        <div className="chart-card full-width">
                            <h3 className="chart-title">Temperature vs Depth — {floatLabel}</h3>
                            <p className="chart-subtitle">{dataCount} data points · Temperature decreases with depth through the thermocline</p>
                            <ResponsiveContainer width="100%" height={500}>
                                <ScatterChart margin={{ top: 20, right: 40, left: 70, bottom: 50 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                                    <XAxis dataKey="temperature" name="Temperature" type="number" domain={tempDomain.x}
                                        tick={{ fill: "#cbd5e1", fontSize: 12 }} stroke="rgba(255,255,255,0.12)"
                                        tickFormatter={v => `${v}°C`}
                                        label={{ value: "Temperature (°C)", position: "bottom", offset: 28, fill: "#94a3b8", fontSize: 13 }} />
                                    <YAxis dataKey="depth" name="Depth" type="number" reversed domain={tempDomain.y}
                                        tick={{ fill: "#cbd5e1", fontSize: 12 }} stroke="rgba(255,255,255,0.12)" width={60}
                                        tickFormatter={v => `${v}m`}
                                        label={{ value: "Depth (dbar)", angle: -90, position: "insideLeft", offset: -12, fill: "#94a3b8", fontSize: 13 }} />
                                    <Tooltip contentStyle={tooltipCs} formatter={fmtGeneric} />
                                    <Scatter data={tempData} fill="#06b6d4" fillOpacity={0.65} r={4} />
                                </ScatterChart>
                            </ResponsiveContainer>
                        </div>
                    )}

                    {/* Salinity */}
                    {activeTab === "sal" && (
                        <div className="chart-card full-width">
                            <h3 className="chart-title">Salinity vs Depth — {floatLabel}</h3>
                            <p className="chart-subtitle">{dataCount} data points · Salinity structure through the water column</p>
                            <ResponsiveContainer width="100%" height={500}>
                                <ScatterChart margin={{ top: 20, right: 40, left: 70, bottom: 50 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                                    <XAxis dataKey="salinity" name="Salinity" type="number" domain={salDomain.x}
                                        tick={{ fill: "#cbd5e1", fontSize: 12 }} stroke="rgba(255,255,255,0.12)"
                                        tickFormatter={v => `${Number(v).toFixed(1)}`}
                                        label={{ value: "Salinity (PSU)", position: "bottom", offset: 28, fill: "#94a3b8", fontSize: 13 }} />
                                    <YAxis dataKey="depth" name="Depth" type="number" reversed domain={salDomain.y}
                                        tick={{ fill: "#cbd5e1", fontSize: 12 }} stroke="rgba(255,255,255,0.12)" width={60}
                                        tickFormatter={v => `${v}m`}
                                        label={{ value: "Depth (dbar)", angle: -90, position: "insideLeft", offset: -12, fill: "#94a3b8", fontSize: 13 }} />
                                    <Tooltip contentStyle={tooltipCs} formatter={fmtGeneric} />
                                    <Scatter data={salData} fill="#10b981" fillOpacity={0.65} r={4} />
                                </ScatterChart>
                            </ResponsiveContainer>
                        </div>
                    )}

                    {/* T-S Diagram */}
                    {activeTab === "ts" && (
                        <div className="chart-card full-width">
                            <h3 className="chart-title">Temperature-Salinity Diagram — {floatLabel}</h3>
                            <p className="chart-subtitle">{dataCount} data points · Water mass classification and mixing analysis</p>
                            <ResponsiveContainer width="100%" height={500}>
                                <ScatterChart margin={{ top: 20, right: 40, left: 70, bottom: 50 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                                    <XAxis dataKey="salinity" name="Salinity" type="number" domain={tsDomain.x}
                                        tick={{ fill: "#cbd5e1", fontSize: 12 }} stroke="rgba(255,255,255,0.12)"
                                        tickFormatter={v => `${Number(v).toFixed(1)}`}
                                        label={{ value: "Salinity (PSU)", position: "bottom", offset: 28, fill: "#94a3b8", fontSize: 13 }} />
                                    <YAxis dataKey="temperature" name="Temperature" type="number" domain={tsDomain.y}
                                        tick={{ fill: "#cbd5e1", fontSize: 12 }} stroke="rgba(255,255,255,0.12)" width={60}
                                        tickFormatter={v => `${v}°C`}
                                        label={{ value: "Temperature (°C)", angle: -90, position: "insideLeft", offset: -12, fill: "#94a3b8", fontSize: 13 }} />
                                    <Tooltip contentStyle={tooltipCs} formatter={fmtGeneric} />
                                    <Scatter data={tsData} fill="#8b5cf6" fillOpacity={0.55} r={4} />
                                </ScatterChart>
                            </ResponsiveContainer>
                        </div>
                    )}

                    {/* Float summary */}
                    {floatInfo && (
                        <div className="chart-card full-width data-summary-card">
                            <h3 className="chart-title">Float Details — {selectedFloat}</h3>
                            <div className="summary-grid">
                                <div className="summary-item"><span className="summary-label">Region</span><span className="summary-value">{floatInfo.ocean_region}</span></div>
                                <div className="summary-item"><span className="summary-label">Position</span><span className="summary-value">{floatInfo.latitude?.toFixed(3)}°N, {floatInfo.longitude?.toFixed(3)}°E</span></div>
                                <div className="summary-item"><span className="summary-label">Profiles</span><span className="summary-value">{floatInfo.num_profiles || "—"}</span></div>
                                <div className="summary-item"><span className="summary-label">Status</span><span className="summary-value" style={{ color: "#10b981" }}>{floatInfo.status}</span></div>
                                {floatInfo.summary && <div className="summary-item span-full"><span className="summary-label">Summary</span><span className="summary-value">{floatInfo.summary}</span></div>}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function fmtGeneric(val, name) {
    if (name === "Temperature") return [`${val}°C`, "Temperature"];
    if (name === "Depth") return [`${val} dbar`, "Depth"];
    if (name === "Salinity") return [`${val} PSU`, "Salinity"];
    return [val, name];
}
