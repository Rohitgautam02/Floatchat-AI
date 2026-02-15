import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const API = process.env.REACT_APP_API_URL || "http://localhost:5000";

const REGION_COLORS = {
    "Arabian Sea": "#f59e0b",
    "Bay of Bengal": "#06b6d4",
    "Equatorial Indian Ocean": "#10b981",
    "Southern Indian Ocean": "#8b5cf6",
    "Indian Ocean": "#3b82f6",
    "Unknown": "#94a3b8",
};

function FitBounds({ floats }) {
    const map = useMap();
    useEffect(() => {
        if (floats.length > 0) {
            const lats = floats.map(f => f.latitude).filter(Boolean);
            const lons = floats.map(f => f.longitude).filter(Boolean);
            if (lats.length && lons.length) {
                map.fitBounds([
                    [Math.min(...lats) - 5, Math.min(...lons) - 5],
                    [Math.max(...lats) + 5, Math.max(...lons) + 5],
                ]);
            }
        }
    }, [floats, map]);
    return null;
}

export default function MapView() {
    const [floats, setFloats] = useState([]);
    const [trajectory, setTrajectory] = useState([]);
    const [selectedFloat, setSelectedFloat] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${API}/api/data/floats`)
            .then(r => r.json())
            .then(data => { setFloats(Array.isArray(data) ? data : []); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    const loadTrajectory = async (wmoId) => {
        setSelectedFloat(wmoId);
        try {
            const res = await fetch(`${API}/api/data/floats/${wmoId}/trajectory`);
            const data = await res.json();
            setTrajectory(Array.isArray(data) ? data : []);
        } catch { setTrajectory([]); }
    };

    if (loading) return (
        <div className="page-container"><div className="loading-state"><div className="loading-spinner"></div><p>Loading map data...</p></div></div>
    );

    const trajectoryCoords = trajectory.filter(t => t.latitude && t.longitude).map(t => [t.latitude, t.longitude]);
    const selectedInfo = floats.find(f => f.wmo_id === selectedFloat);

    return (
        <div className="page-container map-page">
            <div className="page-header">
                <h1>ARGO Float Map</h1>
                <p className="page-subtitle">Interactive Indian Ocean observation network</p>
            </div>

            <div className="map-layout">
                {/* Float List Sidebar */}
                <div className="map-sidebar">
                    <h3>Active Floats ({floats.length})</h3>
                    <div className="float-list">
                        {floats.map((f, i) => (
                            <div key={i} className={`float-item ${selectedFloat === f.wmo_id ? "selected" : ""}`}
                                onClick={() => loadTrajectory(f.wmo_id)}>
                                <div className="float-dot" style={{ background: REGION_COLORS[f.ocean_region] || "#3b82f6" }}></div>
                                <div className="float-info">
                                    <div className="float-wmo">{f.wmo_id}</div>
                                    <div className="float-region">{f.ocean_region}</div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Legend */}
                    <div className="map-legend">
                        <h4>Region Legend</h4>
                        {Object.entries(REGION_COLORS).filter(([k]) => k !== "Unknown" && k !== "Indian Ocean").map(([name, color]) => (
                            <div key={name} className="legend-item">
                                <span className="legend-dot" style={{ background: color }}></span>
                                <span className="legend-label">{name}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Map */}
                <div className="map-container">
                    <MapContainer center={[5, 72]} zoom={4}
                        style={{ height: "100%", width: "100%", borderRadius: "12px" }} scrollWheelZoom={true}>
                        <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                            attribution='&copy; <a href="https://carto.com/">CARTO</a>' />
                        <FitBounds floats={floats} />

                        {floats.map((f, i) => f.latitude && f.longitude ? (
                            <CircleMarker key={i} center={[f.latitude, f.longitude]}
                                radius={selectedFloat === f.wmo_id ? 10 : 7}
                                pathOptions={{
                                    color: REGION_COLORS[f.ocean_region] || "#3b82f6",
                                    fillColor: REGION_COLORS[f.ocean_region] || "#3b82f6",
                                    fillOpacity: 0.8,
                                    weight: selectedFloat === f.wmo_id ? 3 : 1,
                                }}
                                eventHandlers={{ click: () => loadTrajectory(f.wmo_id) }}>
                                <Popup>
                                    <div style={{ color: "#1e293b", minWidth: 180, fontSize: 13 }}>
                                        <strong>Float {f.wmo_id}</strong><br />
                                        Region: {f.ocean_region}<br />
                                        Position: {f.latitude?.toFixed(2)}°N, {f.longitude?.toFixed(2)}°E<br />
                                        Profiles: {f.num_profiles || f.num_records || "—"}<br />
                                        Status: {f.status}
                                    </div>
                                </Popup>
                            </CircleMarker>
                        ) : null)}

                        {trajectoryCoords.length > 1 && (
                            <Polyline positions={trajectoryCoords}
                                pathOptions={{ color: "#f59e0b", weight: 2.5, opacity: 0.8, dashArray: "5,8" }} />
                        )}
                    </MapContainer>
                </div>
            </div>

            {/* Trajectory Info */}
            {selectedFloat && trajectory.length > 0 && (
                <div className="trajectory-info">
                    <h3>Float {selectedFloat} Trajectory — {trajectory.length} positions
                        {selectedInfo ? ` — ${selectedInfo.ocean_region}` : ""}</h3>
                    <div className="trajectory-timeline">
                        {trajectory.slice(0, 20).map((t, i) => (
                            <div key={i} className="traj-point">
                                <span className="traj-cycle">Cycle {t.cycle_number || i + 1}</span>
                                <span className="traj-pos">{t.latitude?.toFixed(2)}°N, {t.longitude?.toFixed(2)}°E</span>
                                <span className="traj-date">{t.time?.slice(0, 10)}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
