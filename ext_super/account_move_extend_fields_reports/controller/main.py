# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict


import json
import logging
from datetime import datetime
from operator import pos
from werkzeug.exceptions import Forbidden, NotFound

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request

from odoo.addons.payment.controllers.portal import PaymentProcessing

from odoo.exceptions import ValidationError

from odoo.addons.portal.controllers.portal import CustomerPortal

from odoo.addons.payment_paypal.controllers.main import PaypalController


from odoo.osv import expression
_logger = logging.getLogger(__name__)


class CustomerPortal(CustomerPortal):

	@http.route(['/invoice/report_html/impress/<int:type>/<int:invoice>'], type='http', auth="public", website=True)
	def portal_my_invoice_report_html(self, invoice=None,type=None, **post):
		invoice_id = request.env['account.move'].sudo().search([
			('id', '=', invoice)
		])
		values = self._prepare_portal_layout_values()
		values.update({'o': invoice_id})
		if invoice_id.company_id.paperformat == 'letter':
			if type == 2:
				return request.render("account_move_extend_fields_reports.account_move_invoice_extend_letter_usd", values)
			else :
				return request.render("account_move_extend_fields_reports.account_move_invoice_extend_letter_bs", values)
		else: 
			if type == 2:
    				return request.render("account_move_extend_fields_reports.account_move_invoice_extend_half_letter_usd", values)
			else :
				return request.render("account_move_extend_fields_reports.account_move_invoice_extend_half_letter_bs", values)