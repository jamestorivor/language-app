import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import StudySettings from "../src/components/StudySettings";
import * as api from "../src/api/study";
import { defaultStudyShortcuts } from "../src/utils/studyShortcuts";

vi.mock("../src/api/study", () => ({ getStudySettings: vi.fn(), saveStudySettings: vi.fn() }));

describe("study settings", () => {
  afterEach(cleanup);
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.getStudySettings).mockResolvedValue({ retention_percent: 90, maximum_interval: 36500, fuzzing: true, shortcuts: defaultStudyShortcuts });
  });

  it("loads and saves the selected preferences", async () => {
    const user = userEvent.setup();
    vi.mocked(api.saveStudySettings).mockImplementation(async (settings) => settings);
    render(<MemoryRouter><StudySettings /></MemoryRouter>);
    const retention = await screen.findByRole("spinbutton", { name: /desired retention/i });
    await user.clear(retention);
    await user.type(retention, "95");
    const maximum = screen.getByRole("spinbutton", { name: /maximum review interval/i });
    await user.clear(maximum);
    await user.type(maximum, "30");
    await user.click(screen.getByRole("checkbox", { name: /spread reviews/i }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Show answer" }), "Space");
    await user.selectOptions(screen.getByRole("combobox", { name: "Good" }), "3");
    await user.click(screen.getByRole("button", { name: /save settings/i }));
    await waitFor(() => expect(api.saveStudySettings).toHaveBeenCalledWith({ retention_percent: 95, maximum_interval: 30, fuzzing: false, shortcuts: { ...defaultStudyShortcuts, show_answer: "Space", good: "3" } }));
    expect(await screen.findByText("Study settings saved.")).toBeTruthy();
  });

  it("rejects duplicate bindings and can reset them", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><StudySettings /></MemoryRouter>);
    await screen.findByRole("combobox", { name: "Again" });
    await user.selectOptions(screen.getByRole("combobox", { name: "Again" }), "s");
    await user.click(screen.getByRole("button", { name: /save settings/i }));
    expect(screen.getByRole("alert").textContent).toContain("different key");
    expect(api.saveStudySettings).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Reset shortcuts" }));
    expect(screen.getByRole("combobox", { name: "Again" })).toHaveProperty("value", "a");
  });

  it("does not offer the form when settings fail to load and can retry", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getStudySettings).mockRejectedValueOnce(new Error("offline"));
    render(<MemoryRouter><StudySettings /></MemoryRouter>);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /save settings/i })).toBeNull();
    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByRole("spinbutton", { name: /desired retention/i })).toBeTruthy();
  });
});
