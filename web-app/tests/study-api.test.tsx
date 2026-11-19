import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { deleteStudyCard, getStudyCards, getStudySources, getStudyStats, reviewStudyCard } from "../src/api/study";

describe("study API client", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(console, "info").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
    fetchMock.mockReset();
  });
  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it("requests the server-filtered due queue and local-day statistics", async () => {
    fetchMock.mockResolvedValueOnce(new Response("[]", { status: 200 }))
      .mockResolvedValueOnce(new Response("[]", { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ due_count: 1, due_today_count: 2, completed_count: 3 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ due_count: 2, due_today_count: 3, completed_count: 4 }), { status: 200 }));
    await expect(getStudyCards({ dueOnly: true })).resolves.toEqual([]);
    await expect(getStudyStats("Asia/Singapore")).resolves.toEqual({ due_count: 3, due_today_count: 5, completed_count: 7 });
    const due = fetchMock.mock.calls[0][0] as URL;
    const stats = fetchMock.mock.calls[2][0] as URL;
    expect(due.pathname).toBe("/api/study/cards");
    expect(due.searchParams.get("due_only")).toBe("true");
    expect(stats.pathname).toBe("/api/study/stats");
    expect(stats.searchParams.get("timezone")).toBe("Asia/Singapore");
  });

  it("sends the chosen rating and card version and reports failed requests", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ id: 9 }), { status: 200 }))
      .mockResolvedValueOnce(new Response("", { status: 409 }));
    await reviewStudyCard(9, 3, 4);
    const [url, options] = fetchMock.mock.calls[0];
    expect((url as URL).pathname).toBe("/api/study/cards/9/review");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ rating: 3, version: 4 });
    await expect(reviewStudyCard(9, 1, 4)).rejects.toThrow("Backend response 409");
  });

  it("removes only the requested card", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(deleteStudyCard(9)).resolves.toBeUndefined();
    const [url, options] = fetchMock.mock.calls[0];
    expect((url as URL).pathname).toBe("/api/study/cards/9");
    expect(options.method).toBe("DELETE");
  });

  it("loads removed cards and saved sources without enrolling or reviewing", async () => {
    fetchMock.mockResolvedValueOnce(new Response("[]", { status: 200 }))
      .mockResolvedValueOnce(new Response("[]", { status: 200 }))
      .mockResolvedValueOnce(new Response("[]", { status: 200 }));
    await getStudyCards({ includeRemoved: true });
    await getStudySources(9);
    expect((fetchMock.mock.calls[0][0] as URL).searchParams.get("include_removed")).toBe("true");
    expect((fetchMock.mock.calls[2][0] as URL).pathname).toBe("/api/study/cards/9/sources");
    expect(fetchMock.mock.calls.every(([, options]) => !options.method || options.method === "GET")).toBe(true);
  });
  it("keeps overlapping English and Japanese IDs distinct for review and sources", async () => {
    const card = { id: 1, word_id: 7, due_at: "2026-01-01T00:00:00Z" };
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify([{ ...card, language: "ja" }]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([{ ...card, language: "en" }]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([{ id: 9, card_id: 1 }]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...card, language: "en" }), { status: 200 }));
    const cards = await getStudyCards();
    expect(cards.map((item) => item.id).sort()).toEqual([-1, 1]);
    expect((await getStudySources(-1))[0].card_id).toBe(-1);
    expect((await reviewStudyCard(-1, 3, 0)).id).toBe(-1);
    for (const call of fetchMock.mock.calls.slice(2)) {
      expect((call[0] as URL).searchParams.get("language")).toBe("en");
    }
  });

});
