# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import ustr


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    purchase_id = fields.Many2one(comodel_name='purchase.order', string='Pedido de Compra')
    is_purchase = fields.Selection(related="category_id.is_purchase")
