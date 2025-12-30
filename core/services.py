# core/services.py
import xml.etree.ElementTree as ET
from decimal import Decimal
from django.db import transaction
from .models import Invoice, InvoiceLine

class InvoiceProcessor:
    def __init__(self, xml_file):
        self.tree = ET.parse(xml_file)
        self.root = self.tree.getroot()
        # Namespace genérico de UBL (ajustable)
        self.ns = {'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'}

    def parse_and_save(self, filename):
        try:
            # Usamos atomic para asegurar integridad de datos (SQL transaction)
            with transaction.atomic():
                # 1. Extraer Cabecera
                # Nota: El path depende del XML, usamos búsqueda simplificada
                inv_id = self.root.find('.//{*}ID').text
                total_rep = Decimal(self.root.find('.//{*}PayableAmount').text)
                currency = self.root.find('.//{*}PayableAmount').attrib.get('currencyID', 'USD')
                
                # --- NUEVO: Extraer Fecha de Emisión ---
                # Buscamos el nodo IssueDate (fecha real de la factura)
                issue_date_node = self.root.find('.//{*}IssueDate')
                issue_date = issue_date_node.text if issue_date_node is not None else None

                # Crear Objeto Invoice
                invoice = Invoice.objects.create(
                    filename=filename,
                    invoice_id=inv_id,
                    currency=currency,
                    total_reported=total_rep,
                    issue_date=issue_date  # <--- Guardamos la fecha aquí
                )

                # 2. Procesar Líneas y Recalcular
                calculated_sum = Decimal(0)
                
                # Buscar todas las líneas de la factura
                for line_node in self.root.findall('.//{*}InvoiceLine'):
                    desc = line_node.find('.//{*}Description').text
                    qty = Decimal(line_node.find('.//{*}InvoicedQuantity').text)
                    price = Decimal(line_node.find('.//{*}PriceAmount').text)
                    
                    line_total = qty * price
                    calculated_sum += line_total

                    InvoiceLine.objects.create(
                        invoice=invoice,
                        description=desc,
                        quantity=qty,
                        unit_price=price,
                        line_total=line_total
                    )

                # 3. Validación de Auditoría
                # Si la diferencia es menor a 0.01, es válido
                invoice.total_calculated = calculated_sum
                if abs(total_rep - calculated_sum) < Decimal('0.01'):
                    invoice.is_mathematically_valid = True
                else:
                    invoice.is_mathematically_valid = False
                
                invoice.save()
                return invoice

        except Exception as e:
            # Captura errores de XML mal formados
            print(f"Error procesando {filename}: {e}")
            return None