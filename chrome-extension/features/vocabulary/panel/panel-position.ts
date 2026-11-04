export default function getPanelPosition(
  rect: DOMRect,
  windowHeight: number,
  windowWidth: number,
  panelHeight: number,
  panelWidth: number,
) {
  let panelTopLeft;
  let x: number = rect.left;
  let y: number;

  const panelWordSpacingPx = 8;

  const panelExceedsBottomOfWindow =
    rect.bottom + panelWordSpacingPx + panelHeight > windowHeight;

  const panelExceedsLeftOfWindow = x < panelWordSpacingPx;

  const panelExceedsRightOfWindow =
    x + panelWidth + panelWordSpacingPx > windowWidth;

  const panelExceedsTopOfWindw =
    rect.top - panelWordSpacingPx - panelHeight < 0;

  const yAbove = rect.top - panelWordSpacingPx - panelHeight;
  const yBelow = rect.bottom + panelWordSpacingPx;

  if (panelExceedsBottomOfWindow) {
    y = yAbove;
  } else {
    y = yBelow;
  }

  if (panelExceedsRightOfWindow) {
    x = windowWidth - panelWidth - panelWordSpacingPx;
  }

  if (panelExceedsLeftOfWindow) {
    x = panelWordSpacingPx;
  }

  return (panelTopLeft = {
    x: x,
    y: y,
  });
}
