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
  // 4-dimension scores (each 0-10, total 0-40)
  semantic_value: number;
  trend_relevance: number;
  market_potential: number;
  brandability: number;
  domain_score_total: number;
};

type Meta = {
  languages: string[];
  countries: [string, string][];
  extensions: string[];
};

type DomainType = "brandable" | "meaningful" | "both";

type TrendingNiche = {
  niche: string;
  trend_score: number;
  heat_index: number;
};

type SortKey =
  | "name"
  | "score"
  | "length"
  | "extension"
  | "type"
  | "trend_score"
  | "heat_index"
  | "registration_cost_usd"
  | "expected_monthly_clicks"
  | "domain_score_total"
  | "semantic_value"
  | "trend_relevance"
  | "market_potential"
  | "brandability";

const ALL_EXTENSIONS = [".com", ".net", ".ai", ".org"];

function formatGeo(geo: Record<string, number>): string {
  return Object.entries(geo)
    .filter(([country]) => country !== "Other")
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([country, pct]) => `${country} ${pct}%`)
    .join(", ");
}

function ScoreBadge({ value }: { value: number }) {
  const color =
    value >= 75 ? "text-green-400" : value >= 50 ? "text-yellow-400" : "text-gray-400";
  return <span className={`font-bold tabular-nums ${color}`}>{value}</span>;
}

function RegistrarBadges({ avail }: { avail: Record<string, boolean | null> }) {
  return (
    <span className="flex gap-1 flex-wrap font-mono text-xs">
      {Object.entries(avail).map(([ext, v]) => {
        const color =
          v === true ? "text-green-400" : v === false ? "text-red-400" : "text-gray-600";
        const symbol = v === true ? "✓" : v === false ? "✗" : "–";
        return (
          <span
            key={ext}
            className={color}
            title={`${ext}: ${v === null ? "not checked" : v ? "available" : "taken"}`}
          >
            {ext.slice(1)}
            {symbol}
          </span>
        );
      })}
    </span>
  );
}

function DimScore({ value, label }: { value: number; label: string }) {
  const color =
    value >= 8 ? "text-green-400" : value >= 5 ? "text-yellow-400" : "text-gray-500";
  return (
    <span className={`tabular-nums ${color}`} title={label}>
      {value}
    </span>
  );
}

function FilterLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wide">{children}</label>;
}

function FilterCard({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-col gap-1">{children}</div>;
}

export default function Home() {
  const [niche, setNiche] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<DomainResult[] | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [trendSource, setTrendSource] = useState<string>("");
  const [resolvedNiche, setResolvedNiche] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortAsc, setSortAsc] = useState(false);

  const [meta, setMeta] = useState<Meta | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [trendingNiches, setTrendingNiches] = useState<TrendingNiche[]>([]);
  const [partialNote, setPartialNote] = useState<string | null>(null);

  // Filter state
  const [selectedLanguage, setSelectedLanguage] = useState<string>("");
  const [domainType, setDomainType] = useState<DomainType>("both");
  const [trendLocation, setTrendLocation] = useState("auto");
  const [lengthMin, setLengthMin] = useState(3);
  const [lengthMax, setLengthMax] = useState(12);
  const [costMin, setCostMin] = useState("");
  const [costMax, setCostMax] = useState("");
  const [trendIndexMin, setTrendIndexMin] = useState(1);
  const [extensions, setExtensions] = useState<string[]>(ALL_EXTENSIONS);
  const [numResults, setNumResults] = useState(20);

  useEffect(() => {
    fetch(`${API_URL}/meta`)
      .then((r) => r.json())
      .then((d: Meta) => {
        setMeta(d);
        if (d.extensions?.length) setExtensions(d.extensions);
      })
      .catch(() => setMeta(null));
    fetch(`${API_URL}/trending-niches?limit=8`)
      .then((r) => r.json())
      .then((d: { niches: TrendingNiche[] }) => setTrendingNiches(d.niches ?? []))
      .catch(() => setTrendingNiches([]));
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
    setLoading(true);
    setError(null);
    setResults(null);
    setResolvedNiche("");
    setPartialNote(null);
    try {
      const body: Record<string, unknown> = {
        domain_type: domainType,
        trend_location: trendLocation,
        score_heat_min: trendIndexMin,
        min_length: lengthMin,
        max_length: lengthMax,
        extensions,
        num_results: numResults,
      };
      if (niche.trim()) body.niche = niche.trim();
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
      setResolvedNiche(data.niche);
      setPartialNote(data.partial_result_note ?? null);
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
    if (sortKey !== col) return <span className="text-gray-600 ml-1">↕</span>;
    return <span className="ml-1 text-indigo-400">{sortAsc ? "↑" : "↓"}</span>;
  }

  const sortableColumns: { key: SortKey; label: string }[] = [
    { key: "name", label: "Domain" },
    { key: "type", label: "Type" },
    { key: "score", label: "Score" },
    { key: "domain_score_total", label: "Dim Score" },
    { key: "trend_score", label: "Trend" },
    { key: "heat_index", label: "Heat" },
    { key: "registration_cost_usd", label: "Cost" },
    { key: "expected_monthly_clicks", label: "Clicks/mo" },
  ];

  const selectClass = "w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-1.5 text-sm text-gray-100 focus:outline-none focus:ring-1 focus:ring-indigo-500";

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-950/95 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-4">
          <div className="flex-1">
            <h1 className="text-xl font-bold text-indigo-400 leading-none">Domain Market Intelligence</h1>
            <p className="text-gray-500 text-xs mt-0.5">Discover available, scored domains with trend &amp; multi-language insight</p>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Search bar */}
        <form onSubmit={handleSearch} className="flex gap-3 mb-4">
          <div className="relative flex-1">
            <input
              type="text"
              value={niche}
              onChange={(e) => setNiche(e.target.value)}
              placeholder="Niche (optional) — e.g. fitness, crypto, travel"
              className="w-full rounded-lg bg-gray-800 border border-gray-700 px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
              maxLength={80}
              disabled={loading}
            />
            {!niche.trim() && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-indigo-400/70 pointer-events-none">
                auto-trending
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-2.5 border rounded-lg text-sm transition whitespace-nowrap ${
              showFilters
                ? "bg-indigo-900/40 border-indigo-600 text-indigo-300"
                : "bg-gray-800 border-gray-700 hover:bg-gray-700 text-gray-300"
            }`}
          >
            Filters {showFilters ? "▲" : "▼"}
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-semibold transition text-sm whitespace-nowrap"
          >
            {loading ? "Searching…" : "Find Domains"}
          </button>
        </form>

        {/* Trending niche chips — shown when niche field is empty */}
        {!niche.trim() && trendingNiches.length > 0 && !loading && (
          <div className="flex items-center gap-2 mb-4 flex-wrap">
            <span className="text-xs text-gray-500 shrink-0">Trending:</span>
            {trendingNiches.map((n) => (
              <button
                key={n.niche}
                type="button"
                onClick={() => setNiche(n.niche)}
                title={`Trend score: ${n.trend_score}  Trend Index: ${n.heat_index}`}
                className="px-3 py-1 rounded-full text-xs border border-indigo-700/50 bg-indigo-900/20 text-indigo-300 hover:bg-indigo-800/40 hover:border-indigo-500 transition capitalize"
              >
                {n.niche}
                <span className="ml-1.5 text-indigo-500 tabular-nums">{n.trend_score}</span>
              </button>
            ))}
          </div>
        )}

        {/* Filter panel */}
        {showFilters && (
          <div className="mb-6 bg-gray-900 border border-gray-700 rounded-xl p-5">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">

              {/* --- Search criteria group --- */}
              <FilterCard>
                <FilterLabel>Language origin</FilterLabel>
                <select
                  value={selectedLanguage}
                  onChange={(e) => setSelectedLanguage(e.target.value)}
                  className={selectClass}
                >
                  <option value="">All languages</option>
                  {(meta?.languages ?? ["English"]).map((lang) => (
                    <option key={lang} value={lang}>{lang}</option>
                  ))}
                </select>
              </FilterCard>

              <FilterCard>
                <FilterLabel>Domain type</FilterLabel>
                <select
                  value={domainType}
                  onChange={(e) => setDomainType(e.target.value as DomainType)}
                  className={selectClass}
                >
                  <option value="both">Both</option>
                  <option value="brandable">Brandable</option>
                  <option value="meaningful">Meaningful</option>
                </select>
              </FilterCard>

              <FilterCard>
                <FilterLabel>Trend location</FilterLabel>
                <select
                  value={trendLocation}
                  onChange={(e) => setTrendLocation(e.target.value)}
                  className={selectClass}
                >
                  <option value="auto">Auto</option>
                  <option value="global">Global</option>
                  {(meta?.countries ?? []).map(([code, name]) => (
                    <option key={code} value={code}>{name}</option>
                  ))}
                </select>
              </FilterCard>

              <FilterCard>
                <FilterLabel>Extensions</FilterLabel>
                <div className="flex gap-2 mb-1.5">
                  <button
                    type="button"
                    onClick={() => setExtensions(meta?.extensions ?? ALL_EXTENSIONS)}
                    className="text-xs px-2 py-0.5 rounded border border-indigo-700 text-indigo-400 hover:bg-indigo-900/30 transition"
                  >
                    Select All
                  </button>
                  <button
                    type="button"
                    onClick={() => setExtensions([])}
                    className="text-xs px-2 py-0.5 rounded border border-gray-600 text-gray-400 hover:bg-gray-800 transition"
                  >
                    Clear All
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5 pt-0.5">
                  {(meta?.extensions ?? ALL_EXTENSIONS).map((ext) => (
                    <button
                      type="button"
                      key={ext}
                      onClick={() => toggleInArray(extensions, ext, setExtensions)}
                      className={`px-2.5 py-1 rounded-md border text-xs font-mono transition ${
                        extensions.includes(ext)
                          ? "bg-indigo-600 border-indigo-500 text-white"
                          : "bg-gray-800 border-gray-600 text-gray-400 hover:border-gray-500"
                      }`}
                    >
                      {ext}
                    </button>
                  ))}
                </div>
              </FilterCard>

              {/* --- Technical filters group --- */}
              <FilterCard>
                <FilterLabel>Character length: {lengthMin}–{lengthMax}</FilterLabel>
                <div className="flex flex-col gap-2 pt-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-6">min</span>
                    <input
                      type="range"
                      min={1}
                      max={20}
                      value={lengthMin}
                      onChange={(e) => setLengthMin(Math.min(Number(e.target.value), lengthMax - 1))}
                      className="flex-1 accent-indigo-500"
                    />
                    <span className="text-xs text-gray-300 w-4 text-right tabular-nums">{lengthMin}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-6">max</span>
                    <input
                      type="range"
                      min={1}
                      max={20}
                      value={lengthMax}
                      onChange={(e) => setLengthMax(Math.max(Number(e.target.value), lengthMin + 1))}
                      className="flex-1 accent-indigo-500"
                    />
                    <span className="text-xs text-gray-300 w-4 text-right tabular-nums">{lengthMax}</span>
                  </div>
                </div>
              </FilterCard>

              <FilterCard>
                <FilterLabel>Cost range (USD/yr)</FilterLabel>
                <div className="flex gap-2">
                  <input
                    type="number"
                    placeholder="min"
                    value={costMin}
                    onChange={(e) => setCostMin(e.target.value)}
                    className="w-1/2 bg-gray-800 border border-gray-700 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                  <input
                    type="number"
                    placeholder="max"
                    value={costMax}
                    onChange={(e) => setCostMax(e.target.value)}
                    className="w-1/2 bg-gray-800 border border-gray-700 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </FilterCard>

              {/* --- Trend / results group --- */}
              <FilterCard>
                <FilterLabel>Trend Index min: {trendIndexMin}</FilterLabel>
                <div className="pt-0.5">
                  <input
                    type="range"
                    min={1}
                    max={100}
                    value={trendIndexMin}
                    onChange={(e) => setTrendIndexMin(Number(e.target.value))}
                    className="w-full accent-indigo-500"
                  />
                  <p className="text-gray-600 text-xs mt-1">Filters by combined trend score &amp; heat (1–100)</p>
                </div>
              </FilterCard>

              <FilterCard>
                <FilterLabel>Number of domains</FilterLabel>
                <input
                  type="number"
                  value={numResults}
                  min={1}
                  onChange={(e) => setNumResults(Math.max(1, Number(e.target.value) || 1))}
                  placeholder="e.g. 20"
                  className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-1.5 text-sm text-gray-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <p className="text-gray-600 text-xs">How many domain results to generate</p>
              </FilterCard>

            </div>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="text-center py-16">
            <div className="inline-block w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-gray-400 text-sm">Searching trends and checking availability… (10–30 sec)</p>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="bg-red-900/30 border border-red-800 rounded-xl p-4 text-red-300 mb-4 text-sm">
            {error}
          </div>
        )}

        {/* Results */}
        {results !== null && !loading && (
          <>
            {/* Partial result warning */}
            {partialNote && (
              <div className="bg-yellow-900/30 border border-yellow-800 rounded-xl p-4 text-yellow-300 mb-4 text-sm">
                ⚠ {partialNote}
              </div>
            )}
            {/* Results meta bar */}
            <div className="mb-3 flex flex-wrap gap-x-6 gap-y-1 items-center text-xs text-gray-500">
              {resolvedNiche && (
                <span>
                  Niche: <span className="text-gray-300 font-medium">{resolvedNiche}</span>
                </span>
              )}
              {keywords.length > 0 && (
                <span>
                  Trend keywords: <span className="text-gray-300">{keywords.join(", ")}</span>
                </span>
              )}
              <span>
                Source: <span className="text-gray-300">{trendSource}</span>
              </span>
              <span className="ml-auto text-gray-400 font-medium">
                {displayed.length} result{displayed.length !== 1 ? "s" : ""}
              </span>
            </div>

            {displayed.length === 0 ? (
              <div className="text-center py-16 text-gray-500 border border-gray-800 rounded-xl">
                <p className="text-base mb-1">No available domains found</p>
                <p className="text-xs text-gray-600">Try widening your filters or a different niche</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-gray-800">
                <table className="w-full text-sm">
                  <thead className="bg-gray-900 border-b border-gray-800 text-xs text-gray-400 uppercase tracking-wide">
                    <tr>
                      {sortableColumns.map((col) => (
                        <th
                          key={col.key}
                          onClick={() => toggleSort(col.key)}
                          className="px-3 py-3 text-left cursor-pointer hover:bg-gray-800 select-none whitespace-nowrap transition"
                        >
                          {col.label}
                          <SortArrow col={col.key} />
                        </th>
                      ))}
                      <th className="px-3 py-3 text-left whitespace-nowrap text-xs" title="Semantic Value / Trend Relevance / Market Potential / Brandability (each 0-10)">S·T·M·B</th>
                      <th className="px-3 py-3 text-left whitespace-nowrap">Language</th>
                      <th className="px-3 py-3 text-left">Meaning / Construction</th>
                      <th className="px-3 py-3 text-left whitespace-nowrap">Registrar Avail.</th>
                      <th className="px-3 py-3 text-left whitespace-nowrap">Geo Breakdown</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/60">
                    {displayed.map((r, i) => (
                      <tr
                        key={r.name + r.extension + i}
                        className="hover:bg-gray-800/40 transition-colors"
                      >
                        <td className="px-3 py-2.5 font-mono text-indigo-300 whitespace-nowrap font-medium">
                          {r.name}{r.extension}
                        </td>
                        <td className="px-3 py-2.5 whitespace-nowrap">
                          <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                            r.type === "Brandable"
                              ? "border-purple-700 text-purple-300 bg-purple-900/20"
                              : "border-blue-700 text-blue-300 bg-blue-900/20"
                          }`}>
                            {r.type}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-center tabular-nums">
                          <ScoreBadge value={r.score} />
                        </td>
                        <td className="px-3 py-2.5 text-center tabular-nums">
                          <span className={`font-bold ${r.domain_score_total >= 30 ? "text-green-400" : r.domain_score_total >= 20 ? "text-yellow-400" : "text-gray-400"}`}>
                            {r.domain_score_total ?? "—"}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-gray-300 text-center tabular-nums">{r.trend_score}</td>
                        <td className="px-3 py-2.5 text-center tabular-nums">
                          <span className={`${r.heat_index >= 60 ? "text-orange-400" : "text-gray-400"}`}>
                            {r.heat_index}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-gray-400 whitespace-nowrap tabular-nums">
                          ${r.registration_cost_usd}/yr
                        </td>
                        <td className="px-3 py-2.5 text-gray-300 tabular-nums">
                          {r.expected_monthly_clicks.toLocaleString()}
                        </td>
                        <td className="px-3 py-2.5 whitespace-nowrap text-xs font-mono">
                          <span className="flex gap-1" title={`Semantic: ${r.semantic_value} · Trend: ${r.trend_relevance} · Market: ${r.market_potential} · Brand: ${r.brandability}`}>
                            <DimScore value={r.semantic_value ?? 0} label="Semantic Value" />
                            <span className="text-gray-700">·</span>
                            <DimScore value={r.trend_relevance ?? 0} label="Trend Relevance" />
                            <span className="text-gray-700">·</span>
                            <DimScore value={r.market_potential ?? 0} label="Market Potential" />
                            <span className="text-gray-700">·</span>
                            <DimScore value={r.brandability ?? 0} label="Brandability" />
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-gray-400 whitespace-nowrap text-xs">
                          {r.language_origin}
                        </td>
                        <td className="px-3 py-2.5 text-gray-400 max-w-xs text-xs" title={r.meaning}>
                          {r.meaning}
                        </td>
                        <td className="px-3 py-2.5">
                          <RegistrarBadges avail={r.registrar_availability} />
                        </td>
                        <td className="px-3 py-2.5 text-gray-500 whitespace-nowrap text-xs">
                          {formatGeo(r.geo_breakdown)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <p className="text-xs text-gray-700 mt-3 text-right">
              Showing {displayed.length} of up to {numResults} requested results
            </p>
          </>
        )}
      </div>
    </main>
  );
}
