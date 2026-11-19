import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter, Link, Route, Routes } from "react-router";
import BackButton from "../src/components/BackButton";

afterEach(cleanup);

describe("page back navigation", () => {
  it.each(["/", "/podcasts", "/study", "/podcasts/add"])("omits the back button on main page %s", (path) => {
    window.history.replaceState({ idx: 0 }, "", path);
    render(<BrowserRouter><BackButton /></BrowserRouter>);
    expect(screen.queryByRole("button", { name: "Back" })).toBeNull();
  });
  it("returns to the actual previous page instead of a fixed parent", async () => {
    const user = userEvent.setup();
    window.history.replaceState({ idx: 0 }, "", "/study/list");
    render(<BrowserRouter><BackButton /><Routes>
      <Route path="/study/list" element={<><h1>Study list</h1><Link to="/podcasts/segments/1">Source</Link></>} />
      <Route path="/podcasts/segments/1" element={<h1>Source segment</h1>} />
    </Routes></BrowserRouter>);
    await user.click(screen.getByRole("link", { name: "Source" }));
    expect(screen.getByRole("heading", { name: "Source segment" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Back" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Study list" })).toBeTruthy());
  });

  it("uses a sensible parent for a direct visit", async () => {
    const user = userEvent.setup();
    window.history.replaceState({ idx: 0 }, "", "/study/settings");
    render(<BrowserRouter><BackButton /><Routes>
      <Route path="/study/settings" element={<h1>Settings</h1>} />
      <Route path="/study" element={<h1>Review</h1>} />
    </Routes></BrowserRouter>);
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("heading", { name: "Review" })).toBeTruthy();
  });
});
