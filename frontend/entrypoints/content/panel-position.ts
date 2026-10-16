export default function getPanelPosition(
  rect: DOMRect,
  windowData: { height: number; width: number },
  panelData: { height: number; width: number },
) {
  let panelTopLeft;

  const windowHeight = windowData.height;
  const windowWidth = windowData.width;

  const panelWordSpacingPx = 8;

  const panelExceedsBottomOfWindow =
    rect.bottom + panelWordSpacingPx + panelData.height > windowHeight;

  if (panelExceedsBottomOfWindow) {
    panelTopLeft = {
      x: rect.left,
      y: rect.top - panelWordSpacingPx - panelData.height,
    };
  } else if (!panelExceedsBottomOfWindow) {
    panelTopLeft = { x: rect.left, y: rect.bottom + panelWordSpacingPx };
  }
  return panelTopLeft;
}
