
from django.db import models

class OutstandingPayable(models.Model):
    docno = models.CharField('Doc No', max_length=100, primary_key=True)
    docdate = models.DateField('Doc Date')
    duedate = models.DateField('Due Date')
    settlementdate = models.DateField('Settlement Date', null=True, blank=True)
    doctype = models.CharField('Doc Type', max_length=50)
    Vendor = models.CharField('Vendor', max_length=255)
    amount = models.DecimalField('Amount', max_digits=12, decimal_places=2)
    paymentsadjustment = models.DecimalField('Payments Adjustment', max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField('Balance', max_digits=12, decimal_places=2)
    remarks = models.TextField(blank=True)
    PFRFtype = models.CharField('PFRF Type', max_length=50)
    documentstatus = models.CharField('Document Status', max_length=50)

    class Meta:
        managed = False
        db_table = 'outstandingpayables'

    def __str__(self):
        return f"{self.docno} - {self.Vendor} - ₱{self.balance}"

