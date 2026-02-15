import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Dashboard from "./components/Dashboard";
import MapView from "./components/MapView";
import Charts from "./components/Charts";
import ChatPanel from "./components/ChatPanel";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-root">
        <Navbar />
        <div className="app-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/map" element={<MapView />} />
            <Route path="/explore" element={<Charts />} />
            <Route path="/chat" element={<ChatPanel />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
