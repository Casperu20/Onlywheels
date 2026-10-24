"""
Catalog search with Meilisearch (phase 4) – not installed yet; PostgreSQL search is used today.

Plan:
- `MEILISEARCH_URL` / `MEILISEARCH_KEY` in env; index "products" with documents built from
  Product + active variants: name, brand, type, style, finishes, diameters, pcd list,
  tire sizes, min price, in_stock, rating.
- Filterable: type, brand, diameters, finishes, pcd, in_stock; sortable: min_price, rating.
- `reindex_product(product_id)` is called from a post_save signal on Product/ProductVariant/StockItem
  through Celery; `reindex_all()` is a management command.
- `catalog.filters.ProductFilter.filter_search` switches to Meilisearch when configured and
  filters the queryset by the returned ids (keeping fitment filtering in PostgreSQL).
"""


def reindex_product(product_id) -> None:
    raise NotImplementedError("Meilisearch is planned for phase 4 (see module docstring).")


def reindex_all() -> None:
    raise NotImplementedError("Meilisearch is planned for phase 4 (see module docstring).")
