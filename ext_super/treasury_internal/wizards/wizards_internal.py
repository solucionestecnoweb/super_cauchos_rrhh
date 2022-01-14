from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
import logging

import io
from io import BytesIO

import xlsxwriter
import shutil
import base64
import csv
import xlwt

_logger = logging.getLogger(__name__)

class Internal(models.Model):
    _name ='internal.transfers'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', default='Nuevo', copy=False)


    out_company_id = fields.Many2one('res.company', string='Compañía que envía' ,track_visibility='onchange')
    out_journal_id = fields.Many2one('account.journal',track_visibility='onchange')
    out_payment_type = fields.Selection([('outbound', 'Enviar Dinero'), ('inbound', 'Recibir Dinero'), ('transfer', 'Transferencia Interna')], default='outbound', string='Tipo de Pago')
    out_payment_method_id = fields.Many2one('account.payment.method', string='Método de Pago')
    out_destination_account_id  = fields.Many2one('account.account',string='Cuenta Transitoria',track_visibility='onchange')

    in_company_id = fields.Many2one('res.company', string='Recieving Company',track_visibility='onchange')
    in_journal_id = fields.Many2one('account.journal',track_visibility='onchange')
    in_payment_type = fields.Selection([('outbound', 'Enviar Dinero'), ('inbound', 'Recibir Dinero'), ('transfer', 'Transferencia Interna')], default='inbound', string='Tipo de Pago')
    in_payment_method_id = fields.Many2one('account.payment.method', string='Método de Pago')
    in_destination_account_id  = fields.Many2one('account.account',string='Cuenta Transitoria',track_visibility='onchange')

    amount = fields.Monetary(string='Monto',track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', string='Currency',track_visibility='onchange')
    rate = fields.Float(string="Tipo de Cambio ",track_visibility='onchange')

    out_payment_date = fields.Date(string='Fecha de Envío', default=fields.Date.context_today,track_visibility='onchange')
    in_payment_date = fields.Date(string='Fecha de Recibo',track_visibility='onchange')
    communication = fields.Char(string='Memo')
    payment_concept = fields.Char(string='Concepto de Pago')

    move_transient_id  = fields.Many2one('account.move',"Asiento Origen",track_visibility='onchange')
    move_transient_line_id =  fields.Many2one('account.move.line',compute='_compute_move_transient_line_id', string='Lineas')
    
    def _compute_move_transient_line_id(self):
        line = self.env['account.move.line']
        lines = self.env['account.move.line'].search([
            ('move_id','=', self.move_transient_id.id)
        ])
        if len(lines) > 0 :
            line = lines
        return line

    move_id   = fields.Many2one('account.move',"Asiento Destino")

    move_line_id =  fields.Many2one('account.move.line',compute='_compute_move_line_id', string='Lineas')
    
    def _compute_move_line_id(self):
        line = self.env['account.move.line']
        line = self.env['account.move.line'].search([
            ('move_id','=', self.move_id.id)
        ])
        return line

    
    partner_type = fields.Selection([('customer', 'Cliente'), ('supplier', 'Proveedor')], default='supplier')

    state = fields.Selection(selection=[("draft", "Borrador"), ("confirmed", "Confirmado"), ("done", "Terminado"), ("cancel", "Cancel")], default="draft")
    
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)


    @api.constrains('state')
    def _compute_name(self):
        if self.name == 'Nuevo':
            self.name = self.env['ir.sequence'].next_by_code('internal.transfers.seq')


    def validate(self):
        move_vals = {
                'date': self.out_payment_date,
                'journal_id': self.out_journal_id.id,
                'currency_id': self.currency_id.id if  self.currency_id.id else  self.out_company_id.currency_id.id ,
                'partner_id': self.out_company_id.partner_id.id,
                'custom_rate': True,
                'ref': self.payment_concept,
                'os_currency_rate': self.rate,
                'line_ids': [
                    (0, 0, {
                        'name': self.payment_concept,
                        'amount_currency': self.amount * -1 if self.currency_id.id else 0 ,
                        'currency_id': self.currency_id.id  if self.currency_id.id  else 0 ,
                        'debit':  0,
                        'credit': self.amount * self.rate  if  self.currency_id.id else self.amount,
                        'partner_id': self.out_company_id.partner_id.id,
                        'account_id': self.out_journal_id.default_debit_account_id.id,
                    }),
                    (0, 0, {
                        'name': self.payment_concept,
                        'amount_currency': self.amount * 1   if self.currency_id.id  else 0 ,
                        'currency_id': self.currency_id.id  if  self.currency_id.id  else 0 ,
                        'debit': self.amount * self.rate  if  self.currency_id.id else self.amount,
                        'credit': 0 ,
                        'partner_id': self.out_company_id.partner_id.id,
                        'account_id': self.out_destination_account_id.id,
                    }),
                    
                ],
            }
        print(move_vals)
        self.move_transient_id = self.env['account.move'].create(move_vals)
        self.state = "confirmed"
    
    def terminar(self):
        move_vals_v2 = {
                'date': self.in_payment_date,
                'journal_id': self.in_journal_id.id,
                'currency_id': self.currency_id.id if  self.currency_id.id else  self.in_company_id.currency_id.id ,
                'partner_id': self.in_company_id.partner_id.id,
                'custom_rate': True,
                'ref': self.payment_concept,
                'os_currency_rate': self.rate,
                'line_ids': [
                    (0, 0, {
                        'name': self.payment_concept,
                        'amount_currency': self.amount * 1   if self.currency_id.id   else 0 ,
                        'currency_id': self.currency_id.id    if  self.currency_id.id  else 0 ,
                        'debit': self.amount * self.rate  if  self.currency_id.id else self.amount ,
                        'credit': 0 ,
                        'partner_id': self.in_company_id.partner_id.id,
                        'account_id': self.in_destination_account_id.id,
                    }),
                    (0, 0, {
                        'name': self.payment_concept,
                        'amount_currency': self.amount * -1  if self.currency_id.id  else 0 ,
                        'currency_id': self.currency_id.id  if self.currency_id.id  else 0 ,
                        'debit':  0,
                        'credit': self.amount * self.rate  if  self.currency_id.id else self.amount ,
                        'partner_id': self.in_company_id.partner_id.id,
                        'account_id': self.in_journal_id.default_debit_account_id.id,
                    }),
                    
                    
                ],
            }
        self.move_id = self.env['account.move'].create(move_vals_v2)
        self.move_transient_id.action_post()
        self.move_id.action_post()
        self.state = "done"


    def cancel(self):
        self.move_transient_id.unlink()
        self.state = 'cancel'

#     def validate(self):
#         out_values = {
#             'partner_type': self.partner_type,
#             'payment_type': self.out_payment_type,
#             'company_id': self.out_company_id.id,
#             'partner_id': self.in_company_id.id,
#             'amount': self.amount,
#             'currency_id': self.currency_id.id,
#             'payment_date': self.out_payment_date,
#             'communication': self.communication,
#             'journal_id': self.out_journal_id.id,
#             'payment_method_id': self.out_payment_method_id.id,
#         }

#         out_payment = self.env['account.payment'].create(out_values)

#         in_values = {
#             'partner_type': self.partner_type,
#             'payment_type': self.in_payment_type,
#             'company_id': self.in_company_id.id,
#             'partner_id': self.out_company_id.id,
#             'amount': self.amount,
#             'currency_id': self.currency_id.id,
#             'payment_date': self.in_payment_date,
#             'communication': self.communication,
#             'journal_id': self.in_journal_id.id,
#             'payment_method_id': self.in_payment_method_id.id,
#             'seller_id': self.out_company_id.id,
#             'payment_concept': self.payment_concept,
#         }
#         in_payment = self.env['account.payment'].create(in_values)

#         out_payment.partner_id = self.in_company_id.partner_id.id
# #        out_payment.destination_account_id = self.out_destination_account_id.id
# #        in_payment.destination_account_id = self.in_destination_account_id.id

#         out_payment.post()
#         in_payment.post()

#         action = self.env.ref('account.action_account_payments').read()[0]
#         action['domain'] = [('id', 'in', [out_payment.id, in_payment.id])]
#         action['context'] = {}
#         return action

