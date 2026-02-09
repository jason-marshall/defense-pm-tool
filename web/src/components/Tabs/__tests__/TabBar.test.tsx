import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TabBar } from "../TabBar";
import type { TabItem } from "../TabBar";
import { Calendar, Activity, Settings } from "lucide-react";

function renderTabBar(tabs: TabItem[], initialRoute = "/") {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <TabBar tabs={tabs} />
    </MemoryRouter>
  );
}

const mockTabs: TabItem[] = [
  { to: "/overview", label: "Overview", end: true },
  { to: "/activities", label: "Activities", icon: Activity },
  { to: "/schedule", label: "Schedule", icon: Calendar },
  { to: "/settings", label: "Settings", icon: Settings },
];

describe("TabBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all tab labels", () => {
    renderTabBar(mockTabs);

    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Activities")).toBeInTheDocument();
    expect(screen.getByText("Schedule")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("renders correct number of tabs", () => {
    renderTabBar(mockTabs);

    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(4);
  });

  it("renders tabs as links with correct hrefs", () => {
    renderTabBar(mockTabs);

    const links = screen.getAllByRole("tab");
    expect(links[0]).toHaveAttribute("href", "/overview");
    expect(links[1]).toHaveAttribute("href", "/activities");
    expect(links[2]).toHaveAttribute("href", "/schedule");
    expect(links[3]).toHaveAttribute("href", "/settings");
  });

  it("applies active style to matching tab", () => {
    renderTabBar(mockTabs, "/activities");

    const activeTab = screen.getByText("Activities").closest("a");
    expect(activeTab?.className).toContain("border-blue-600");
    expect(activeTab?.className).toContain("text-blue-600");
  });

  it("applies inactive style to non-matching tabs", () => {
    renderTabBar(mockTabs, "/activities");

    const inactiveTab = screen.getByText("Schedule").closest("a");
    expect(inactiveTab?.className).toContain("border-transparent");
    expect(inactiveTab?.className).toContain("text-gray-500");
  });

  it("renders tabs without icons", () => {
    const noIconTabs: TabItem[] = [
      { to: "/tab1", label: "Tab 1" },
      { to: "/tab2", label: "Tab 2" },
    ];

    renderTabBar(noIconTabs);

    expect(screen.getByText("Tab 1")).toBeInTheDocument();
    expect(screen.getByText("Tab 2")).toBeInTheDocument();
  });
});
