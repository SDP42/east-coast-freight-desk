import { lazy, Suspense, useEffect, useState } from "react";
import Loading from "../components/Loading";
import SpotlightCard from "../components/SpotlightCard";
import { Note, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import type { TerrainData } from "../components/three/TerrainScene";

const TerrainScene = lazy(() => import("../components/three/TerrainScene"));
interface Data extends TerrainData { method: string }

export default function Terrain() {
  const [d, setD] = useState<Data | null>(null);
  useEffect(() => { api.get<Data>("/lab/terrain").then((r) => setD(r.data)); }, []);
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Market terrain" subtitle="Eight series over seven years as one landscape. Peaks are months when a series was far above its own normal; valleys are troughs. Hover the surface for values; drag to orbit." />
      <SpotlightCard>
        <div className="relative h-[34rem] bg-gradient-to-b from-sky-50 to-white">
          {d ? <Suspense fallback={null}><TerrainScene className="h-full" data={d} /></Suspense> : <div className="flex h-full items-center justify-center"><Loading label="Building the terrain" pattern="sweep" /></div>}
          <div className="pointer-events-none absolute bottom-3 right-3 flex items-center gap-2 rounded-xl border border-border-soft bg-white/90 px-3 py-2 text-[10px] text-body backdrop-blur">
            <span>below normal</span><span className="h-2 w-24 rounded-full" style={{ background: "linear-gradient(90deg,#3b82c4,#e8f1f8,#d97706)" }} /><span>above normal</span>
          </div>
        </div>
      </SpotlightCard>
      {d && <div className="mt-4"><Note>{d.method} Look for ridges that rise together (the Capesize, Panamax, Supramax and Handysize indices co-move), and for series that run against them, such as the dollar index.</Note></div>}
    </div>
  );
}
