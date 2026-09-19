import { Sparkles } from "lucide-react";
import SpotlightCard from "./SpotlightCard";

export default function ComingSoon({ title, section }: { title: string; section: string }) {
  return (
    <SpotlightCard className="border-dashed">
      <div className="p-8 text-center">
        <div className="mx-auto mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-cyan/10 border border-cyan/20">
          <Sparkles className="h-4 w-4 text-cyan" />
        </div>
        <h2 className="text-base font-semibold text-strong">{title}</h2>
        <p className="mt-2 text-sm text-muted">
          This screen will be wired up to the live API in <span className="font-medium text-body">{section}</span>.
          The layout below is a working preview.
        </p>
      </div>
    </SpotlightCard>
  );
}
