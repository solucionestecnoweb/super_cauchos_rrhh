# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'
    
    is_picking = fields.Selection(string='Inventario', selection=[
        ('required', 'Required'), ('optional', 'Optional'), ('no', 'Ninguno')], default='no')
