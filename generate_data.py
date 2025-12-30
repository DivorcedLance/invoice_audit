import random
import os
from datetime import datetime, timedelta

# Crear carpeta
os.makedirs("sample_xmls", exist_ok=True)

def create_xml(filename, date_obj, is_valid=True):
    issue_date = date_obj.strftime("%Y-%m-%d")
    
    # Lógica de precios
    item_price = random.randint(50, 500)
    qty = random.randint(1, 10)
    real_total = item_price * qty
    display_total = real_total if is_valid else real_total + random.randint(10, 100)
    
    invoice_id = f"F{random.randint(10,99)}-{random.randint(1000, 9999)}"

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>{invoice_id}</cbc:ID>
    <cbc:IssueDate>{issue_date}</cbc:IssueDate>
    <cac:LegalMonetaryTotal>
        <cbc:PayableAmount currencyID="PEN">{display_total}.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    <cac:InvoiceLine>
        <cbc:ID>1</cbc:ID>
        <cbc:InvoicedQuantity unitCode="NIU">{qty}.00</cbc:InvoicedQuantity>
        <cac:Item>
            <cbc:Description>Servicio Consultoría TI - {date_obj.strftime('%A')}</cbc:Description>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="PEN">{item_price}.00</cbc:PriceAmount>
        </cac:Price>
    </cac:InvoiceLine>
</Invoice>"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(xml_content)

# --- Lógica de Semana Actual ---
print("--- Generando data para la semana actual ---")

# Obtener el lunes de esta semana
today = datetime.now()
start_of_week = today - timedelta(days=today.weekday())

file_counter = 0

# Generar facturas desde el lunes hasta hoy
for i in range((today - start_of_week).days + 1):
    current_day = start_of_week + timedelta(days=i)
    
    # Generar entre 2 y 5 facturas por día para que se vea movimiento
    num_docs = random.randint(2, 5)
    
    for _ in range(num_docs):
        # 85% de probabilidad de ser válida
        es_valido = random.random() > 0.15
        filename = f"sample_xmls/inv_week_{file_counter}.xml"
        create_xml(filename, current_day, is_valid=es_valido)
        file_counter += 1
        print(f"Generado: {filename} ({current_day.strftime('%Y-%m-%d')})")