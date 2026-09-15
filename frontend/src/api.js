/* Every call the interface makes. The Python server answers all of these. */

async function call(path, body) {
  const options =
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        };
  const response = await fetch(path, options);
  return response.json();
}

export const getStats    = ()                    => call("/api/stats");
export const getNextCard = (mode)                => call(`/api/next?mode=${mode}`);
export const importText  = (text, source)        => call("/api/import", { text, source });
export const sendAnswer  = (mode, termId, guess) => call("/api/answer", { mode, term_id: termId, guess });
export const saveMeaning = (termId, meaning)     => call("/api/meaning", { term_id: termId, meaning });
export const markMastered = (termId)             => call("/api/master", { term_id: termId });
