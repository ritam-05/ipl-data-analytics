"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

export interface ChartSpec {
  data: Array<{
    type: string;
    x: Array<string | number>;
    y: Array<number>;
    name?: string;
    mode?: string;
  }>;
  layout?: {
    title?: string;
    xaxis?: { title?: string };
    yaxis?: { title?: string };
  };
}

interface DynamicChartProps {
  spec: ChartSpec;
}

export default function DynamicChart({ spec }: DynamicChartProps) {
  const trace = spec?.data?.[0];
  if (!trace || !Array.isArray(trace.x) || !Array.isArray(trace.y) || trace.x.length === 0) {
    return null;
  }

  const chartData = trace.x.map((xVal, idx) => ({
    label: String(xVal),
    value: Number(trace.y[idx] ?? 0),
  }));

  const isLine = trace.type === "scatter" || trace.type === "line";
  const seriesName = trace.name || "Value";
  const title = spec.layout?.title || seriesName;

  return (
    <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/80 p-4">
      <p className="mb-3 text-xs font-semibold text-amber-400">{title}</p>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {isLine ? (
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="label" stroke="#94a3b8" fontSize={11} />
              <YAxis stroke="#94a3b8" fontSize={11} domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0f172a",
                  borderColor: "#334155",
                  borderRadius: 8,
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                name={seriesName}
                stroke="#f59e0b"
                strokeWidth={2.5}
                dot={{ r: 3 }}
              />
            </LineChart>
          ) : (
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="label"
                stroke="#94a3b8"
                fontSize={10}
                interval={0}
                angle={-20}
                textAnchor="end"
                height={55}
              />
              <YAxis stroke="#94a3b8" fontSize={11} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0f172a",
                  borderColor: "#334155",
                  borderRadius: 8,
                }}
              />
              <Bar dataKey="value" name={seriesName} fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}