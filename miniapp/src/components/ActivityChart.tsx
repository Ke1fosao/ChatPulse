import type { ActivityPoint } from "../api/types";

type ChartMetric = "xp" | "messages" | "reactions" | "replies";

interface ActivityChartProps {
  data: ActivityPoint[];
  metric: ChartMetric;
  title?: string;
}

export function ActivityChart({ data, metric, title = "Динаміка" }: ActivityChartProps) {
  const values = data.map((item) => Number(item[metric] ?? 0));
  const max = Math.max(...values, 1);
  const width = 320;
  const height = 132;
  const gap = data.length > 1 ? width / (data.length - 1) : width;
  const points = values
    .map((value, index) => `${index * gap},${height - (value / max) * 104 - 12}`)
    .join(" ");
  const area = `0,${height} ${points} ${width},${height}`;
  const total = values.reduce((sum, value) => sum + value, 0);

  return (
    <section className="chart-card" aria-label={`${title}: усього ${total}`}>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Останній період</p>
          <h2>{title}</h2>
        </div>
        <strong>{total.toLocaleString("uk-UA")}</strong>
      </div>
      {data.length === 0 ? (
        <div className="chart-empty">Поки немає даних для графіка</div>
      ) : (
        <svg
          className="activity-chart"
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`Графік ${metric} за ${data.length} днів`}
        >
          <defs>
            <linearGradient id="chartArea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.34" />
              <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
            </linearGradient>
          </defs>
          <line x1="0" y1="120" x2="320" y2="120" className="chart-grid" />
          <line x1="0" y1="70" x2="320" y2="70" className="chart-grid" />
          <polygon points={area} fill="url(#chartArea)" />
          <polyline points={points} className="chart-line" />
          {values.map((value, index) => (
            <circle
              className="chart-dot"
              cx={index * gap}
              cy={height - (value / max) * 104 - 12}
              key={`${data[index]?.date}-${metric}`}
              r="3.4"
            />
          ))}
        </svg>
      )}
      <div className="chart-labels" aria-hidden="true">
        {data.map((item) => (
          <span key={item.date}>
            {new Intl.DateTimeFormat("uk-UA", { weekday: "short" }).format(
              new Date(`${item.date}T12:00:00`),
            )}
          </span>
        ))}
      </div>
    </section>
  );
}
