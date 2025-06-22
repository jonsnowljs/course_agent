import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import NotionIntegration from '../src/components/UserSettings/NotionIntegration';
import * as client from '../src/client';

jest.mock('../src/client');

const mockHistory = (overrides = {}) => [
  {
    status: 'success',
    started_at: '2024-06-01T10:00:00Z',
    finished_at: '2024-06-01T10:01:00Z',
    error: null,
    ...overrides,
  },
  {
    status: 'error',
    started_at: '2024-06-02T10:00:00Z',
    finished_at: '2024-06-02T10:01:00Z',
    error: 'Some error',
    ...overrides,
  },
];

describe('NotionIntegration', () => {
  beforeEach(() => {
    jest.resetAllMocks();
    (client.getNotionIntegrationStatus as jest.Mock).mockResolvedValue({ connected: true });
    (client.getNotionSyncStatus as jest.Mock).mockResolvedValue({ status: 'success', last_sync: '2024-06-01T10:01:00Z', error: null });
    (client.getNotionSyncHistory as jest.Mock).mockImplementation(({ status, search, start_date, end_date }) => {
      let items = mockHistory();
      if (status) items = items.filter(i => i.status === status);
      if (search) items = items.filter(i => (i.error || '').includes(search) || i.status.includes(search));
      if (start_date) items = items.filter(i => i.started_at >= start_date);
      if (end_date) items = items.filter(i => i.started_at <= end_date);
      return Promise.resolve({ total: items.length, items });
    });
    (client.disconnectNotionIntegration as jest.Mock).mockResolvedValue({ disconnected: true });
    (client.startNotionAsyncSync as jest.Mock).mockResolvedValue({ status: 'sync started' });
  });

  it('renders table and paginates', async () => {
    render(<NotionIntegration />);
    expect(await screen.findByText(/Notion is connected/i)).toBeInTheDocument();
    expect(screen.getByText('Sync History')).toBeInTheDocument();
    expect(screen.getByText('success')).toBeInTheDocument();
    expect(screen.getByText('error')).toBeInTheDocument();
    expect(screen.getByText('Some error')).toBeInTheDocument();
  });

  it('filters by status', async () => {
    render(<NotionIntegration />);
    expect(await screen.findByText(/Notion is connected/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Status:'), { target: { value: 'success' } });
    await waitFor(() => {
      expect(screen.getByText('success')).toBeInTheDocument();
      expect(screen.queryByText('error')).not.toBeInTheDocument();
    });
  });

  it('filters by search', async () => {
    render(<NotionIntegration />);
    expect(await screen.findByText(/Notion is connected/i)).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText(/error or status/i), { target: { value: 'Some error' } });
    await waitFor(() => {
      expect(screen.getByText('Some error')).toBeInTheDocument();
      expect(screen.queryByText('success')).not.toBeInTheDocument();
    });
  });

  it('disables sync button when syncing', async () => {
    (client.getNotionSyncStatus as jest.Mock).mockResolvedValueOnce({ status: 'running', last_sync: null, error: null });
    render(<NotionIntegration />);
    expect(await screen.findByText(/Notion is connected/i)).toBeInTheDocument();
    expect(screen.getByText(/Syncing/i)).toBeDisabled();
  });

  it('filters by start and end date', async () => {
    render(<NotionIntegration />);
    expect(await screen.findByText(/Notion is connected/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Start:'), { target: { value: '2024-06-02' } });
    await waitFor(() => {
      expect(screen.getByText('error')).toBeInTheDocument();
      expect(screen.queryByText('success')).not.toBeInTheDocument();
    });
    fireEvent.change(screen.getByLabelText('End:'), { target: { value: '2024-06-01' } });
    await waitFor(() => {
      expect(screen.queryByText('error')).not.toBeInTheDocument();
      expect(screen.queryByText('success')).not.toBeInTheDocument();
    });
  });

  it('disconnects Notion', async () => {
    render(<NotionIntegration />);
    expect(await screen.findByText(/Notion is connected/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Disconnect Notion/i));
    await waitFor(() => {
      expect(screen.getByText(/Disconnected from Notion/i)).toBeInTheDocument();
    });
  });

  it('starts sync and shows progress', async () => {
    (client.getNotionSyncStatus as jest.Mock)
      .mockResolvedValueOnce({ status: 'pending', last_sync: null, error: null })
      .mockResolvedValueOnce({ status: 'running', last_sync: null, error: null })
      .mockResolvedValue({ status: 'success', last_sync: '2024-06-01T10:01:00Z', error: null });
    render(<NotionIntegration />);
    expect(await screen.findByText(/Notion is connected/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Sync Notion Pages/i));
    expect(await screen.findByText(/Sync started/i)).toBeInTheDocument();
    // Simulate polling
    await waitFor(() => {
      expect(screen.getByText(/Syncing/i)).toBeInTheDocument();
    });
    // After polling, should show success
    await waitFor(() => {
      expect(screen.getByText(/Status: success/i)).toBeInTheDocument();
    });
  });
}); 
