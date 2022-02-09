from odoo import api, fields, models


class AccountJournalSales(models.Model):
    _inherit = 'account.journal'

    closing_report = fields.Boolean(string='¿Usar en el reporte de cierre de cobranza?')
    