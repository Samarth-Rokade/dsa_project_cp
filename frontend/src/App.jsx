import { useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import {
  BookOpen, Boxes, FlaskConical, History, LayoutDashboard, Menu, Settings as SettingsIcon, ShieldAlert,
  Siren, X,
} from "lucide-react";
import { BloodDrop } from "./components/ui.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Inventory from "./pages/Inventory.jsx";
import Requests from "./pages/Requests.jsx";
import Dispatches from "./pages/Dispatches.jsx";
import DsaLab from "./pages/DsaLab.jsx";
import About from "./pages/About.jsx";
import Settings from "./pages/Settings.jsx";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/inventory", label: "Blood Inventory", icon: Boxes },
  { to: "/requests", label: "Hospital Requests", icon: Siren },
  { to: "/dispatches", label: "Dispatch History", icon: History },
];
const NAV_LEARN = [
  { to: "/dsa-lab", label: "DSA Lab", icon: FlaskConical },
  { to: "/about", label: "About / DSA Notes", icon: BookOpen },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function App() {
  const [open, setOpen] = useState(false);
  useLocation(); // re-render on navigation

  const link = ({ to, label, icon: Icon, end }) => (
    <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)}>
      <Icon size={19} /> {label}
    </NavLink>
  );

  return (
    <div className="app">
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><BloodDrop size={22} /></div>
          <div>
            <div className="brand-title">Blood Dispatch<br />Engine</div>
          </div>
        </div>
        <nav className="nav" aria-label="Main">
          <div className="nav-label" style={{ paddingTop: 0 }}>Operations</div>
          {NAV.map(link)}
          <div className="nav-label">Learn &amp; configure</div>
          {NAV_LEARN.map(link)}
        </nav>
        <div className="sidebar-note">
          <ShieldAlert size={18} style={{ flexShrink: 0 }} />
          <span>Educational simulation. Synthetic data only. Not for clinical use.</span>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button className="btn icon sm" onClick={() => setOpen(!open)} aria-label="Toggle menu">
            {open ? <X size={18} /> : <Menu size={18} />}
          </button>
          <strong>Blood Dispatch Engine</strong>
        </header>
        <div className="disclaimer-bar" role="note">
          <ShieldAlert size={15} style={{ flexShrink: 0 }} />
          <span>
            <b>Educational DSA project.</b> Allocation uses a simplified teaching compatibility table and is not
            medical advice.
          </span>
        </div>
        <main className="content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/requests" element={<Requests />} />
            <Route path="/dispatches" element={<Dispatches />} />
            <Route path="/dsa-lab" element={<DsaLab />} />
            <Route path="/about" element={<About />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
