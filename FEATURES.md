# Jeba Enterprise - Master Feature Registry

## 1. Inventory & Catalog (App: `jeba_inventory`)
- [ ] **Homepage Hero:** Displays the latest product marked as `is_featured`.
- [ ] **Dynamic Pricing Display:** - Shows "Contact for Price" if `call_for_price` is True.
    - Shows "Out of Stock" badge if `stock_quantity` <= 0.
    - Shows "Hurry! Only X left" if stock <= 5.
- [ ] **Visual Search:** Users can upload an image to find products (Logic: `imagehash`).
- [ ] **Text Search:** Filters by Name, Description, and Category.
- [ ] **Gallery Navigation:** Supports multiple images per product with thumbnail switching.
- [ ] **Related Products:** Suggests products from the same category or recent history.

## 2. Sales & Checkout (App: `jeba_sales`)
- [ ] **Cart Logic:** - Add to cart (Standard & Variations).
    - Prevent adding if stock is 0.
    - Update quantity/Remove items.
- [ ] **Dynamic Delivery Charge:**
    - Inside Dhaka: 60 Tk (Default).
    - Outside Dhaka: 120 Tk (Updates total dynamically).
- [ ] **Checkout Process:**
    - Guest checkout support.
    - **Atomic Transaction:** Stock is deducted *only* when the order is successfully confirmed.
    - **bKash Logic:** Requires Transaction ID if "bKash" is selected.
- [ ] **Post-Order:**
    - Generates a unique Invoice ID (e.g., `#JEBA-8055`).
    - Generates a PDF Receipt.
    - Sends Confirmation Email (Background Thread).

## 3. Logistics (Steadfast Integration)
- [ ] **Admin Action:** "Send to Steadfast" button in Admin Panel.
- [ ] **API Submission:** Pushes Name, Address, COD Amount to Steadfast API.
- [ ] **Live Tracking:** Updates local order status based on API response (Delivered/Cancelled).

## 4. User Accounts (App: `jeba_accounts`)
- [ ] **Registration:** Captures Name, Email. Sends Welcome Email.
- [ ] **Dashboard:** - View Order History.
    - Update Address/Profile.
    - Change Password.
- [ ] **Password Reset:** Email-based reset flow.

## 5. Engagement & Analytics (App: `jeba_engagement` / `jeba_analytics`)
- [ ] **Wishlist:** Toggle Add/Remove items.
- [ ] **Reviews:** Authenticated users can rate (1-5 stars) and comment.
- [ ] **Share Tracking:** Logs when a user clicks the "Share" button.
- [ ] **Winning Product Analysis:** Admin view calculating Cart-to-Order conversion rates.

## 6. Intelligence & Admin Tools (App: `jeba_intelligence`)
- [ ] **Competitor Scraper:** Scrapes Daraz for price comparison using Playwright.
- [ ] **Scraper Presets:** Save configuration (Text Weight vs Image Weight).
- [ ] **Maintenance Mode:** Global toggle in `SiteSettings` to lock the frontend.