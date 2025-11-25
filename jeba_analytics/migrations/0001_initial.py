import django.db.models.deletion
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
                    name='ProductEvent',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('session_id', models.CharField(blank=True, max_length=100, null=True)),
                        ('event_type', models.CharField(choices=[('VIEW', 'Product View'), ('CART', 'Added to Cart'), ('PURCHASE', 'Purchased'), ('SHARE', 'Shared')], max_length=20)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='jeba_inventory.product')),
                        ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'db_table': 'products_productevent',
                    },
                ),
                migrations.CreateModel(
                    name='SearchEvent',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('query', models.CharField(max_length=255)),
                        ('session_id', models.CharField(blank=True, max_length=100, null=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'db_table': 'products_searchevent',
                    },
                ),
            ],
            database_operations=[],
        ),
    ]