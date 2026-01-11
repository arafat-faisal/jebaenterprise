# Jeba Enterprise - Project Codex Overview

> **Version:** 1.0.0  
> **Generated:** 2026-01-11  
> **Project Path:** `e:\WebProjects\jebaenterprise`  
> **Repository:** arafat-faisal/jebaenterprise

---

## Executive Summary

**Jeba Enterprise** is a comprehensive, modular **Django 5.2-based e-commerce platform** designed for the Bangladesh market. The platform provides a complete end-to-end e-commerce solution including:

- **Product Catalog & Inventory Management**
- **Sales & Order Processing** with COD and bKash payment
- **Courier Integration** (Steadfast/Packzy API)
- **AI-Powered Tools** (Product description generation, SEO optimization, landing page builder)
- **Advanced Analytics** (Session traces, conversion tracking, ROI calculation)
- **Facebook Messenger Integration** with AI-powered response suggestions
- **Landing Page Builder** for marketing campaigns with A/B testing
- **SEO Toolkit** with sitemap and robots.txt generation

---

## Technology Stack

| Component             | Technology                 | Version/Details              |
| --------------------- | -------------------------- | ---------------------------- |
| **Backend Framework** | Django                     | 5.2.8                        |
| **Database**          | PostgreSQL                 | via psycopg2                 |
| **Admin UI**          | Django Jazzmin             | Dark theme with custom icons |
| **Static Files**      | WhiteNoise                 | Compressed Manifest Storage  |
| **AI Services**       | Google Gemini              | google-generativeai 0.8.5    |
| **Web Scraping**      | Playwright + BeautifulSoup | Price comparison tools       |
| **Image Processing**  | Pillow, ImageHash, rembg   | Background removal, hashing  |
| **Email**             | Gmail SMTP                 | Transactional emails         |
| **PDF Generation**    | xhtml2pdf, reportlab       | Invoices/receipts            |
| **Geo Location**      | GeoIP2                     | MaxMind GeoLite2-City        |
| **Courier API**       | Steadfast (Packzy)         | Order fulfillment            |

---

## Architectural Overview

### Modular Django Apps Structure

The project follows a **domain-driven modular architecture** with 13 specialized Django apps:

```
jebaenterprise/
├── config/                    # Django project configuration
│   ├── settings.py           # Main settings with environment variables
│   ├── urls.py               # Root URL configuration
│   └── wsgi.py / asgi.py     # Server entry points
│
├── jeba_core/                 # Core settings & utilities
│   ├── models.py             # SiteSettings (singleton), branding, payment config
│   ├── middleware.py         # MaintenanceModeMiddleware
│   ├── context_processors.py # Global template context
│   └── image_optimizer.py    # Image optimization utilities
│
├── jeba_inventory/            # Product catalog management
│   ├── models.py             # Product, Category, Tag, ProductVariant, ProductImage
│   ├── admin.py              # Advanced product admin with inline variants
│   └── templates/            # Product browsing UI
│
├── jeba_sales/                # Order processing & checkout
│   ├── models.py             # Sale, SaleItem, Coupon
│   ├── views.py              # Cart, checkout, order confirmation
│   └── steadfast.py          # Courier API integration
│
├── jeba_accounts/             # User authentication & profiles
│   ├── models.py             # UserProfile
│   └── views.py              # Login, register, dashboard
│
├── jeba_analytics/            # User behavior tracking & ROI
│   ├── models.py             # SearchEvent, ProductEvent, SessionTrace, DailyAdSpend
│   ├── middleware.py         # AnalyticsMiddleware
│   └── views.py              # Analytics dashboard
│
├── jeba_engagement/           # User engagement features
│   └── models.py             # Review, Wishlist
│
├── jeba_intelligence/         # Competitor analysis & scraping
│   ├── models.py             # CompetitorPrice, ScraperPreset
│   └── scraper.py            # Playwright-based Daraz scraper
│
├── jeba_blog/                 # Content marketing
│   └── models.py             # BlogPost with SEO fields
│
├── jeba_landing/              # Marketing landing pages
│   ├── models.py             # Campaign, CampaignVariant, LandingSection
│   └── analytics/            # VisitorSession, ConversionEvent
│
├── jeba_ai_builder/           # AI-powered page generator
│   └── models.py             # AIPage, PageConversation, PageVersion
│
├── jeba_messenger/            # Facebook Messenger integration
│   └── models.py             # Conversation, Message, AISuggestion
│
├── jeba_seo/                  # SEO management
│   ├── models.py             # GlobalSEOSettings, StaticPageSEO
│   └── sitemaps.py           # XML sitemap generators
│
├── jeba_diagnostics/          # Performance monitoring
│   └── models.py             # PageReport
│
└── products/                  # Legacy/routing app (deprecated)
```

---

## Key Features by Domain

### 1. E-Commerce Core

- **Product Management:** Multi-image gallery, dynamic variations (color, size), stock tracking
- **Dynamic Pricing:** Regular/sale prices, competitor price comparison, "Contact for Price" mode
- **Search:** Text search + Visual search via `imagehash` for product matching
- **SEO-Ready:** Slugs, meta fields, automatic sitemap generation

### 2. Sales & Fulfillment

- **Cart Logic:** Session-based cart with stock validation
- **Checkout:** Guest checkout support, atomic stock reduction
- **Payment:** Cash on Delivery (COD), bKash (manual with Transaction ID)
- **Delivery Zones:** Dynamic pricing (Inside/Outside Dhaka)
- **Courier Integration:** Steadfast API for order submission + live tracking
- **Invoicing:** Auto-generated invoice numbers (#JEBA-8XXX format)

### 3. AI & Intelligence

- **Competitor Scraper:** Playwright-based Daraz price scraper with hybrid matching (text + image)
- **AI Content Generation:** Gemini-powered product descriptions
- **AI Landing Pages:** Full conversational page builder
- **Messenger AI:** Auto-suggestions for customer responses

### 4. Analytics & Marketing

- **Event Tracking:** Page views, cart actions, purchases, shares
- **Session Telemetry:** Full JavaScript event capture (scroll, clicks, timing)
- **ROI Calculator:** Daily ad spend tracking with ROAS calculation
- **A/B Testing:** Campaign variants with traffic weighting
- **Conversion Funnels:** Scroll depth, exit intent, CTA clicks

### 5. Localization

- **Languages:** English + Bengali (bn)
- **Currency:** Bangladesh Taka (BDT) with ৳ symbol
- **Timezone:** Asia/Dhaka

---

## Database Strategy

- **Primary Database:** PostgreSQL (configured via environment variables)
- **Legacy Compatibility:** Many models use `db_table` to preserve existing table names
- **Singleton Pattern:** Used for settings models (`SiteSettings`, `GlobalSEOSettings`)
- **Session Storage:** File-based sessions in `sessions/` directory

---

## Security Configuration

### Production Mode (DEBUG=False)

- SSL redirect enforced
- HSTS enabled (1 year)
- Secure cookies for sessions and CSRF
- Proxy SSL header support for Nginx

### Environment Variables

All sensitive configuration is externalized to `.env`:

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `STEADFAST_API_KEY`, `STEADFAST_SECRET_KEY`
- `GEMINI_API_KEY`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

---

## Deployment Notes

- **Static Files:** Served via WhiteNoise with compression
- **WSGI:** Configured in `config/wsgi.py`
- **Gunicorn:** Listed in requirements (gunicorn==21.2.0)
- **Nginx:** Recommended reverse proxy (see `deploymentnotes/`)

---

## Quick Start Commands

```bash
# Activate virtual environment
cd e:\WebProjects\jebaenterprise
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run development server
python manage.py runserver
```

---

## Related Codex Files

| File                                       | Description                           |
| ------------------------------------------ | ------------------------------------- |
| [code_structure.md](./code_structure.md)   | Full directory tree with descriptions |
| [data_schemas.md](./data_schemas.md)       | Database models and relationships     |
| [dependencies.md](./dependencies.md)       | All pip packages with purposes        |
| [logic_flows.md](./logic_flows.md)         | Key business process diagrams         |
| [edge_cases.md](./edge_cases.md)           | Known issues and handling             |
| [rules.toml](./rules.toml)                 | AI operational guidelines             |
| [initial_prompt.txt](./initial_prompt.txt) | Reusable AI context prefix            |
