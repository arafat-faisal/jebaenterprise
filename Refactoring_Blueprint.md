# Project Refactoring Blueprint: JebaEnterprise Modularization

## Objective
Refactor monolithic `products` app into modular apps while **preserving all production data** using `db_table` mapping and `--fake-initial` migrations.

## Migration Strategy (Crucial for Production)
1.  **Create Apps:** Initialize `jeba_core`, `jeba_inventory`, `jeba_sales`, `jeba_accounts`, `jeba_engagement`, `jeba_intelligence`, `jeba_analytics`.
2.  **Move Models:** Copy model code to new apps.
3.  **Map Tables:** Add `class Meta: db_table = 'products_<model_name>'` to EVERY new model. This links the new code to the old data.
4.  **Translation Prep:** Wrap all verbose names and help texts in `gettext_lazy` as `_()`.
5.  **Deprecate Old App:** Delete `models.py` content in `products` (or make them Abstract/Proxy if needed, but deletion is cleaner if we fake the migration).
6.  **Deploy:**
    * `python manage.py makemigrations`
    * `python manage.py migrate --fake-initial` (This detects existing tables and skips creation).

## Module Structure
* **jeba_core:** `SiteSettings` (Table: `products_sitesettings`)
* **jeba_inventory:** `Category`, `Product`, `ProductVariation`, `ProductImage` (Tables: `products_category`, etc.)
* **jeba_sales:** `Sale`, `SaleItem` (Tables: `products_sale`, etc.)
* **jeba_accounts:** `UserProfile` (Table: `products_userprofile`)
* **jeba_engagement:** `Review`, `Wishlist` (Tables: `products_review`, etc.)
* **jeba_intelligence:** `CompetitorPrice`, `ScraperPreset`
* **jeba_analytics:** `SearchEvent`, `ProductEvent`