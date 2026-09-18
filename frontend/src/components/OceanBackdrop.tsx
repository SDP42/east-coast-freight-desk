/** Decorative, non-interactive backdrop: a faint nautical grid plus a slow
 * radar sweep in the corner — sets the "maritime trading terminal" tone
 * without competing with real content. */
export default function OceanBackdrop() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-navy">
      <svg className="absolute inset-0 h-full w-full opacity-[0.05]" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
            <path d="M 48 0 L 0 0 0 48" fill="none" stroke="#22d3ee" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>

      <div className="absolute -right-40 -top-40 h-96 w-96 rounded-full bg-cyan/10 blur-3xl" />
      <div className="absolute -left-40 bottom-0 h-96 w-96 rounded-full bg-steel/20 blur-3xl" />

      <div className="absolute right-10 top-10 h-40 w-40 opacity-20">
        <div className="absolute inset-0 rounded-full border border-cyan/30" />
        <div className="absolute inset-6 rounded-full border border-cyan/20" />
        <div className="absolute inset-12 rounded-full border border-cyan/10" />
        <div className="absolute inset-0 origin-center animate-radar">
          <div className="absolute left-1/2 top-1/2 h-1/2 w-px origin-top bg-gradient-to-b from-cyan to-transparent" />
        </div>
      </div>
    </div>
  );
}
