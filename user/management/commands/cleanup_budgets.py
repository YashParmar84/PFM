from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from user.models import Budget
from decimal import Decimal


class Command(BaseCommand):
    help = 'Clean up problematic budgets with extremely high amounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--max-amount',
            type=float,
            default=1000000,
            help='Maximum allowed budget amount (default: 1,000,000)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        max_amount = Decimal(str(options['max_amount']))

        # Find budgets with extremely high amounts
        problematic_budgets = Budget.objects.filter(amount__gt=max_amount)

        if not problematic_budgets:
            self.stdout.write(
                self.style.SUCCESS(f'No budgets found with amounts exceeding ₹{max_amount}')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'Found {problematic_budgets.count()} budgets with amounts exceeding ₹{max_amount}')
        )

        # Show details of problematic budgets
        for budget in problematic_budgets:
            self.stdout.write(
                f'  - User: {budget.user.username}, Category: {budget.get_category_display()}, '
                f'Amount: ₹{budget.amount}, Month: {budget.month}'
            )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Dry run completed. {problematic_budgets.count()} budgets would be deleted.')
            )
            return

        # Delete problematic budgets
        deleted_count, _ = problematic_budgets.delete()

        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_count} problematic budgets.')
        )
