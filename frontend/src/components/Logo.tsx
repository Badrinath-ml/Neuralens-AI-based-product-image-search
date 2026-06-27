import { Link } from "react-router-dom";

interface LogoProps {
  size?: "sm" | "lg";
  asLink?: boolean;
}

export default function Logo({ size = "lg", asLink = true }: LogoProps) {
  const textSize = size === "lg" ? "text-4xl sm:text-5xl" : "text-xl";
  const iconSize = size === "lg" ? "h-10 w-10 sm:h-12 sm:w-12" : "h-7 w-7";

  const content = (
    <div className={`flex items-center gap-3 ${size === "lg" ? "flex-col sm:flex-row" : ""}`}>
      <div
        className={`${iconSize} flex shrink-0 items-center justify-center rounded-2xl shadow-glow`}
        style={{ background: "var(--gradient-brand)" }}
      >
        <svg className={size === "lg" ? "h-6 w-6" : "h-4 w-4"} viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="3" stroke="white" strokeWidth="1.5" />
          <circle cx="12" cy="12" r="7" stroke="white" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.7" />
          <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="1" opacity="0.4" />
          <path d="M12 2v2M12 20v2M2 12h2M20 12h2" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </div>
      <div className={size === "lg" ? "text-center sm:text-left" : ""}>
        <span className={`font-display font-bold tracking-tight brand-gradient-text ${textSize}`}>
          NeuralLens
        </span>
        {size === "lg" && (
          <p className="mt-1 text-sm text-secondary">
            Vision AI · Object Detection · Price Intelligence
          </p>
        )}
      </div>
    </div>
  );

  if (asLink) {
    return (
      <Link to="/" className="inline-block transition-opacity hover:opacity-90">
        {content}
      </Link>
    );
  }

  return content;
}
