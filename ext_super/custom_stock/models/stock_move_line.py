# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    filler = fields.Float(related='product_id.filler', string="Filler", store=True)