import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import SearchBar from "../components/SearchBar";
import BoundingBoxOverlay from "../components/BoundingBoxOverlay";
import PriceGrid from "../components/PriceGrid";
import ChatPanel from "../components/ChatPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import Logo from "../components/Logo";
import ThemeToggle from "../components/ThemeToggle";
import { formatPrice, getSearchResult, searchByImage, searchByText } from "../api/client";
import CameraModal from "../components/CameraModal";
import type { SearchResult } from "../types";

const POLL_INTERVAL = 2000;
const MAX_POLLS = 30;

export default function ResultsPage() {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<SearchResult | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"shopping" | "about" | "chat">("shopping");
  const [isCameraOpen, setIsCameraOpen] = useState(false);

  const fetchResult = useCallback(async (id: number, silent = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await getSearchResult(id);
      setResult(data);
      setQuery(data.product.search_query);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load results");
      return null;
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const id = Number(productId);
    if (!id) return;

    let cancelled = false;
    let pollCount = 0;

    const poll = async () => {
      const data = await fetchResult(id, pollCount > 0);
      if (cancelled || !data) return;

      if (data.status === "complete" || data.price_count > 0) {
        setPolling(false);
        return;
      }

      pollCount += 1;
      if (pollCount < MAX_POLLS) {
        setPolling(true);
        setTimeout(poll, POLL_INTERVAL);
      } else {
        setPolling(false);
      }
    };

    poll();
    return () => {
      cancelled = true;
    };
  }, [productId, fetchResult]);

  const handleNewSearch = async (action: () => Promise<SearchResult>) => {
    setError("");
    setLoading(true);
    try {
      const data = await action();
      navigate(`/search/${data.product.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setLoading(false);
    }
  };

  if (loading && !result) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner label="Loading scan results..." />
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p className="text-error">{error || "Results not found"}</p>
        <Link to="/" className="text-accent hover:underline">
          Back to NeuralLens
        </Link>
      </div>
    );
  }

  const { product, prices } = result;
  const title = [product.brand, product.model_name].filter(Boolean).join(" ") || product.search_query;
  const lowestPrice = prices.length > 0 ? Math.min(...prices.map((p) => p.price)) : null;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-theme bg-glass px-4 py-3 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center gap-4">
          <Logo size="sm" />
          <div className="flex-1">
            <SearchBar
              compact
              query={query}
              onQueryChange={setQuery}
              onSearch={() => handleNewSearch(() => searchByText(query))}
              onImageSelect={(file) => handleNewSearch(() => searchByImage(file))}
              onCameraClick={() => setIsCameraOpen(true)}
              loading={loading}
            />
          </div>
          <ThemeToggle />
        </div>
      </header>

      <CameraModal
        isOpen={isCameraOpen}
        onClose={() => setIsCameraOpen(false)}
        onCapture={(blob) => {
          setIsCameraOpen(false);
          handleNewSearch(() => searchByImage(blob));
        }}
        isSearching={loading}
      />

      <div className="mx-auto max-w-6xl px-4 py-6 animate-fade-up">
        <div className="mb-2 flex items-center gap-2 text-sm text-muted">
          <span>{prices.length || "…"} listings</span>
          {polling && (
            <>
              <span>·</span>
              <span className="flex items-center gap-1.5 text-accent">
                <span className="loading-dot inline-block h-1.5 w-1.5 rounded-full" />
                Syncing prices
              </span>
            </>
          )}
        </div>

        <h1 className="font-display text-2xl font-semibold text-primary">{title}</h1>
        {lowestPrice !== null && (
          <p className="mt-1 text-sm text-success">
            Best price from {formatPrice(lowestPrice, prices[0]?.currency || "INR")}
          </p>
        )}

        <nav className="mt-5 flex gap-1 border-b border-theme text-sm">
          {(["shopping", "about", "chat"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 pb-3 font-medium capitalize transition ${
                activeTab === tab ? "tab-active" : "tab-inactive"
              }`}
            >
              {tab === "shopping" ? "Market Prices" : tab === "about" ? "Scan Details" : "AI Assistant"}
            </button>
          ))}
        </nav>

        {error && (
          <div className="mt-4 rounded-2xl border border-error/20 bg-error/5 p-4 text-center animate-fade-up">
            <p className="text-sm font-medium text-error">{error}</p>
            {error.includes("rate limit") && (
              <p className="mt-1.5 text-xs text-muted">
                Free-tier Google AI endpoints can experience high traffic. Please wait a few seconds and try again.
              </p>
            )}
          </div>
        )}

        {activeTab === "shopping" && (
          <div className="mt-6">
            <PriceGrid prices={prices} loading={polling && prices.length === 0} />
          </div>
        )}

        {activeTab === "about" && (
          <div className="mt-6 grid gap-8 lg:grid-cols-2">
            <div className="card p-4">
              <BoundingBoxOverlay product={product} />
              {product.bounding_box && (
                <p className="mt-3 text-xs text-muted">YOLO detection overlay · normalized 0–1000 coords</p>
              )}
            </div>
            <div className="space-y-5">
              <div className="card p-5">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Description</h3>
                <p className="mt-2 text-sm leading-relaxed text-primary">
                  {product.description || "No description available."}
                </p>
              </div>
              {product.specification?.length > 0 && (
                <div className="card p-5">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Specifications</h3>
                  <ul className="mt-2 space-y-1.5">
                    {product.specification.map((spec, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-primary">
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                        {spec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="card grid grid-cols-2 gap-4 p-5 text-sm">
                <div>
                  <span className="text-muted">Brand</span>
                  <p className="mt-0.5 font-medium text-primary">{product.brand || "—"}</p>
                </div>
                <div>
                  <span className="text-muted">Color</span>
                  <p className="mt-0.5 font-medium text-primary">{product.color || "—"}</p>
                </div>
                <div className="col-span-2">
                  <span className="text-muted">Optimized query</span>
                  <p className="mt-0.5 font-medium text-primary">{product.search_query}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "chat" && (
          <div className="mt-6 h-[500px]">
            <ChatPanel sessionId={product.id} />
          </div>
        )}
      </div>
    </div>
  );
}
