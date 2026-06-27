import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import SearchBar from "../components/SearchBar";
import LoadingSpinner from "../components/LoadingSpinner";
import Logo from "../components/Logo";
import ThemeToggle from "../components/ThemeToggle";
import CameraModal from "../components/CameraModal";
import { getSearchHistory, searchByImage, searchByText } from "../api/client";
import type { ProductScan } from "../types";

export default function HomePage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [recent, setRecent] = useState<ProductScan[]>([]);
  const [isCameraOpen, setIsCameraOpen] = useState(false);

  useEffect(() => {
    getSearchHistory()
      .then((data) => setRecent(data.items))
      .catch(() => setRecent([]));
  }, []);

  const runSearch = async (action: () => Promise<{ product: { id: number } }>) => {
    setError("");
    setLoading(true);
    try {
      const result = await action();
      navigate(`/search/${result.product.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2 text-xs text-muted">
          <span className="rounded-full bg-accent-soft px-2.5 py-1 font-medium text-accent">Gemini Vision</span>
          <span className="rounded-full bg-cyan-soft px-2.5 py-1 font-medium" style={{ color: "var(--cyan)" }}>YOLO v26</span>
        </div>
        <ThemeToggle />
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-4 pb-16">
        <div className="mb-10 animate-fade-up">
          <Logo size="lg" asLink={false} />
        </div>

        <div className="w-full max-w-xl animate-fade-up" style={{ animationDelay: "0.1s" }}>
          <SearchBar
            query={query}
            onQueryChange={setQuery}
            onSearch={() => runSearch(() => searchByText(query))}
            onImageSelect={(file) => runSearch(() => searchByImage(file))}
            onCameraClick={() => setIsCameraOpen(true)}
            loading={loading}
          />
        </div>

        <CameraModal
          isOpen={isCameraOpen}
          onClose={() => setIsCameraOpen(false)}
          onCapture={(blob) => {
            setIsCameraOpen(false);
            runSearch(() => searchByImage(blob));
          }}
          isSearching={loading}
        />

        {loading && <LoadingSpinner label="Running vision pipeline..." />}
        {error && (
          <div className="mt-6 w-full max-w-xl rounded-2xl border border-error/20 bg-error/5 p-4 text-center animate-fade-up">
            <p className="text-sm font-medium text-error">{error}</p>
            {error.includes("rate limit") && (
              <p className="mt-1.5 text-xs text-muted">
                Free-tier Google AI endpoints can experience high traffic. Please wait a few seconds and try again.
              </p>
            )}
          </div>
        )}

        {recent.length > 0 && !loading && (
          <section className="mt-16 w-full max-w-xl animate-fade-up" style={{ animationDelay: "0.15s" }}>
            <h2 className="mb-3 font-display text-xs font-semibold uppercase tracking-widest text-muted">
              Recent scans
            </h2>
            <div className="space-y-1">
              {recent.slice(0, 5).map((item) => (
                <button
                  key={item.id}
                  onClick={() => navigate(`/search/${item.id}`)}
                  className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition hover-bg"
                >
                  <img
                    src={item.image_path}
                    alt=""
                    className="h-11 w-11 rounded-lg border border-theme object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = "/favicon.svg";
                    }}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-primary">
                      {item.brand} {item.model_name}
                    </p>
                    <p className="truncate text-xs text-muted">{item.search_query}</p>
                  </div>
                  <svg className="h-4 w-4 shrink-0 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              ))}
            </div>
          </section>
        )}
      </main>

      <footer className="border-t border-theme px-6 py-4 text-xs text-muted">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-2 sm:flex-row">
          <span>NeuralLens · AI Based Product Image Search</span>
          <span>Gemini · YOLO · SerpAPI · LangChain · Made with ❤️ by Badri</span>
        </div>
      </footer>
    </div>
  );
}
