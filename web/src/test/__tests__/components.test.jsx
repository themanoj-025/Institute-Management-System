import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../../hooks/useAuth';
import { ToastProvider } from '../../components/Toast/ToastContext';
import RiskCard from '../../components/RiskCard';
import { Skeleton, SkeletonCard, SkeletonTable, SkeletonChart } from '../../components/Skeleton/Skeleton';
import ProtectedRoute from '../../components/ProtectedRoute';
import Sidebar from '../../components/Layout/Sidebar';

// ── Mock API client — auth state tracks localStorage ──
vi.mock('../../api/client', () => ({
  getToken: () => localStorage.getItem('bbims_token'),
  setToken: (t) => localStorage.setItem('bbims_token', t),
  getUser: () => {
    try {
      const raw = localStorage.getItem('bbims_user');
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  },
  setUser: (u) => localStorage.setItem('bbims_user', JSON.stringify(u)),
  clearAuth: () => {
    localStorage.removeItem('bbims_token');
    localStorage.removeItem('bbims_user');
  },
  isTokenExpired: () => false,
  login: vi.fn().mockResolvedValue({}),
  logout: vi.fn().mockImplementation(() => {
    localStorage.removeItem('bbims_token');
    localStorage.removeItem('bbims_user');
  }),
  verifyOtp: vi.fn(),
  fetchRiskExplanation: vi.fn().mockResolvedValue({
    student_id: 1, name: 'John Doe', risk_score: 0.85, risk_level: 'High',
    model: 'risk_v1',
    explanations: [{ name: 'attendance_rate_4wk', label: 'Attendance (4wk)', value: 45, importance: 0.3, direction: 'increases' }],
  }),
  fetchDashboardKpis: vi.fn(),
  fetchAtRiskStudents: vi.fn(),
  fetchStudents: vi.fn(),
  fetchStudent: vi.fn(),
  fetchRiskThresholds: vi.fn(),
  updateStudent: vi.fn(),
  updateRiskThresholds: vi.fn(),
  apiRequest: vi.fn(),
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

// ── Wrapper ──
function TestWrapper({ children, initialRoute = '/' }) {
  return (
    <MemoryRouter initialEntries={[initialRoute]}>
      <AuthProvider>
        <ToastProvider>
          {children}
        </ToastProvider>
      </AuthProvider>
    </MemoryRouter>
  );
}

// ── RiskCard Tests ──

describe('RiskCard Component', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('bbims_token', 'test-token');
    localStorage.setItem('bbims_user', JSON.stringify({ id: 1, role: 'admin', username: 'admin' }));
  });

  it('renders student name', () => {
    render(<TestWrapper><RiskCard studentId={1} studentName="John Doe" /></TestWrapper>);
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('renders expand/collapse button', () => {
    render(<TestWrapper><RiskCard studentId={1} studentName="Jane Doe" /></TestWrapper>);
    const toggle = screen.getByRole('button', { expanded: false });
    expect(toggle).toBeInTheDocument();
  });

  it('expands on click and shows explanation', async () => {
    render(<TestWrapper><RiskCard studentId={1} studentName="Test Student" /></TestWrapper>);
    const toggle = screen.getByRole('button', { expanded: false });
    await userEvent.click(toggle);
    await waitFor(() => {
      expect(screen.getByText(/why this student/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });
});

// ── Skeleton Components Tests ──

describe('Skeleton Components', () => {
  it('renders basic skeleton with custom dimensions', () => {
    const { container } = render(<Skeleton width="100px" height="20px" />);
    const skeleton = container.querySelector('.skeleton');
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveStyle({ width: '100px', height: '20px' });
  });

  it('renders rounded skeleton', () => {
    const { container } = render(<Skeleton rounded width="40px" height="40px" />);
    expect(container.querySelector('.skeleton-rounded')).toBeInTheDocument();
  });

  it('renders SkeletonCard', () => {
    const { container } = render(<SkeletonCard />);
    expect(container.querySelector('.skeleton-card')).toBeInTheDocument();
  });

  it('renders SkeletonTable with default rows', () => {
    const { container } = render(<SkeletonTable />);
    expect(container.querySelector('.skeleton-table')).toBeInTheDocument();
  });

  it('renders SkeletonTable with custom rows', () => {
    const { container } = render(<SkeletonTable rows={3} cols={2} />);
    const rows = container.querySelectorAll('.skeleton-table-row');
    expect(rows.length).toBe(3);
  });

  it('renders SkeletonChart', () => {
    const { container } = render(<SkeletonChart />);
    expect(container.querySelector('.skeleton-chart')).toBeInTheDocument();
    expect(container.querySelector('.skeleton-chart-bars')).toBeInTheDocument();
  });
});

// ── ProtectedRoute Tests ──

describe('ProtectedRoute', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('redirects to login when not authenticated', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AuthProvider>
          <ToastProvider>
            <ProtectedRoute>
              <div>Protected Content</div>
            </ProtectedRoute>
          </ToastProvider>
        </AuthProvider>
      </MemoryRouter>
    );
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    localStorage.setItem('bbims_token', 'test-token');
    localStorage.setItem('bbims_user', JSON.stringify({ id: 1, role: 'admin', username: 'admin' }));
    render(
      <MemoryRouter initialEntries={['/']}>
        <AuthProvider>
          <ToastProvider>
            <ProtectedRoute>
              <div>Protected Content</div>
            </ProtectedRoute>
          </ToastProvider>
        </AuthProvider>
      </MemoryRouter>
    );
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });
});

// ── Sidebar Tests ──

describe('Sidebar Component', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('bbims_token', 'test-token');
    localStorage.setItem('bbims_user', JSON.stringify({ id: 1, role: 'admin', username: 'admin' }));
  });

  it('renders navigation links', () => {
    render(<TestWrapper><Sidebar collapsed={false} onToggle={() => {}} onOpenPalette={() => {}} /></TestWrapper>);
    expect(screen.getByText('BB-IMS')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('renders collapsed state', () => {
    render(<TestWrapper><Sidebar collapsed={true} onToggle={() => {}} onOpenPalette={() => {}} /></TestWrapper>);
    expect(screen.getByText('BB')).toBeInTheDocument();
  });

  it('calls onToggle when toggle button is clicked', async () => {
    const onToggle = vi.fn();
    render(<TestWrapper><Sidebar collapsed={false} onToggle={onToggle} onOpenPalette={() => {}} /></TestWrapper>);
    const toggleBtn = screen.getByLabelText(/collapse sidebar/i);
    await userEvent.click(toggleBtn);
    expect(onToggle).toHaveBeenCalledOnce();
  });
});
