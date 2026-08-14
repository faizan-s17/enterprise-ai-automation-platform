import { useCallback, useEffect, useState, type DependencyList } from "react";
import { ApiError } from "./api";

/** Runs `fetcher` whenever `deps` change, tracking loading/error/data.
 *
 * Every page needs the same three states around a fetch call. Centralising it
 * here means a page component is the fetch call plus how to render the
 * result, not sixty lines of state plumbing repeated eleven times.
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: DependencyList
): {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
} {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcher()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Something went wrong.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return { data, loading, error, reload };
}
