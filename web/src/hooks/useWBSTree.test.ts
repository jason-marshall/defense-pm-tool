import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useWBSTree,
  useWBSElements,
  useWBSElement,
  useCreateWBSElement,
  useUpdateWBSElement,
  useDeleteWBSElement,
} from "./useWBSTree";

vi.mock("@/services/wbsApi", () => ({
  getWBSTree: vi.fn(),
  getWBSElements: vi.fn(),
  getWBSElement: vi.fn(),
  createWBSElement: vi.fn(),
  updateWBSElement: vi.fn(),
  deleteWBSElement: vi.fn(),
}));

import {
  getWBSTree,
  getWBSElements,
  getWBSElement,
  createWBSElement,
  updateWBSElement,
  deleteWBSElement,
} from "@/services/wbsApi";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

const mockTree = [
  {
    id: "wbs-1",
    programId: "prog-1",
    code: "1.0",
    name: "Project Root",
    description: null,
    level: 0,
    budgetedCost: "100000",
    children: [],
  },
];

const mockElement = {
  id: "wbs-1",
  programId: "prog-1",
  code: "1.0",
  name: "Project Root",
  description: null,
  level: 0,
  budgetedCost: "100000",
};

describe("useWBSTree", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches WBS tree", async () => {
    vi.mocked(getWBSTree).mockResolvedValue(mockTree);

    const { result } = renderHook(() => useWBSTree("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].name).toBe("Project Root");
    expect(getWBSTree).toHaveBeenCalledWith("prog-1");
  });

  it("does not fetch when programId is empty", () => {
    renderHook(() => useWBSTree(""), { wrapper });
    expect(getWBSTree).not.toHaveBeenCalled();
  });
});

describe("useWBSElements", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches flat list of WBS elements", async () => {
    vi.mocked(getWBSElements).mockResolvedValue([mockElement]);

    const { result } = renderHook(() => useWBSElements("prog-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(getWBSElements).toHaveBeenCalledWith("prog-1");
  });
});

describe("useWBSElement", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches a single WBS element", async () => {
    vi.mocked(getWBSElement).mockResolvedValue(mockElement);

    const { result } = renderHook(() => useWBSElement("wbs-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.name).toBe("Project Root");
    expect(getWBSElement).toHaveBeenCalledWith("wbs-1");
  });

  it("does not fetch when elementId is empty", () => {
    renderHook(() => useWBSElement(""), { wrapper });
    expect(getWBSElement).not.toHaveBeenCalled();
  });
});

describe("useCreateWBSElement", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates a WBS element", async () => {
    vi.mocked(createWBSElement).mockResolvedValue(mockElement as any);

    const { result } = renderHook(() => useCreateWBSElement(), { wrapper });

    result.current.mutate({
      programId: "prog-1",
      parentId: null,
      wbsCode: "1.0",
      name: "Project Root",
      description: null,
      budgetedCost: "100000",
      isControlAccount: false,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createWBSElement).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Project Root" })
    );
  });
});

describe("useUpdateWBSElement", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("updates a WBS element", async () => {
    vi.mocked(updateWBSElement).mockResolvedValue(mockElement as any);

    const { result } = renderHook(
      () => useUpdateWBSElement("prog-1"),
      { wrapper }
    );

    result.current.mutate({
      elementId: "wbs-1",
      data: { name: "Updated Root" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updateWBSElement).toHaveBeenCalledWith("wbs-1", {
      name: "Updated Root",
    });
  });
});

describe("useDeleteWBSElement", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes a WBS element", async () => {
    vi.mocked(deleteWBSElement).mockResolvedValue(undefined);

    const { result } = renderHook(
      () => useDeleteWBSElement("prog-1"),
      { wrapper }
    );

    result.current.mutate("wbs-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteWBSElement).toHaveBeenCalledWith("wbs-1");
  });
});
