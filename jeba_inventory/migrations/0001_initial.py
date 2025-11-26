# jeba_inventory/migrations/0001_initial.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    initial = True

    # --- FIX: REMOVED DEPENDENCY ON DEFUNCT 'PRODUCTS' APP ---
    dependencies = [
        # This list should be empty or only contain core dependencies like auth/users, 
        # but the problem dependency is removed.
    ]
    # --------------------------------------------------------

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Category',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=100, unique=True, verbose_name='Name')),
                    ],
                    options={
                        'verbose_name_plural': 'Categories',
                        'db_table': 'products_category',
                    },
                ),
                migrations.CreateModel(
                    name='Product',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=255, verbose_name='Product Name')),
                        ('short_description', models.TextField(blank=True, help_text='Short summary shown beside the image', null=True, verbose_name='Short Description')),
                        ('description', models.TextField(blank=True, null=True, verbose_name='Full Description')),
                        ('call_for_price', models.BooleanField(default=False, help_text="If checked, price will be hidden and 'Call for Price' shown.", verbose_name='Call for Price')),
                        ('is_featured', models.BooleanField(default=False, help_text='Check this to show on Homepage Hero section', verbose_name='Is Featured')),
                        ('buying_cost', models.DecimalField(decimal_places=2, default=0.00, max_digits=10, verbose_name='Buying Cost')),
                        ('selling_price', models.DecimalField(decimal_places=2, default=0.00, max_digits=10, verbose_name='Selling Price')),
                        ('stock_quantity', models.PositiveIntegerField(default=0, verbose_name='Stock Quantity')),
                        ('box_quantity', models.PositiveIntegerField(default=1, help_text='How many products are in a box', verbose_name='Box Quantity')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='jeba_inventory.category', verbose_name='Category')),
                    ],
                    options={
                        'db_table': 'products_product',
                    },
                ),
                migrations.CreateModel(
                    name='ProductImage',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('image', models.ImageField(upload_to='products/gallery/', verbose_name='Image')),
                        ('transparent_image', models.ImageField(blank=True, help_text='Upload a PNG with no background here (Optional)', null=True, upload_to='products/transparent/', verbose_name='Transparent Image')),
                        ('is_main', models.BooleanField(default=False, verbose_name='Main Thumbnail')),
                        ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='jeba_inventory.product')),
                    ],
                    options={
                        'db_table': 'products_productimage',
                    },
                ),
                migrations.CreateModel(
                    name='ProductVariation',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=255, verbose_name='Variation Name')),
                        ('selling_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Selling Price')),
                        ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
                        ('stock_quantity', models.PositiveIntegerField(default=0, verbose_name='Stock Quantity')),
                        ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variations', to='jeba_inventory.product')),
                    ],
                    options={
                        'db_table': 'products_productvariation',
                    },
                ),
            ],
            database_operations=[
                migrations.AlterModelTable(
                    name='Category',
                    table='products_category',
                ),
                migrations.AlterModelTable(
                    name='Product',
                    table='products_product',
                ),
                migrations.AlterModelTable(
                    name='ProductImage',
                    table='products_productimage',
                ),
                migrations.AlterModelTable(
                    name='ProductVariation',
                    table='products_productvariation',
                ),
            ],
        ),
    ]