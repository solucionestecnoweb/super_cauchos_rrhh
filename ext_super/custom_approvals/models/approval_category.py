# -*- coding: utf-8 -*-

from odoo import fields, models, tools


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    is_rejected = fields.Selection(string='Motivo Rechazo', selection=[
        ('required', 'Required'), ('optional', 'Optional'), ('no', 'Ninguno')], default='no')
