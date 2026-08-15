import { useState } from 'react';
import { usePaginatedApi } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/Toast/ToastContext';
import { fetchFees, recordPayment } from '../api/client';
import { SkeletonTable } from '../components/Skeleton/Skeleton';

function StatusBadge({ status }) {
  const cls = status === 'paid' ? 'risk-badge-low'
    : status === 'partial' ? 'risk-badge-medium'
    : 'risk-badge-high';
  return <span className={`risk-badge ${cls}`}>{status}</span>;
}

function PaymentModal({ onClose, onSuccess }) {
  const [feeId, setFeeId] = useState('');
  const [amount, setAmount] = useState('');
  const [mode, setMode] = useState('Cash');
  const [transactionId, setTransactionId] = useState('');
  const [saving, setSaving] = useState(false);
  const { addToast } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!feeId || !amount) {
      addToast('Fee ID and amount are required', 'error');
      return;
    }
    setSaving(true);
    try {
      await recordPayment({
        fee_id: parseInt(feeId),
        amount: parseFloat(amount),
        mode,
        transaction_id: transactionId || undefined,
      });
      addToast('Payment recorded successfully', 'success');
      onSuccess();
    } catch (err) {
      addToast(err.message || 'Failed to record payment', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="command-palette-overlay" onClick={onClose}>
      <div className="command-palette" style={{ maxHeight: '80vh' }} onClick={(e) => e.stopPropagation()}>
        <div className="command-palette-input-wrapper" style={{ borderBottom: '1px solid var(--border-primary)' }}>
          <h3 style={{ margin: 0, fontSize: 'var(--text-base)', fontWeight: 'var(--font-semibold)' }}>
            Record Payment
          </h3>
        </div>
        <form onSubmit={handleSubmit} style={{ padding: 'var(--space-4)', overflowY: 'auto' }}>
          <div className="form-group">
            <label className="form-label">Fee ID</label>
            <input className="form-input" type="number" value={feeId} onChange={(e) => setFeeId(e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Amount (₹)</label>
            <input className="form-input" type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Payment Mode</label>
            <select className="form-input" value={mode} onChange={(e) => setMode(e.target.value)}>
              <option>Cash</option>
              <option>Bank Transfer</option>
              <option>Cheque</option>
              <option>UPI</option>
              <option>Card</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Transaction ID (optional)</label>
            <input className="form-input" value={transactionId} onChange={(e) => setTransactionId(e.target.value)} />
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end', marginTop: 'var(--space-4)' }}>
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Recording…' : 'Record Payment'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function Fees() {
  const { isAdmin } = useAuth();
  const { data: fees, pagination, loading, error, refresh, goToPage } = usePaginatedApi(
    (params) => fetchFees({ ...params, per_page: 25 }),
    [],
    { perPage: 25 }
  );
  const [showPaymentModal, setShowPaymentModal] = useState(false);

  return (
    <div className="fees-page">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2 className="page-title">Fee Records</h2>
            <p className="page-subtitle">
              {pagination ? `${pagination.total} total records` : 'Manage fee payments'}
            </p>
          </div>
          {isAdmin && (
            <button className="btn btn-primary" onClick={() => setShowPaymentModal(true)}>
              + Record Payment
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          {error.message}
          <button className="error-retry" onClick={refresh}>Retry</button>
        </div>
      )}

      {loading ? (
        <SkeletonTable rows={8} cols={5} />
      ) : fees.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">💰</div>
          <h3>No fee records found</h3>
          <p>Fee records will appear once students are enrolled and fees are created.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table" role="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Student</th>
                <th>Total (₹)</th>
                <th>Paid (₹)</th>
                <th>Balance (₹)</th>
                <th>Status</th>
                <th>Due Date</th>
              </tr>
            </thead>
            <tbody>
              {fees.map((fee) => (
                <tr key={fee.id}>
                  <td className="cell-mono">{fee.id}</td>
                  <td className="cell-primary">{fee.student_name}</td>
                  <td>{fee.total_amount?.toLocaleString()}</td>
                  <td>{fee.paid_amount?.toLocaleString()}</td>
                  <td className="cell-mono">{fee.balance?.toLocaleString()}</td>
                  <td><StatusBadge status={fee.status} /></td>
                  <td className="cell-secondary">{fee.due_date || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {pagination && pagination.totalPages > 1 && (
            <div className="pagination">
              <button className="btn btn-ghost btn-sm" disabled={!pagination.prevPage} onClick={() => goToPage(pagination.prevPage)}>
                ← Previous
              </button>
              <span className="pagination-info">Page {pagination.page} of {pagination.totalPages}</span>
              <button className="btn btn-ghost btn-sm" disabled={!pagination.nextPage} onClick={() => goToPage(pagination.nextPage)}>
                Next →
              </button>
            </div>
          )}
        </div>
      )}

      {showPaymentModal && (
        <PaymentModal
          onClose={() => setShowPaymentModal(false)}
          onSuccess={() => {
            setShowPaymentModal(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}
