from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import base64
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.tools.float_utils import float_round

class SaleOrderDivisionReference(models.Model):
    _inherit = 'sale.order'

    national_purchase = fields.Many2one(comodel_name='purchase.order', string='Purchase Order')
    international_purchase = fields.Many2one(comodel_name='purchase.order', string='International Purchase Order')
    
