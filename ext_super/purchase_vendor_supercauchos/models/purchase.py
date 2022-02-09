# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning

import time

class PurchaseOrderExtend(models.Model):
    _inherit = "purchase.order"

    marter_partner_id = fields.Many2one('res.partner', string='Sub Proveedor')
    
    


class AccountMove(models.Model):
    _inherit = "account.move"

    marter_partner_id = fields.Many2one('res.partner', string='Proveedor Master')
    
    @api.constrains('marter_partner_id')
    def set_marter_partner_id(self):
        if self.marter_partner_id.id :
            for item in self.line_ids:
                item.partner_id = self.partner_id 

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange('purchase_line_id')
    def marte_purchase_line_id(self):
        for item in self:
            if item.purchase_line_id.id and item.purchase_line_id.order_id.marter_partner_id.id:
                
                item.move_id.partner_id = item.purchase_line_id.order_id.marter_partner_id.id
                item.move_id.marter_partner_id = item.purchase_line_id.order_id.partner_id.id

    @api.constrains('purchase_line_id')
    def marte_purchase_line_id(self):
        for item in self:
            if item.purchase_line_id.id and item.purchase_line_id.order_id.marter_partner_id.id:
                item.move_id.partner_id = item.purchase_line_id.order_id.marter_partner_id.id
                item.move_id.marter_partner_id = item.purchase_line_id.order_id.partner_id.id