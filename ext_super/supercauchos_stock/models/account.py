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

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    filler = fields.Float(string='Filler', related='product_id.filler')
    fillert = fields.Float(string='FillerT')

    @api.onchange('product_id', 'quantity')
    def onchange_filler(self):
        for line in self:
            line.fillert = line.filler * line.quantity

    @api.constrains('product_id', 'quantity')
    def constrains_filler(self):
        for line in self:
            line.fillert = line.filler * line.quantity

class AccountMoveLine(models.Model):
    _inherit = 'account.move'

    fillert = fields.Float(string='Filler Total')

    @api.onchange('invoice_line_ids')
    def onchange_filler(self):
        self.calculate_filler()

    @api.constrains('invoice_line_ids')
    def constrains_filler(self):
        self.calculate_filler()

    def calculate_filler(self):
        filler = 0
        for line in self.invoice_line_ids:
            filler += line.fillert
        self.fillert = filler
