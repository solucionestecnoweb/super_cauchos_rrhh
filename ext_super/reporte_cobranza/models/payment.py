from odoo import api, fields, models


class AccountPaymentMethodSales(models.Model):
    _inherit = 'account.payment.method'

    closing_report = fields.Boolean(string='¿Usar en el reporte de cierre de cobranza?')
    