export default function LoadingSpinner({ label = "Processing" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center gap-4 py-10 animate-fade-up">
      <div className="flex gap-2">
        <span className="loading-dot h-2.5 w-2.5 rounded-full" />
        <span className="loading-dot h-2.5 w-2.5 rounded-full" />
        <span className="loading-dot h-2.5 w-2.5 rounded-full" />
      </div>
      <p className="text-sm text-secondary">{label}</p>
    </div>
  );
}
