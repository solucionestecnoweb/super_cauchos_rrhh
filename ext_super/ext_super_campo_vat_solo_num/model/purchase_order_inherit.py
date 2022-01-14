# -*- coding: utf-8 -*-


import logging
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    price_unit = fields.Float(digits=(12, 4), string="ccc")
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True,digits=(12, 4))
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True, digits=(12, 4))
    #price_subtotal = fields.Float(digits=(12, 4))

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    price_unit = fields.Float('Unit Price', required=True, digits=(12, 4), default=0.0)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    price_unit = fields.Float(string='Unit Price', digits=(12, 4))
    discount = fields.Float(string='Discount (%)', digits=(12, 4), default=0.0)

