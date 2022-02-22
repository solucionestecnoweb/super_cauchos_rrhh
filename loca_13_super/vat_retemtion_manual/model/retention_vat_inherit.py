import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

_logger = logging.getLogger('__name__')


class RetentionVat(models.Model):
    """This is a main model for rentetion vat control."""
    _inherit = 'vat.retention'

    diario=fields.Many2one('account.journal')
    nro_control = fields.Char()

class VatRetentionInvoiceLine(models.Model):
    """This model is for a line invoices withholed."""
    _inherit = 'vat.retention.invoice.line'

    retention_amount_aux=fields.Float(compute='_compute_calcula')

    @api.onchange('retention_amount','retention_rate')
    def _compute_calcula(self):
        for rec in self:
            rec.retention_amount_aux=rec.amount_vat_ret*rec.retention_rate/100
            rec.retention_amount=rec.amount_vat_ret*rec.retention_rate/100