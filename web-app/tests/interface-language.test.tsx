import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import WordPanel from "../src/components/transcript/WordPanel";
import type { TokenGroup } from "../src/contracts/japanese";
import { LanguageProvider } from "../src/i18n";
import * as podcastApi from "../src/api/podcast";

vi.mock("../src/api/podcast", async (importOriginal) => ({
  ...await importOriginal<typeof import("../src/api/podcast")>(),
  getEpisodes: vi.fn().mockResolvedValue([]),
}));

function showApp(path = "/") {
  return render(<MemoryRouter initialEntries={[path]}><LanguageProvider><App /></LanguageProvider></MemoryRouter>);
}

afterEach(() => { cleanup(); localStorage.clear(); vi.unstubAllGlobals(); });

describe("interface language", () => {
  it("switches the interface, defaults to English study, and remembers the choice", async () => {
    const user = userEvent.setup();
    const view = showApp();
    await user.click(screen.getByRole("link", { name: "User settings" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Choose your interface language" }), "ja");
    expect(screen.getByRole("heading", { name: "ユーザー設定" })).toBeTruthy();
    expect(document.documentElement.lang).toBe("ja");
    expect((screen.getByRole("combobox", { name: "言語" }) as HTMLSelectElement).value).toBe("en");
    expect((screen.getByRole("combobox", { name: "CEFRレベル" }) as HTMLSelectElement).value).toBe("A1");
    expect(localStorage.getItem("interface-language")).toBe("ja");
    view.unmount();
    showApp("/podcasts");
    const languages = await screen.findByRole("group", { name: "ポッドキャストの言語" });
    expect(within(languages).getByRole("button", { name: "English" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByRole("heading", { name: "英語のエピソードはまだありません" })).toBeTruthy();
    await user.click(screen.getAllByRole("link", { name: "ポッドキャストを追加", exact: true })[1]);
    expect((screen.getByRole("combobox", { name: "ポッドキャストの言語" }) as HTMLSelectElement).value).toBe("en");
    expect(vi.mocked(podcastApi.getEpisodes)).toHaveBeenCalled();
  });

  it("keeps English learning content while translating word controls", () => {
    localStorage.setItem("interface-language", "ja");
    vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
    const anchor = document.createElement("button");
    document.body.appendChild(anchor);
    const word: TokenGroup = { word_id: 7, text: "cat", lookup_form: "cat", familiarity_score: 0,
      senses: [{ glosses: ["猫"], pos: [], stagk: [], stagr: [], s_inf: [] }],
      start_idx: 0, end_idx: 3, tokens: [], display: true };
    render(<LanguageProvider><WordPanel language="en" word={word} anchor={anchor} saving={false}
      onClose={() => {}} onChange={() => {}} /></LanguageProvider>);
    const panel = screen.getByRole("region", { name: "単語の詳細" });
    expect(within(panel).getByText("cat")).toBeTruthy();
    expect(within(panel).getByText("猫")).toBeTruthy();
    expect(within(panel).getByRole("button", { name: "単語の詳細を閉じる" })).toBeTruthy();
    expect(within(panel).getByRole("group", { name: "習熟度" })).toBeTruthy();
    anchor.remove();
  });

  it("honors an explicit podcast language and can switch back to English", async () => {
    localStorage.setItem("interface-language", "ja");
    const user = userEvent.setup();
    const view = showApp("/podcasts/add?language=ja");
    expect((screen.getByRole("combobox", { name: "ポッドキャストの言語" }) as HTMLSelectElement).value).toBe("ja");
    await user.click(screen.getByRole("link", { name: "ユーザー設定" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "表示言語を選択" }), "en");
    view.unmount();
    showApp("/podcasts/add?language=ja");
    expect(screen.getByRole("heading", { name: "Add a podcast" })).toBeTruthy();
    expect((screen.getByRole("combobox", { name: "Podcast language" }) as HTMLSelectElement).value).toBe("ja");
    expect(document.documentElement.lang).toBe("en");
    expect(localStorage.getItem("interface-language")).toBe("en");
  });
});
