# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models, _
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning

import time

class SaleOrderExtend(models.Model):
	_inherit = "sale.order"

	arrive_date = fields.Date(string='Arrive Date')
	payment_condition_id = fields.Many2one(comodel_name='account.condition.payment', string='Payment Condition')
	rate = fields.Float(string='Tasa', default=lambda x: x.env['res.currency.rate'].search([('name', '<=', fields.Date.today()), ('currency_id', '=', 2)], limit=1).sell_rate)
	
	@api.onchange('partner_id')
	def _onchange_seller(self):
		if self.partner_id.payment_condition_id:
			self.payment_condition_id = self.partner_id.payment_condition_id.id


	def _date_now_purchase(self):
		xdate = datetime.now() - timedelta(hours=4)
		return xdate

	def _get_rate(self):
		xfind = self.env['res.currency.rate'].search([
			('name', '=', self.date_order)
		], limit=1)
		rate = 0.00
		for item in xfind:
			rate = item.sell_rate
		return rate

	def _get_boss_signature(self):
		xfind = self.env['res.users'].search([
			('is_boss', '=', True)
		])
		return xfind
