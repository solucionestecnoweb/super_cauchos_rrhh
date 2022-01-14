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

class AccountMoveExtend(models.Model):
	_inherit = "account.move"

	seller_id = fields.Many2one(comodel_name='res.partner', string='Seller')
	payment_condition_id = fields.Many2one(comodel_name='account.condition.payment', string='Payment Condition')
	paperformat = fields.Selection(string='Invoice Format', selection=[('letter', 'Letter'), ('half', 'Half Letter')], related='company_id.paperformat')
	reason = fields.Char(string='Razón de Nota')

	@api.onchange('partner_id')
	def _onchange_partner_id(self):
		xfind = self.env['account.payment'].search([
			('partner_id', '=', self.partner_id.id),
			('anticipo', '=', True),
			('state', '=', 'posted')
		])
		if len(xfind) > 0:
			return {'warning': {'message':'El cliente posee un anticipo disponible'}}
	
	def get_currency_rate(self):
		xfind = self.env['res.currency.rate'].search([
			('name', '<=', self.invoice_date)
		], limit=1).sell_rate
		if xfind:
			return xfind
		else:
			return 1

	def invoice_letter_bs(self):
		return {'type': 'ir.actions.report','report_name': 'account_move_extend_fields_reports.account_move_invoice_extend_multirepuestos_bs','report_type':"qweb-pdf"}
	
	def invoice_half_bs(self):
		return {'type': 'ir.actions.report','report_name': 'account_move_extend_fields_reports.account_move_invoice_extend_supercauchos_bs','report_type':"qweb-pdf"}

	def invoice_letter_usd(self):
		return {'type': 'ir.actions.report','report_name': 'account_move_extend_fields_reports.account_move_invoice_extend_multirepuestos_usd','report_type':"qweb-pdf"}

	def invoice_half_usd(self):
		return {'type': 'ir.actions.report','report_name': 'account_move_extend_fields_reports.account_move_invoice_extend_supercauchos_usd','report_type':"qweb-pdf"}

	def validate_seq(self, seq):
		new_seq = ''
		for item in seq:
			if item.isdigit():
				new_seq += item
		
		return new_seq

	def vencimiento_real(self, dias, fecha):
		new_date = fecha + timedelta(days=dias)
		return new_date

class AccountConditionPayment(models.Model):
	_name = 'account.condition.payment'
	_inherit = ['mail.thread', 'mail.activity.mixin']

	name = fields.Char(string='Name')

class AccountPaymentExtend(models.Model):
	_inherit = "account.payment"

	seller_id = fields.Many2one(comodel_name='res.partner', string='Seller')
	payment_concept = fields.Char(string='Payment Concept')
	payment_notes = fields.Text(string='Notes')

	def current_date_format(self,date):
		months = ("Enero", "Febrero", "Marzo", "Abri", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")
		day = date.day
		month = months[date.month - 1]
		year = date.year
		messsage = "{} de {} del {}".format(day, month, year)
		return messsage

	def get_debt_amount(self, partner):
		debt = 0
		xfind = self.env['account.move'].search([
			('partner_id', '=', partner),
			('invoice_payment_state', '=', 'not_paid'),
			('state', '=', 'posted'),
		])
		for item in xfind:
			debt += item.amount_residual_signed
		return debt

	def get_advance_amount(self, partner):
		advance = 0
		xfind = self.env['account.payment'].search([
			('partner_id', '=', partner),
			('anticipo', '=', True),
			('state', '=', 'posted'),
		])
		for item in xfind:
			advance += item.amount
		return advance

	def get_literal_amount(self,amount):
		indicador = [("",""),("MIL","MIL"),("MILLON","MILLONES"),("MIL","MIL"),("BILLON","BILLONES")]
		entero = int(amount)
		decimal = int(round((amount - entero)*100))
		contador = 0
		numero_letras = ""
		while entero >0:
			a = entero % 1000
			if contador == 0:
				en_letras = self.convierte_cifra(a,1).strip()
			else:
				en_letras = self.convierte_cifra(a,0).strip()
			if a==0:
				numero_letras = en_letras+" "+numero_letras
			elif a==1:
				if contador in (1,3):
					numero_letras = indicador[contador][0]+" "+numero_letras
				else:
					numero_letras = en_letras+" "+indicador[contador][0]+" "+numero_letras
			else:
				numero_letras = en_letras+" "+indicador[contador][1]+" "+numero_letras
			numero_letras = numero_letras.strip()
			contador = contador + 1
			entero = int(entero / 1000)
		numero_letras = numero_letras+" con " + str(decimal) +"/100"
		print('numero: ',amount)
		print(numero_letras)
		return numero_letras
		
	def convierte_cifra(self, numero, sw):
		lista_centana = ["",("CIEN","CIENTO"),"DOSCIENTOS","TRESCIENTOS","CUATROCIENTOS","QUINIENTOS","SEISCIENTOS","SETECIENTOS","OCHOCIENTOS","NOVECIENTOS"]
		lista_decena = 	["",("DIEZ","ONCE","DOCE","TRECE","CATORCE","QUINCE","DIECISEIS","DIECISIETE","DIECIOCHO","DIECINUEVE"),
						("VEINTE","VEINTI"),("TREINTA","TREINTA Y "),("CUARENTA" , "CUARENTA Y "),
						("CINCUENTA" , "CINCUENTA Y "),("SESENTA" , "SESENTA Y "),
						("SETENTA" , "SETENTA Y "),("OCHENTA" , "OCHENTA Y "),
						("NOVENTA" , "NOVENTA Y ")
						]
		lista_unidad = ["",("UN" , "UNO"),"DOS","TRES","CUATRO","CINCO","SEIS","SIETE","OCHO","NUEVE"]
		centena = int (numero / 100)
		decena = int((numero -(centena * 100))/10)
		unidad = int(numero - (centena * 100 + decena * 10))
		
		texto_centena = ""
		texto_decena = ""
		texto_unidad = ""
		
		#Validad las centenas
		texto_centena = lista_centana[centena]
		if centena == 1:
			if (decena + unidad)!=0:
				texto_centena = texto_centena[1]
			else:
				texto_centena = texto_centena[0]
		
		#Valida las decenas
		texto_decena = lista_decena[decena]
		if decena == 1:
			texto_decena = texto_decena[unidad]
		elif decena > 1:
			if unidad != 0:
				texto_decena = texto_decena[1]
			else:
				texto_decena = texto_decena[0]
		
		#Validar las unidades
		if decena != 1:
			texto_unidad = lista_unidad[unidad]
			if unidad == 1:
				texto_unidad = texto_unidad[sw]
		
		return "%s %s %s" %(texto_centena,texto_decena,texto_unidad)