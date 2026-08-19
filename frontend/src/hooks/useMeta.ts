import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { Meta } from "../api/types";

// Server capabilities drive the UI, so strategies and labels are never duplicated client side.
export function useMeta() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.meta().then(setMeta).catch((cause: Error) => setError(cause.message));
  }, []);

  return { meta, error };
}
