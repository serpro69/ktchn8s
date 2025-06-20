(function () {
  // Begin async loading icon packs ASAP so they don't slow down the diagram rendering
  const iconify_logos = fetch(
    "https://unpkg.com/@iconify-json/logos@1/icons.json",
  )
    .then((res) => res.json())
    .catch((e) => console.error("Failed to fetch Mermaid icon pack:", e));

  // Example of loading additional packs if needed
  const iconify_material = fetch(
    "https://unpkg.com/@iconify-json/material-symbols@1/icons.json",
  )
    .then((res) => res.json())
    .catch((e) => console.error("Failed to fetch Mermaid icon pack:", e));

  // Intercept Mermaid loading into the global scope so we can register
  // the icon packs before Mermaid is initialized is finalized by Material for MkDocs
  Object.defineProperty(window, "mermaid", {
    configurable: true,
    set: async function (value) {
      delete window.mermaid;
      window.mermaid = value;

      try {
        value.registerIconPacks([
          { name: "logos", loader: () => iconify_logos },
          { name: "material-symbols", loader: () => iconify_material },
        ]);
      } catch (e) {
        console.error("Error registering Mermaid icon pack:", e);
      }
    },
  });
})();
