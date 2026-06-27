import { useRef } from "react";

interface SearchBarProps {
  query: string;
  onQueryChange: (value: string) => void;
  onSearch: () => void;
  onImageSelect: (file: File) => void;
  onCameraClick?: () => void;
  loading?: boolean;
  compact?: boolean;
}

export default function SearchBar({
  query,
  onQueryChange,
  onSearch,
  onImageSelect,
  onCameraClick,
  loading,
  compact,
}: SearchBarProps) {
  const fileRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && query.trim()) onSearch();
  };

  return (
    <div className={`w-full ${compact ? "max-w-2xl" : "max-w-xl"}`}>
      <div
        className={`input-field flex items-center gap-2 rounded-2xl px-3.5 shadow-theme ${
          compact ? "h-11" : "h-13 py-1"
        }`}
        style={{ height: compact ? undefined : "3.25rem" }}
      >
        <svg className="h-5 w-5 shrink-0 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" strokeLinecap="round" />
        </svg>
        <input
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search by product name, brand, or model..."
          className="flex-1 bg-transparent text-base outline-none placeholder:text-muted min-w-0"
          disabled={loading}
        />
        {onCameraClick && (
          <button
            type="button"
            onClick={onCameraClick}
            className="flex items-center gap-1 rounded-xl bg-cyan-soft px-2.5 py-1.5 text-xs transition hover:opacity-85"
            style={{ color: "var(--cyan)", background: "var(--cyan-soft)" }}
            title="Camera Lens — snapshot & live stream"
            disabled={loading}
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
            {!compact && <span className="hidden sm:inline">Camera</span>}
          </button>
        )}
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="flex items-center gap-1 rounded-xl bg-accent-soft px-2.5 py-1.5 text-xs text-accent transition hover:opacity-85"
          title="Visual search — upload image"
          disabled={loading}
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="5" width="18" height="14" rx="2" />
            <circle cx="8.5" cy="10.5" r="1.5" fill="currentColor" stroke="none" />
            <path d="M21 17l-5-5-4 4-2-2-5 5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {!compact && <span className="hidden sm:inline">Upload</span>}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onImageSelect(file);
            e.target.value = "";
          }}
        />
      </div>
      {!compact && (
        <div className="mt-5 flex justify-center gap-3">
          <button
            onClick={onSearch}
            disabled={loading || !query.trim()}
            className="btn-primary rounded-xl px-5 py-2.5 text-sm font-medium"
          >
            Search
          </button>
          <button
            onClick={() => fileRef.current?.click()}
            disabled={loading}
            className="btn-secondary rounded-xl px-5 py-2.5 text-sm font-medium"
          >
            Upload Image
          </button>
        </div>
      )}
    </div>
  );
}
