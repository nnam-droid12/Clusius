export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold tracking-tight">Clusius</h1>
      <p className="max-w-xl text-center text-sm text-neutral-500">
        Launch a migration run to see live Analyze → Migrate → Tune → Benchmark → Report
        progress, the split-screen x86-vs-Arm cost comparison, and the Pareto frontier of
        the optimization search.
      </p>
    </main>
  );
}
