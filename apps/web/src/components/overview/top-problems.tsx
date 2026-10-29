import type { Dashboard } from "@/lib/api";
import { PROBLEM_LABELS } from "@/lib/format";

/** The most common 3-way match problems, as labelled bars (the counts are written out). */
export function TopProblems({ problems }: { problems: Dashboard["top_problems"] }) {
  if (problems.length === 0) {
    return <p className="text-sm text-muted-foreground">No problems found so far.</p>;
  }
  const largest = Math.max(...problems.map((problem) => problem.count));

  return (
    <ul className="flex flex-col gap-4">
      {problems.map((problem) => (
        <li key={problem.code}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="truncate">{PROBLEM_LABELS[problem.code] ?? problem.code}</span>
            <span className="numeric text-muted-foreground">{problem.count}</span>
          </div>
          <div className="mt-1.5 h-1.5 rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary/80"
              style={{ width: `${(problem.count / largest) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
