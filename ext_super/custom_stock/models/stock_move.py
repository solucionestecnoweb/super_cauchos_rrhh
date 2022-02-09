# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = "stock.move"
    
    filler = fields.Float(related='product_id.filler', string="Filler", store=True)