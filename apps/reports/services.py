from datetime import date
from decimal import Decimal
from django.db.models import Sum, Count, Q
from apps.reports.models import Report
from apps.finance.models import Transaction, Account
from apps.real_estate.models import IndustrialUnitRecord, IndustrialBuilding, IndustrialReservationLead

def create_report(**data):
    return Report.objects.create(**data)

def generate_project_detailed_report(report_id):
    """
    Generates a comprehensive JSON data structure for a detailed project report.
    """
    try:
        report = Report.objects.get(pk=report_id)
        project = report.project
        if not project:
            return None

        # 1. Financial Data (Transactions)
        transactions = Transaction.objects.filter(
            project=project,
            date__range=[report.period_start, report.period_end]
        ).select_related('account', 'category')

        total_income = transactions.filter(transaction_type='income').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_expense = transactions.filter(transaction_type='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Categorized Finance
        finance_by_category = []
        categories = transactions.values('category__name', 'transaction_type').annotate(total=Sum('amount')).order_by('-total')
        for cat in categories:
            finance_by_category.append({
                'name': cat['category__name'] or 'غير مصنف',
                'type': cat['transaction_type'],
                'amount': float(cat['total'])
            })

        # 2. Real Estate Data (Units & Occupancy)
        all_units = IndustrialUnitRecord.objects.filter(building__project=project).select_related('building')
        total_units = all_units.count()
        
        status_counts = all_units.values('status').annotate(count=Count('id'))
        status_map = dict(IndustrialUnitRecord.Status.choices)
        
        occupancy_data = []
        for s in status_counts:
            occupancy_data.append({
                'label': status_map.get(s['status'], s['status']),
                'count': s['count']
            })

        rented_reserved = all_units.filter(status__in=[
            IndustrialUnitRecord.Status.RENTED, 
            IndustrialUnitRecord.Status.RESERVED
        ]).count()
        occupancy_rate = round((rented_reserved / total_units * 100), 1) if total_units else 0

        # 3. Revenue & Collections
        revenue_metrics = all_units.aggregate(
            expected=Sum('annual_rent'),
            paid=Sum('paid_amount'),
            remaining=Sum('remaining_amount'),
            area=Sum('area')
        )
        
        expected_total = revenue_metrics['expected'] or Decimal('0')
        paid_total = revenue_metrics['paid'] or Decimal('0')
        collection_rate = round(float((paid_total / expected_total) * 100), 1) if expected_total else 0

        # 4. Building Performance
        buildings = IndustrialBuilding.objects.filter(project=project)
        building_stats = []
        for b in buildings:
            b_units = all_units.filter(building=b)
            b_metrics = b_units.aggregate(rent=Sum('annual_rent'), paid=Sum('paid_amount'), count=Count('id'))
            b_rented = b_units.filter(status=IndustrialUnitRecord.Status.RENTED).count()
            b_reserved = b_units.filter(status=IndustrialUnitRecord.Status.RESERVED).count()
            
            building_stats.append({
                'name': b.name,
                'units': b_metrics['count'],
                'occupancy': round(((b_rented + b_reserved) / b_metrics['count'] * 100), 1) if b_metrics['count'] else 0,
                'annual_rent': float(b_metrics['rent'] or 0),
                'paid': float(b_metrics['paid'] or 0)
            })

        # 5. Leads & Customers
        leads_count = IndustrialReservationLead.objects.filter(project=project, created_at__date__range=[report.period_start, report.period_end]).count()

        # Compile final data
        report.data = {
            'summary': {
                'project_name': project.name,
                'period': f"{report.period_start} to {report.period_end}",
                'total_income': float(total_income),
                'total_expense': float(total_expense),
                'net_profit': float(total_income - total_expense),
                'occupancy_rate': occupancy_rate,
                'collection_rate': collection_rate,
                'total_units': total_units,
                'total_area': float(revenue_metrics['area'] or 0),
            },
            'finance': {
                'by_category': finance_by_category,
                'recent_transactions': [
                    {'date': str(t.date), 'desc': t.description, 'amount': float(t.amount), 'type': t.transaction_type}
                    for t in transactions[:20]
                ]
            },
            'real_estate': {
                'occupancy_breakdown': occupancy_data,
                'building_performance': building_stats,
                'revenue': {
                    'expected': float(expected_total),
                    'paid': float(paid_total),
                    'remaining': float(revenue_metrics['remaining'] or 0)
                }
            },
            'growth': {
                'new_leads': leads_count
            }
        }
        report.status = 'generated'
        report.save()
        return True
    except Exception as e:
        print(f"Error generating report: {e}")
        return False
