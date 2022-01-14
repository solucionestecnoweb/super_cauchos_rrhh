import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models, _
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning
import time

class AccountMove(models.Model):
    _inherit ='account.move'

    base_efectiva   = fields.Float(string='Base Efectiva', digits=(12, 4))
    fecha_efectiva  = fields.Date(string='Fecha Cierre')
    dias_efectivo   = fields.Integer(string='Dias de cobranza')

    @api.constrains('invoice_payment_state')
    def _constrains_invoice_payments_widget(self):
        for item in self:
            if item.invoice_payment_state == "paid":
                item.cal_comission()
            else :
                item.base_efectiva = 0
                item.fecha_efectiva = item.date

    def calcular_comision(self):
        buscar = [
            ('type', '=', 'out_invoice'),
            ('invoice_payment_state', '=', 'paid'),
            ('company_id','=',self.env.company.id)
        ]
        xfind = self.env['account.move'].search(buscar)
        for item in xfind: 
            item.cal_comission()

    def cal_comission(self):
        self.base_efectiva = self.amount_untaxed
        if self.invoice_payments_widget :
            parse_dict = json.loads(self.invoice_payments_widget)
            if parse_dict:
                self.fecha_efectiva = parse_dict['content'][0]['date']
                for pay in parse_dict.get('content'):
                    move_id = self.env['account.move'].search([('id', '=', pay['move_id'])])
                    d = datetime.strptime(pay['date'],'%Y-%m-%d').date()
                    if self.fecha_efectiva  < d :
                        self.fecha_efectiva = pay['date']
                    if move_id.type == "out_refund":
                        # if move_id.company_id.currency_id == move_id.currency_id:
                        #     self.base_efectiva -= move_id.amount_untaxed
                        # else :
                        #     self.base_efectiva =  self.env['account.move.line'].search([('id', '=', self.id),('account_id.internal_type','=','payable')]).amount_currency

                        self.base_efectiva -= move_id.amount_untaxed
            if self.fecha_efectiva and self.invoice_date:
                delta =self.fecha_efectiva -  self.invoice_date
                self.dias_efectivo = int(delta.days)