import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type DomainResult = {
  name: string;
  extension: string;
  score: number;
  length: number;
  available: boolean;
  registration_cost_usd: number;
};

type SortKey = keyof Pick<DomainResult, "name" | "score" | "length" | "extension">;

export default function Home() {
  const [niche, setNiche] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<DomainResult[] | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortAsc, setSortAsc] = useState(false);
  const [minScore, setMinScore] = useState(0);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!niche.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const res = await fetch(`${API_URL}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ niche: niche.trim() }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Server error ${res.status}: ${text}`);
      }
      const data = await res.json();
      setResults(data.domains);
      setKeywords(data.keyword_seeds);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(
        msg.includes("Failed to fetch")
          ? "Could not reach the backend. If using the deployed version, the server may be waking up (free tier cold start — try again in 30s)."
          : msg
      );
    } finally {
      setLoading(false);
    }
  }

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(key === "name");
    }
  }

  const displayed = results
    ? [...results]
        .filter((r) => r.score >= minScore)
        .sort((a, b) => {
          const av = a[sortKey];
          const bv = b[sortKey];
          const cmp =
            typeof av === "string"
              ? av.localeCompare(bv as string)
              : (av as number) - (bv as number);
          return sortAsc ? cmp : -cmp;
        })
    : [];

  function SortArrow({ col }: { col: SortKey }) {
    if (sortKey !== col) return <span className="text-gray-400 ml-1">↕</span>;
    return <span className="ml-1">{sortAsc ? "↑" : "↓"}</span>;
  }

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-1 text-indigo-400">
          Domain Market Intelligence
        </h1>
        <p className="text-gray-400 mb-6 text-sm">
          Enter a niche to discover available, brandable domain names ranked by
          score.
        </p>

        <form onSubmit={handleSearch} className="flex gap-3 mb-6">
          <input
            type="text"
            value={niche}
            onChange={(e) => setNiche(e.target.value)}
            placeholder="e.g. fitness, crypto, travel"
            className="flex-1 rounded-lg bg-gray-800 border border-gray-600 px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            maxLength={80}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !niche.trim()}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-semibold transition"
          >
            {loading ? "Searching…" : "Find Domains"}
          </button>
        </form>

        {loading && (
          <div className="text-center py-12">
            <div className="inline-block w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-gray-400">
              Searching trends and checking availability… (10–30 sec)
            </p>
          </div>
        )}

        {error && (
          <div className="bg-red-900/40 border border-red-500 rounded-lg p-4 text-red-300 mb-4">
            {error}
          </div>
        )}

        {results !== null && !loading && (
          <>
            {keywords.length > 0 && (
              <div className="mb-4 text-sm text-gray-400">
                <span className="text-gray-500">Trend keywords: </span>
                {keywords.join(", ")}
              </div>
            )}

            <div className="mb-4 flex items-center gap-3 text-sm">
              <label className="text-gray-400">Min score:</label>
              <input
                type="range"
                min={0}
                max={100}
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                className="w-32 accent-indigo-500"
              />
              <span className="text-indigo-300 font-mono w-8">{minScore}</span>
              <span className="text-gray-500 ml-2">
                {displayed.length} result{displayed.length !== 1 ? "s" : ""}
              </span>
            </div>

            {displayed.length === 0 ? (
              <p className="text-gray-500 py-8 text-center">
                No available domains found for this niche. Try a different
                search.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-gray-700">
                <table className="w-full text-sm">
                  <thead className="bg-gray-800 text-gray-300">
                    <tr>
                      {(
                        [
                          "name",
                          "extension",
                          "score",
                          "length",
                        ] as SortKey[]
                      ).map((col) => (
                        <th
                          key={col}
                          onClick={() => toggleSort(col)}
                          className="px-4 py-3 text-left cursor-pointer hover:bg-gray-700 select-none capitalize"
                        >
                          {col}
                          <SortArrow col={col} />
                        </th>
                      ))}
                      <th className="px-4 py-3 text-left">Cost/yr</th>
                      <th className="px-4 py-3 text-left">Available</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayed.map((r, i) => (
                      <tr
                        key={r.name + r.extension + i}
                        className={
                          i % 2 === 0 ? "bg-gray-900" : "bg-gray-900/50"
                        }
                      >
                        <td className="px-4 py-2 font-mono text-indigo-300">
                          {r.name}{r.extension}
                        </td>
                        <td className="px-4 py-2 text-gray-400">
                          {r.extension}
                        </td>
                        <td className="px-4 py-2">
                          <span
                            className={`font-bold ${
                              r.score >= 75
                                ? "text-green-400"
                                : r.score >= 50
                                ? "text-yellow-400"
                                : "text-gray-400"
                            }`}
                          >
                            {r.score}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-gray-300">{r.length}</td>
                        <td className="px-4 py-2 text-gray-400">
                          ${r.registration_cost_usd}/yr
                        </td>
                        <td className="px-4 py-2">
                          <span className="text-green-400 font-semibold">
                            ✓
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
