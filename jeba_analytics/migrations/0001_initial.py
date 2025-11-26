# jeba_analytics/migrations/0001_initial.py

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # --- FIX: Removed defunct dependency on 'products' app ---
        ('jeba_inventory', '0001_initial'), # Dependency on Product model
        migrations.swappable_dependency(settings.AUTH_USER_MODEL), # Dependency on User model
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='ProductEvent',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('session_id', models.CharField(blank=True, max_length=50, null=True, verbose_name='Session ID')),
                        ('event_type', models.CharField(choices=[('VIEW', 'View'), ('CART', 'Add to Cart'), ('PURCHASE', 'Purchase')], max_length=20, verbose_name='Event Type')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='jeba_inventory.product')),
                        ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='product_events', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'verbose_name': 'Product Event',
                        'verbose_name_plural': 'Product Events',
                        'db_table': 'products_productevent',
                    },
                ),
                migrations.CreateModel(
                    name='SearchEvent',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('session_id', models.CharField(blank=True, max_length=50, null=True, verbose_name='Session ID')),
                        ('query', models.CharField(max_length=255, verbose_name='Search Query')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='search_events', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'verbose_name': 'Search Event',
                        'verbose_name_plural': 'Search Events',
                        'db_table': 'products_searchevent',
                    },
                ),
            ],
            database_operations=[
                migrations.AlterModelTable(
                    name='ProductEvent',
                    table='products_productevent',
                ),
                migrations.AlterModelTable(
                    name='SearchEvent',
                    table='products_searchevent',
                ),
            ],
        ),
    ]