import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { Sidebar } from "../Sidebar";

function renderSidebar(route = "/") {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/*" element={<Sidebar />} />
        <Route path="/programs/:id/*" element={<Sidebar />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("Sidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders main navigation links", () => {
    renderSidebar("/");

    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Programs")).toBeInTheDocument();
  });

  it("renders Navigation heading", () => {
    renderSidebar("/");

    expect(screen.getByText("Navigation")).toBeInTheDocument();
  });

  it("does not show program sub-navigation at root", () => {
    renderSidebar("/");

    expect(screen.queryByText("Program")).not.toBeInTheDocument();
    expect(screen.queryByText("Activities")).not.toBeInTheDocument();
    expect(screen.queryByText("Schedule")).not.toBeInTheDocument();
  });

  it("shows program sub-navigation when viewing a program", () => {
    renderSidebar("/programs/prog-1");

    expect(screen.getByText("Program")).toBeInTheDocument();
    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Activities")).toBeInTheDocument();
    expect(screen.getByText("Dependencies")).toBeInTheDocument();
    expect(screen.getByText("Schedule")).toBeInTheDocument();
    expect(screen.getByText("WBS")).toBeInTheDocument();
    expect(screen.getByText("EVMS")).toBeInTheDocument();
    expect(screen.getByText("Resources")).toBeInTheDocument();
    expect(screen.getByText("Reports")).toBeInTheDocument();
    expect(screen.getByText("Scenarios")).toBeInTheDocument();
    expect(screen.getByText("Baselines")).toBeInTheDocument();
    expect(screen.getByText("Monte Carlo")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("renders correct links for program sub-navigation", () => {
    renderSidebar("/programs/prog-1");

    const activitiesLink = screen.getByText("Activities").closest("a");
    expect(activitiesLink).toHaveAttribute(
      "href",
      "/programs/prog-1/activities"
    );

    const scheduleLink = screen.getByText("Schedule").closest("a");
    expect(scheduleLink).toHaveAttribute(
      "href",
      "/programs/prog-1/schedule"
    );
  });
});
