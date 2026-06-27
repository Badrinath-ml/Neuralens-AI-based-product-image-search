import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMarkdownProps {
  content: string;
  streaming?: boolean;
}

export default function ChatMarkdown({ content, streaming }: ChatMarkdownProps) {
  if (!content && streaming) {
    return <span className="text-muted">▍</span>;
  }

  if (!content) return null;

  return (
    <div className="chat-markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      {streaming && <span className="ml-0.5 inline-block animate-pulse text-accent">▍</span>}
    </div>
  );
}
