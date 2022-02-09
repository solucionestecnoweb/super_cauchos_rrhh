# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError, except_orm, Warning


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'
    
    is_sale = fields.Selection(string='Ventas', selection=[
        ('required', 'Required'), ('optional', 'Optional'), ('no', 'Ninguno')], default='no')
