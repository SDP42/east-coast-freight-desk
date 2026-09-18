import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import TickerTape from "./components/TickerTape";
import OceanBackdrop from "./components/OceanBackdrop";
import Overview from "./pages/Overview";
import Forecast from "./pages/Forecast";
import Recommendation from "./pages/Recommendation";
import Ports from "./pages/Ports";
import Risk from "./pages/Risk";
import Financial from "./pages/Financial";
import Scenario from "./pages/Scenario";

export default function App() {
  return (
    <div className="flex min-h-screen text-slate-100">
      <OceanBackdrop />
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TickerTape />
        <main className="flex-1 p-8 overflow-x-hidden">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="/recommendation" element={<Recommendation />} />
            <Route path="/ports" element={<Ports />} />
            <Route path="/risk" element={<Risk />} />
            <Route path="/financial" element={<Financial />} />
            <Route path="/scenario" element={<Scenario />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
