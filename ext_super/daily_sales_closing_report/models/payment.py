from odoo import api, fields, models


class AccountPaymentMethodSales(models.Model):
    _inherit = 'account.payment.method'

    sales_report = fields.Boolean(string='¿Usar en el reporte de cierre de ventas diario?')
    