import React from "react";
import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
    { to: "/", label: "Dashboard" },
    { to: "/map", label: "Map" },
    { to: "/explore", label: "Explorer" },
    { to: "/chat", label: "Chat" },
];

export default function Navbar() {
    return (
        <nav className="navbar">
            <div className="navbar-brand">
                <div className="brand-logo">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="url(#grad)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <defs><linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#06b6d4" /><stop offset="100%" stopColor="#3b82f6" /></linearGradient></defs>
                        <path d="M2 12c2-3 4-3 6 0s4 3 6 0 4-3 6 0" />
                        <path d="M2 18c2-3 4-3 6 0s4 3 6 0 4-3 6 0" opacity=".5" />
                        <path d="M2 6c2-3 4-3 6 0s4 3 6 0 4-3 6 0" opacity=".5" />
                    </svg>
                </div>
                <span className="brand-text">FloatChat</span>
                <span className="brand-badge">AI</span>
            </div>
            <div className="navbar-links">
                {NAV_ITEMS.map((item) => (
                    <NavLink
                        key={item.to}
                        to={item.to}
                        end={item.to === "/"}
                        className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
                    >
                        {item.label}
                    </NavLink>
                ))}
            </div>
            <div className="navbar-right">
                <span className="status-dot"></span>
                <span className="status-text">ARGO Live</span>
            </div>
        </nav>
    );
}
