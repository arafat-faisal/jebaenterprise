import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('jeba_inventory', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('products', '0035_alter_sale_access_token'), # Force wait
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Sale',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('customer_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='Customer Name')),
                        ('access_token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                        ('phone_number', models.CharField(blank=True, max_length=20, null=True, verbose_name='Phone Number')),
                        ('shipping_address', models.TextField(blank=True, null=True, verbose_name='Shipping Address')),
                        ('consignment_id', models.IntegerField(blank=True, help_text='Steadfast Consignment ID', null=True)),
                        ('tracking_code', models.CharField(blank=True, help_text='Steadfast Tracking Code', max_length=50, null=True)),
                        ('payment_method', models.CharField(choices=[('COD', 'Cash on Delivery'), ('BKASH', 'bKash')], default='COD', max_length=10, verbose_name='Payment Method')),
                        ('transaction_id', models.CharField(blank=True, max_length=50, null=True, verbose_name='Transaction ID')),
                        ('delivery_charge', models.DecimalField(decimal_places=2, default=60.0, max_digits=6, verbose_name='Delivery Charge')),
                        ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('SHIPPED', 'Shipped'), ('DELIVERED', 'Delivered'), ('CANCELLED', 'Cancelled')], default='PENDING', max_length=20, verbose_name='Status')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'db_table': 'products_sale',
                    },
                ),
                migrations.CreateModel(
                    name='SaleItem',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('quantity', models.PositiveIntegerField(default=1, verbose_name='Quantity')),
                        ('buying_cost', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                        ('sold_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Sold Price')),
                        ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='jeba_inventory.product')),
                        ('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='jeba_sales.sale')),
                        ('variation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='jeba_inventory.productvariation')),
                    ],
                    options={
                        'db_table': 'products_saleitem',
                    },
                ),
            ],
            database_operations=[],
        ),
    ]