import React, { useEffect, useState, useMemo } from "react";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, BarChart, Bar, Legend,
} from "recharts";

const API = process.env.REACT_APP_API_URL || "http://localhost:5000";

const REGION_COLORS = {
    "Arabian Sea": "#f59e0b",
    "Bay of Bengal": "#06b6d4",
    "Equatorial Indian Ocean": "#10b981",
    "Southern Indian Ocean": "#8b5cf6",
    "Indian Ocean": "#3b82f6",
};
const PALETTE = ["#06b6d4", "#3b82f6", "#8b5cf6", "#f59e0b", "#10b981", "#ec4899", "#f43f5e", "#6366f1"];

const renderPieLabel = ({ name, value, cx, cy, midAngle, outerRadius }) => {
    const RADIAN = Math.PI / 180;
    const radius = outerRadius + 28;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    return (
        <text x={x} y={y} fill="#cbd5e1" fontSize={12} fontWeight={500}
            textAnchor={x > cx ? "start" : "end"} dominantBaseline="central">
            {name} ({value})
        </text>
    );
};

export default function Dashboard() {
    const [stats, setStats] = useState(null);
    const [floats, setFloats] = useState([]);
    const [allRecords, setAllRecords] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            try {
                const [sRes, fRes, tRes] = await Promise.all([
                    fetch(`${API}/api/data/stats`),
                    fetch(`${API}/api/data/floats`),
                    fetch(`${API}/api/data/charts/temp-profile`),
                ]);
                setStats(await sRes.json());
                setFloats(await fRes.json());
                const t = await tRes.json();
                setAllRecords(Array.isArray(t) ? t : []);
            } catch (e) {
                console.error("Dashboard load error:", e);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, []);

    // Build platform → region lookup
    const platformRegionMap = useMemo(() => {
        const map = {};
        floats.forEach(f => { map[f.wmo_id] = f.ocean_region || "Indian Ocean"; });
        return map;
    }, [floats]);

    // Compute Average Profile Lines (bins of 10m)
    const avgProfileData = useMemo(() => {
        if (!allRecords.length) return [];

        const bins = {}; // depth_bin -> { region -> { sum, count } }
        const BIN_SIZE = 10;

        allRecords.forEach(d => {
            if (d.depth == null || d.temperature == null) return;
            const bin = Math.floor(d.depth / BIN_SIZE) * BIN_SIZE;
            if (bin > 2000) return; // Cap at 2000m

            const region = platformRegionMap[d.platform] || "Indian Ocean";

            if (!bins[bin]) bins[bin] = {};
            if (!bins[bin][region]) bins[bin][region] = { sum: 0, count: 0 };

            bins[bin][region].sum += d.temperature;
            bins[bin][region].count += 1;
        });

        // Convert to array
        return Object.keys(bins).sort((a, b) => Number(a) - Number(b)).map(depth => {
            const row = { depth: Number(depth) };
            Object.keys(bins[depth]).forEach(region => {
                row[region] = Number((bins[depth][region].sum / bins[depth][region].count).toFixed(2));
            });
            return row;
        });
    }, [allRecords, platformRegionMap]);

    if (loading) return (
        <div className="page-container"><div className="loading-state"><div className="loading-spinner"></div><p>Loading ocean data...</p></div></div>
    );
    if (!stats || stats.total_records === 0) return (
        <div className="page-container"><div className="empty-state"><h2>No Data Available</h2><p>Run <code>python fetch_argovis.py</code> to ingest ARGO data.</p></div></div>
    );

    // Region distribution
    const regionCounts = {};
    floats.forEach((f) => { regionCounts[f.ocean_region || "Other"] = (regionCounts[f.ocean_region || "Other"] || 0) + 1; });
    const regionData = Object.entries(regionCounts).map(([name, value]) => ({ name, value }));

    // Temperature Histogram
    const tempBuckets = {};
    allRecords.forEach(d => {
        if (d.temperature == null) return;
        const b = Math.floor(d.temperature / 2) * 2; // 2 degree bins
        const label = `${b}\u2013${b + 2}`;
        tempBuckets[label] = (tempBuckets[label] || 0) + 1;
    });
    const tempDistData = Object.entries(tempBuckets)
        .sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]))
        .map(([range, count]) => ({ range: `${range}\u00b0C`, count }));

    return (
        <div className="page-container">
            <div className="page-header">
                <h1>ARGO Ocean Data Dashboard</h1>
                <p className="page-subtitle">
                    Indian Ocean Float Observatory &mdash; Data via{" "}
                    <a href="https://argovis.colorado.edu" target="_blank" rel="noopener noreferrer"
                        style={{ color: "#06b6d4", textDecoration: "underline" }}>Argovis API</a>
                </p>
            </div>

            {/* Stats Cards */}
            <div className="stats-grid">
                <StatCard accent="cyan" value={stats.float_count} label="Verified Floats" />
                <StatCard accent="blue" value={stats.total_records?.toLocaleString()} label="Total Profiles" sub="from Argovis API" />
                <StatCard accent="teal" value={`${stats.surface_temperature?.avg || "\u2014"}\u00b0C`} label="Surface Temp" sub="avg at 0\u201310m depth" />
                <StatCard accent="purple" value={`${stats.surface_salinity?.avg || "\u2014"} PSU`} label="Surface Salinity" sub="avg at 0\u201310m depth" />
                <StatCard accent="indigo" value={`${Math.round(stats.depth_range?.max || 0)}m`} label="Max Depth" />
                <StatCard accent="rose" value={stats.date_range?.max?.slice(0, 10) || "\u2014"} label="Last Profile" sub="most recent observation" />
            </div>

            {/* Charts */}
            <div className="charts-grid">
                {/* Average Temperature Profile Line Chart */}
                <div className="chart-card span-2">
                    <h3 className="chart-title">Average Temperature Profile by Region</h3>
                    <p className="chart-subtitle">
                        Mean temperature at each depth (10m bins). Shows distinct thermal structures for different ocean regions.
                    </p>
                    <ResponsiveContainer width="100%" height={400}>
                        <LineChart data={avgProfileData} layout="vertical" margin={{ top: 20, right: 30, left: 65, bottom: 50 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                            <XAxis type="number" domain={[0, 32]}
                                tick={{ fill: "#cbd5e1", fontSize: 12 }} stroke="rgba(255,255,255,0.12)"
                                tickFormatter={v => `${v}\u00b0C`}
                                label={{ value: "Water Temperature (\u00b0C)", position: "insideBottom", offset: -5, fill: "#94a3b8", fontSize: 13 }} />
                            <YAxis type="number" dataKey="depth" reversed domain={[0, 2000]}
                                tick={{ fill: "#cbd5e1", fontSize: 12 }} stroke="rgba(255,255,255,0.12)" width={55}
                                tickFormatter={v => `${v}m`}
                                label={{ value: "Depth (meters)", angle: -90, position: "insideLeft", offset: 0, fill: "#94a3b8", fontSize: 13 }} />
                            <Tooltip contentStyle={tooltipCs} formatter={fmtTooltip} labelFormatter={v => `Depth: ${v}m`} />
                            <Legend verticalAlign="top" height={36} iconType="plainline"
                                formatter={v => <span style={{ color: "#cbd5e1", fontSize: 13, marginRight: 10 }}>{v}</span>} />

                            {/* Lines for each region present in data */}
                            {Object.keys(REGION_COLORS).map(region => (
                                <Line
                                    key={region}
                                    type="monotone"
                                    dataKey={region}
                                    stroke={REGION_COLORS[region]}
                                    dot={false}
                                    strokeWidth={3}
                                    activeDot={{ r: 6 }}
                                    connectNulls
                                />
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                {/* Pie Chart */}
                <div className="chart-card">
                    <h3 className="chart-title">Floats by Region</h3>
                    <p className="chart-subtitle">Regional distribution of {floats.length} floats</p>
                    <ResponsiveContainer width="100%" height={380}>
                        <PieChart>
                            <Pie data={regionData} cx="50%" cy="45%" outerRadius={75} innerRadius={40}
                                dataKey="value" label={renderPieLabel}
                                labelLine={{ stroke: "#475569", strokeWidth: 1 }} strokeWidth={2} stroke="#0a1628">
                                {regionData.map((entry, i) => (
                                    <Cell key={i} fill={REGION_COLORS[entry.name] || PALETTE[i % PALETTE.length]} />
                                ))}
                            </Pie>
                            <Legend verticalAlign="bottom" height={36} iconSize={10}
                                formatter={v => <span style={{ color: "#94a3b8", fontSize: 11 }}>{v}</span>} />
                            <Tooltip contentStyle={tooltipCs} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                {/* Temperature Distribution */}
                <div className="chart-card">
                    <h3 className="chart-title">Temperature Distribution</h3>
                    <p className="chart-subtitle">Histogram of all temperature readings</p>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={tempDistData} margin={{ top: 10, right: 30, left: 10, bottom: 45 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                            <XAxis dataKey="range" tick={{ fill: "#cbd5e1", fontSize: 10 }} stroke="rgba(255,255,255,0.1)" angle={-45} textAnchor="end" height={60}
                                label={{ value: "Temperature Range (\u00b0C)", position: "insideBottom", offset: -5, fill: "#94a3b8", fontSize: 12 }} />
                            <YAxis tick={{ fill: "#cbd5e1", fontSize: 11 }} stroke="rgba(255,255,255,0.1)" width={45}
                                label={{ value: "Count", angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 12 }} />
                            <Tooltip contentStyle={tooltipCs} formatter={v => [`${v} readings`, "Count"]} />
                            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                {tempDistData.map((_, i) => (
                                    <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* Float Table */}
                <div className="chart-card span-2">
                    <h3 className="chart-title">Active ARGO Floats (Verified Locations)</h3>
                    <p className="chart-subtitle">{floats.length} floats confirmed within Indian Ocean basin</p>
                    <div className="table-wrapper">
                        <table className="data-table">
                            <thead>
                                <tr><th>WMO ID</th><th>Region</th><th>Latitude</th><th>Longitude</th><th>Profiles</th><th>Status</th></tr>
                            </thead>
                            <tbody>
                                {floats.map((f, i) => (
                                    <tr key={i}>
                                        <td className="mono">{f.wmo_id}</td>
                                        <td>{f.ocean_region}</td>
                                        <td>{f.latitude?.toFixed(2)}\u00b0</td>
                                        <td>{f.longitude?.toFixed(2)}\u00b0</td>
                                        <td>{f.num_profiles || f.num_records || "\u2014"}</td>
                                        <td><span className={`status-badge ${f.status}`}>{f.status}</span></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}

function StatCard({ accent, value, label, sub }) {
    return (
        <div className={`stat-card accent-${accent}`}>
            <div className="stat-info">
                <div className="stat-value">{value}</div>
                <div className="stat-label">{label}</div>
                {sub && <div className="stat-sub" style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>{sub}</div>}
            </div>
        </div>
    );
}

const tooltipCs = {
    background: "#1e293b", border: "1px solid rgba(255,255,255,0.15)",
    borderRadius: 10, color: "#e2e8f0", fontSize: 13, padding: "10px 14px",
};

function fmtTooltip(val, name) {
    if (name === "depth") return ""; // Don't show depth twice
    return [`${val}\u00b0C`, name];
}
