"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { BarChart3, Building2, Globe2, TrendingUp } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, StateChartPoint, Stats } from "@/lib/api";
import { useAppContext } from "@/lib/context";

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  delay,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="glass rounded-xl p-5 shadow-soft"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p>
          {sub && <p className="mt-1 text-xs text-success">{sub}</p>}
        </div>
        <div className="rounded-lg bg-primary/10 p-2.5 text-primary">
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </motion.div>
  );
}

export default function DashboardPage() {
  const { country } = useAppContext();
  const [stats, setStats] = useState<Stats | null>(null);
  const [chart, setChart] = useState<StateChartPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.getStats(country), api.getChartByState(country)])
      .then(([s, c]) => {
        setStats(s);
        setChart(c.slice(0, 8));
      })
      .finally(() => setLoading(false));
  }, [country]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Media &amp; marketing lead pipeline — {country === "CA" ? "Canada" : "Australia"}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total Companies"
          value={loading ? "—" : stats?.total_companies ?? 0}
          sub="In pipeline"
          icon={Building2}
          delay={0}
        />
        <StatCard
          label="Avg Lead Score"
          value={loading ? "—" : stats?.avg_lead_score ?? 0}
          sub="Data completeness"
          icon={TrendingUp}
          delay={0.05}
        />
        <StatCard
          label={country === "CA" ? "Canada Leads" : "Australia Leads"}
          value={loading ? "—" : country === "CA" ? stats?.canada_count ?? 0 : stats?.australia_count ?? 0}
          icon={Globe2}
          delay={0.1}
        />
        <StatCard
          label="Top Industry"
          value={loading ? "—" : stats?.top_industry ?? "N/A"}
          icon={BarChart3}
          delay={0.15}
        />
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="glass rounded-xl p-5 shadow-soft"
      >
        <h2 className="mb-4 text-sm font-medium text-muted-foreground">Companies by province/state</h2>
        <div className="h-64">
          {chart.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              {loading ? "Loading chart…" : "Run discovery to populate chart data"}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(223 28% 16%)" />
                <XAxis dataKey="state" tick={{ fill: "hsl(215 16% 62%)", fontSize: 12 }} />
                <YAxis tick={{ fill: "hsl(215 16% 62%)", fontSize: 12 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    background: "hsl(222 44% 8%)",
                    border: "1px solid hsl(223 28% 16%)",
                    borderRadius: 8,
                  }}
                />
                <Bar dataKey="count" fill="hsl(262 83% 58%)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </motion.div>
    </div>
  );
}
