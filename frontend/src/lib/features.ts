import { useEffect, useState } from "react";
import { api } from "./api";

// Server feature switches (from /health). Simulated demo feeds are off unless the deployment turns them on.
let cache: { simulated: boolean } | null = null;
export function useFeatures() {
  const [f, setF] = useState(cache ?? { simulated: false });
  useEffect(() => {
    if (cache) return;
    api.get<{ simulated_feeds?: boolean }>("/health").then((r) => { cache = { simulated: !!r.data.simulated_feeds }; setF(cache); }).catch(() => undefined);
  }, []);
  return f;
}
