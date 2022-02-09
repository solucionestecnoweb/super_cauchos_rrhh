# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountConditionPayment(models.Model):
    _inherit = 'account.condition.payment'
    
    is_approval = fields.Boolean(string="Tiene Aprobacion")
    approver_ids = fields.Many2many('res.users', string='Aprobadores')
