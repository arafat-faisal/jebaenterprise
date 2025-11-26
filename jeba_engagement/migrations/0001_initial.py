import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # --- FIX: Removed dependency on 'products' app ---
        ('jeba_inventory', '0001_initial'), # Dependency on Product
        migrations.swappable_dependency(settings.AUTH_USER_MODEL), # Dependency on User
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Review',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('rating', models.IntegerField(default=5, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='Rating')),
                        ('comment', models.TextField(blank=True, null=True, verbose_name='Comment')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='jeba_inventory.product')),
                        ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'db_table': 'products_review',
                    },
                ),
                migrations.CreateModel(
                    name='Wishlist',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='jeba_inventory.product')),
                        ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wishlist', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'db_table': 'products_wishlist',
                        'unique_together': {('user', 'product')},
                    },
                ),
            ],
            database_operations=[
                migrations.AlterModelTable(
                    name='Review',
                    table='products_review',
                ),
                migrations.AlterModelTable(
                    name='Wishlist',
                    table='products_wishlist',
                ),
            ],
        ),
    ]