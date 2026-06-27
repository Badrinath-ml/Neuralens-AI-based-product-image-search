export interface ProductScan {
  id: number;
  brand: string | null;
  model_name: string | null;
  color: string | null;
  specification: string[];
  description: string | null;
  search_query: string;
  image_path: string;
  bounding_box: { xmin: number; ymin: number; xmax: number; ymax: number } | null;
  created_at: string;
}

export interface PriceResult {
  id: number;
  title: string;
  price: number;
  currency: string;
  source_website: string;
  product_url: string;
  thumbnail_url: string | null;
  fetched_at: string;
}

export type SearchStatus = "analyzing" | "fetching_prices" | "complete" | "failed";

export interface SearchResult {
  product: ProductScan;
  prices: PriceResult[];
  status: SearchStatus;
  price_count: number;
}

export interface ChatMessage {
  sender: "user" | "assistant";
  text: string;
}

export interface DetectedObject {
  box: {
    xmin: number;
    ymin: number;
    xmax: number;
    ymax: number;
  };
  label: string;
  confidence: number;
}
