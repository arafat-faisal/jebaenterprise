import time
import cProfile
import pstats
import io
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
from jeba_inventory.models import Product
from jeba_sales.models import Sale
import os

class Command(BaseCommand):
    help = 'Benchmarks database read/write speed and CPU execution'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting Internal Speed Test..."))
        
        # 1. Database Read Test
        start_time = time.time()
        product_count = Product.objects.count()
        # Fetch 500 products (simulates a heavy category page)
        products = list(Product.objects.all().select_related()[:500]) 
        db_read_time = time.time() - start_time
        
        self.stdout.write(f"✅ DB READ: Fetched 500/{product_count} products in {db_read_time:.4f} seconds")
        
        # 2. Template/CPU Rendering Simulation
        # We simulate some Python logic processing (calculating totals)
        start_time = time.time()
        total_value = sum(p.selling_price for p in products if p.selling_price)
        cpu_time = time.time() - start_time
        
        self.stdout.write(f"✅ CPU/LOGIC: Processed calculations in {cpu_time:.4f} seconds")

        # 3. File System I/O (Crucial because you use File-based sessions)
        start_time = time.time()
        session_path = settings.SESSION_FILE_PATH
        test_file = session_path / 'speed_test_temp'
        with open(test_file, 'w') as f:
            f.write("test" * 1000)
        os.remove(test_file)
        io_time = time.time() - start_time
        
        self.stdout.write(f"✅ DISK I/O: File write/delete took {io_time:.4f} seconds")
        
        # Summary
        if db_read_time > 0.5:
            self.stdout.write(self.style.ERROR("⚠️  Database is responding slowly."))
        elif io_time > 0.1:
            self.stdout.write(self.style.ERROR("⚠️  Disk storage is slow (This affects your Sessions!)."))
        else:
            self.stdout.write(self.style.SUCCESS("🚀 Internal system speed looks good! The issue might be Network/Internet."))