import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Generic data-fetching hook with loading, error, and refresh support.
 *
 * @param {Function} fetcher - Async function to call.
 * @param {Array} deps - Dependencies that trigger re-fetch.
 * @param {Object} options
 * @param {boolean} options.immediate - Fetch immediately on mount (default true).
 */
export function useApi(fetcher, deps = [], { immediate = true } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(immediate);
  const mountedRef = useRef(true);

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher(...args);
      if (mountedRef.current) {
        setData(result);
      }
      return result;
    } catch (err) {
      if (mountedRef.current) {
        setError(err);
        setData(null);
      }
      throw err;
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    mountedRef.current = true;
    if (immediate) {
      execute();
    }
    return () => {
      mountedRef.current = false;
    };
  }, [execute, immediate]);

  return { data, error, loading, execute, refresh: execute };
}

/**
 * Paginated data-fetching hook.
 */
export function usePaginatedApi(fetcher, deps = [], { perPage = 25 } = {}) {
  const [page, setPage] = useState(1);
  const [allData, setAllData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchPage = useCallback(async (pageNum) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher({ page: pageNum, per_page: perPage });
      if (result) {
        setAllData(result);
        setPage(pageNum);
      }
      return result;
    } catch (err) {
      setError(err);
      return null;
    } finally {
      setLoading(false);
    }
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchPage(1);
  }, [fetchPage]);

  const goToPage = useCallback((p) => {
    if (p >= 1 && (!allData || p <= allData.total_pages)) {
      fetchPage(p);
    }
  }, [fetchPage, allData]);

  return {
    data: allData?.data || [],
    pagination: allData ? {
      total: allData.total,
      page: allData.page,
      perPage: allData.per_page,
      totalPages: allData.total_pages,
      nextPage: allData.next_page,
      prevPage: allData.prev_page,
    } : null,
    error,
    loading,
    goToPage,
    refresh: () => fetchPage(page),
  };
}
