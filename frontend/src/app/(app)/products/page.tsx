"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, ShoppingBag, Star } from "lucide-react";
import { getProductRecommendations } from "@/lib/api/endpoints";
import { PRODUCT_TIERS, STALE } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorCard } from "@/components/ui/ErrorCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import type { Product } from "@/lib/zod";

export default function ProductsPage() {
  const [tier, setTier] = useState("mid_range");

  const q = useQuery({
    queryKey: ["products", tier],
    queryFn: () => getProductRecommendations(tier),
    staleTime: STALE.products,
  });

  if (q.isLoading) return <ProductsSkeleton />;
  if (q.isError) {
    return (
      <div className="mx-auto max-w-md pt-10">
        <ErrorCard message="Something went wrong. Please try again." onRetry={() => q.refetch()} />
      </div>
    );
  }

  const data = q.data;
  const products = data?.recommendations ?? [];

  return (
    <div>
      <ScreenHeader
        title="Products"
        subtitle="Because your weakest areas are skin & jawline…"
      />

      {/* Budget filter */}
      <div className="mb-5 flex gap-2" role="tablist" aria-label="Budget tier">
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

      {products.length ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<ShoppingBag className="h-8 w-8" />}
          title="No recommendations yet"
          description="Analyze a photo first to get products matched to your weakest areas."
        />
      )}

      <p className="mt-6 text-center text-xs text-muted">
        We may earn a commission if you buy through these links. Affiliate links open in a new tab.
      </p>
    </div>
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
      className="card-border flex flex-col rounded-card p-4 transition-colors hover:border-gold/40"
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <Badge variant="muted">{product.category || "General"}</Badge>
        {product.rating != null ? (
          <span className="inline-flex items-center gap-1 text-xs text-muted">
            <Star className="h-3.5 w-3.5 text-gold" aria-hidden />
            {product.rating.toFixed(1)}
            {product.review_count > 0 ? ` (${product.review_count})` : ""}
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
    </a>
  );
}

function ProductsSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-9 w-40" />
      <div className="flex gap-2">
        <Skeleton className="h-9 w-20" />
        <Skeleton className="h-9 w-20" />
        <Skeleton className="h-9 w-20" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
    </div>
  );
}
