import type { ProductScan } from "../types";

interface BoundingBoxOverlayProps {
  product: ProductScan;
}

export default function BoundingBoxOverlay({ product }: BoundingBoxOverlayProps) {
  const box = product.bounding_box;

  return (
    <div className="relative inline-block max-w-full">
      <img
        src={product.image_path}
        alt={product.search_query}
        className="max-h-80 rounded-2xl border border-theme object-contain shadow-theme"
        onError={(e) => {
          (e.target as HTMLImageElement).src = "/favicon.svg";
        }}
      />
      {box && (
        <div
          className="pointer-events-none absolute rounded-sm"
          style={{
            left: `${box.xmin / 10}%`,
            top: `${box.ymin / 10}%`,
            width: `${(box.xmax - box.xmin) / 10}%`,
            height: `${(box.ymax - box.ymin) / 10}%`,
            border: "2px solid var(--bbox)",
            background: "var(--accent-soft)",
            boxShadow: "0 0 12px var(--accent-glow)",
          }}
        />
      )}
    </div>
  );
}
