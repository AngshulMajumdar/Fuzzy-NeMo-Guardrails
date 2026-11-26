"use strict";

// One filter step with the versioned illustrative policy in policies/default.yaml.
// This is deliberately a local numerical illustration; it is not an enforcement API.
const modes = ["routine", "uncertain", "restricted", "probing"];
const prior = [0.94, 0.04, 0.015, 0.005];
const transition = [
  [0.94, 0.035, 0.015, 0.01],
  [0.20, 0.70, 0.06, 0.04],
  [0.06, 0.04, 0.85, 0.05],
  [0.025, 0.025, 0.10, 0.85],
];
const observationNames = ["routine", "ambiguous", "restricted", "probing", "unknown", "neutral"];
const emissions = [
  [0.84, 0.06, 0.01, 0.005, 0.035, 0.05],
  [0.20, 0.60, 0.04, 0.015, 0.095, 0.05],
  [0.08, 0.06, 0.72, 0.04, 0.05, 0.05],
  [0.04, 0.04, 0.12, 0.70, 0.05, 0.05],
];

function filterOnce(observation) {
  const index = observationNames.indexOf(observation);
  if (index < 0) return null;
  const prediction = modes.map((_, next) =>
    prior.reduce((sum, probability, state) => sum + probability * transition[state][next], 0)
  );
  const weighted = prediction.map((probability, state) => probability * emissions[state][index]);
  const total = weighted.reduce((sum, value) => sum + value, 0);
  if (total <= 0) return null;
  return weighted.map(value => value / total);
}

function renderPosterior(observation) {
  const values = filterOnce(observation);
  const container = document.getElementById("posterior-bars");
  if (!container || !values) return;
  container.replaceChildren(...modes.map((mode, index) => {
    const card = document.createElement("div");
    card.className = "mode";
    card.dataset.mode = mode;
    const name = document.createElement("div");
    name.className = "mode-name";
    name.textContent = mode;
    const percentage = document.createElement("div");
    percentage.className = "mode-number";
    percentage.textContent = `${(values[index] * 100).toFixed(1)}%`;
    const bar = document.createElement("div");
    bar.className = "mode-bar";
    bar.setAttribute("role", "img");
    bar.setAttribute("aria-label", `${mode}: ${(values[index] * 100).toFixed(1)} percent`);
    const fill = document.createElement("span");
    fill.style.width = `${values[index] * 100}%`;
    bar.append(fill);
    card.append(name, percentage, bar);
    return card;
  }));
}

const observationSelect = document.getElementById("observation");
if (observationSelect) {
  renderPosterior(observationSelect.value);
  observationSelect.addEventListener("change", event => renderPosterior(event.target.value));
}

const navigationButton = document.getElementById("nav-toggle");
const navigation = document.getElementById("main-nav");
if (navigationButton && navigation) {
  navigationButton.addEventListener("click", () => {
    const open = navigationButton.getAttribute("aria-expanded") !== "true";
    navigationButton.setAttribute("aria-expanded", String(open));
    navigationButton.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
    navigation.classList.toggle("open", open);
  });
  navigation.querySelectorAll("a").forEach(link => link.addEventListener("click", () => {
    navigation.classList.remove("open");
    navigationButton.setAttribute("aria-expanded", "false");
    navigationButton.setAttribute("aria-label", "Open navigation");
  }));
}

const scrollProgress = document.getElementById("scroll-progress");
if (scrollProgress) {
  let requested = false;
  const updateProgress = () => {
    const distance = document.documentElement.scrollHeight - window.innerHeight;
    scrollProgress.style.width = `${distance > 0 ? Math.min(100, 100 * window.scrollY / distance) : 0}%`;
    requested = false;
  };
  window.addEventListener("scroll", () => {
    if (!requested) {
      requested = true;
      window.requestAnimationFrame(updateProgress);
    }
  }, {passive: true});
  updateProgress();
}
