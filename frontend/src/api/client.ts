import type { ChatMessage, ProductScan, SearchResult, DetectedObject } from "../types";

const API_BASE = "/api/v1/ai";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    if (response.status === 429) {
      throw new Error("Gemini API rate limit reached. Server is busy, please try again in a few moments.");
    }
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Request failed");
  }
  return response.json();
}

export async function detectObjects(file: Blob): Promise<{ objects: DetectedObject[] }> {
  const form = new FormData();
  form.append("file", file, "frame.jpg");
  const response = await fetch(`${API_BASE}/detect`, { method: "POST", body: form });
  return handleResponse<{ objects: DetectedObject[] }>(response);
}

export async function searchByImage(file: File | Blob): Promise<SearchResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE}/search?`, { method: "POST", body: form });
  return handleResponse<SearchResult>(response);
}

export async function searchByText(query: string): Promise<SearchResult> {
  const response = await fetch(`${API_BASE}/search/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  return handleResponse<SearchResult>(response);
}

export async function getSearchResult(productId: number): Promise<SearchResult> {
  const response = await fetch(`${API_BASE}/search/${productId}`);
  return handleResponse<SearchResult>(response);
}

export async function getSearchHistory(page = 1): Promise<{ items: ProductScan[]; total: number }> {
  const response = await fetch(`${API_BASE}/search/history?page=${page}&page_size=8`);
  return handleResponse(response);
}

export async function streamChat(
  sessionId: number,
  query: string,
  chatHistory: ChatMessage[],
  onToken: (token: string) => void,
): Promise<void> {
  const response = await fetch(`${API_BASE}/chat/${sessionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, chat_history: chatHistory }),
  });

  if (!response.ok || !response.body) {
    throw new Error("Chat request failed");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    onToken(decoder.decode(value, { stream: true }));
  }
}

export function formatPrice(price: number, currency: string): string {
  if (currency === "INR") return `₹${price.toLocaleString("en-IN")}`;
  return `${currency} ${price.toLocaleString()}`;
}
