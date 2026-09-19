/** Light aurora backdrop: soft drifting colour blobs over a faint chart grid
 * (the Aurora/Blob pattern popularised by reactbits.dev, reimplemented in CSS). */
export default function OceanBackdrop() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-navy">
      <div className="aurora-blob absolute -left-32 -top-32 h-[28rem] w-[28rem] rounded-full bg-sky-300/40" />
      <div className="aurora-blob absolute right-[-8rem] top-1/3 h-[26rem] w-[26rem] rounded-full bg-teal-200/40 [animation-delay:-6s]" />
      <div className="aurora-blob absolute bottom-[-10rem] left-1/3 h-[24rem] w-[24rem] rounded-full bg-amber-100/60 [animation-delay:-12s]" />
      <svg className="absolute inset-0 h-full w-full opacity-[0.35]" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#c9d8e8" strokeWidth="0.6" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>
    </div>
  );
}
