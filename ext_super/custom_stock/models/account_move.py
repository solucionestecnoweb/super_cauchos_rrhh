# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    date_venc = fields.Date(string='Fecha de Venc. Real')
    date_delivered = fields.Date(string='Fecha de despacho')

