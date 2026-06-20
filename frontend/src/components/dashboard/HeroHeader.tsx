"use client";

import { motion } from "framer-motion";

export function HeroHeader() {
  return (
    <motion.header
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-2xl border border-border bg-card p-8"
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-violet-600/20 via-fuchsia-600/10 to-transparent" />
      <div className="relative">
        <h1 className="bg-gradient-to-r from-violet-300 via-fuchsia-300 to-violet-200 bg-clip-text text-4xl font-bold tracking-tight text-transparent">
          KrowLive
        </h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          B2B lead intelligence for media &amp; marketing companies in Canada &amp; Australia.
        </p>
      </div>
    </motion.header>
  );
}
