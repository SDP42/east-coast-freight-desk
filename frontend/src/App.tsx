import { Routes, Route, Navigate } from "react-router-dom";
import AppShell from "./components/AppShell";
import Voyage from "./pages/Voyage";
import Signals from "./pages/Signals";
import Ledger from "./pages/Ledger";
import Monitor from "./pages/Monitor";
import Alerts from "./pages/Alerts";
import Explorer from "./pages/Explorer";
import Ask from "./pages/Ask";
import TradeGlobe from "./pages/TradeGlobe";
import RiskLab from "./pages/RiskLab";
import Terrain from "./pages/Terrain";
import ModelLab from "./pages/ModelLab";
import Report from "./pages/Report";
import Access from "./pages/Access";
import Profile from "./pages/Profile";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Overview from "./pages/Overview";
import Markets from "./pages/Markets";
import Forecast from "./pages/Forecast";
import Recommendation from "./pages/Recommendation";
import Ports from "./pages/Ports";
import Risk from "./pages/Risk";
import Financial from "./pages/Financial";
import Scenario from "./pages/Scenario";
import PortMap from "./pages/PortMap";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route path="/app" element={<AppShell />}>
        <Route index element={<Overview />} />
        <Route path="markets" element={<Markets />} />
        <Route path="forecast" element={<Forecast />} />
        <Route path="recommendation" element={<Recommendation />} />
        <Route path="ports" element={<Ports />} />
        <Route path="map" element={<PortMap />} />
        <Route path="risk" element={<Risk />} />
        <Route path="financial" element={<Financial />} />
        <Route path="scenario" element={<Scenario />} />
        <Route path="ask" element={<Ask />} />
        <Route path="voyage" element={<Voyage />} />
        <Route path="signals" element={<Signals />} />
        <Route path="ledger" element={<Ledger />} />
        <Route path="monitor" element={<Monitor />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="explorer" element={<Explorer />} />
        <Route path="profile" element={<Profile />} />
        <Route path="access" element={<Access />} />
        <Route path="globe" element={<TradeGlobe />} />
        <Route path="risklab" element={<RiskLab />} />
        <Route path="terrain" element={<Terrain />} />
        <Route path="lab" element={<ModelLab />} />
        <Route path="report" element={<Report />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
