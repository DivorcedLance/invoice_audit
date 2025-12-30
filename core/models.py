from django.db import models

class Invoice(models.Model):
    # Cabecera de la factura
    filename = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    issue_date = models.DateField(null=True, blank=True)
    invoice_id = models.CharField(max_length=50)  # Ej: F001-442
    currency = models.CharField(max_length=3, default='USD')
    total_reported = models.DecimalField(max_digits=10, decimal_places=2)
    total_calculated = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # El campo clave para tu dashboard
    is_mathematically_valid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.invoice_id} - {self.total_reported}"

class InvoiceLine(models.Model):
    # Detalle de items (Relación 1 a muchos)
    invoice = models.ForeignKey(Invoice, related_name='lines', on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)