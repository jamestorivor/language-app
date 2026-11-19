import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import PodcastLibrary from "../src/components/PodcastLibrary";
import * as api from "../src/api/podcast";
import type { EpisodeResponse } from "../src/contracts/podcast";

vi.mock("../src/api/podcast", () => ({ getEpisodes: vi.fn() }));

const episode = (id: number, title: string, added_at: string | null, language: "ja" | "en" = "ja"): EpisodeResponse => ({
  id, title, added_at, language, user_id: 1, author: "Author", audio_location: "https://example.com", duration: 60,
});

describe("podcast library sorting", () => {
  afterEach(cleanup);

  it("sorts by date or title and keeps the choice when switching languages", async () => {
    vi.mocked(api.getEpisodes).mockResolvedValue([
      episode(1, "zebra", "2025-01-01T00:00:00Z"),
      episode(2, "Apple", "2025-02-01T00:00:00Z"),
      episode(3, "Banana", null),
      episode(4, "English Z", "2025-01-01T00:00:00Z", "en"),
      episode(5, "English A", "2025-02-01T00:00:00Z", "en"),
    ]);
    const user = userEvent.setup();
    render(<MemoryRouter><PodcastLibrary /></MemoryRouter>);
    const select = await screen.findByRole("combobox", { name: /sort by/i });
    const titles = () => screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent);

    expect(titles()).toEqual(["Apple", "zebra", "Banana"]);
    await user.selectOptions(select, "oldest");
    expect(titles()).toEqual(["zebra", "Apple", "Banana"]);
    await user.selectOptions(select, "title-asc");
    expect(titles()).toEqual(["Apple", "Banana", "zebra"]);
    await user.selectOptions(select, "title-desc");
    expect(titles()).toEqual(["zebra", "Banana", "Apple"]);
    await user.click(within(screen.getByRole("group", { name: /podcast language/i })).getByRole("button", { name: "English" }));
    expect(titles()).toEqual(["English Z", "English A"]);
    expect((select as HTMLSelectElement).value).toBe("title-desc");
  });
});
