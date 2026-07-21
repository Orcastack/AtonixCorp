from django.contrib import admin
from .models import Expense, Income, Budget


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['description', 'amount', 'category', 'date', 'created_at']
    list_filter = ['category', 'date']
    search_fields = ['description', 'category']
    date_hierarchy = 'date'


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ['source', 'amount', 'date', 'created_at']
    list_filter = ['date']
    search_fields = ['source']
    date_hierarchy = 'date'


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['category', 'spent', 'limit', 'remaining', 'percentage_used']
    list_filter = ['category']
    search_fields = ['category']
    
    def remaining(self, obj):
        return f"${obj.remaining:.2f}"
    
    def percentage_used(self, obj):
        return f"{obj.percentage_used:.1f}%"
