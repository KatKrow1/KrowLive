"use client";

import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { useEffect } from "react";

function AnimatedNumber({ value, decimals = 0 }: { value: number; decimals?: number }) {
  const motionValue = useMotionValue(0);
  const rounded = useTransform(motionValue, (v) =>
    decimals > 0 ? v.toFixed(decimals) : Math.round(v).toString()
  );

  useEffect(() => {
    const controls = animate(motionValue, value, { duration: 1.2, ease: "easeOut" });
    return controls.stop;
  }, [value, motionValue]);

  return <motion.span>{rounded}</motion.span>;
}

type StatCardsProps = {
  stats: {
    total_companies: number;
    avg_lead_score: number;
    canada_count: number;
    australia_count: number;
    top_industry: string;
  } | null;
  loading: boolean;
  country: "CA" | "AU";
};

export function StatCards({ stats, loading, country }: StatCardsProps) {
  const cards = [
    { label: "Total Companies", value: stats?.total_companies ?? 0, decimals: 0 },
    { label: "Avg Lead Score", value: stats?.avg_lead_score ?? 0, decimals: 1 },
    {
      label: country === "CA" ? "Canada Leads" : "Australia Leads",
      value: country === "CA" ? stats?.canada_count ?? 0 : stats?.australia_count ?? 0,
      decimals: 0,
    },
    { label: "Top Industry", value: stats?.top_industry ?? "—", isText: true },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.08 }}
          className="rounded-xl border border-border bg-card/80 p-5 backdrop-blur"
        >
          <p className="text-sm text-muted-foreground">{card.label}</p>
          <p className="mt-2 text-2xl font-semibold">
            {loading ? (
              <span className="inline-block h-7 w-16 animate-pulse rounded bg-muted" />
            ) : card.isText ? (
              card.value
            ) : (
              <AnimatedNumber value={Number(card.value)} decimals={card.decimals} />
            )}
          </p>
        </motion.div>
      ))}
    </div>
  );
}
