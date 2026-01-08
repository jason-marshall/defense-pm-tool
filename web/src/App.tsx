import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/programs" element={<ProgramsPlaceholder />} />
          <Route path="/programs/:id" element={<ProgramDetailPlaceholder />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

function Home() {
  return (
    <div style={{ padding: "2rem" }}>
      <h1>Defense Program Management Tool</h1>
      <p>EVMS/DFARS Compliant Project Management</p>
      <nav>
        <ul>
          <li>
            <a href="/programs">Programs</a>
          </li>
        </ul>
      </nav>
    </div>
  );
}

function ProgramsPlaceholder() {
  return (
    <div style={{ padding: "2rem" }}>
      <h1>Programs</h1>
      <p>Program list will be implemented here.</p>
    </div>
  );
}

function ProgramDetailPlaceholder() {
  return (
    <div style={{ padding: "2rem" }}>
      <h1>Program Details</h1>
      <p>Program details, activities, and Gantt chart will be implemented here.</p>
    </div>
  );
}
