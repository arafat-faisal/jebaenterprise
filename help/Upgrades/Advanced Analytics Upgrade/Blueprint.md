# Blueprint: Advanced Analytics Upgrade

## 🎯 Objective
Capture granular user context (Location, Device, Source) alongside core events.

## 🏗 Architecture

### 1. Data Modeling (`jeba_analytics`)
- [x] **Add `metadata` Field:** Add `JSONField` to `ProductEvent` & `SearchEvent`.
- [ ] **New Events:** Add `CONTACT` (WhatsApp/Call) and `CHECKOUT` to `EVENT_CHOICES`.

### 2. Context Engine (`analytics_service.py`)
- [x] **`get_client_ip(request)`:** Extract standard IP.
- [x] **`get_device_info(request)`:** Parse User-Agent.
- [x] **`get_location(ip)`:** Resolve IP to City/Country.

### 3. Profile Expansion (Optional)
- [ ] Add `gender` and `birth_date` to `UserProfile` for registered user accuracy.