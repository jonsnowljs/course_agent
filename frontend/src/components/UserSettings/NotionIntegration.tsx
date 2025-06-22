import React, { useEffect, useState, useRef } from 'react';
import {
  getNotionIntegrationStatus,
  disconnectNotionIntegration,
  getNotionOAuthStartUrl,
  startNotionAsyncSync,
  getNotionSyncStatus,
  getNotionSyncHistory,
} from '../../client';
import type { NotionSyncHistoryItem, NotionSyncHistoryResponse } from '../../client/types.gen';

const PAGE_SIZE = 10;
const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'success', label: 'Success' },
  { value: 'error', label: 'Error' },
  { value: 'running', label: 'Running' },
  { value: 'pending', label: 'Pending' },
];

const NotionIntegration: React.FC = () => {
  const [connected, setConnected] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<null | {
    status: string;
    last_sync: string | null;
    error: string | null;
  }>(null);
  const [history, setHistory] = useState<NotionSyncHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [search, setSearch] = useState('');
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await getNotionIntegrationStatus();
      setConnected(res.connected);
    } catch (e) {
      setConnected(false);
    } finally {
      setLoading(false);
    }
  };

  const fetchSyncStatus = async () => {
    try {
      const res = await getNotionSyncStatus();
      setSyncStatus(res);
      if (res.status === 'running' || res.status === 'pending') {
        setSyncing(true);
      } else {
        setSyncing(false);
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        fetchHistory(page, statusFilter, startDate, endDate, search);
      }
    } catch {
      setSyncStatus(null);
    }
  };

  const fetchHistory = async (pageNum = 1, status = '', start = '', end = '', searchText = '') => {
    try {
      const res: NotionSyncHistoryResponse = await getNotionSyncHistory({
        limit: PAGE_SIZE,
        offset: (pageNum - 1) * PAGE_SIZE,
        status: status || undefined,
        start_date: start || undefined,
        end_date: end || undefined,
        search: searchText || undefined,
      });
      setHistory(res.items);
      setTotal(res.total);
    } catch {
      setHistory([]);
      setTotal(0);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchSyncStatus();
    fetchHistory(page, statusFilter, startDate, endDate, search);
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    fetchHistory(page, statusFilter, startDate, endDate, search);
    // eslint-disable-next-line
  }, [page, statusFilter, startDate, endDate, search]);

  useEffect(() => {
    if (syncing && !pollingRef.current) {
      pollingRef.current = setInterval(fetchSyncStatus, 3000);
    }
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [syncing]);

  const handleConnect = () => {
    window.location.href = getNotionOAuthStartUrl();
  };

  const handleDisconnect = async () => {
    setLoading(true);
    setResult(null);
    try {
      await disconnectNotionIntegration();
      setConnected(false);
      setResult('Disconnected from Notion.');
    } catch (e: any) {
      setResult(e?.message || 'Failed to disconnect');
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setResult(null);
    try {
      await startNotionAsyncSync();
      setResult('Sync started! This may take a while.');
      fetchSyncStatus();
    } catch (e: any) {
      setResult(e?.message || 'Sync failed');
      setSyncing(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div>
      <h3>Notion Integration</h3>
      {loading ? (
        <div>Loading...</div>
      ) : connected ? (
        <>
          <div style={{ marginBottom: 8 }}>Notion is <b>connected</b>.</div>
          <button onClick={handleDisconnect} disabled={loading} style={{ marginRight: 8 }}>
            Disconnect Notion
          </button>
          <button onClick={handleSync} disabled={syncing}>
            {syncing ? 'Syncing...' : 'Sync Notion Pages'}
          </button>
          {syncStatus && (
            <div style={{ marginTop: 12 }}>
              <div>Last sync: {syncStatus.last_sync ? new Date(syncStatus.last_sync).toLocaleString() : 'Never'}</div>
              <div>Status: {syncStatus.status}</div>
              {syncStatus.error && <div style={{ color: 'red' }}>Error: {syncStatus.error}</div>}
            </div>
          )}
          <h4 style={{ marginTop: 24 }}>Sync History</h4>
          <div style={{ marginBottom: 8, display: 'flex', gap: 12, alignItems: 'center' }}>
            <label>Status: </label>
            <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}>
              {STATUS_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <label>Start:</label>
            <input type="date" value={startDate} onChange={e => { setStartDate(e.target.value); setPage(1); }} />
            <label>End:</label>
            <input type="date" value={endDate} onChange={e => { setEndDate(e.target.value); setPage(1); }} />
            <label>Search:</label>
            <input type="text" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="Error or status..." />
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 8 }}>
            <thead>
              <tr>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: 4 }}>Start Time</th>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: 4 }}>End Time</th>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: 4 }}>Status</th>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left', padding: 4 }}>Error</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 && (
                <tr>
                  <td colSpan={4} style={{ padding: 4, color: '#888' }}>No sync history.</td>
                </tr>
              )}
              {history.map((h, i) => (
                <tr key={i}>
                  <td style={{ padding: 4 }}>{new Date(h.started_at).toLocaleString()}</td>
                  <td style={{ padding: 4 }}>{h.finished_at ? new Date(h.finished_at).toLocaleString() : '-'}</td>
                  <td style={{ padding: 4 }}>{h.status}</td>
                  <td style={{ padding: 4, color: h.error ? 'red' : undefined }}>{h.error || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 8 }}>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>&lt; Prev</button>
            <span style={{ margin: '0 12px' }}>Page {page} of {totalPages || 1}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages || totalPages === 0}>Next &gt;</button>
          </div>
        </>
      ) : (
        <>
          <div style={{ marginBottom: 8 }}>Notion is <b>not connected</b>.</div>
          <button onClick={handleConnect} disabled={loading}>
            Connect Notion
          </button>
        </>
      )}
      {result && <div style={{ marginTop: 12 }}>{result}</div>}
    </div>
  );
};

export default NotionIntegration; 
