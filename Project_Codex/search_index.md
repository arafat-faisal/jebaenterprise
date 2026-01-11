# Jeba Enterprise - Search Index

> **Purpose:** Quick keyword lookup for navigating Project Codex  
> **Usage:** Search for keywords to find relevant sections and files

---

## A

| Keyword                | Location          | Reference                                                                  |
| ---------------------- | ----------------- | -------------------------------------------------------------------------- |
| **A/B Testing**        | logic_flows.md    | [#8 Landing Page A/B Testing](logic_flows.md#8-landing-page-ab-testing)    |
| **Add to Cart**        | logic_flows.md    | [#2 Cart Management](logic_flows.md#2-cart-management)                     |
| **Admin Panel**        | code_structure.md | `*/admin.py` files                                                         |
| **AI Builder**         | data_schemas.md   | [#10 AI Builder](data_schemas.md#10-ai-builder-jeba_ai_builder)            |
| **AI Content**         | overview.md       | Product AI fields                                                          |
| **Analytics**          | data_schemas.md   | [#5 Analytics](data_schemas.md#5-analytics--events-jeba_analytics)         |
| **Atomic Transaction** | edge_cases.md     | [#1 Stock Race Condition](edge_cases.md#edge-case-race-condition-on-stock) |
| **Authentication**     | logic_flows.md    | [#11 User Authentication](logic_flows.md#11-user-authentication)           |

## B

| Keyword               | Location        | Reference                                                     |
| --------------------- | --------------- | ------------------------------------------------------------- |
| **Background Thread** | logic_flows.md  | Email sending in checkout                                     |
| **bKash**             | data_schemas.md | `Sale.payment_method`                                         |
| **bKash Validation**  | edge_cases.md   | [#2 Payment Processing](edge_cases.md#2-payment-processing)   |
| **Blog**              | data_schemas.md | [#8 Blog](data_schemas.md#8-blog-jeba_blog)                   |
| **Bot Detection**     | edge_cases.md   | [#8 Analytics](edge_cases.md#edge-case-bot-traffic-pollution) |

## C

| Keyword                 | Location          | Reference                                                       |
| ----------------------- | ----------------- | --------------------------------------------------------------- |
| **Campaign**            | data_schemas.md   | `jeba_landing.Campaign`                                         |
| **Cart**                | logic_flows.md    | [#2 Cart Management](logic_flows.md#2-cart-management)          |
| **Category**            | data_schemas.md   | `jeba_inventory.Category`                                       |
| **Checkout**            | logic_flows.md    | [#3 Checkout Process](logic_flows.md#3-checkout-process)        |
| **Checkpoint**          | rules.toml        | `[resumability]` section                                        |
| **Competitor Scraping** | logic_flows.md    | [#7 Price Scraping](logic_flows.md#7-competitor-price-scraping) |
| **Configuration**       | code_structure.md | `config/settings.py`                                            |
| **Conversion Event**    | data_schemas.md   | `jeba_landing.ConversionEvent`                                  |
| **Coupon**              | data_schemas.md   | `jeba_sales.Coupon`                                             |
| **CSRF**                | edge_cases.md     | [Security Edge Cases](edge_cases.md#security-edge-cases)        |

## D

| Keyword             | Location        | Reference                                                          |
| ------------------- | --------------- | ------------------------------------------------------------------ |
| **DailyAdSpend**    | data_schemas.md | `jeba_analytics.DailyAdSpend`                                      |
| **Database**        | overview.md     | PostgreSQL via psycopg2                                            |
| **Delivery Charge** | data_schemas.md | `SiteSettings.delivery_charge_*`                                   |
| **Dependencies**    | dependencies.md | Complete package list                                              |
| **Deployment**      | overview.md     | Gunicorn, WhiteNoise, Nginx                                        |
| **Diagnostics**     | data_schemas.md | [#13 Diagnostics](data_schemas.md#13-diagnostics-jeba_diagnostics) |

## E

| Keyword                   | Location        | Reference                                                   |
| ------------------------- | --------------- | ----------------------------------------------------------- |
| **Edge Cases**            | edge_cases.md   | Full document                                               |
| **Email**                 | dependencies.md | Gmail SMTP configuration                                    |
| **Environment Variables** | overview.md     | `.env` file contents                                        |
| **Event Tracking**        | logic_flows.md  | [#10 Analytics](logic_flows.md#10-analytics-event-tracking) |
| **Exit Intent**           | data_schemas.md | `ConversionEvent.EXIT_INTENT`                               |

## F

| Keyword                | Location        | Reference                                                    |
| ---------------------- | --------------- | ------------------------------------------------------------ |
| **Facebook Messenger** | data_schemas.md | [#11 Messenger](data_schemas.md#11-messenger-jeba_messenger) |
| **Featured Products**  | data_schemas.md | `SiteSettings.featured_products`                             |
| **FOMO Timer**         | data_schemas.md | `CampaignVariant.fomo_timer_end`                             |

## G

| Keyword    | Location        | Reference           |
| ---------- | --------------- | ------------------- |
| **Gemini** | dependencies.md | google-generativeai |
| **GeoIP**  | dependencies.md | geoip2, MaxMind     |

## H

| Keyword          | Location        | Reference                        |
| ---------------- | --------------- | -------------------------------- |
| **Hero Section** | data_schemas.md | `SiteSettings.featured_products` |
| **HSTS**         | overview.md     | Security configuration           |

## I

| Keyword                | Location          | Reference                                                        |
| ---------------------- | ----------------- | ---------------------------------------------------------------- |
| **Image Optimization** | code_structure.md | `jeba_core/image_optimizer.py`                                   |
| **ImageHash**          | logic_flows.md    | [#5 Visual Search](logic_flows.md#5-product-search-text--visual) |
| **Invoice**            | data_schemas.md   | `Sale.invoice_number` property                                   |

## J

| Keyword     | Location        | Reference                  |
| ----------- | --------------- | -------------------------- |
| **Jazzmin** | dependencies.md | django-jazzmin admin theme |

## L

| Keyword          | Location          | Reference                                                        |
| ---------------- | ----------------- | ---------------------------------------------------------------- |
| **Landing Page** | data_schemas.md   | [#9 Landing Pages](data_schemas.md#9-landing-pages-jeba_landing) |
| **Localization** | overview.md       | EN/BN languages                                                  |
| **LQIP**         | code_structure.md | Low-quality image placeholder                                    |

## M

| Keyword               | Location        | Reference                                                  |
| --------------------- | --------------- | ---------------------------------------------------------- |
| **Maintenance Mode**  | data_schemas.md | `SiteSettings.maintenance_mode`                            |
| **Message**           | data_schemas.md | `jeba_messenger.Message`                                   |
| **Messenger Webhook** | logic_flows.md  | [#9 Webhook Flow](logic_flows.md#9-messenger-webhook-flow) |
| **Meta Pixel**        | data_schemas.md | `SiteSettings.meta_pixel_id`                               |
| **Migration**         | rules.toml      | `[modifications.models]`                                   |
| **Models**            | data_schemas.md | Complete schema reference                                  |

## O

| Keyword               | Location        | Reference                                                                |
| --------------------- | --------------- | ------------------------------------------------------------------------ |
| **Order**             | data_schemas.md | `jeba_sales.Sale`                                                        |
| **Order Fulfillment** | logic_flows.md  | [#4 Steadfast](logic_flows.md#4-order-fulfillment-steadfast-integration) |

## P

| Keyword            | Location        | Reference                                                   |
| ------------------ | --------------- | ----------------------------------------------------------- |
| **Password Reset** | logic_flows.md  | [#11 Authentication](logic_flows.md#11-user-authentication) |
| **Payment**        | edge_cases.md   | [#2 Payment Processing](edge_cases.md#2-payment-processing) |
| **Performance**    | data_schemas.md | `jeba_diagnostics.PageReport`                               |
| **Playwright**     | dependencies.md | Browser automation                                          |
| **Product**        | data_schemas.md | `jeba_inventory.Product`                                    |
| **ProductEvent**   | data_schemas.md | `jeba_analytics.ProductEvent`                               |
| **ProductVariant** | data_schemas.md | `jeba_inventory.ProductVariant`                             |

## R

| Keyword            | Location          | Reference                                                        |
| ------------------ | ----------------- | ---------------------------------------------------------------- |
| **Race Condition** | edge_cases.md     | [Stock locking](edge_cases.md#edge-case-race-condition-on-stock) |
| **Review**         | data_schemas.md   | `jeba_engagement.Review`                                         |
| **ROAS**           | data_schemas.md   | `DailyAdSpend.roas` property                                     |
| **Robots.txt**     | code_structure.md | `jeba_seo/views.py`                                              |
| **Rules**          | rules.toml        | Complete operational rules                                       |

## S

| Keyword          | Location          | Reference                                                                        |
| ---------------- | ----------------- | -------------------------------------------------------------------------------- |
| **Sale**         | data_schemas.md   | `jeba_sales.Sale`                                                                |
| **SaleItem**     | data_schemas.md   | `jeba_sales.SaleItem`                                                            |
| **Scraper**      | logic_flows.md    | [#7 Competitor Scraping](logic_flows.md#7-competitor-price-scraping)             |
| **Search**       | logic_flows.md    | [#5 Product Search](logic_flows.md#5-product-search-text--visual)                |
| **SearchEvent**  | data_schemas.md   | `jeba_analytics.SearchEvent`                                                     |
| **Security**     | edge_cases.md     | [Security Edge Cases](edge_cases.md#security-edge-cases)                         |
| **SEO**          | data_schemas.md   | [#12 SEO](data_schemas.md#12-seo-jeba_seo)                                       |
| **Session**      | data_schemas.md   | `jeba_analytics.SessionTrace`                                                    |
| **Settings**     | data_schemas.md   | [#1 Core Settings](data_schemas.md#1-core-settings-jeba_core)                    |
| **Sitemap**      | code_structure.md | `jeba_seo/sitemaps.py`                                                           |
| **SiteSettings** | data_schemas.md   | Singleton settings model                                                         |
| **Steadfast**    | logic_flows.md    | [#4 Order Fulfillment](logic_flows.md#4-order-fulfillment-steadfast-integration) |
| **Stock**        | edge_cases.md     | [#1 Inventory](edge_cases.md#1-inventory--stock-management)                      |

## T

| Keyword         | Location          | Reference                                                   |
| --------------- | ----------------- | ----------------------------------------------------------- |
| **Tag**         | data_schemas.md   | `jeba_inventory.Tag`                                        |
| **Telegram**    | overview.md       | Notification integration                                    |
| **Template**    | code_structure.md | `*/templates/` directories                                  |
| **Testing**     | rules.toml        | `[testing]` section                                         |
| **thefuzz**     | logic_flows.md    | Fuzzy string matching                                       |
| **Tracking**    | logic_flows.md    | [#10 Analytics](logic_flows.md#10-analytics-event-tracking) |
| **Transaction** | logic_flows.md    | Atomic checkout                                             |

## U

| Keyword               | Location          | Reference                   |
| --------------------- | ----------------- | --------------------------- |
| **URL Configuration** | code_structure.md | `config/urls.py`            |
| **User**              | data_schemas.md   | Django auth.User            |
| **UserProfile**       | data_schemas.md   | `jeba_accounts.UserProfile` |
| **UTM**               | data_schemas.md   | Attribution tracking fields |

## V

| Keyword            | Location        | Reference                                                         |
| ------------------ | --------------- | ----------------------------------------------------------------- |
| **Variant**        | data_schemas.md | `jeba_inventory.ProductVariant`                                   |
| **Visual Search**  | logic_flows.md  | [#5 Product Search](logic_flows.md#5-product-search-text--visual) |
| **VisitorSession** | data_schemas.md | `jeba_landing.VisitorSession`                                     |

## W

| Keyword        | Location        | Reference                                                       |
| -------------- | --------------- | --------------------------------------------------------------- |
| **Webhook**    | logic_flows.md  | [#9 Messenger Webhook](logic_flows.md#9-messenger-webhook-flow) |
| **WhatsApp**   | data_schemas.md | `SiteSettings.whatsapp_number`                                  |
| **WhiteNoise** | dependencies.md | Static file serving                                             |
| **Wishlist**   | data_schemas.md | `jeba_engagement.Wishlist`                                      |

---

## File Path Quick Reference

| What                | Path                            |
| ------------------- | ------------------------------- |
| Main settings       | `config/settings.py`            |
| URL routing         | `config/urls.py`                |
| Core settings model | `jeba_core/models.py`           |
| Product model       | `jeba_inventory/models.py`      |
| Order model         | `jeba_sales/models.py`          |
| Checkout views      | `jeba_sales/views.py`           |
| Courier API         | `products/steadfast.py`         |
| Analytics models    | `jeba_analytics/models.py`      |
| Landing page models | `jeba_landing/models.py`        |
| AI service          | `jeba_ai_builder/ai_service.py` |
| Messenger models    | `jeba_messenger/models.py`      |
| Image optimizer     | `jeba_core/image_optimizer.py`  |
| SEO sitemaps        | `jeba_seo/sitemaps.py`          |
