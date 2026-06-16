import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type DomainResult = {
  name: string;
  extension: string;
  score: number;
  length: number;
  available: boolean;
  registration_cost_usd: number;
  type: string;
  language_origin: string;
  meaning: string;
  trend_score: number;
  heat_index: number;
  registrar_availability: Record<string, boolean | null>;
  geo_breakdown: Record<string, number>;
  expected_monthly_clicks: number;
};

type Meta = {
  languages: string[];
  countries: [string, string][];
  extensions: string[];
};

type DomainType = "brandable" | "meaningful" | "both";

type SortKey =
  | "name"
  | "score"
  | "length"
  | "extension"
  | "type"
  | "trend_score"
  | "heat_index"
  | "registration_cost_usd"
  | "expected_monthly_clicks";

const ALL_EXTENSIONS = [".com", ".net", ".ai", ".org"];

function formatGeo(geo: Record<string, number>): string {
  return Object.entries(geo)
    .filter(([country]) => country !== "Other")
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([country, pct]) => `${country} ${pct}%`)
    .join(", ");
}

function RegistrarBadges({ avail }: { avail: Record<string, boolean | null> }) {
  return (
    <span className="flex gap-1 font-mono text-xs">
      {ALL_EXTENSIONS.map((ext) => {
        const v = avail[ext];
        const color =
          v === true ? "text-green-400" : v === false ? "text-red-400" : "text-gray-600";
        const symbol = v === true ? "✓" : v === false ? "✗" : "–";
        return (
          <span key={ext} className={color} title={`${ext}: ${v === null ? "not checked" : v ? "available" : "taken"}`}>
            {ext.slice(1)}
            {symbol}
          </span>
        );
      })}
    </span>
  );
}

export default function Home() {
  const [niche, setNiche] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<DomainResult[] | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [trendSource, setTrendSource] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortAsc, setSortAsc] = useState(false);

  const [meta, setMeta] = useState<Meta | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state
  const [selectedLanguage, setSelectedLanguage] = useState<string>("");
  const [domainType, setDomainType] = useState<DomainType>("both");
  const [trendLocation, setTrendLocation] = useState("auto");
  const [lengthMin, setLengthMin] = useState(3);
  const [lengthMax, setLengthMax] = useState(20);
  const [costMin, setCostMin] = useState("");
  const [costMax, setCostMax] = useState("");
  const [trendIndexMin, setTrendIndexMin] = useState(1);
  const [extensions, setExtensions] = useState<string[]>(ALL_EXTENSIONS);

  useEffect(() => {
    fetch(`${API_URL}/meta`)
      .then((r) => r.json())
      .then((d: Meta) => setMeta(d))
      .catch(() => setMeta(null));
  }, []);

  function toggleInArray<T>(arr: T[], val: T, setter: (v: T[]) => void) {
    if (arr.includes(val)) {
      setter(arr.filter((v) => v !== val));
    } else {
      setter([...arr, val]);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!niche.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const body: Record<string, unknown> = {
        niche: niche.trim(),
        domain_type: domainType,
        trend_location: trendLocation,
        score_heat_min: trendIndexMin,
        min_length: lengthMin,
        max_length: lengthMax,
        extensions,
      };
      if (selectedLanguage) body.languages = [selectedLanguage];
      if (costMin !== "") body.cost_min = Number(costMin);
      if (costMax !== "") body.cost_max = Number(costMax);

      const res = await fetch(`${API_URL}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Server error ${res.status}: ${text}`);
      }
      const data = await res.json();
      setResults(data.domains);
      setKeywords(data.keyword_seeds);
      setTrendSource(data.trend_source);
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
    ? [...results].sort((a, b) => {
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
    if (sortKey !== col) return <span className="text-gray-500 ml-1">↕</span>;
    return <span className="ml-1">{sortAsc ? "↑" : "↓"}</span>;
  }

  const columns: { key: SortKey; label: string }[] = [
    { key: "name", label: "Domain" },
    { key: "type", label: "Type" },
    { key: "score", label: "Total" },
    { key: "trend_score", label: "Trend" },
    { key: "heat_index", label: "Heat" },
    { key: "registration_cost_usd", label: "Cost" },
    { key: "expected_monthly_clicks", label: "Clicks/mo" },
  ];

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-1 text-indigo-400">
          Domain Market Intelligence
        </h1>
        <p className="text-gray-400 mb-6 text-sm">
          Enter a niche to discover available, scored domain names with trend,
          semantics, and multi-language insight.
        </p>

        <form onSubmit={handleSearch} className="flex gap-3 mb-4">
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
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className="px-4 py-2 bg-gray-800 border border-gray-600 hover:bg-gray-700 rounded-lg text-sm transition"
          >
            Filters {showFilters ? "▲" : "▼"}
          </button>
          <button
            type="submit"
            disabled={loading || !niche.trim()}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-semibold transition"
          >
            {loading ? "Searching…" : "Find Domains"}
          </button>
        </form>

        {showFilters && (
          <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4 bg-gray-900 border border-gray-700 rounded-lg p-4 text-sm">
            <div>
              <label className="block text-gray-400 mb-1">Language</label>
              <select
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1"
              >
                <option value="">All languages</option>
                {(meta?.languages ?? ["English"]).map((lang) => (
                  <option key={lang} value={lang}>{lang}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-gray-400 mb-1">Domain type</label>
              <select
                value={domainType}
                onChange={(e) => setDomainType(e.target.value as DomainType)}
                className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1"
              >
                <option value="both">Both</option>
                <option value="brandable">Brandable</option>
                <option value="meaningful">Meaningful</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-400 mb-1">Trend location</label>
              <select
                value={trendLocation}
                onChange={(e) => setTrendLocation(e.target.value)}
                className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1"
              >
                <option value="auto">Auto</option>
                <option value="global">Global</option>
                {(meta?.countries ?? []).map(([code, name]) => (
                  <option key={code} value={code}>
                    {name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-gray-400 mb-1">
                Character length: {lengthMin}–{lengthMax}
              </label>
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 w-7">min</span>
                  <input
                    type="range"
                    min={1}
                    max={20}
                    value={lengthMin}
                    onChange={(e) => setLengthMin(Math.min(Number(e.target.value), lengthMax - 1))}
                    className="flex-1 accent-indigo-500"
                  />
                  <span className="text-xs text-gray-300 w-4 text-right">{lengthMin}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 w-7">max</span>
                  <input
                    type="range"
                    min={1}
                    max={20}
                    value={lengthMax}
                    onChange={(e) => setLengthMax(Math.max(Number(e.target.value), lengthMin + 1))}
                    className="flex-1 accent-indigo-500"
                  />
                  <span className="text-xs text-gray-300 w-4 text-right">{lengthMax}</span>
                </div>
              </div>
            </div>

            <div>
              <label className="block text-gray-400 mb-1">Cost range (USD/yr)</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  placeholder="min"
                  value={costMin}
                  onChange={(e) => setCostMin(e.target.value)}
                  className="w-1/2 bg-gray-800 border border-gray-600 rounded px-2 py-1"
                />
                <input
                  type="number"
                  placeholder="max"
                  value={costMax}
                  onChange={(e) => setCostMax(e.target.value)}
                  className="w-1/2 bg-gray-800 border border-gray-600 rounded px-2 py-1"
                />
              </div>
            </div>

            <div>
              <label className="block text-gray-400 mb-1">Extensions</label>
              <div className="flex gap-2">
                {ALL_EXTENSIONS.map((ext) => (
                  <button
                    type="button"
                    key={ext}
                    onClick={() => toggleInArray(extensions, ext, setExtensions)}
                    className={`px-2 py-1 rounded border text-xs ${
                      extensions.includes(ext)
                        ? "bg-indigo-600 border-indigo-500"
                        : "bg-gray-800 border-gray-600 text-gray-300"
                    }`}
                  >
                    {ext}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-gray-400 mb-1">
                Trend Index min: {trendIndexMin}
              </label>
              <input
                type="range"
                min={1}
                max={100}
                value={trendIndexMin}
                onChange={(e) => setTrendIndexMin(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
              <p className="text-gray-500 text-xs mt-1">Filters on combined trend score &amp; heat index (1–100)</p>
            </div>
          </div>
        )}

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
            <div className="mb-4 text-sm text-gray-400 flex flex-wrap gap-4 items-center">
              {keywords.length > 0 && (
                <span>
                  <span className="text-gray-500">Trend keywords: </span>
                  {keywords.join(", ")}
                </span>
              )}
              <span className="text-gray-500">
                Trend source: <span className="text-gray-300">{trendSource}</span>
              </span>
              <span className="text-gray-500 ml-auto">
                {displayed.length} result{displayed.length !== 1 ? "s" : ""}
              </span>
            </div>

            {displayed.length === 0 ? (
              <p className="text-gray-500 py-8 text-center">
                No available domains found for this niche/filter combination.
                Try widening your filters.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-gray-700">
                <table className="w-full text-sm">
                  <thead className="bg-gray-800 text-gray-300">
                    <tr>
                      {columns.map((col) => (
                        <th
                          key={col.key}
                          onClick={() => toggleSort(col.key)}
                          className="px-3 py-3 text-left cursor-pointer hover:bg-gray-700 select-none whitespace-nowrap"
                        >
                          {col.label}
                          <SortArrow col={col.key} />
                        </th>
                      ))}
                      <th className="px-3 py-3 text-left">Language</th>
                      <th className="px-3 py-3 text-left">Meaning / Construction</th>
                      <th className="px-3 py-3 text-left">Registrar availability</th>
                      <th className="px-3 py-3 text-left">Geo breakdown</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayed.map((r, i) => (
                      <tr
                        key={r.name + r.extension + i}
                        className={i % 2 === 0 ? "bg-gray-900" : "bg-gray-900/50"}
                      >
                        <td className="px-3 py-2 font-mono text-indigo-300 whitespace-nowrap">
                          {r.name}
                          {r.extension}
                        </td>
                        <td className="px-3 py-2 text-gray-300 whitespace-nowrap">{r.type}</td>
                        <td className="px-3 py-2">
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
                        <td className="px-3 py-2 text-gray-300">{r.trend_score}</td>
                        <td className="px-3 py-2 text-gray-300">{r.heat_index}</td>
                        <td className="px-3 py-2 text-gray-400 whitespace-nowrap">
                          ${r.registration_cost_usd}/yr
                        </td>
                        <td className="px-3 py-2 text-gray-300">{r.expected_monthly_clicks}</td>
                        <td className="px-3 py-2 text-gray-300 whitespace-nowrap">
                          {r.language_origin}
                        </td>
                        <td className="px-3 py-2 text-gray-400 max-w-xs" title={r.meaning}>
                          {r.meaning}
                        </td>
                        <td className="px-3 py-2">
                          <RegistrarBadges avail={r.registrar_availability} />
                        </td>
                        <td className="px-3 py-2 text-gray-400 whitespace-nowrap text-xs">
                          {formatGeo(r.geo_breakdown)}
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
