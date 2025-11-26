# jeba_intelligence/migrations/0001_initial.py

import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # --- FIX: Removed defunct dependency on 'products' app (the implicit 0035 migration) ---
        ('jeba_inventory', '0001_initial'), # Dependency on Product model
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='CompetitorPrice',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('website_name', models.CharField(max_length=100, verbose_name='Website Name')),
                        ('min_price', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='Min Price')),
                        ('max_price', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='Max Price')),
                        ('last_checked', models.DateTimeField(auto_now=True)),
                        ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='competitor_prices', to='jeba_inventory.product')),
                    ],
                    options={
                        'verbose_name': 'Competitor Price',
                        'verbose_name_plural': 'Competitor Prices',
                        'db_table': 'products_competitorprice',
                    },
                ),
                migrations.CreateModel(
                    name='ScraperPreset',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=100, unique=True, verbose_name='Preset Name')),
                        ('confidence_threshold', models.DecimalField(decimal_places=2, default=0.8, max_digits=3, verbose_name='Confidence Threshold')),
                        ('text_slam_dunk', models.TextField(blank=True, help_text='Keywords that guarantee a match (one per line)', null=True, verbose_name='Slam Dunk Keywords')),
                    ],
                    options={
                        'verbose_name': 'Scraper Preset',
                        'verbose_name_plural': 'Scraper Presets',
                        'db_table': 'products_scraperpreset',
                    },
                ),
            ],
            database_operations=[
                migrations.AlterModelTable(
                    name='CompetitorPrice',
                    table='products_competitorprice',
                ),
                migrations.AlterModelTable(
                    name='ScraperPreset',
                    table='products_scraperpreset',
                ),
            ],
        ),
    ]