# core/views.py
import xml.etree.ElementTree as ET

from django.db.models import Sum, Count
from django.db.models.functions import TruncDay
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
import os
import json

from django.shortcuts import redirect, render
from .models import Invoice
from .services import InvoiceProcessor

# --- Helper para listar ejemplos ---
def get_available_samples():
    samples_dir = os.path.join(settings.BASE_DIR, 'sample_xmls')
    if not os.path.exists(samples_dir):
        return []
    # Listar solo archivos .xml
    return [f for f in os.listdir(samples_dir) if f.endswith('.xml')]

# --- Vistas ---

def dashboard(request):
    invoices = Invoice.objects.all().order_by('-upload_date')
    
    # 1. KPIs Generales
    total_docs = invoices.count()
    valid_docs = invoices.filter(is_mathematically_valid=True).count()
    
    # Suma total de dinero (Manejar caso de 0 si no hay facturas)
    total_amount_sum = invoices.aggregate(Sum('total_reported'))['total_reported__sum'] or 0

    # 2. Preparar datos para el Gráfico de Tendencia (Agrupar por Día)
    # Esto crea una lista: [{'day': datetime.date(2023,10,25), 'total': 1500}, ...]
    daily_stats = Invoice.objects.filter(issue_date__isnull=False).annotate(
        day=TruncDay('issue_date')  # <--- CAMBIO AQUÍ
    ).values('day').annotate(
        daily_total=Sum('total_reported')
    ).order_by('day')

    # Separar en listas para Chart.js
    chart_labels = [stat['day'].strftime("%d/%m") for stat in daily_stats]
    chart_data = [float(stat['daily_total']) for stat in daily_stats]

    context = {
        'invoices': invoices,
        'kpi_total': total_docs,
        'kpi_valid': valid_docs,
        'kpi_error': total_docs - valid_docs,
        'kpi_money': total_amount_sum, # Nuevo KPI
        'available_samples': get_available_samples(),
        # Datos para gráficos
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'dashboard.html', context)

def get_invoice_detail(request, pk):
    try:
        invoice = Invoice.objects.get(pk=pk)
        lines = []
        for line in invoice.lines.all():
            lines.append({
                'desc': line.description,
                'qty': float(line.quantity),
                'price': float(line.unit_price),
                'total': float(line.line_total)
            })
        
        data = {
            'id': invoice.invoice_id,
            'date': invoice.issue_date.strftime('%Y-%m-%d') if invoice.issue_date else 'N/A',
            'lines': lines,
            'total_calculated': float(invoice.total_calculated or 0),
            'total_reported': float(invoice.total_reported or 0)
        }
        return JsonResponse(data)
    except Invoice.DoesNotExist:
        return JsonResponse({'error': 'Factura no encontrada'}, status=404)

def upload_invoice(request):
    if request.method == 'POST':
        processor = None
        
        # --- CASO 1: Subida manual (Múltiples archivos desde PC) ---
        if request.FILES.getlist('xml_file'):
            files = request.FILES.getlist('xml_file')
            count = 0
            for xml_file in files:
                processor = InvoiceProcessor(xml_file)
                if processor.parse_and_save(xml_file.name):
                    count += 1
            messages.success(request, f"Se cargaron {count} archivos desde tu PC.")

        # --- CASO 2: Procesar TODO el repositorio (NUEVO) ---
        elif request.POST.get('process_all') == 'true':
            samples_dir = os.path.join(settings.BASE_DIR, 'sample_xmls')
            if os.path.exists(samples_dir):
                files = [f for f in os.listdir(samples_dir) if f.endswith('.xml')]
                count = 0
                for fname in files:
                    fpath = os.path.join(samples_dir, fname)
                    with open(fpath, 'rb') as f:
                        processor = InvoiceProcessor(f)
                        if processor.parse_and_save(fname):
                            count += 1
                
                if count > 0:
                    messages.success(request, f"¡Éxito! Se procesaron {count} facturas del repositorio automáticamente.")
                else:
                    messages.warning(request, "No se encontraron archivos XML válidos en la carpeta de ejemplos.")

        # --- CASO 3: Procesar un solo ejemplo seleccionado ---
        elif request.POST.get('sample_filename'):
            sample_name = request.POST.get('sample_filename')
            sample_path = os.path.join(settings.BASE_DIR, 'sample_xmls', sample_name)
            
            if os.path.exists(sample_path):
                with open(sample_path, 'rb') as f:
                    processor = InvoiceProcessor(f)
                    result = processor.parse_and_save(sample_name)
                    if result:
                         status = "Válida" if result.is_mathematically_valid else "Error Math"
                         tags = "success" if result.is_mathematically_valid else "warning"
                         messages.add_message(request, getattr(messages, tags.upper()), 
                                              f"Factura {result.invoice_id}: {status}")

    return redirect('dashboard')

# Nueva vista para AJAX: Obtener contenido para preview
def get_sample_preview(request):
    filename = request.GET.get('filename')
    file_path = os.path.join(settings.BASE_DIR, 'sample_xmls', filename)
    
    if not os.path.exists(file_path):
        return JsonResponse({'error': 'File not found'}, status=404)

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Namespaces para UBL Invoice
        ns = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
        }
        
        # 1. Total Reportado (Lo que dice el XML en la cabecera)
        total_reported = root.findtext('.//cac:LegalMonetaryTotal/cbc:PayableAmount', namespaces=ns, default='0.00')

        # 2. Total Calculado (Sumamos los items manualmente para el preview)
        items = []
        calculated_sum = 0.0

        for line in root.findall('.//cac:InvoiceLine', namespaces=ns):
            qty = float(line.findtext('.//cbc:InvoicedQuantity', namespaces=ns, default='0'))
            price = float(line.findtext('.//cac:Price/cbc:PriceAmount', namespaces=ns, default='0.00'))
            subtotal = qty * price
            calculated_sum += subtotal
            items.append({
                'desc': line.findtext('.//cac:Item/cbc:Description', namespaces=ns, default='Item'),
                'qty': qty,
                'price': price,
                'subtotal': subtotal
            })

        data = {
            'id': root.findtext('.//cbc:ID', namespaces=ns, default='N/A'),
            'date': root.findtext('.//cbc:IssueDate', namespaces=ns, default='N/A'),
            'total_reported': float(total_reported),
            'total_calculated': calculated_sum,
            'items': items
        }
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': f'Error parsing XML: {str(e)}'}, status=500)