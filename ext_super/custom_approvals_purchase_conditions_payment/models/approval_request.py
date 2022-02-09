# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import ustr


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    purchase_pay_id = fields.Many2one(comodel_name='purchase.pay.order', string='Orden de pago')
    is_purchase_pay = fields.Selection(related="category_id.is_purchase_pay")
