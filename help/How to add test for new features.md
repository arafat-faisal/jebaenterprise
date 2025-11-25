### 1\. How to Add a Test for a New Feature

Whenever you build a new feature, follow this simple 3-step process to "lock it in" so it never breaks accidentally.

#### Step 1: Pick the Right App

Go to the `tests.py` file of the app where you added the feature code.

  * **New Product Feature?** $\rightarrow$ `jeba_inventory/tests.py`
  * **New Money/Order Logic?** $\rightarrow$ `jeba_sales/tests.py`
  * **User/Profile Stuff?** $\rightarrow$ `jeba_accounts/tests.py`

#### Step 2: Add the Test Function

Inside the existing `TestCase` class (or create a new class if it's a totally different topic), add a function.
**Rule:** The function name **must** start with `test_`.

#### Step 3: Use this Template

Copy-paste this template into your `tests.py` and fill in the blanks:

```python
    def test_feature_name_here(self):
        """Feature: [Short Description, e.g., 'Free Shipping over 5k']"""
        
        # --- 1. SETUP (Prepare the data) ---
        # Example: Create a product with a specific price
        self.product.selling_price = 6000 
        self.product.save()
        
        # Example: Login if the feature requires it
        # self.client.login(username='testuser', password='password')

        # --- 2. ACTION (Trigger the feature) ---
        # Example: Visit a URL or Submit a Form
        url = reverse('checkout') # Make sure to import reverse
        response = self.client.get(url) 
        
        # OR for posting forms:
        # response = self.client.post(url, {'field': 'value'})

        # --- 3. ASSERTION (Did it work?) ---
        # Check if page loaded (200 OK)
        self.assertEqual(response.status_code, 200)
        
        # Check if specific text appears on screen
        self.assertContains(response, "Free Shipping Applied")
        
        # OR Check database changes
        # sale = Sale.objects.last()
        # self.assertEqual(sale.total_amount, 6000)
```

-----

### Real World Example: Adding a "Coupon Code"

Imagine you just added a feature where entering "JEBA10" gives a 10% discount.

1.  You would open **`jeba_sales/tests.py`**.
2.  You would add this method to `AdvancedCheckoutTest`:

<!-- end list -->

```python
    def test_coupon_code_logic(self):
        """Feature: Apply 10% Discount with JEBA10 code"""
        # 1. Setup: Product costs 1000
        self.product.selling_price = 1000
        self.product.save()
        
        # Update Cart Session
        session = self.client.session
        session['cart'][str(self.product.id)]['price'] = 1000
        session.save()

        # 2. Action: Submit checkout with coupon
        url = reverse('checkout')
        data = {
            'customer_name': 'Test',
            'phone_number': '017...',
            'shipping_address': 'Dhaka',
            'delivery_area': 'INSIDE',
            'payment_method': 'COD',
            'coupon_code': 'JEBA10'  # <--- The new input field
        }
        self.client.post(url, data)

        # 3. Assertion: Verify 10% was deducted
        sale = Sale.objects.last()
        # Expected: (1000 - 10%) + 60 delivery = 900 + 60 = 960
        self.assertEqual(sale.total_amount, 960) 
```

### Summary

  * **To Run All Tests:** `python manage.py test`
  * **To Run Specific App:** `python manage.py test jeba_sales`
  * **Green Light (`OK`):** Safe to deploy.
  * **Red Light (`FAIL`):** Do not deploy; fix the bug first.