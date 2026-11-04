import { createRoot } from "react-dom/client";
import "../../assets/tailwind.css";
import VocabularyApp from "@/features/vocabulary/VocabularyApp.tsx";

export default defineContentScript({
  matches: [
    "*://*.google.com/*",
    "http://localhost/*",
    "http://*/*",
    "https://*/*",
  ],
  cssInjectionMode: "ui",
  async main(ctx) {
    const ui = await createShadowRootUi(ctx, {
      name: "vocab-popup",
      position: "inline",

      onMount(container) {
        const root = createRoot(container);

        root.render(<VocabularyApp></VocabularyApp>);

        return root;
      },

      onRemove(root) {
        root?.unmount();
      },
    });

    ui.mount();
  },
});
