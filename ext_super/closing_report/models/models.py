import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models, _
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning
import time
import json

class Report(models.Model):
    
    _inherit ='account.payment'

    def get_rate(self):
        rate_value = 1
        rate = self.env['res.currency.rate'].search([('name','=', self.payment_date)], limit=1).sell_rate
        if rate:
            rate_value = rate
        return rate_value

    rate = fields.Float(string="Rate", default=lambda self: self.get_rate(), digits=(12,2))
    amount_bs = fields.Monetary(compute='_compute_amount_bs', currency_field='currency_bs_id', digits=(12,2))
    amount_currency = fields.Monetary(compute='_compute_amount_currency', currency_field='currency_usd_id', digits=(12,2))
    currency_bs_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id)
    currency_usd_id = fields.Many2one('res.currency', default= lambda self: self.env['res.currency'].search([('id', '=', 2)]))
    amount_currency_cash = fields.Monetary(compute='_compute_cash', currency_field='currency_usd_id', digits=(12,2))
    amount_currency_transfer =fields.Monetary(compute='_compute_transfer', currency_field='currency_usd_id', digits=(12,2))

    # @api.onchange('payment_date')
    # def _onchange_rate(self):
    #     rate = self.get_rate()
    #     self.rate = rate

    def _compute_amount_bs(self):
        for item in self:
            item.amount_bs = 0.00
            if (item.currency_id.name == 'USD'):
                item.amount_bs = item.amount * item.rate
            if (item.currency_id.name == 'EUR'):
                item.amount_bs = item.amount * item.rate
            if (item.currency_id.name == 'Bs.'):
                item.amount_bs = item.amount
    def _compute_amount_currency(self):
        for item in self:
            item.amount_currency = 0.00
            if (item.currency_id.name == 'USD'):
                item.amount_currency = item.amount
            if (item.currency_id.name == 'EUR'):
                item.amount_currency = item.amount
            if (item.currency_id.name == 'Bs.'):
                item.amount_currency = item.amount / item.rate
    
    def _compute_cash(self):
        for item in self:
            item.amount_currency_cash = 0.00
            if (item.currency_id.name == 'USD'):
                if (item.payment_method_id.name == 'Efectivo $'):
                    item.amount_currency_cash = item.amount
            if (item.currency_id.name == 'EUR'):
                if (item.payment_method_id.name == 'Efectivo €'):
                    item.amount_currency_cash = item.amount
            if (item.currency_id.name == 'USD'):
                if (item.payment_method_id.name == 'Transferencia'):
                    item.amount_currency_cash = 0.00

    def _compute_transfer(self):
        for item in self:
            item.amount_currency_transfer = 0.00
            if (item.currency_id.name == 'USD'):
                if (item.payment_method_id.name == 'Efectivo $'):
                    item.amount_currency_transfer = 0.00
            if (item.currency_id.name == 'EUR'):
                if (item.payment_method_id.name == 'Efectivo €'):
                    item.amount_currency_transfer = 0.00
            if (item.currency_id.name == 'USD'):
                if (item.payment_method_id.name == 'Transferencia'):
                    item.amount_currency_transfer = item.amount