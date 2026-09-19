import { useEffect, useState } from "react";
import { Newspaper } from "lucide-react";
import SpotlightCard from "./SpotlightCard";
import { api } from "../lib/api";

interface Section { title: string; text: string; figures: { label: string; value: string }[] }

/** Always-on plain-English briefing from the same engines as "Ask the Desk". */
export default function BriefingCard() {
  const [sections, setSections] = useState<Section[] | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => { api.get<{ sections: Section[] }>("/briefing").then((r) => setSections(r.data.sections)).catch(() => setFailed(true)); }, []);
  return (
    <SpotlightCard>
      <div className="p-6">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-strong"><Newspaper className="h-4 w-4 text-cyan" /> Desk briefing</h2>
        {failed && <p className="mt-3 text-sm text-muted">The briefing could not be built right now.</p>}
        {!sections && !failed && <p className="mt-3 text-sm text-muted">Reading the market…</p>}
        {sections && (
          <div className="mt-4 grid gap-5 md:grid-cols-2">
            {sections.map((s) => (
              <div key={s.title}>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-cyan">{s.title}</p>
                <p className="mt-1 text-sm leading-relaxed text-body">{s.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </SpotlightCard>
  );
}
