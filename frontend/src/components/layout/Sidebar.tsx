"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Building2, LayoutDashboard, Radar, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/discovery", label: "Discovery", icon: Radar },
  { href: "/companies", label: "Companies", icon: Building2 },
  { href: "/admin/upload", label: "Admin", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border/60 bg-card/40 p-4 md:flex">
      <div className="mb-8 px-2">
        <p className="bg-gradient-to-r from-violet-300 to-cyan-300 bg-clip-text text-xl font-bold text-transparent">
          KrowLive
        </p>
        <p className="mt-1 text-xs text-muted-foreground">Media &amp; marketing intelligence</p>
      </div>
      <nav className="flex flex-1 flex-col gap-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active =
            pathname === href ||
            (href !== "/" && pathname.startsWith(href)) ||
            (href === "/companies" && pathname.startsWith("/company"));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
                active
                  ? "bg-primary/15 text-primary shadow-glow"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
