# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import ustr


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    payment_id = fields.Many2one('account.payment', string='Registro de Pago')
    is_payment = fields.Selection(related="category_id.is_payment")

