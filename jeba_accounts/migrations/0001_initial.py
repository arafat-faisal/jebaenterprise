import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # --- FIX: Removed defunct dependency on 'products' app ---
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='UserProfile',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('phone_number', models.CharField(blank=True, max_length=20, null=True, verbose_name='Phone Number')),
                        ('address', models.TextField(blank=True, null=True, verbose_name='Address')),
                        ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'db_table': 'products_userprofile',
                    },
                ),
            ],
            database_operations=[],
        ),
    ]