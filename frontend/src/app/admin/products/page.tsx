"use client";

import { useState, type ChangeEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  activateProduct,
  createProduct,
  deleteProduct,
  getAdminProducts,
  importProducts,
  updateProduct,
  type AdminProduct,
} from "@/lib/api/admin";
import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Skeleton";

const CATEGORIES = ["skin_quality", "jawline_definition", "eye_appeal", "facial_structure", "grooming", "general"];
const TIERS = ["budget", "mid_range", "premium"];

type FormState = {
  name: string;
  brand: string;
  category: string;
  price: string;
  currency: string;
  tier: string;
  image_url: string;
  affiliate_url: string;
  description: string;
  rating: string;
  review_count: string;
  commission: string;
};

function toForm(p?: AdminProduct): FormState {
  return {
    name: p?.name ?? "",
    brand: p?.brand ?? "",
    category: p?.category ?? "skin_quality",
    price: p?.price != null ? String(p.price) : "",
    currency: p?.currency || "USD",
    tier: p?.tier || "mid_range",
    image_url: p?.image_url ?? "",
    affiliate_url: p?.affiliate_url ?? "",
    description: p?.description ?? "",
    rating: p?.rating != null ? String(p.rating) : "",
    review_count: p ? String(p.review_count) : "",
    commission: p?.commission != null ? String(p.commission) : "",
  };
}

function toPayload(f: FormState): Record<string, unknown> {
  return {
    name: f.name,
    brand: f.brand || null,
    category: f.category,
    price: f.price === "" ? 0 : Number(f.price),
    currency: f.currency || "USD",
    tier: f.tier,
    image_url: f.image_url || null,
    affiliate_url: f.affiliate_url || null,
    description: f.description || null,
    rating: f.rating === "" ? null : Number(f.rating),
    review_count: f.review_count === "" ? 0 : Number(f.review_count),
    commission: f.commission === "" ? null : Number(f.commission),
  };
}

function ProductForm({
  initial,
  saving,
  onSave,
  onCancel,
}: {
  initial: AdminProduct | null;
  saving: boolean;
  onSave: (payload: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [f, setF] = useState<FormState>(toForm(initial ?? undefined));
  const set = (k: keyof FormState) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setF((prev) => ({ ...prev, [k]: e.target.value }));

  const field = (k: keyof FormState, label: string, placeholder = "") => (
    <Input id={`p-${k}`} label={label} value={f[k]} onChange={set(k)} placeholder={placeholder} />
  );

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSave(toPayload(f));
      }}
      className="space-y-3"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        {field("name", "Name *", "Hydrating Cleanser")}
        {field("brand", "Brand", "CeraVe")}
        <div className="space-y-1.5">
          <label htmlFor="p-category" className="block text-sm font-medium text-muted">
            Category
          </label>
          <select
            id="p-category"
            value={f.category}
            onChange={set("category")}
            className="h-11 w-full rounded-xl border border-border-soft bg-surface-2 px-3 text-sm text-ink"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="p-tier" className="block text-sm font-medium text-muted">
            Tier
          </label>
          <select
            id="p-tier"
            value={f.tier}
            onChange={set("tier")}
            className="h-11 w-full rounded-xl border border-border-soft bg-surface-2 px-3 text-sm text-ink"
          >
            {TIERS.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        {field("price", "Price", "14.99")}
        {field("currency", "Currency", "USD")}
        {field("rating", "Rating (0–5)", "4.5")}
        {field("review_count", "Review count", "89500")}
        {field("commission", "Commission", "0.05")}
        {field("image_url", "Image URL")}
        {field("affiliate_url", "Affiliate URL")}
        {field("description", "Description / social proof")}
      </div>
      <div className="flex gap-2">
        <Button type="submit" loading={saving}>
          Save
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

export default function AdminProducts() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<AdminProduct | null>(null);

  const products = useQuery({
    queryKey: ["admin-products"],
    queryFn: () => getAdminProducts({ limit: 500 }),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin-products"] });

  const createMut = useMutation({
    mutationFn: createProduct,
    onSuccess: () => {
      invalidate();
      setShowForm(false);
    },
  });
  const updateMut = useMutation({
    mutationFn: (v: { id: string; payload: Record<string, unknown> }) =>
      updateProduct(v.id, v.payload),
    onSuccess: () => {
      invalidate();
      setShowForm(false);
      setEditing(null);
    },
  });
  const deleteMut = useMutation({ mutationFn: deleteProduct, onSuccess: invalidate });
  const activateMut = useMutation({ mutationFn: activateProduct, onSuccess: invalidate });
  const importMut = useMutation({ mutationFn: importProducts, onSuccess: invalidate });

  const openNew = () => {
    setEditing(null);
    setShowForm(true);
  };
  const openEdit = (p: AdminProduct) => {
    setEditing(p);
    setShowForm(true);
  };

  const handleSave = (payload: Record<string, unknown>) => {
    if (editing) updateMut.mutate({ id: editing.id, payload });
    else createMut.mutate(payload);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-ink">Products</h1>
          <p className="text-sm text-muted">Add, edit, archive and re-activate products — no redeploys.</p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button variant="secondary" size="sm" loading={importMut.isPending} onClick={() => importMut.mutate()}>
            Re-import JSON
          </Button>
          <Button size="sm" onClick={openNew}>
            + New product
          </Button>
        </div>
      </div>

      {showForm && (
        <Card>
          <CardTitle className="mb-4">{editing ? "Edit product" : "New product"}</CardTitle>
          <ProductForm
            initial={editing}
            saving={createMut.isPending || updateMut.isPending}
            onSave={handleSave}
            onCancel={() => {
              setShowForm(false);
              setEditing(null);
            }}
          />
        </Card>
      )}

      <Card>
        {products.isLoading ? (
          <div className="flex justify-center py-10">
            <Spinner className="h-6 w-6" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-soft text-left text-muted">
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Category</th>
                  <th className="py-2 pr-4 font-medium">Tier</th>
                  <th className="py-2 pr-4 font-medium">Price</th>
                  <th className="py-2 pr-4 font-medium">Rating</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.data?.products.map((p) => (
                  <tr key={p.id} className="border-b border-border-soft/50">
                    <td className="py-2 pr-4">
                      <div className="text-ink">{p.name}</div>
                      <div className="text-xs text-muted">{p.brand}</div>
                    </td>
                    <td className="py-2 pr-4 text-muted">{p.category}</td>
                    <td className="py-2 pr-4 text-muted">{p.tier}</td>
                    <td className="py-2 pr-4 tabular text-ink">
                      {p.price != null ? `${p.currency} ${p.price}` : "—"}
                    </td>
                    <td className="py-2 pr-4 tabular text-ink">{p.rating ?? "—"}</td>
                    <td className="py-2 pr-4">
                      <Badge variant={p.is_active ? "success" : "muted"}>
                        {p.is_active ? "active" : "archived"}
                      </Badge>
                    </td>
                    <td className="py-2">
                      <div className="flex gap-2">
                        <Button size="sm" variant="secondary" onClick={() => openEdit(p)}>
                          Edit
                        </Button>
                        {p.is_active ? (
                          <Button size="sm" variant="danger" onClick={() => deleteMut.mutate(p.id)}>
                            Archive
                          </Button>
                        ) : (
                          <Button size="sm" onClick={() => activateMut.mutate(p.id)}>
                            Activate
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {products.data && products.data.products.length === 0 && (
                  <tr>
                    <td className="py-6 text-center text-muted" colSpan={7}>
                      No products.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

