import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../../hooks/useAuth';
import { ToastProvider } from '../../components/Toast/ToastContext';
import Login from '../../pages/Login';
import Dashboard from '../../pages/Dashboard';
import Settings from '../../pages/Settings';
import Students from '../../pages/Students';
import Fees from '../../pages/Fees';
import Attendance from '../../pages/Attendance';
import Placements from '../../pages/Placements';
import Results from '../../pages/Results';
import Leaves from '../../pages/Leaves';
import Notices from '../../pages/Notices';
import Feedback from '../../pages/Feedback';

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

// ── Mock API client with ALL exports used by AuthProvider + pages ──
vi.mock('../../api/client', () => {
  const mockToken = 'test-token';
  const mockUser = JSON.stringify({ id: 1, role: 'admin', username: 'admin' });

  // We store in a module-level store so getToken/getUser return what setToken/setUser stored
  let storedToken = mockToken;
  let storedUser = mockUser;

  return {
    // Auth helpers used by useAuth.jsx
    getToken: () => storedToken,
    setToken: (t) => { storedToken = t; },
    getUser: () => storedUser ? JSON.parse(storedUser) : null,
    setUser: (u) => { storedUser = JSON.stringify(u); },
    clearAuth: () => { storedToken = null; storedUser = null; },
    isTokenExpired: () => false,

    // API functions
    login: vi.fn().mockResolvedValue({ access_token: 'new-token', role: 'admin', user_id: 1 }),
    logout: vi.fn().mockResolvedValue({}),
    verifyOtp: vi.fn(),
    fetchDashboardKpis: vi.fn().mockResolvedValue({
      total_students: 150,
      total_fees_expected: 5000000,
      total_fees_collected: 3500000,
      collection_rate: 70,
      at_risk_count: 12,
      model_version: 'risk_v1',
    }),
    fetchAtRiskStudents: vi.fn().mockResolvedValue({
      students: [
        { student_id: 1, name: 'John Doe', risk_score: 0.85, risk_level: 'High', explanations: [] },
      ],
      count: 1,
    }),
    fetchStudents: vi.fn().mockResolvedValue({
      data: [
        { id: 1, first_name: 'John', last_name: 'Doe', enrollment_no: 'BB10000001', email: 'john@test.edu', course_name: 'CS' },
      ],
      total: 1, page: 1, per_page: 25, total_pages: 1,
    }),
    fetchStudent: vi.fn().mockResolvedValue({
      id: 1, first_name: 'John', last_name: 'Doe', enrollment_no: 'BB10000001',
      email: 'john@test.edu', phone: '1234567890', gender: 'Male',
    }),
    updateStudent: vi.fn(),
    fetchRiskThresholds: vi.fn().mockResolvedValue({
      thresholds: { attendance_risk_threshold: 60, marks_risk_threshold: 40, high_risk_threshold: 0.7, medium_risk_threshold: 0.5, attendance_warning_days: 28 },
    }),
    updateRiskThresholds: vi.fn(),
    fetchFees: vi.fn().mockResolvedValue({
      data: [{ id: 1, student_name: 'John Doe', total_amount: 50000, paid_amount: 30000, balance: 20000, status: 'partial', due_date: '2024-08-01' }],
      total: 1, page: 1, per_page: 25, total_pages: 1,
    }),
    fetchPlacements: vi.fn().mockResolvedValue({
      data: [{ id: 1, student_name: 'Jane Doe', company_name: 'Google', job_title: 'SDE', package_lpa: 15, offer_date: '2025-01-15' }],
      total: 1, page: 1, per_page: 25, total_pages: 1,
    }),
    fetchAttendance: vi.fn().mockResolvedValue({
      data: [{ id: 1, student_id: 1, subject_id: 1, date: '2025-01-15', status: 'present' }],
      total: 1, page: 1, per_page: 30, total_pages: 1,
    }),
    fetchRiskExplanation: vi.fn().mockResolvedValue({
      student_id: 1, name: 'John Doe', risk_score: 0.85, risk_level: 'High',
      model: 'risk_v1', explanations: [{ name: 'attendance_rate_4wk', label: 'Attendance (4wk)', value: 45, importance: 0.3, direction: 'increases' }],
    }),
    // Generic api object for direct use
    api: {
      get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn(),
    },
    apiRequest: vi.fn(),
  };
});

describe('Login Page', () => {
  it('renders login form', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </MemoryRouter>
    );
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('renders login title', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </MemoryRouter>
    );
    expect(screen.getByText(/binary brain/i)).toBeInTheDocument();
  });
});

describe('Dashboard Page', () => {
  it('renders page title', async () => {
    render(<TestWrapper><Dashboard /></TestWrapper>);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('renders tabs', () => {
    render(<TestWrapper><Dashboard /></TestWrapper>);
    expect(screen.getByRole('tab', { name: /overview/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /at-risk/i })).toBeInTheDocument();
  });
});

describe('Settings Page', () => {
  it('renders page title', () => {
    render(<TestWrapper><Settings /></TestWrapper>);
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders theme toggle', () => {
    render(<TestWrapper><Settings /></TestWrapper>);
    expect(screen.getByText('Appearance')).toBeInTheDocument();
    expect(screen.getByText(/light/i)).toBeInTheDocument();
    expect(screen.getByText(/dark/i)).toBeInTheDocument();
  });
});

describe('Students Page', () => {
  it('renders page title', () => {
    render(<TestWrapper><Students /></TestWrapper>);
    expect(screen.getByText('Students')).toBeInTheDocument();
  });

  it('renders search input', () => {
    render(<TestWrapper><Students /></TestWrapper>);
    expect(screen.getByPlaceholderText(/search students/i)).toBeInTheDocument();
  });
});

describe('Fees Page', () => {
  it('renders page title', () => {
    render(<TestWrapper><Fees /></TestWrapper>);
    expect(screen.getByText('Fee Records')).toBeInTheDocument();
  });

  it('renders record payment button for admin', () => {
    render(<TestWrapper><Fees /></TestWrapper>);
    expect(screen.getByText(/record payment/i)).toBeInTheDocument();
  });
});

describe('Attendance Page', () => {
  it('renders page title', () => {
    render(<TestWrapper><Attendance /></TestWrapper>);
    expect(screen.getByText('Attendance')).toBeInTheDocument();
  });

  it('renders mark attendance button for staff', async () => {
    // Set staff role
    localStorage.setItem('bbims_user', JSON.stringify({ id: 2, role: 'staff', username: 'staff' }));
    render(<TestWrapper><Attendance /></TestWrapper>);
    expect(screen.getByText(/mark attendance/i)).toBeInTheDocument();
  });
});

describe('Placements Page', () => {
  it('renders page title', () => {
    render(<TestWrapper><Placements /></TestWrapper>);
    expect(screen.getByText('Placements')).toBeInTheDocument();
  });
});

describe('Results Page', () => {
  beforeEach(() => {
    localStorage.setItem('bbims_token', 'test-token');
    localStorage.setItem('bbims_user', JSON.stringify({ id: 1, role: 'admin', username: 'admin' }));
  });

  it('renders page title', () => {
    render(<TestWrapper><Results /></TestWrapper>);
    expect(screen.getByText('Results')).toBeInTheDocument();
  });
});

describe('Leaves Page', () => {
  beforeEach(() => {
    localStorage.setItem('bbims_token', 'test-token');
    localStorage.setItem('bbims_user', JSON.stringify({ id: 1, role: 'admin', username: 'admin' }));
  });

  it('renders page title', () => {
    render(<TestWrapper><Leaves /></TestWrapper>);
    expect(screen.getByText('Leaves')).toBeInTheDocument();
  });
});

describe('Notices Page', () => {
  beforeEach(() => {
    localStorage.setItem('bbims_token', 'test-token');
    localStorage.setItem('bbims_user', JSON.stringify({ id: 1, role: 'admin', username: 'admin' }));
  });

  it('renders page title', () => {
    render(<TestWrapper><Notices /></TestWrapper>);
    expect(screen.getByText('Notices')).toBeInTheDocument();
  });
});

describe('Feedback Page', () => {
  beforeEach(() => {
    localStorage.setItem('bbims_token', 'test-token');
    localStorage.setItem('bbims_user', JSON.stringify({ id: 1, role: 'admin', username: 'admin' }));
  });

  it('renders page title', () => {
    render(<TestWrapper><Feedback /></TestWrapper>);
    expect(screen.getByText('Feedback')).toBeInTheDocument();
  });
});
