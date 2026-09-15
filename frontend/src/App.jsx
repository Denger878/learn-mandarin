import { useCallback, useEffect, useRef, useState } from "react";
import {
  getNextCard,
  getStats,
  importText,
  markMastered,
  saveMeaning,
  sendAnswer,
} from "./api.js";

const TABS = [
  { id: "import", label: "input text" },
  { id: "learn", label: "learn new words" },
  { id: "review", label: "review known words" },
];

const SOURCES = ["dm", "gc", "discovery", "other"];
const STATUSES = ["new", "learning", "known", "mastered"];

/* ── masthead counts ──────────────────────────────────── */

function Stats({ stats }) {
  if (!stats) return <div className="stats" />;
  return (
    <div className="stats">
      {STATUSES.map((status) => (
        <span className="stat" key={status}>
          <b>{stats[status]}</b>
          <i>{status}</i>
        </span>
      ))}
    </div>
  );
}

/* ── tab 1: paste text in ─────────────────────────────── */

function ImportPanel({ active, onChanged }) {
  const [text, setText] = useState("");
  const [source, setSource] = useState("dm");
  const [message, setMessage] = useState("");

  async function submit(event) {
    event.preventDefault();
    const result = await importText(text, source);
    setMessage(result.message);
    if (result.ok) {
      setText("");
      onChanged();
    }
  }

  return (
    <section className={`panel${active ? " active" : ""}`}>
      <div className="sheet">
        <form className="import-form" onSubmit={submit}>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="paste Chinese text here"
            spellCheck="false"
          />
          <div className="row">
            <label htmlFor="source">source</label>
            <select id="source" value={source} onChange={(e) => setSource(e.target.value)}>
              {SOURCES.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
            <button type="submit" className="solid">import</button>
          </div>
        </form>
        <p className="message">{message}</p>
      </div>
    </section>
  );
}

/* ── tabs 2 and 3: drilling ───────────────────────────────
   Both piles behave the same way. The next word is only
   fetched when you ask for it, so a graded card stays on
   screen until you press next.                            */

function DrillPanel({ mode, active, onChanged }) {
  const [card, setCard] = useState(null);
  const [remaining, setRemaining] = useState(0);
  const [guess, setGuess] = useState("");
  const [result, setResult] = useState(null);
  const [meaning, setMeaning] = useState(null);
  const [meaningDraft, setMeaningDraft] = useState("");
  const [mastered, setMastered] = useState(false);
  const [note, setNote] = useState("");

  const guessRef = useRef(null);
  const nextRef = useRef(null);
  const requested = useRef(false);

  const loadCard = useCallback(async () => {
    const data = await getNextCard(mode);
    setCard(data.card);
    setRemaining(data.remaining);
    setGuess("");
    setResult(null);
    setMeaning(data.card ? data.card.meaning : null);
    setMeaningDraft("");
    setMastered(false);
    setNote("");
  }, [mode]);

  /* Pull the first word the first time this tab is opened. */
  useEffect(() => {
    if (!active || requested.current) return;
    requested.current = true;
    loadCard();
  }, [active, loadCard]);

  useEffect(() => {
    if (active && card && !result) guessRef.current?.focus();
  }, [active, card, result]);

  useEffect(() => {
    if (active && result) nextRef.current?.focus();
  }, [active, result]);

  async function check(event) {
    event.preventDefault();
    if (!card || result) return;
    const data = await sendAnswer(mode, card.id, guess);
    if (!data.ok) {
      setNote(data.message);
      return;
    }
    setResult(data);
    setMeaning(data.meaning);
    setNote(
      data.promoted
        ? "Learned. It moves to your known words."
        : data.demoted
          ? "Back to learning."
          : `streak ${data.streak}`
    );
    onChanged();
  }

  async function submitMeaning(event) {
    event.preventDefault();
    const text = meaningDraft.trim();
    if (!text) return;
    await saveMeaning(card.id, text);
    setMeaning(text);
    setMeaningDraft("");
  }

  async function retire() {
    const data = await markMastered(card.id);
    setNote(data.message || "");
    if (data.ok) {
      setMastered(true);
      onChanged();
    }
  }

  const emptyText = remaining
    ? "Every word here has come up recently. Come back after more cards."
    : mode === "learn"
      ? "No words to learn yet. Import some text first."
      : "No known words yet. Get a word to a streak of 5 in learn mode.";

  return (
    <section className={`panel${active ? " active" : ""}`}>
      <div className="sheet">
        <div className="drill">
          {card ? (
            <>
              <p className="count">
                {remaining} word{remaining === 1 ? "" : "s"} in this pile
              </p>
              <p className="hanzi">{card.hanzi}</p>

              <form className="guess-form" onSubmit={check}>
                <input
                  ref={guessRef}
                  className="guess"
                  type="text"
                  value={guess}
                  onChange={(e) => setGuess(e.target.value)}
                  disabled={Boolean(result)}
                  placeholder="pinyin, no tones"
                  autoComplete="off"
                  spellCheck="false"
                />
                <button type="submit" className="solid" disabled={Boolean(result)}>
                  check
                </button>
              </form>

              {result && (
                <div className="result">
                  <p className={`verdict${result.correct ? "" : " wrong"}`}>
                    {result.correct ? "correct" : "wrong"}
                  </p>
                  <p className="answer">{result.pinyin}</p>
                  {meaning && <p className="meaning">{meaning}</p>}

                  {!meaning && (
                    <form className="meaning-form" onSubmit={submitMeaning}>
                      <input
                        className="meaning-input"
                        type="text"
                        value={meaningDraft}
                        onChange={(e) => setMeaningDraft(e.target.value)}
                        placeholder="add the English meaning"
                        autoComplete="off"
                      />
                      <button type="submit">save</button>
                    </form>
                  )}

                  <p className="note">{note}</p>
                  <div className="row">
                    <button ref={nextRef} className="next solid" onClick={loadCard}>
                      next word
                    </button>
                    {result.status === "known" && !mastered && (
                      <button className="master" onClick={retire}>mark mastered</button>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="empty">{emptyText}</p>
          )}
        </div>
      </div>
    </section>
  );
}

/* ── the page ─────────────────────────────────────────── */

export default function App() {
  const [tab, setTab] = useState("import");
  const [stats, setStats] = useState(null);

  const refreshStats = useCallback(async () => {
    setStats(await getStats());
  }, []);

  useEffect(() => {
    refreshStats();
  }, [refreshStats]);

  return (
    <div className="shell">
      <header>
        <h1>
          learn mandarin<span className="mark">学</span>
        </h1>
        <Stats stats={stats} />
      </header>

      <nav className="tabs">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            className="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      <main>
        <ImportPanel active={tab === "import"} onChanged={refreshStats} />
        <DrillPanel mode="learn" active={tab === "learn"} onChanged={refreshStats} />
        <DrillPanel mode="review" active={tab === "review"} onChanged={refreshStats} />
      </main>
    </div>
  );
}
