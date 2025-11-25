import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('jeba_inventory', '0001_initial'),
        ('products', '0035_alter_sale_access_token'), # Force wait
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='ScraperPreset',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=100, unique=True, verbose_name='Preset Name')),
                        ('image_weight', models.DecimalField(decimal_places=2, default=0.3, max_digits=3)),
                        ('text_weight', models.DecimalField(decimal_places=2, default=0.7, max_digits=3)),
                        ('confidence_threshold', models.IntegerField(default=60)),
                        ('text_slam_dunk', models.IntegerField(default=85)),
                        ('image_slam_dunk', models.IntegerField(default=90)),
                    ],
                    options={
                        'db_table': 'products_scraperpreset',
                    },
                ),
                migrations.CreateModel(
                    name='CompetitorPrice',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('website_name', models.CharField(max_length=100, verbose_name='Website Name')),
                        ('min_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                        ('max_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                        ('last_checked', models.DateTimeField(auto_now=True)),
                        ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='competitor_prices', to='jeba_inventory.product')),
                    ],
                    options={
                        'db_table': 'products_competitorprice',
                    },
                ),
            ],
            database_operations=[],
        ),
    ]