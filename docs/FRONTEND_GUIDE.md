# Defense PM Tool - Frontend Development Guide

> **Version**: 1.2.0
> **Last Updated**: March 2026
> **Framework**: React 19 + TypeScript + TailwindCSS

This guide covers frontend development standards, patterns, and best practices for the Defense PM Tool.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Project Structure](#project-structure)
3. [Coding Standards](#coding-standards)
4. [Component Patterns](#component-patterns)
5. [State Management](#state-management)
6. [API Integration](#api-integration)
7. [Testing](#testing)
8. [Styling with Tailwind](#styling-with-tailwind)
9. [Performance](#performance)
10. [Accessibility](#accessibility)

---

## Quick Start

### Prerequisites

- Node.js 20 LTS
- npm 10+
- VS Code (recommended)

### Setup

```bash
cd web
npm install
npm run dev
```

### Available Scripts

```bash
npm run dev          # Start development server (port 5173)
npm run build        # Production build
npm run preview      # Preview production build
npm run lint         # Run ESLint
npm run lint:fix     # Fix linting issues
npm run type-check   # TypeScript type checking
npm run test         # Run tests with Vitest
npm run test:ui      # Run tests with UI
npm run test:coverage # Run tests with coverage
```

---

## Project Structure

```
web/
├── src/
│   ├── api/                    # API client and endpoints
│   │   ├── client.ts           # Axios instance configuration
│   │   ├── programs.ts         # Program-related API calls
│   │   ├── activities.ts       # Activity-related API calls
│   │   └── ...
│   │
│   ├── components/             # Reusable UI components
│   │   ├── common/             # Generic components
│   │   │   ├── Button/
│   │   │   ├── Modal/
│   │   │   ├── Table/
│   │   │   └── ...
│   │   ├── program/            # Program-specific components
│   │   ├── activity/           # Activity-specific components
│   │   ├── gantt/              # Gantt chart components
│   │   ├── evms/               # EVMS dashboard components
│   │   └── resource/           # Resource management components
│   │
│   ├── hooks/                  # Custom React hooks
│   │   ├── usePrograms.ts
│   │   ├── useActivities.ts
│   │   ├── useAuth.ts
│   │   └── ...
│   │
│   ├── pages/                  # Page components (routes)
│   │   ├── Dashboard.tsx
│   │   ├── Programs.tsx
│   │   ├── ProgramDetail.tsx
│   │   └── ...
│   │
│   ├── store/                  # Zustand state stores
│   │   ├── authStore.ts
│   │   ├── programStore.ts
│   │   └── ...
│   │
│   ├── types/                  # TypeScript type definitions
│   │   ├── api.ts              # API response types
│   │   ├── program.ts
│   │   ├── activity.ts
│   │   └── ...
│   │
│   ├── utils/                  # Utility functions
│   │   ├── formatters.ts       # Date, number formatting
│   │   ├── validators.ts       # Form validation
│   │   └── ...
│   │
│   ├── App.tsx                 # Root component
│   ├── main.tsx                # Entry point
│   └── index.css               # Global styles
│
├── tests/                      # Test files
│   ├── setup.ts                # Test setup
│   └── ...
│
├── public/                     # Static assets
├── index.html                  # HTML template
├── vite.config.ts              # Vite configuration
├── tailwind.config.js          # Tailwind configuration
├── tsconfig.json               # TypeScript configuration
└── package.json
```

---

## Coding Standards

### TypeScript

```typescript
// Always use explicit types - never use 'any'
interface Activity {
  id: string;
  name: string;
  duration: number;
  budgetedCost: string;  // Decimal values as strings
  percentComplete: number;
  isCritical: boolean;
  isMilestone: boolean;
}

// Use type for unions and simple types
type ActivityStatus = 'not_started' | 'in_progress' | 'completed';

// Use interface for object shapes (can be extended)
interface ActivityWithRelations extends Activity {
  predecessors: Dependency[];
  successors: Dependency[];
}

// Prefer const assertions for enums
const DEPENDENCY_TYPES = {
  FS: 'Finish-to-Start',
  SS: 'Start-to-Start',
  FF: 'Finish-to-Finish',
  SF: 'Start-to-Finish',
} as const;

type DependencyType = keyof typeof DEPENDENCY_TYPES;
```

### Naming Conventions

```typescript
// Components: PascalCase
export function ActivityList() { ... }
export function GanttChart() { ... }

// Hooks: camelCase starting with 'use'
export function useActivities() { ... }
export function useGanttData() { ... }

// Types/Interfaces: PascalCase
interface ActivityResponse { ... }
type ActivityStatus = ...

// Constants: UPPER_SNAKE_CASE
const MAX_PAGE_SIZE = 100;
const API_BASE_URL = '/api/v1';

// Files:
// - Components: PascalCase.tsx (ActivityList.tsx)
// - Hooks: camelCase.ts (useActivities.ts)
// - Utils: camelCase.ts (formatters.ts)
// - Types: camelCase.ts (activity.ts)
```

### ESLint Rules

The project uses strict ESLint configuration:

```javascript
// Key rules enforced:
{
  "@typescript-eslint/no-explicit-any": "error",
  "@typescript-eslint/explicit-function-return-type": "warn",
  "react-hooks/rules-of-hooks": "error",
  "react-hooks/exhaustive-deps": "warn",
  "no-console": "warn",
  "prefer-const": "error"
}
```

---

## Component Patterns

### Functional Components

```typescript
// Props interface above component
interface ActivityCardProps {
  activity: Activity;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
  isSelected?: boolean;  // Optional props have ?
}

// Destructure props, provide defaults
export function ActivityCard({
  activity,
  onEdit,
  onDelete,
  isSelected = false,
}: ActivityCardProps): JSX.Element {
  return (
    <div className={`card ${isSelected ? 'selected' : ''}`}>
      <h3>{activity.name}</h3>
      <p>Duration: {activity.duration} days</p>
      <div className="actions">
        <button onClick={() => onEdit(activity.id)}>Edit</button>
        <button onClick={() => onDelete(activity.id)}>Delete</button>
      </div>
    </div>
  );
}
```

### Compound Components

```typescript
// For complex UI with related sub-components
interface TableProps {
  children: React.ReactNode;
}

function Table({ children }: TableProps): JSX.Element {
  return <table className="data-table">{children}</table>;
}

function TableHeader({ children }: { children: React.ReactNode }): JSX.Element {
  return <thead>{children}</thead>;
}

function TableBody({ children }: { children: React.ReactNode }): JSX.Element {
  return <tbody>{children}</tbody>;
}

function TableRow({ children }: { children: React.ReactNode }): JSX.Element {
  return <tr>{children}</tr>;
}

// Attach sub-components
Table.Header = TableHeader;
Table.Body = TableBody;
Table.Row = TableRow;

// Usage
<Table>
  <Table.Header>
    <Table.Row>...</Table.Row>
  </Table.Header>
  <Table.Body>
    <Table.Row>...</Table.Row>
  </Table.Body>
</Table>
```

### Custom Hooks

```typescript
// Encapsulate data fetching logic
export function useActivities(programId: string) {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!programId) return;

    const fetchActivities = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get(`/activities?program_id=${programId}`);
        setActivities(response.data.items);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Unknown error'));
      } finally {
        setLoading(false);
      }
    };

    fetchActivities();
  }, [programId]);

  return { activities, loading, error };
}
```

### Error Boundaries

```typescript
// Use for graceful error handling
import { ErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div className="error-container" role="alert">
      <h2>Something went wrong</h2>
      <pre>{error.message}</pre>
      <button onClick={resetErrorBoundary}>Try again</button>
    </div>
  );
}

// Wrap components that might throw
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <GanttChart activities={activities} />
</ErrorBoundary>
```

---

## State Management

### Local State (useState)

```typescript
// Use for component-specific state
function ActivityForm() {
  const [name, setName] = useState('');
  const [duration, setDuration] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // ...
}
```

### React Query (Server State)

```typescript
// Use for server data - handles caching, refetching, etc.
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function useProgram(programId: string) {
  return useQuery({
    queryKey: ['program', programId],
    queryFn: () => apiClient.get(`/programs/${programId}`).then(r => r.data),
    enabled: !!programId,
    staleTime: 5 * 60 * 1000,  // 5 minutes
  });
}

export function useCreateActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ActivityCreate) =>
      apiClient.post('/activities', data).then(r => r.data),
    onSuccess: (_, variables) => {
      // Invalidate activities list to refetch
      queryClient.invalidateQueries({
        queryKey: ['activities', variables.program_id]
      });
    },
  });
}
```

### Zustand (Global State)

```typescript
// Use for app-wide state that doesn't come from server
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  token: string | null;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      login: async (email, password) => {
        const response = await apiClient.post('/auth/login', { email, password });
        set({ token: response.data.access_token, user: response.data.user });
      },
      logout: () => set({ token: null, user: null }),
    }),
    {
      name: 'auth-storage',
    }
  )
);
```

---

## API Integration

### API Client Setup

```typescript
// src/api/client.ts
import axios from 'axios';
import { useAuthStore } from '@/store/authStore';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle errors globally
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### Type-Safe API Calls

```typescript
// src/api/activities.ts
import { apiClient } from './client';
import type { Activity, ActivityCreate, PaginatedResponse } from '@/types';

export const activitiesApi = {
  list: (programId: string, page = 1, pageSize = 50) =>
    apiClient.get<PaginatedResponse<Activity>>('/activities', {
      params: { program_id: programId, page, page_size: pageSize },
    }),

  get: (id: string) =>
    apiClient.get<Activity>(`/activities/${id}`),

  create: (data: ActivityCreate) =>
    apiClient.post<Activity>('/activities', data),

  update: (id: string, data: Partial<ActivityCreate>) =>
    apiClient.patch<Activity>(`/activities/${id}`, data),

  delete: (id: string) =>
    apiClient.delete(`/activities/${id}`),
};
```

---

## Testing

### Testing Library

We use Vitest + React Testing Library.

### Unit Tests

```typescript
// src/components/ActivityCard/__tests__/ActivityCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ActivityCard } from '../ActivityCard';

describe('ActivityCard', () => {
  const mockActivity = {
    id: '1',
    name: 'Test Activity',
    duration: 5,
    isCritical: false,
    isMilestone: false,
  };

  it('renders activity name', () => {
    render(
      <ActivityCard
        activity={mockActivity}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />
    );
    expect(screen.getByText('Test Activity')).toBeInTheDocument();
  });

  it('calls onEdit when edit button clicked', () => {
    const onEdit = vi.fn();
    render(
      <ActivityCard
        activity={mockActivity}
        onEdit={onEdit}
        onDelete={vi.fn()}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /edit/i }));
    expect(onEdit).toHaveBeenCalledWith('1');
  });

  it('highlights critical activities', () => {
    render(
      <ActivityCard
        activity={{ ...mockActivity, isCritical: true }}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />
    );
    expect(screen.getByTestId('activity-card')).toHaveClass('critical');
  });
});
```

### Integration Tests

```typescript
// Testing with API mocking
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ActivityList } from '../ActivityList';

const server = setupServer(
  rest.get('/api/v1/activities', (req, res, ctx) => {
    return res(
      ctx.json({
        items: [
          { id: '1', name: 'Activity 1', duration: 5 },
          { id: '2', name: 'Activity 2', duration: 3 },
        ],
        total: 2,
      })
    );
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

it('loads and displays activities', async () => {
  const queryClient = new QueryClient();
  render(
    <QueryClientProvider client={queryClient}>
      <ActivityList programId="test-program" />
    </QueryClientProvider>
  );

  await waitFor(() => {
    expect(screen.getByText('Activity 1')).toBeInTheDocument();
    expect(screen.getByText('Activity 2')).toBeInTheDocument();
  });
});
```

---

## Styling with Tailwind

### Configuration

```javascript
// tailwind.config.js
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
        },
        critical: '#ef4444',
        milestone: '#8b5cf6',
      },
    },
  },
  plugins: [],
};
```

### Component Styling

```typescript
// Use className with Tailwind utilities
function ActivityCard({ activity, isSelected }: Props) {
  return (
    <div
      className={`
        rounded-lg border p-4 shadow-sm
        transition-colors duration-200
        ${isSelected ? 'border-primary-500 bg-primary-50' : 'border-gray-200'}
        ${activity.isCritical ? 'border-l-4 border-l-critical' : ''}
        hover:shadow-md
      `}
    >
      <h3 className="text-lg font-semibold text-gray-900">
        {activity.name}
      </h3>
      <p className="mt-1 text-sm text-gray-500">
        Duration: {activity.duration} days
      </p>
    </div>
  );
}
```

### Utility Pattern

```typescript
// src/utils/cn.ts - Conditional class names
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Usage
<div className={cn(
  'rounded-lg border p-4',
  isSelected && 'border-primary-500',
  isCritical && 'bg-red-50'
)} />
```

---

## Performance

### Code Splitting

```typescript
// Lazy load routes
import { lazy, Suspense } from 'react';

const GanttChart = lazy(() => import('./components/GanttChart'));
const EVMSDashboard = lazy(() => import('./components/EVMSDashboard'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/gantt" element={<GanttChart />} />
        <Route path="/evms" element={<EVMSDashboard />} />
      </Routes>
    </Suspense>
  );
}
```

### Memoization

```typescript
// Memoize expensive computations
const criticalPath = useMemo(() => {
  return activities.filter(a => a.isCritical);
}, [activities]);

// Memoize callbacks
const handleActivityClick = useCallback((id: string) => {
  setSelectedId(id);
}, []);

// Memoize components with React.memo
const ActivityRow = React.memo(function ActivityRow({ activity }: Props) {
  return <tr>...</tr>;
});
```

### Virtual Lists

```typescript
// For large lists, use react-virtual
import { useVirtualizer } from '@tanstack/react-virtual';

function ActivityList({ activities }: { activities: Activity[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: activities.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
  });

  return (
    <div ref={parentRef} className="h-[500px] overflow-auto">
      <div style={{ height: `${virtualizer.getTotalSize()}px` }}>
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.index}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            <ActivityRow activity={activities[virtualRow.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Accessibility

### ARIA Attributes

```typescript
// Use semantic HTML and ARIA
<button
  aria-label="Delete activity"
  aria-describedby="delete-confirmation"
  onClick={handleDelete}
>
  <TrashIcon />
</button>

// For dynamic content
<div
  role="status"
  aria-live="polite"
  aria-busy={isLoading}
>
  {isLoading ? 'Loading...' : `${count} activities`}
</div>

// For forms
<label htmlFor="activity-name">Activity Name</label>
<input
  id="activity-name"
  aria-required="true"
  aria-invalid={!!errors.name}
  aria-describedby={errors.name ? 'name-error' : undefined}
/>
{errors.name && <span id="name-error" role="alert">{errors.name}</span>}
```

### Keyboard Navigation

```typescript
// Support keyboard navigation
function Menu() {
  const [focusIndex, setFocusIndex] = useState(0);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setFocusIndex(i => Math.min(i + 1, items.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setFocusIndex(i => Math.max(i - 1, 0));
        break;
      case 'Enter':
        handleSelect(items[focusIndex]);
        break;
    }
  };

  return (
    <ul role="menu" onKeyDown={handleKeyDown}>
      {items.map((item, i) => (
        <li
          key={item.id}
          role="menuitem"
          tabIndex={i === focusIndex ? 0 : -1}
        >
          {item.name}
        </li>
      ))}
    </ul>
  );
}
```

---

## VS Code Extensions

Recommended extensions for frontend development:

- **ESLint** - Linting
- **Prettier** - Code formatting
- **Tailwind CSS IntelliSense** - Tailwind autocomplete
- **TypeScript Vue Plugin** - TypeScript support
- **Error Lens** - Inline error display

---

*Defense PM Tool v1.2.0 - Frontend Development Guide*
*Last Updated: March 2026*
