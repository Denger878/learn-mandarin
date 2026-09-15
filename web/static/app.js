"use strict";

async function api(path, body) {
  const options = body === undefined
    ? {}
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const response = await fetch(path, options);
  return response.json();
}

async function refreshStats() {
  const stats = await api("/api/stats");
  document.getElementById("stats").textContent =
    `${stats.new} new · ${stats.learning} learning · ${stats.known} known · ${stats.mastered} mastered`;
}

/* One drill panel: learn or review. Both behave the same, they just pull from
   different piles. The next word is only fetched when the user asks for it. */
class Drill {
  constructor(root) {
    this.mode = root.dataset.mode;
    this.count = root.querySelector(".count");
    this.empty = root.querySelector(".empty");
    this.card = root.querySelector(".card");
    this.hanzi = root.querySelector(".hanzi");
    this.guessForm = root.querySelector(".guess-form");
    this.guess = root.querySelector(".guess");
    this.result = root.querySelector(".result");
    this.verdict = root.querySelector(".verdict");
    this.answer = root.querySelector(".answer");
    this.meaning = root.querySelector(".meaning");
    this.meaningForm = root.querySelector(".meaning-form");
    this.meaningInput = root.querySelector(".meaning-input");
    this.note = root.querySelector(".note");
    this.nextButton = root.querySelector(".next");
    this.masterButton = root.querySelector(".master");
    this.term = null;

    this.guessForm.addEventListener("submit", (event) => {
      event.preventDefault();
      this.check();
    });
    this.meaningForm.addEventListener("submit", (event) => {
      event.preventDefault();
      this.saveMeaning();
    });
    this.nextButton.addEventListener("click", () => this.load());
    this.masterButton.addEventListener("click", () => this.master());
  }

  /* Switching tabs shouldn't throw away a word you're part way through. */
  ensureCard() {
    if (!this.term || this.guess.disabled) this.load();
    else this.guess.focus();
  }

  async load() {
    const data = await api(`/api/next?mode=${this.mode}`);
    this.term = data.card;
    this.result.hidden = true;
    this.guess.value = "";
    this.guess.disabled = false;

    if (!this.term) {
      this.card.hidden = true;
      this.empty.textContent = data.remaining
        ? "Every word here has come up recently. Come back after more cards."
        : this.mode === "learn"
          ? "No words to learn yet. Import some text first."
          : "No known words yet. Get a word to a streak of 5 in learn mode.";
      this.count.textContent = "";
      return;
    }

    this.empty.textContent = "";
    this.card.hidden = false;
    this.hanzi.textContent = this.term.hanzi;
    this.count.textContent = `${data.remaining} word${data.remaining === 1 ? "" : "s"} in this pile`;
    this.guess.focus();
  }

  async check() {
    if (!this.term || this.guess.disabled) return;
    const data = await api("/api/answer", {
      mode: this.mode,
      term_id: this.term.id,
      guess: this.guess.value,
    });
    if (!data.ok) {
      this.note.textContent = data.message;
      return;
    }

    this.guess.disabled = true;
    this.result.hidden = false;
    this.verdict.textContent = data.correct ? "correct" : "wrong";
    this.verdict.classList.toggle("wrong", !data.correct);
    this.answer.textContent = data.pinyin;
    this.meaning.textContent = data.meaning || "";
    this.meaningForm.hidden = Boolean(data.meaning);
    this.meaningInput.value = "";
    this.masterButton.hidden = data.status !== "known";
    this.note.textContent = data.promoted
      ? "Learned. It moves to your known words."
      : data.demoted
        ? "Back to learning."
        : `streak ${data.streak}`;
    this.nextButton.focus();
    refreshStats();
  }

  async saveMeaning() {
    const meaning = this.meaningInput.value.trim();
    if (!meaning) return;
    await api("/api/meaning", { term_id: this.term.id, meaning });
    this.meaning.textContent = meaning;
    this.meaningForm.hidden = true;
  }

  async master() {
    const data = await api("/api/master", { term_id: this.term.id });
    this.note.textContent = data.message || "";
    if (data.ok) {
      this.masterButton.hidden = true;
      refreshStats();
    }
  }
}

const drills = {};
document.querySelectorAll(".drill").forEach((root) => {
  drills[root.dataset.mode] = new Drill(root);
});

function showPanel(name) {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.setAttribute("aria-selected", String(tab.dataset.panel === name));
  });
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `panel-${name}`);
  });
  if (drills[name]) drills[name].ensureCard();
}

document.getElementById("tabs").addEventListener("click", (event) => {
  const tab = event.target.closest(".tab");
  if (tab) showPanel(tab.dataset.panel);
});

document.getElementById("import-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = document.getElementById("import-text");
  const data = await api("/api/import", {
    text: text.value,
    source: document.getElementById("import-source").value,
  });
  document.getElementById("import-message").textContent = data.message;
  if (data.ok) text.value = "";
  refreshStats();
});

showPanel("import");
refreshStats();
