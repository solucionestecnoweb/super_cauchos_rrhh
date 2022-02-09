# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    picking_id = fields.Many2one('stock.picking', string='Picking')
    is_picking = fields.Selection(related="category_id.is_picking")
