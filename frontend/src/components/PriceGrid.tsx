import type { PriceResult } from "../types";
import { formatPrice } from "../api/client";

interface PriceGridProps {
  prices: PriceResult[];
  loading?: boolean;
}

export default function PriceGrid({ prices, loading }: PriceGridProps) {
  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="skeleton h-52 rounded-2xl" />
        ))}
      </div>
    );
  }

  if (prices.length === 0) {
    return (
      <div className="card border-dashed p-10 text-center text-secondary">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft">
          <svg className="h-6 w-6 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" strokeLinecap="round" />
          </svg>
        </div>
        Fetching live market prices from shopping APIs...
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {prices.map((item) => (
        <a
          key={item.id}
          href={item.product_url}
          target="_blank"
          rel="noopener noreferrer"
          className="card group flex flex-col overflow-hidden hover:-translate-y-0.5 hover:shadow-glow"
        >
          <div className="flex h-36 items-center justify-center bg-muted p-4">
            {item.thumbnail_url ? (
              <img src={item.thumbnail_url} alt={item.title} className="max-h-full max-w-full object-contain transition group-hover:scale-105" />
            ) : (
              <div className="text-3xl opacity-30">◈</div>
            )}
          </div>
          <div className="flex flex-1 flex-col gap-1.5 p-4">
            <p className="line-clamp-2 text-sm text-primary group-hover:text-accent">{item.title}</p>
            <p className="font-display text-lg font-semibold text-primary">{formatPrice(item.price, item.currency)}</p>
            <p className="text-xs text-muted">{item.source_website}</p>
          </div>
        </a>
      ))}
    </div>
  );
}
