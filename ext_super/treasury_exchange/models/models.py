import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models, _
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning
import time

class Exchange(models.Model):
	_name ='account.exchange'

	name = fields.Char(string='Transaction', default='/')

	amount = fields.Monetary(string="Amount", currency_field='origin_currency_id',track_visibility='onchange')
	transaction = fields.Selection(selection=[("buy","Buy"),("sale","Sale")] ,string="Transaction", default='buy',track_visibility='onchange')
	final_currency_id = fields.Many2one ('res.currency' ,"Modeda Destino" ,track_visibility='onchange')
	rate = fields.Float(string="Rate", default=1 ,track_visibility='onchange')

	journal_id = fields.Many2one('account.journal', "Diario" ,track_visibility='onchange')
	debit_id = fields.Many2one('account.journal', "Origen de Fondos" ,track_visibility='onchange')
	credit_id = fields.Many2one('account.journal',"Destino de Fondos" ,track_visibility='onchange')
	account_id = fields.Many2one('account.account',"Cuenta Transitoria" ,track_visibility='onchange')

	move_transient_id  = fields.Many2one('account.move',"Asiento Origen" ,track_visibility='onchange')
	move_id   = fields.Many2one('account.move',"Asiento Destino" ,track_visibility='onchange')

	final_amount = fields.Monetary(string="Final Amount", currency_field='final_currency_id' ,track_visibility='onchange')
	company_id = fields.Many2one ('res.company', default=lambda self: self.env.company.id ,track_visibility='onchange')
	origin_currency_id = fields.Many2one ('res.currency', default=lambda self: self.env.company.currency_id.id ,track_visibility='onchange')
	request = fields.Date(string='Date of request', default=fields.Date.context_today,track_visibility='onchange')
	confirmation = fields.Datetime(string='Date of confirmation',track_visibility='onchange')
	reference = fields.Char ("Bank reference",track_visibility='onchange')
	state = fields.Selection(selection=[("draft", "Draft"), ("confirmed", "Confirmed"), ("done", "Done"), ("cancel", "Cancel")], default="draft",track_visibility='onchange')


	@api.onchange('debit_id')
	def _onchange_debit_id(self):
		if self.debit_id.id:
			if self.debit_id.currency_id.id:
				self.origin_currency_id = self.debit_id.currency_id.id
			else:
				self.origin_currency_id = self.env.company.currency_id.id
	
	@api.onchange('credit_id')
	def _onchange_credit_id(self):
		if self.credit_id.id:
			if self.credit_id.currency_id.id:
				self.final_currency_id = self.credit_id.currency_id.id
			else:
				self.final_currency_id = self.env.company.currency_id.id
	
	@api.constrains('state')
	def _compute_name(self):
		if self.name == '/' and self.state == 'confirmed':
			self.name = self.env['ir.sequence'].next_by_code('account.exchange.seq')


	@api.onchange('request')
	def _onchange_rate(self):
		rate = self.env['res.currency.rate'].search([('name','=', self.request)], limit=1).sell_rate
		if not rate:
			return {'warning': {'message':'No existe una tasa para esta fecha'}}
	
	
	@api.onchange('origin_currency_id','origin_currency_id','amount','rate')
	def calculate(self):
		if(self.origin_currency_id.name == 'USD' or self.origin_currency_id.name == 'EUR'):
			self.final_amount = self.amount * self.rate
		
		elif (self.origin_currency_id.name in ('Bs.', 'Bs', 'bs', 'bs.', 'BS', 'BS.')):
			if self.rate > 0: 
				self.final_amount = self.amount / self.rate
	
	def draft(self):
		self.state = "draft"
		if self.move_id.id:
			self.move_id.button_draft()
			self.move_id.unlink()
		if self.move_transient_id.id:
			self.move_transient_id.button_draft()
			self.move_transient_id.unlink()

	
	def confirmed(self):
		move_vals = {
				'date': self.request,
				#'ref': payment.communication,
				'journal_id': self.credit_id.id,
				'currency_id': self.credit_id.currency_id.id if  self.credit_id.currency_id.id else  self.company_id.currency_id.id ,
				'partner_id': self.company_id.partner_id.id,
				'custom_rate': True,
				'os_currency_rate': self.rate,
				'line_ids': [
					(0, 0, {
						'name': self.reference,
						'amount_currency': self.final_amount * -1 if self.credit_id.currency_id.id else 0,
						'currency_id': self.credit_id.currency_id.id if self.credit_id.currency_id.id else 0,
						'debit':  0,
						'credit': self.amount ,
						'partner_id': self.company_id.partner_id.id,
						'account_id': self.credit_id.default_debit_account_id.id,
					}),
					(0, 0, {
						'name': self.reference,
						'amount_currency': self.final_amount * 1 if self.credit_id.currency_id.id else 0,
						'currency_id': self.credit_id.currency_id.id if self.credit_id.currency_id.id else 0,
						'debit': self.amount ,
						'credit': 0 ,
						'partner_id': self.company_id.partner_id.id,
						'account_id': self.account_id.id,
					}),
					
				],
			}
		self.move_transient_id = self.env['account.move'].create(move_vals)
		self.move_transient_id.action_post()
		self.state = "confirmed"

	def done(self):
		#self.confirmation = fields.Datetime.now()
		move_vals = {
				'date': self.confirmation,
				#'ref': payment.communication,
				'journal_id': self.debit_id.id,
				'currency_id': self.debit_id.currency_id.id if self.debit_id.currency_id.id else self.company_id.currency_id.id,
				'partner_id': self.company_id.partner_id.id,
				'custom_rate': True,
				'os_currency_rate': self.rate,
				'line_ids': [
					
					(0, 0, {
						'name': self.reference,
						'amount_currency': self.final_amount * -1 if self.debit_id.currency_id.id else 0 ,
						'currency_id': self.debit_id.currency_id.id  if self.debit_id.currency_id.id else 0 ,
						'debit':  0,
						'credit': self.amount ,
						'partner_id': self.company_id.partner_id.id,
						'account_id': self.account_id.id,
					}),
					(0, 0, {
						'name': self.reference,
						'amount_currency': self.final_amount * 1 if self.debit_id.currency_id.id else 0 ,
						'currency_id': self.debit_id.currency_id.id  if self.debit_id.currency_id.id else 0 ,
						'debit': self.amount ,
						'credit': 0 ,
						'partner_id': self.company_id.partner_id.id,
						'account_id': self.credit_id.default_debit_account_id.id,
					}),
				],
			}
		self.move_id = self.env['account.move'].create(move_vals)
		self.move_id.action_post()
		self.state = "done"

	def cancel(self):
		self.state = "cancel"