import { createRoot } from "react-dom/client";
import Panel from "./shadow_root_components/Panel.tsx";
import "../../assets/tailwind.css";
import { parsePageOnLoad } from "./page-text.ts";

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

    parsePageOnLoad();
  },
});
