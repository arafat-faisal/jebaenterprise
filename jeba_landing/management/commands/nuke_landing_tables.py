from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Drops all jeba_landing tables to fix migration sync issues.'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Find all tables starting with jeba_landing_
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name LIKE 'jeba_landing_%' 
                AND table_schema = 'public'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                self.stdout.write(self.style.WARNING("No tables found to drop."))
                return

            self.stdout.write(f"Dropping {len(tables)} tables: {', '.join(tables)}")
            
            # Disable constraints to allow dropping in any order
            # (Postgres specific, but usually works if we cascade)
            for table in tables:
                self.stdout.write(f"Dropping {table}...")
                cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')

        self.stdout.write(self.style.SUCCESS("Boom! Tables nuked."))
