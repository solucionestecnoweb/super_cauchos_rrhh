# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from itertools import product
import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning

import time

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    filler = fields.Float(string='Filler', related='product_id.filler')
    fillert = fields.Float(string='FillerT')

    @api.onchange('product_id', 'product_qty')
    def onchange_filler(self):
        for line in self:
            line.fillert = line.filler * line.product_qty

    @api.constrains('product_id', 'product_qty')
    def constrains_filler(self):
        for line in self:
            line.fillert = line.filler * line.product_qty

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    fillert = fields.Float(string='Filler Total')

    @api.onchange('order_line')
    def onchange_filler(self):
        self.calculate_filler()

    @api.constrains('order_line')
    def constrains_filler(self):
        self.calculate_filler()

    def calculate_filler(self):
        filler = 0
        for line in self.order_line:
            filler += line.fillert
        self.fillert = filler