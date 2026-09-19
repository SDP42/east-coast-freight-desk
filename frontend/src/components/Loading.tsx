import LatticeLoaderRaw from "./rb/LatticeLoader";

const LatticeLoader = LatticeLoaderRaw as unknown as React.ComponentType<Record<string, unknown>>;

/** App-wide loading and "thinking" indicator (React Bits LatticeLoader) in the brand colour. */
export default function Loading({ label = "Loading", pattern = "orbit", block = false, timer = true, grid }: { label?: string; pattern?: string; block?: boolean; timer?: boolean; grid?: number }) {
  const g = grid ?? (["sweep", "spin", "rain", "pulse"].includes(pattern) ? 4 : 3);
  const el = <LatticeLoader label={label} pattern={pattern} grid={g} color="#0e7490" cellSize={7} gap={2} fontSize={14} showTimer={timer} glow className="text-body" />;
  return block ? <div className="flex min-h-[8rem] items-center justify-center">{el}</div> : el;
}
