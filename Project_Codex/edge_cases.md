# Jeba Enterprise - Edge Cases & Error Handling

> **Last Updated:** 2026-01-11  
> **Purpose:** Document known edge cases, failure scenarios, and their mitigations

---

## Table of Contents

1. [Inventory & Stock Management](#1-inventory--stock-management)
2. [Payment Processing](#2-payment-processing)
3. [Order Fulfillment](#3-order-fulfillment)
4. [Session & Authentication](#4-session--authentication)
5. [External API Integrations](#5-external-api-integrations)
6. [Image Processing](#6-image-processing)
7. [Search & Matching](#7-search--matching)
8. [Analytics & Tracking](#8-analytics--tracking)
9. [Landing Pages & Campaigns](#9-landing-pages--campaigns)
10. [Database & Data Integrity](#10-database--data-integrity)

---

## 1. Inventory & Stock Management

### Edge Case: Race Condition on Stock

**Scenario:** Two users attempt to purchase the last item simultaneously.

**Problem:** Without proper locking, both orders could succeed, resulting in -1 stock.

**Solution Implemented:**

```python
with transaction.atomic():
    products = Product.objects.select_for_update().filter(id__in=ids)
    # Row-level lock prevents concurrent modifications
```

**Residual Risk:** Very high traffic could cause lock wait timeouts.

**Recommendation:** Consider implementing a queue-based checkout for popular items.

---

### Edge Case: Sale Price Exceeds Regular Price

**Scenario:** Admin sets `sale_price > selling_price` by mistake.

**Current Behavior:** System displays sale price regardless.

**Recommendation:** Add model validation:

```python
def clean(self):
    if self.sale_price and self.sale_price > self.selling_price:
        raise ValidationError("Sale price cannot exceed regular price")
```

---

### Edge Case: Zero Stock but Product Active

**Scenario:** Product has `stock_quantity=0` but `is_active=True`.

**Current Behavior:**

- Shows "Out of Stock" badge ✅
- Add to Cart button disabled ✅
- Product still appears in search/category ⚠️

**Potential Issue:** Users frustrated by seeing unavailable products.

**Recommendation:** Add admin filter for "Hide Out of Stock from Catalog" option in SiteSettings.

---

### Edge Case: Variant Stock vs Product Stock Mismatch

**Scenario:** Product has 10 total stock, but variants sum to 15.

**Current Behavior:** Each variant tracks its own stock independently.

**Potential Issue:** If parent product stock is relied upon somewhere, inconsistency occurs.

**Recommendation:** Either:

1. Disable parent stock when variants exist, OR
2. Sum variant stocks as parent stock (computed property)

---

## 2. Payment Processing

### Edge Case: bKash Transaction ID Already Used

**Scenario:** User submits the same bKash transaction ID for multiple orders.

**Current Behavior:** No validation against duplicate transaction IDs.

**Risk:** Potential fraud - one payment, multiple orders.

**Recommendation:**

```python
class Sale(models.Model):
    transaction_id = models.CharField(..., unique=True)  # Make unique

    def clean(self):
        if self.transaction_id:
            exists = Sale.objects.filter(
                transaction_id=self.transaction_id
            ).exclude(pk=self.pk).exists()
            if exists:
                raise ValidationError("Transaction ID already used")
```

---

### Edge Case: bKash Selected but No Transaction ID

**Scenario:** User selects bKash payment but leaves Transaction ID blank.

**Current Behavior:** Client-side validation prevents submission.

**Risk:** If JavaScript disabled, server accepts empty Transaction ID.

**Recommendation:** Add server-side validation:

```python
if payment_method == 'BKASH' and not transaction_id:
    raise ValidationError("Transaction ID required for bKash")
```

---

### Edge Case: Delivery Charge Manipulation

**Scenario:** Malicious user modifies delivery charge value in form submission.

**Current Behavior:** Delivery charge comes from server-side SiteSettings.

**Verification:** ✅ Correct - charge is recalculated on server, not trusted from client.

---

## 3. Order Fulfillment

### Edge Case: Steadfast API Timeout

**Scenario:** Steadfast API is slow or unresponsive.

**Current Behavior:** Admin sees error message, order stays in "PROCESSING".

**Potential Issue:** Admin doesn't know if order was actually submitted.

**Recommendation:**

1. Implement retry with exponential backoff
2. Queue failed submissions for retry
3. Add admin notification for failed courier submissions

---

### Edge Case: Steadfast Returns Error but Order Created

**Scenario:** API returns error, but courier actually received the order.

**Potential Issue:** Double shipment if admin retries.

**Recommendation:**

1. Log all API requests/responses
2. Before retry, check with Steadfast status endpoint
3. Add "Force Re-submit" with confirmation warning

---

### Edge Case: Order Status Sync Discrepancy

**Scenario:** Steadfast shows "Delivered" but local status is "Shipped".

**Current Behavior:** Live tracking pulls real-time status from API in order_detail view.

**Potential Issue:** Local status in admin doesn't update automatically.

**Recommendation:** Add scheduled task to sync statuses:

```python
# management/commands/sync_steadfast_status.py
for sale in Sale.objects.filter(consignment_id__isnull=False, status='SHIPPED'):
    api_status = steadfast.get_status(sale.consignment_id)
    sale.status = map_steadfast_status(api_status)
    sale.save()
```

---

## 4. Session & Authentication

### Edge Case: Session Expires During Checkout

**Scenario:** User fills checkout form but session expires before submit.

**Current Behavior:** Cart is lost, form submission fails.

**Risk:** Lost sales, user frustration.

**Recommendation:**

1. Extend session duration for checkout flow
2. Store cart in localStorage as backup
3. Show clear "Session expired, please refresh" message

---

### Edge Case: Guest Checkout Then Register

**Scenario:** User completes guest checkout, then registers with same email.

**Current Behavior:** Order remains as guest order, not linked to new account.

**Recommendation:**

```python
# On registration, link orphaned orders
def post_registration(user):
    Sale.objects.filter(
        user__isnull=True,
        phone_number=user.profile.phone_number
    ).update(user=user)
```

---

### Edge Case: Profile Auto-Creation Fails

**Scenario:** `post_save` signal fails to create UserProfile.

**Current Behavior:** Signal uses `get_or_create` which is safe.

**Verification:** ✅ Correct implementation:

```python
@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, **kwargs):
    UserProfile.objects.get_or_create(user=instance)
```

---

## 5. External API Integrations

### Edge Case: Gemini API Rate Limit

**Scenario:** Too many AI content generation requests hit rate limit.

**Potential Issue:** AI features fail silently or with cryptic errors.

**Recommendation:**

1. Implement rate limiting on client side
2. Queue AI requests
3. Cache generated content
4. Add fallback to manual content

---

### Edge Case: Facebook Webhook Verification Fails

**Scenario:** Facebook sends verify request but token doesn't match.

**Current Behavior:** Webhook returns error, Facebook disables integration.

**Recommendation:**

1. Log all verification attempts
2. Alert admin on verification failures
3. Store verify_token in SiteSettings for easy updates

---

### Edge Case: Messenger Message Delivery Failure

**Scenario:** Admin sends reply but Facebook API rejects it.

**Possible Causes:**

- User blocked the page
- 24-hour messaging window expired
- Invalid PSID

**Recommendation:**

```python
def send_message(psid, text):
    try:
        response = fb_api.send(psid, text)
        return True
    except MessagingWindowExpired:
        return "Cannot message: 24-hour window expired"
    except UserBlocked:
        Conversation.objects.filter(psid=psid).update(status='blocked')
        return "User has blocked this page"
```

---

### Edge Case: GeoIP Database Missing/Outdated

**Scenario:** `GeoLite2-City.mmdb` file missing or expired (MaxMind requires updates).

**Current Behavior:** GeoIP lookups fail, analytics missing location data.

**Recommendation:**

1. Add fallback to "Unknown" location
2. Log warning when database missing
3. Add management command to download/update GeoIP database

---

## 6. Image Processing

### Edge Case: Uploaded Image Too Large

**Scenario:** User uploads 50MB raw camera image.

**Current Behavior:** `image_optimizer.py` resizes to max 1200px width.

**Potential Issue:** Memory exhaustion during processing.

**Recommendation:**

1. Add file size limit validation (e.g., max 10MB)
2. Use streaming processing for large files
3. Add progress indicator for uploads

---

### Edge Case: Corrupt Image File

**Scenario:** File extension is .jpg but content is corrupt or different format.

**Current Behavior:** Pillow may crash or produce corrupted output.

**Recommendation:**

```python
def validate_image(image_field):
    try:
        img = Image.open(image_field)
        img.verify()  # Checks file integrity
        return True
    except Exception:
        raise ValidationError("Invalid or corrupt image file")
```

---

### Edge Case: LQIP Generation Fails

**Scenario:** `generate_lqip()` fails for certain image types.

**Current Behavior:** `featured_image_placeholder` remains blank.

**Impact:** No low-quality placeholder, slower perceived loading.

**Recommendation:** Add try/except with fallback:

```python
try:
    self.featured_image_placeholder = generate_lqip(self.featured_image)
except Exception:
    self.featured_image_placeholder = None  # Graceful degradation
```

---

### Edge Case: rembg Background Removal Failure

**Scenario:** Complex images fail to remove background properly.

**Current Behavior:** Returns original image or partial removal.

**Recommendation:**

1. Add user preview before saving
2. Allow manual override/revert
3. Queue for manual review if confidence low

---

## 7. Search & Matching

### Edge Case: Zero Search Results

**Scenario:** User search query matches nothing.

**Current Behavior:** Logs SearchEvent with `result_count=0`.

**UX Issue:** Blank results page frustrating.

**Recommendation:**

1. Show "Did you mean..." suggestions
2. Show popular/related products
3. Track zero-result queries for inventory insights

---

### Edge Case: Special Characters in Search

**Scenario:** User searches for `"Product" <script>alert(1)</script>`.

**Current Behavior:** Django ORM escapes by default (safe from SQL injection).

**Verification:** ✅ Django's ORM parameterizes queries.

**XSS Risk:** Ensure search query is escaped in template:

```html
<!-- Safe -->
<p>Results for: {{ query }}</p>

<!-- DANGEROUS -->
<p>Results for: {{ query|safe }}</p>
```

---

### Edge Case: ImageHash False Positives

**Scenario:** Visual search matches wrong product (similar packaging).

**Current Behavior:** Uses hybrid text+image matching with configurable weights.

**Known Issue:** Products with same packaging but different contents may confuse image matching.

**Recommendation:**

1. Increase text_weight for products with similar packaging
2. Allow admin to manually exclude false matches
3. Implement human review queue for low-confidence matches

---

## 8. Analytics & Tracking

### Edge Case: Bot Traffic Pollution

**Scenario:** Search bots, scrapers flood analytics with fake events.

**Current Behavior:** All page views tracked.

**Impact:** Skewed analytics, inflated numbers.

**Recommendation:**

```python
def is_bot(request):
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    bots = ['googlebot', 'bingbot', 'bot', 'spider', 'crawler']
    return any(bot in ua for bot in bots)

# In middleware
if not is_bot(request):
    ProductEvent.objects.create(...)
```

---

### Edge Case: Ad Spend But No Sales

**Scenario:** DailyAdSpend has spend but `total_revenue=0`.

**Current Behavior:** ROAS calculates as 0 / spend = 0.

**Reporting Issue:** Infinite loss shown.

**Recommendation:** Add visual indicator for "No sales recorded" days.

---

### Edge Case: SessionTrace Overflow

**Scenario:** High-frequency heartbeat events bloat `raw_data` JSON.

**Current Behavior:** All events stored in one JSONField.

**Potential Issue:** JSON becomes too large, slows queries.

**Recommendation:**

1. Limit events per session (e.g., last 100)
2. Summarize/aggregate old events
3. Archive old traces to separate table

---

## 9. Landing Pages & Campaigns

### Edge Case: All Variant Weights = 0

**Scenario:** Admin sets all campaign variant weights to 0.

**Current Behavior:** Weighted random selection fails (empty pool).

**Recommendation:**

```python
if not pool:
    # Fallback to equal distribution
    return random.choice(list(variants))
```

---

### Edge Case: FOMO Timer Already Expired

**Scenario:** `fomo_timer_end` is in the past.

**Current Behavior:** Timer shows negative or "expired".

**Recommendation:**

1. Auto-hide timer if expired
2. Template check: `{% if variant.fomo_timer_end > now %}`
3. Consider auto-disable variant when timer expires

---

### Edge Case: A/B Test Statistical Significance

**Scenario:** Variant has 55% conversion but only 10 visitors.

**Current Behavior:** No significance calculation shown.

**Recommendation:** Add statistical significance indicator:

```python
from scipy import stats

def is_significant(variant_a, variant_b, confidence=0.95):
    # Chi-square test for conversion rates
    ...
```

---

## 10. Database & Data Integrity

### Edge Case: Singleton Deletion

**Scenario:** Attempting to delete SiteSettings or MessengerSettings.

**Current Behavior:** `delete()` is overridden to do nothing:

```python
def delete(self, *args, **kwargs):
    pass  # Prevent deletion
```

**Verification:** ✅ Correctly implemented.

---

### Edge Case: Migration with Existing Data

**Scenario:** Adding `NOT NULL` field to table with existing rows.

**Current Behavior:** Django prompts for default value.

**Risk:** Inappropriate defaults break existing data.

**Recommendation:** Always:

1. Add with `null=True` first
2. Data migration to populate
3. Then alter to `null=False`

---

### Edge Case: Foreign Key to Deleted Object

**Scenario:** Category deleted but products still reference it.

**Current Behavior:** `on_delete=models.CASCADE` or `SET_NULL` per field.

**Audit:**
| Model | Field | on_delete |
|-------|-------|-----------|
| Product.category | Category | CASCADE ⚠️ |
| Sale.user | User | SET_NULL ✅ |
| SaleItem.product | Product | CASCADE ✅ |
| SaleItem.variation | ProductVariation | SET_NULL ✅ |

**Recommendation:** Consider `PROTECT` for Category to prevent accidental cascade deletion.

---

### Edge Case: Decimal Precision Loss

**Scenario:** Division operations on DecimalField lose precision.

**Example:**

```python
# Wrong
item.profit = (sold - cost) / 3

# Correct
from decimal import Decimal
item.profit = (sold - cost) / Decimal('3')
```

**Recommendation:** Audit all arithmetic operations on Decimal fields.

---

## Security Edge Cases

### Edge Case: Admin Page Access Control

**Scenario:** Non-admin user guesses admin URLs.

**Current Behavior:** Django admin restricts to `is_staff=True`.

**Verification:** ✅ Default Django behavior.

**Additional Recommendation:** Rate limit admin login attempts.

---

### Edge Case: CSRF Token on AJAX

**Scenario:** JavaScript POST without CSRF token.

**Current Behavior:** Django rejects request.

**Template Pattern:**

```javascript
fetch("/api/endpoint/", {
  method: "POST",
  headers: {
    "X-CSRFToken": getCookie("csrftoken"),
  },
  body: JSON.stringify(data),
});
```

---

### Edge Case: Order Access Token Guessing

**Scenario:** Attacker tries to guess guest order UUIDs.

**Current Behavior:** UUIDv4 is cryptographically random (2^122 possibilities).

**Verification:** ✅ Secure - UUID4 is unpredictable.

---

## Monitoring Recommendations

| Edge Case Category    | Recommended Alert                            |
| --------------------- | -------------------------------------------- |
| Stock race conditions | Alert if stock goes negative                 |
| API failures          | Alert on >3 consecutive failures             |
| Payment mismatches    | Daily report of bKash without Transaction ID |
| Session expiry        | Track checkout abandonment rate              |
| Bot traffic           | Alert if bot % > 50% of traffic              |
| Database locks        | Alert on lock wait > 5 seconds               |
