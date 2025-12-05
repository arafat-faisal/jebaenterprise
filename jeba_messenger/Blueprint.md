# Blueprint: Jeba Messenger AI Copilot

## 1. Overview
A dedicated Django app to integrate Facebook Messenger, allowing the admin to chat with customers directly from the Jeba Enterprise dashboard. It features an AI Copilot (Gemini 2.0 Flash) that suggests context-aware responses in Bengali and English.

## 2. Architecture
* **App Name:** `jeba_messenger`
* **External APIs:**
    * Facebook Graph API (Send/Receive API)
    * Google Gemini API (Response Generation)
* **Database Models:**
    * `Conversation`: Tracks the user (customer) and status.
    * `Message`: Stores individual texts, timestamps, and sender type (User/Page).
    * `AISuggestion`: Caches generated suggestions for specific messages.

## 3. Development Status
* [x] **Step 1:** App Creation & Database Models
* [x] **Step 2:** Facebook Webhook Verification & Ingestion
* [x] **Step 3:** AI Engine Setup (Gemini 2.0 Flash)
* [x] **Step 4:** Admin Chat Interface (UI)
* [x] **Step 5:** Sending Logic & Testing

## 4. Configuration
* **Facebook Verify Token:** (To be generated in Step 2)
* **Gemini Model:** `gemini-2.0-flash` (or latest available)