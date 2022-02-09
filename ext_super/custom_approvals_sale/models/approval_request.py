# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import ustr
from odoo.exceptions import UserError, ValidationError, except_orm, Warning


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    sale_id = fields.Many2one('sale.order', string='Pedido de Venta')
    is_sale = fields.Selection(related="category_id.is_sale")
