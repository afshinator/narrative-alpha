import { HashRouter, Routes, Route, NavLink } from "react-router-dom";
import { EventPage } from "./EventPage";
import { SettingsPage } from "./SettingsPage";
import { FontSizeControl } from "./FontSizeControl";

export function App() {
  return (
    <HashRouter>
      <div className="app">
        <header className="app-header">
          <NavLink to="/" className="app-logo">Narrative Alpha</NavLink>
          <nav className="app-nav">
            <NavLink to="/event/EVT-20260528-TECH-SEMI" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
              Dashboard
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
              Settings
            </NavLink>
            <FontSizeControl />
          </nav>
        </header>

        <main className="app-content">
          <Routes>
            <Route path="/" element={<EventPage />} />
            <Route path="/event/:clusterId" element={<EventPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </HashRouter>
  );
}
