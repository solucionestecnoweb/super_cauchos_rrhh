# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    date_order = fields.Datetime(string='Order Date',readonly=0, required=True,default=fields.Datetime.now)
    validity_date = fields.Date(string='Expiration',readonly=0)

class PurchaseOrder(models.Model):
	_inherit = 'purchase.order'

	date_order = fields.Datetime('Order Date', required=True,readonly=0,default=fields.Datetime.now)
	date_approve = fields.Datetime('Confirmation Date',readonly=0)
