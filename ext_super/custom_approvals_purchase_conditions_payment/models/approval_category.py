# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'
    
    is_purchase_pay = fields.Selection(string='Ordenes de Pagos', selection=[
        ('required', 'Required'), ('optional', 'Optional'), ('no', 'Ninguno')], default='no')
