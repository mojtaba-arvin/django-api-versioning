const root = document.documentElement;
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

function readStored(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}
function writeStored(key: string, value: string): void {
  try { localStorage.setItem(key, value); } catch { /* storage can be disabled */ }
}

// Colour theme follows the system until the visitor chooses an explicit theme.
const themeButton = document.querySelector<HTMLButtonElement>("[data-theme-toggle]");
function effectiveTheme(): "light" | "dark" {
  return root.dataset.theme === "light" || root.dataset.theme === "dark"
    ? root.dataset.theme
    : window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
function updateThemeButton(): void {
  if (!themeButton) return;
  const dark = effectiveTheme() === "dark";
  themeButton.setAttribute("aria-pressed", String(dark));
  themeButton.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  themeButton.title = dark ? "Switch to light theme" : "Switch to dark theme";
}
themeButton?.addEventListener("click", () => {
  const next = effectiveTheme() === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  writeStored("dav-theme", next);
  updateThemeButton();
});
window.matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", updateThemeButton);
updateThemeButton();

// The site can add a reduced-motion override without defeating an OS preference.
const motionButton = document.querySelector<HTMLButtonElement>("[data-motion-toggle]");
function updateMotionButton(): void {
  if (!motionButton) return;
  const stored = readStored("dav-motion");
  const reduced = stored === "reduce" || prefersReducedMotion.matches;
  motionButton.setAttribute("aria-pressed", String(reduced));
  motionButton.disabled = prefersReducedMotion.matches;
  motionButton.title = prefersReducedMotion.matches
    ? "Motion is reduced by your system preference"
    : reduced ? "Allow motion" : "Reduce motion";
  motionButton.setAttribute("aria-label", motionButton.title);
}
motionButton?.addEventListener("click", () => {
  const reduce = root.dataset.motion !== "reduce";
  if (reduce) { root.dataset.motion = "reduce"; writeStored("dav-motion", "reduce"); }
  else { delete root.dataset.motion; writeStored("dav-motion", "full"); }
  updateMotionButton();
});
prefersReducedMotion.addEventListener?.("change", updateMotionButton);
updateMotionButton();

// Native details disclosure remains functional without JavaScript.
document.querySelectorAll<HTMLDetailsElement>("details[data-dismissable]").forEach((details) => {
  document.addEventListener("pointerdown", (event) => {
    if (details.open && event.target instanceof Node && !details.contains(event.target)) details.open = false;
  });
  details.addEventListener("keydown", (event) => {
    if (event.key === "Escape") { details.open = false; (details.querySelector("summary") as HTMLElement | null)?.focus(); }
  });
});
document.querySelectorAll<HTMLDetailsElement>(".nav-mobile").forEach((details) => {
  details.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => { details.open = false; }));
});

// Search is a progressive enhancement: the trigger remains a normal Articles link without JS.
const searchDialog = document.querySelector<HTMLDialogElement>("#search-dialog");
const searchInput = document.querySelector<HTMLInputElement>("#search-input");
const searchResults = document.querySelector<HTMLDivElement>("#search-results");
const searchStatus = document.querySelector<HTMLElement>("#search-status");
const searchDataElement = document.querySelector<HTMLScriptElement>("#site-search-index");
let searchIndex: Array<{ type: string; title: string; description?: string; keywords?: string[]; href: string }> = [];
try { searchIndex = JSON.parse(searchDataElement?.textContent ?? "[]"); } catch { searchIndex = []; }
let activeResult = -1;
let lastSearchOpener: HTMLElement | null = null;
const normalize = (value: string) => value.toLocaleLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").trim();
function scoreResult(item: (typeof searchIndex)[number], query: string): number {
  const title = normalize(item.title);
  const text = normalize([item.title, item.description, ...(item.keywords ?? [])].join(" "));
  const tokens = normalize(query).split(/\s+/).filter(Boolean);
  let score = 0;
  for (const token of tokens) {
    if (title === token) score += 12;
    else if (title.startsWith(token)) score += 7;
    else if (title.includes(token)) score += 4;
    else if (text.includes(token)) score += 1;
    else return 0;
  }
  return score;
}
function renderSearch(): void {
  if (!searchInput || !searchResults || !searchStatus) return;
  const query = searchInput.value.trim();
  searchResults.replaceChildren();
  activeResult = -1;
  searchInput.removeAttribute("aria-activedescendant");
  if (!query) { searchStatus.textContent = "Search articles, scenarios and page sections."; searchInput.setAttribute("aria-expanded", "false"); return; }
  const matches = searchIndex
    .map((item) => ({ item, score: scoreResult(item, query) }))
    .filter((result) => result.score > 0)
    .sort((a, b) => b.score - a.score || a.item.title.localeCompare(b.item.title))
    .slice(0, 10);
  searchStatus.textContent = matches.length ? `${matches.length} result${matches.length === 1 ? "" : "s"}` : "No matching pages, articles or scenarios.";
  searchInput.setAttribute("aria-expanded", String(matches.length > 0));
  for (const [index, result] of matches.entries()) {
    const link = document.createElement("a");
    link.className = "search-result";
    link.id = `search-result-${index}`;
    link.href = result.item.href;
    link.setAttribute("role", "option");
    link.setAttribute("aria-selected", "false");
    const title = document.createElement("span");
    title.className = "search-result-title";
    title.textContent = result.item.title;
    const meta = document.createElement("span");
    meta.className = "search-result-meta";
    meta.textContent = `${result.item.type} · ${result.item.description ?? "Open result"}`;
    link.append(title, meta);
    searchResults.append(link);
  }
}
function selectSearchResult(next: number): void {
  if (!searchResults || !searchInput) return;
  const links = [...searchResults.querySelectorAll<HTMLAnchorElement>("a[role=option]")];
  if (!links.length) return;
  activeResult = (next + links.length) % links.length;
  links.forEach((link, index) => link.setAttribute("aria-selected", String(index === activeResult)));
  searchInput.setAttribute("aria-activedescendant", links[activeResult].id);
  links[activeResult].scrollIntoView({ block: "nearest" });
}
function openSearch(opener: HTMLElement): void {
  if (!searchDialog || !searchInput) return;
  lastSearchOpener = opener;
  if (!searchDialog.open) searchDialog.showModal();
  searchInput.value = "";
  renderSearch();
  requestAnimationFrame(() => searchInput?.focus());
}
document.querySelectorAll<HTMLElement>("[data-search-open]").forEach((opener) => {
  opener.addEventListener("click", (event) => { event.preventDefault(); openSearch(opener); });
});
document.querySelector<HTMLButtonElement>("[data-search-close]")?.addEventListener("click", () => searchDialog?.close());
document.querySelector<HTMLFormElement>("[data-search-form]")?.addEventListener("submit", (event) => event.preventDefault());
searchDialog?.addEventListener("click", (event) => { if (event.target === searchDialog) searchDialog.close(); });
searchDialog?.addEventListener("close", () => lastSearchOpener?.focus());
searchInput?.addEventListener("input", renderSearch);
searchInput?.addEventListener("keydown", (event) => {
  if (event.key === "ArrowDown") { event.preventDefault(); selectSearchResult(activeResult + 1); }
  if (event.key === "ArrowUp") { event.preventDefault(); selectSearchResult(activeResult <= 0 ? 0 : activeResult - 1); }
  if (event.key === "Enter" && activeResult >= 0) {
    const link = searchResults?.querySelectorAll<HTMLAnchorElement>("a[role=option]")[activeResult];
    if (link) { event.preventDefault(); window.location.assign(link.href); }
  }
});
document.addEventListener("keydown", (event) => {
  const target = event.target;
  const editing = target instanceof HTMLElement && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
  if (!editing && event.key === "/" && !event.metaKey && !event.ctrlKey && !event.altKey) {
    const opener = document.querySelector<HTMLElement>("[data-search-open]");
    if (opener) { event.preventDefault(); openSearch(opener); }
  }
  if (!editing && (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    const opener = document.querySelector<HTMLElement>("[data-search-open]");
    if (opener) { event.preventDefault(); openSearch(opener); }
  }
});

// Add copy controls to Markdown code fences; static code remains readable without JS.
async function copyText(value: string): Promise<void> {
  if (navigator.clipboard?.writeText) { await navigator.clipboard.writeText(value); return; }
  const field = document.createElement("textarea");
  field.value = value; field.setAttribute("readonly", "");
  field.style.position = "fixed"; field.style.opacity = "0";
  document.body.append(field); field.select();
  const ok = document.execCommand("copy"); field.remove();
  if (!ok) throw new Error("Clipboard copy is unavailable in this browser.");
}
function addCopyButton(pre: HTMLPreElement): void {
  const existingWrapper = pre.closest<HTMLElement>(".codeblock");
  if (existingWrapper?.querySelector(".copy-btn")) return;
  const wrapper = existingWrapper ?? document.createElement("figure");
  if (!existingWrapper) {
    wrapper.className = "codeblock";
    pre.parentNode?.insertBefore(wrapper, pre);
    wrapper.append(pre);
  }
  const button = document.createElement("button");
  button.className = "copy-btn copy-floating";
  button.type = "button";
  button.textContent = "Copy";
  button.setAttribute("aria-label", "Copy code block");
  button.addEventListener("click", async () => {
    try {
      await copyText(pre.innerText);
      button.textContent = "Copied"; button.dataset.copied = "";
    } catch {
      button.textContent = "Copy failed";
    }
    window.setTimeout(() => { button.textContent = "Copy"; delete button.dataset.copied; }, 1400);
  });
  wrapper.append(button);
}
document.querySelectorAll<HTMLPreElement>(".prose pre.astro-code, .prose pre.terminal, pre.terminal").forEach(addCopyButton);

// Scroll-driven CSS is preferred; this is the fallback for browsers without scroll timelines.
const progress = document.querySelector<HTMLElement>(".reading-progress");
if (progress && !CSS.supports("animation-timeline: scroll()")) {
  let scheduled = false;
  const update = () => {
    const total = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.transform = `scaleX(${total > 0 ? Math.min(1, window.scrollY / total) : 0})`;
    scheduled = false;
  };
  window.addEventListener("scroll", () => { if (!scheduled) { scheduled = true; requestAnimationFrame(update); } }, { passive: true });
  window.addEventListener("resize", update, { passive: true });
  update();
}

function initSegmentExplorer(): void {
  const root = document.querySelector<HTMLElement>("[data-segment-explorer]");
  if (!root) return;
  const dataElement = root.querySelector<HTMLScriptElement>("#explorer-data");
  const scenarioSelect = root.querySelector<HTMLSelectElement>("[data-explorer-scenario]");
  const routeSelect = root.querySelector<HTMLSelectElement>("[data-explorer-route]");
  const output = root.querySelector<HTMLElement>("[data-explorer-output]");
  const status = root.querySelector<HTMLElement>("[data-explorer-status]");
  if (!dataElement || !scenarioSelect || !routeSelect || !output || !status) return;

  type Segment = { start: number; end: number; sourceVersion: number; callback: string; slot: number };
  type Route = { postfix: string; segments: Segment[] };
  type Scenario = {
    name: string; title: string; question: string; min: number; max: number;
    routes: Route[]; error: string; registrySize: number; requestCount: number;
  };
  let scenarios: Scenario[] = [];
  try { scenarios = JSON.parse(dataElement.textContent ?? "[]"); } catch { return; }

  const setRoutes = (scenario: Scenario, preferred?: string): void => {
    routeSelect.replaceChildren();
    for (const route of scenario.routes) {
      const option = document.createElement("option");
      option.value = route.postfix;
      option.textContent = route.postfix;
      routeSelect.append(option);
    }
    routeSelect.disabled = scenario.routes.length === 0;
    if (preferred && scenario.routes.some((route) => route.postfix === preferred)) {
      routeSelect.value = preferred;
    }
  };

  const render = (): void => {
    const scenario = scenarios.find((item) => item.name === scenarioSelect.value);
    if (!scenario) return;
    const route = scenario.routes.find((item) => item.postfix === routeSelect.value);
    const question = document.createElement("p");
    question.className = "explorer-question";
    question.textContent = scenario.question;
    if (!route) {
      const note = document.createElement("p");
      note.className = "note";
      note.textContent = scenario.error || "No versioned route segments were registered in this scenario.";
      output.replaceChildren(question, note);
      status.textContent = scenario.title + ": no versioned route segments.";
      return;
    }

    const visual = document.createElement("div");
    visual.className = "segment-visual";
    visual.style.setProperty("--version-count", String(scenario.max - scenario.min + 1));
    const axis = document.createElement("div");
    axis.className = "segment-axis";
    axis.setAttribute("aria-hidden", "true");
    for (let version = scenario.min; version <= scenario.max; version += 1) {
      const cell = document.createElement("span");
      cell.textContent = "v" + version;
      axis.append(cell);
    }
    visual.append(axis);

    for (const segment of route.segments) {
      const label = document.createElement("div");
      label.className = "segment-label";
      const callback = document.createElement("strong");
      callback.textContent = segment.callback;
      const detail = document.createElement("span");
      detail.textContent = "declared at v" + segment.sourceVersion + " · active v" + segment.start + "–v" + segment.end;
      label.append(callback, detail);
      visual.append(label);

      const track = document.createElement("div");
      track.className = "segment-track";
      for (let version = scenario.min; version <= scenario.max; version += 1) {
        const cell = document.createElement("span");
        cell.className = "segment-cell";
        const active = version >= segment.start && version <= segment.end;
        if (active) {
          cell.dataset.slot = String(segment.slot);
          cell.textContent = "v" + version;
          cell.title = version === segment.sourceVersion
            ? "Declaration point at version " + version
            : "Inherited from declaration at version " + segment.sourceVersion;
          if (version === segment.sourceVersion) cell.classList.add("is-declaration");
        } else {
          cell.setAttribute("aria-hidden", "true");
        }
        track.append(cell);
      }
      visual.append(track);
    }

    const legend = document.createElement("div");
    legend.className = "segment-legend";
    const declaration = document.createElement("span");
    declaration.textContent = "Declaration point = version where this view is registered";
    const inherited = document.createElement("span");
    inherited.textContent = "Other active cells = forward inheritance";
    legend.append(declaration, inherited);
    visual.append(legend);
    output.replaceChildren(question, visual);
    status.textContent = scenario.title + " · " + route.postfix + " · " + route.segments.length + " declaration segment(s).";
  };

  const requestedScenario = new URLSearchParams(window.location.search).get("scenario");
  if (requestedScenario && scenarios.some((item) => item.name === requestedScenario)) {
    scenarioSelect.value = requestedScenario;
  }
  const initial = scenarios.find((item) => item.name === scenarioSelect.value) ?? scenarios[0];
  if (!initial) return;
  const requestedRoute = new URLSearchParams(window.location.search).get("route") ?? root.dataset.initialRoute;
  setRoutes(initial, requestedRoute);
  render();

  scenarioSelect.addEventListener("change", () => {
    const selected = scenarios.find((item) => item.name === scenarioSelect.value);
    if (!selected) return;
    setRoutes(selected);
    render();
  });
  routeSelect.addEventListener("change", render);
}
initSegmentExplorer();
