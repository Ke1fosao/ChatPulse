import type { HeatmapPoint } from "../api/types";

const weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"];
const buckets: Array<HeatmapPoint["bucket"]> = ["night", "morning", "day"];
const bucketLabels = {
  night: "Ніч",
  morning: "Ранок",
  day: "День",
};

interface HeatmapProps {
  data: HeatmapPoint[];
}

export function Heatmap({ data }: HeatmapProps) {
  const max = Math.max(...data.map((item) => item.value), 1);
  const valueFor = (weekday: number, bucket: HeatmapPoint["bucket"]) =>
    data.find((item) => item.weekday === weekday && item.bucket === bucket)?.value ?? 0;

  return (
    <section className="panel heatmap-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Ритм групи</p>
          <h2>Коли чат оживає</h2>
        </div>
      </div>
      <div className="heatmap" role="table" aria-label="Теплова карта активності">
        <div className="heatmap__corner" />
        {weekdays.map((day) => (
          <span className="heatmap__day" key={day}>
            {day}
          </span>
        ))}
        {buckets.map((bucket) => (
          <div className="heatmap__row" key={bucket}>
            <span className="heatmap__label">{bucketLabels[bucket]}</span>
            {weekdays.map((day, weekday) => {
              const value = valueFor(weekday, bucket);
              const intensity = value / max;
              return (
                <span
                  className="heatmap__cell"
                  key={`${day}-${bucket}`}
                  style={{ "--heat": intensity } as React.CSSProperties}
                  title={`${day}, ${bucketLabels[bucket]}: ${value}`}
                  aria-label={`${day}, ${bucketLabels[bucket]}: ${value}`}
                />
              );
            })}
          </div>
        ))}
      </div>
    </section>
  );
}
