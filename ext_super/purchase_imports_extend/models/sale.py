# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from itertools import accumulate, product
import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import ValidationError, Warning

import time

class SaleOrderImport(models.Model):
    _inherit = 'sale.order'

    is_transit_merch = fields.Boolean(string='Use Merchandise in Transit?')
    company_to_apart_id = fields.Many2one(comodel_name='res.company', string='Compañía a Apartar')

class SaleOrderLineImport(models.Model):
    _inherit = 'sale.order.line'

    is_transit_merch = fields.Boolean(related='order_id.is_transit_merch')
    
    @api.onchange('product_id', 'product_uom_qty')
    def product_transit(self):
        if self.order_id.is_transit_merch:
            if self.product_id:
                cfind = self.env['purchase.order.line'].sudo().search([
                        ('state', 'in', ('draft', 'sent', 'purchase')),
                        ('qty_received', '=', 0),
                        ('company_id.imports_company', '=', True),
                        ('product_id', '=', self.product_id.id),
                        ('order_id.purchase_type', '=', 'international')
                    ])
                amount = 0
                for item in cfind:
                    amount += item.product_qty
                xfind = self.env['sale.order.line'].sudo().search([
                        ('state', 'in', ('draft', 'sent')),
                        ('product_id', '=', self.product_id.id),
                        ('is_transit_merch', '=', True),
                        ('order_id.seller_id', '!=', False),
                    ])
                selled = 0
                for item in xfind:
                    selled += item.product_uom_qty
                result = amount - (selled + self.product_uom_qty)
                if result < 0:
                    raise ValidationError("La cantidad solicitada excede la cantidad disponible en tránsito. \nCantidad en disponible: %d \nCantidad solicitada: %d" %(int(amount - selled), int(self.product_uom_qty)))
