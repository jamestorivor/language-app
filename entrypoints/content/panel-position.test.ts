import { describe, it, expect } from "vitest";
import getPanelPosition from "./panel-position";

const windowData = { height: 500, width: 800 };
const panelData = {
  height: 100,
  width: 200,
};

it("positions the panel above the selection when it exceeds the viewport bottom", () => {
  const rect = {
    top: 450,
    bottom: 470,
    left: 100,
  } as DOMRect;

  const result = getPanelPosition(rect, windowData, panelData);

  expect(result).toEqual({
    x: 100,
    y: 342, // 450 - 8 - 100
  });
});

it("positions the panel below the selection if within viewport", () => {
  const rect = {
    top: 200,
    bottom: 220,
    left: 100,
  } as DOMRect;

  const result = getPanelPosition(rect, windowData, panelData);

  expect(result).toEqual({
    x: 100,
    y: 228, // 220 + 8
  });
});
