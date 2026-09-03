"use client";

import { useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Search, ShoppingBag, Sparkles, Star } from "lucide-react";
import {
  getCategories,
  getProductRecommendations,
  getProductsByCategory,
} from "@/lib/api/endpoints";
import { PRODUCT_TIERS, STALE } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorCard } from "@/components/ui/ErrorCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { SafeImage } from "@/components/ui/SafeImage";
import { track } from "@/lib/api/analytics";
import type { Product } from "@/lib/zod";

export default function ProductsPage() {
  const [tier, setTier] = useState("mid_range");
  const [category, setCategory] = useState<string>("recommended");
  const [search, setSearch] = useState("");

  const cats = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
    staleTime: STALE.products,
  });

  const recs = useQuery({
    queryKey: ["products", tier],
    queryFn: () => getProductRecommendations(tier, 12),
    staleTime: STALE.products,
    enabled: category === "recommended",
  });

  const browse = useQuery({
    queryKey: ["products", "category", category, tier],
    queryFn: () => getProductsByCategory(category, tier),
    staleTime: STALE.products,
    enabled: category !== "recommended",
  });

  const loading = category === "recommended" ? recs.isLoading : browse.isLoading;
  const isError = category === "recommended" ? recs.isError : browse.isError;
  const retry = () => (category === "recommended" ? recs.refetch() : browse.refetch());

  const products: Product[] = useMemo(() => {
    const base =
      category === "recommended" ? (recs.data?.recommendations ?? []) : (browse.data ?? []);
    if (!search.trim()) return base;
    const q = search.trim().toLowerCase();
    return base.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.category.toLowerCase().includes(q) ||
        (p.description ?? "").toLowerCase().includes(q),
    );
  }, [category, recs.data, browse.data, search]);

  const categories = cats.data?.categories ?? [];

  return (
    <div>
      <ScreenHeader
        title="Products"
        subtitle="Matched to your weakest areas — and browsable across every category."
      />

      {/* Category switcher */}
      <div className="mb-4 flex flex-wrap gap-2" role="tablist" aria-label="Product category">
        <CategoryChip
          active={category === "recommended"}
          onClick={() => setCategory("recommended")}
          icon={<Sparkles className="h-3.5 w-3.5" />}
          label="For you"
        />
        {categories.map((c) => (
          <CategoryChip
            key={c.id}
            active={category === c.id}
            onClick={() => setCategory(c.id)}
            label={c.name}
            count={c.count}
          />
        ))}
      </div>

      {/* Budget tier + search */}
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <div className="flex gap-2" role="tablist" aria-label="Budget tier">
          {PRODUCT_TIERS.map((t) => (
            <button
              key={t.value}
              type="button"
              role="tab"
              aria-selected={tier === t.value}
              onClick={() => setTier(t.value)}
              className={cn(
                "rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                tier === t.value
                  ? "border-gold bg-gold/15 text-gold-bright"
                  : "border-border-soft bg-surface-2 text-muted hover:text-ink",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="relative ml-auto w-full sm:w-56">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search products…"
            className="h-9 w-full rounded-full border border-border-soft bg-surface-2 pl-9 pr-3 text-sm text-ink placeholder:text-muted focus:border-gold/50 focus:outline-none"
          />
        </div>
      </div>

      {loading ? (
        <ProductsSkeleton />
      ) : isError ? (
        <div className="mx-auto max-w-md pt-10">
          <ErrorCard message="Something went wrong. Please try again." onRetry={retry} />
        </div>
      ) : products.length ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<ShoppingBag className="h-8 w-8" />}
          title={search ? "No matches" : "No products in this category"}
          description={
            search
              ? "Try a different search term."
              : "Switch category or tier to see more products."
          }
        />
      )}

      <p className="mt-6 text-center text-xs text-muted">
        We may earn a commission if you buy through these links. Affiliate links open in a new tab.
      </p>
    </div>
  );
}

function CategoryChip({
  active,
  onClick,
  label,
  count,
  icon,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count?: number;
  icon?: ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
        active
          ? "border-gold bg-gold/15 text-gold-bright"
          : "border-border-soft bg-surface-2 text-muted hover:text-ink",
      )}
    >
      {icon}
      {label}
      {count != null ? <span className="text-xs opacity-70">{count}</span> : null}
    </button>
  );
}

function ProductCard({ product }: { product: Product }) {
  const price =
    product.price != null
      ? `${product.price.toFixed(2)} ${product.currency || "USD"}`
      : "Check price";

  return (
    <a
      href={product.url}
      target="_blank"
      rel="noopener noreferrer sponsored"
      onClick={() =>
        track("product_click", { metadata: { product_id: product.id, name: product.name } })
      }
      className="card-border card-hover flex flex-col overflow-hidden rounded-card"
    >
      <SafeImage src={product.image_url} alt={product.name} className="h-36 w-full bg-surface-2" />
      <div className="flex flex-1 flex-col p-4">
        <div className="mb-2 flex items-start justify-between gap-2">
          <Badge variant="muted">{product.category?.replace(/_/g, " ") || "General"}</Badge>
          {product.rating != null ? (
            <span className="inline-flex items-center gap-1 text-xs text-muted">
              <Star className="h-3.5 w-3.5 text-gold" aria-hidden />
              {product.rating.toFixed(1)}
              {product.review_count > 0 ? ` (${formatCount(product.review_count)})` : ""}
            </span>
          ) : null}
        </div>
        <h3 className="line-clamp-2 text-sm font-medium text-ink">{product.name}</h3>
        {product.description ? (
          <p className="mt-1 line-clamp-2 text-xs text-muted">{product.description}</p>
        ) : null}
        <div className="mt-auto flex items-center justify-between pt-3">
          <span className="font-display text-sm font-bold text-gold-bright">{price}</span>
          <ArrowUpRight className="h-4 w-4 text-muted" aria-hidden />
        </div>
      </div>
    </a>
  );
}

function formatCount(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function ProductsSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Skeleton className="h-9 w-20" />
        <Skeleton className="h-9 w-20" />
        <Skeleton className="h-9 w-20" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-56" />
        ))}
      </div>
    </div>
  );
}
