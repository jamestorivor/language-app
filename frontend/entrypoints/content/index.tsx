import { createRoot } from "react-dom/client";
import Panel from "../../features/vocabulary/panel/Panel.tsx";
import "../../assets/tailwind.css";
import { parsePageOnLoad } from "@/features/vocabulary/proces-page.ts";

export default defineContentScript({
  matches: ["*://*.google.com/*", "http://localhost/*"],
  cssInjectionMode: "ui",
  async main(ctx) {
    const ui = await createShadowRootUi(ctx, {
      name: "vocab-popup",
      position: "inline",

      onMount(container) {
        const root = createRoot(container);

        root.render(<Panel></Panel>);

        return root;
      },

      onRemove(root) {
        root?.unmount();
      },
    });

    ui.mount();

    await parsePageOnLoad();
  },
});
