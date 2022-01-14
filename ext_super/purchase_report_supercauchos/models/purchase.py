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

	date_end = fields.Date(string='End Date')
	priority = fields.Selection(string='Priority', selection=[('very_low', 'Very Low'), ('low', 'Low'), ('meddium', 'Meddium'), ('high', 'High')], default="low")
	rate = fields.Float(string='Rate',digits=(12, 4))
	
	def _date_now_purchase(self):
		xdate = datetime.now() - timedelta(hours=4)
		return xdate

	@api.onchange('date_order')
	def _onchange_rate(self):
		date_field = self.date_order
		rate = self.env['res.currency.rate'].search([('name', '<=', date_field.date()), ('company_id', '=', self.env.user.company_id.id)], limit=1).sell_rate
		if rate:
			self.rate = rate
		else:
			self.rate = 1
