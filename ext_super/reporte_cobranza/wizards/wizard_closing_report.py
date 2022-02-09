from datetime import datetime, timedelta
from operator import mod
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
import logging

import io
from io import BytesIO

import xlsxwriter
import shutil
import base64
import json
import csv
import xlwt

_logger = logging.getLogger(__name__)

class ClosingSalesJournal(models.Model):
    _name = 'closing.sales.journal'

    journal_id = fields.Many2one(comodel_name='account.journal', string='Diario')
    amount  = fields.Float(string='Monto')
    amount_dollar  = fields.Float(string='Monto $')
    report_id = fields.Many2one(comodel_name='closing.sales.report', string='Totales')

class ClosingSales(models.Model):
    _name = 'closing.sales'

    name = fields.Date(string='Fecha de Registro')
    last_update = fields.Date(string='Fecha Efectiva')
    invoice_num = fields.Char(string='Número de Factura')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    currency_rate = fields.Float(string='Tasa')
    efectivo_bs = fields.Float(string='Efectivo Bs')
    efectivo_dollar = fields.Float(string='Efectivo $')
    banco_bs = fields.Float(string='Banco Bs')
    banco_dollar = fields.Float(string='Banco $')
    asiento_dollar = fields.Float(string='Asiento $')
    asiento_bs = fields.Float(string='Asiento Bs')

    journal_id = fields.Many2one(comodel_name='account.journal', string='Diario')
    amount = fields.Float(string='Monto')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda')

class ClosingSalesReport(models.Model):
    _name = 'closing.sales.report'

    date_from = fields.Date(string='Desde', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Hasta', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())

    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=60)
    company_id = fields.Many2one('res.company','Compañía',default=lambda self: self.env.company.id)
    total_ids = fields.One2many('closing.sales.journal', 'report_id', string='Reporte')
    partner_ids = fields.Many2many('res.partner', string='Vendedores')
    journal_ids = fields.Many2many('account.journal', string='Diarios')
    user_ids = fields.Many2many('res.users', string='Usuario')

    # *******************  FORMATOS ****************************

    def float_format(self,valor):
        if valor:
            result = '{:,.2f}'.format(valor)
            result = result.replace(',','*')
            result = result.replace('.',',')
            result = result.replace('*','.')
        else:
            result="0,00"
        return result

    def print_report(self):
        self.env['closing.sales'].search([]).unlink()
        self.get_invoice()
        return {
            'type': 'ir.actions.report',
            'report_name': 'reporte_cobranza.closing_report',
            'report_type':"qweb-pdf"
            }

    def get_journals(self):
        xfind = self.env['account.journal'].search([
                ('closing_report', '=', True),
            ])
        return xfind

    def get_invoice(self):
        buscar = [
            ('fecha_efectiva', '>=', self.date_from),
            ('fecha_efectiva', '<=', self.date_to),
            #('type', 'in', ('out_invoice', 'out_receipt', 'out_refund')),
            #('type', '=', 'out_invoice'),
            ('invoice_payment_state', '=', 'paid'),
            ('company_id','=',self.env.company.id),
            ('payment_condition_id', '!=', 'Contado')
        ]
        if len(self.partner_ids) > 0:
            buscar.append(('seller_id','in',self.partner_ids.ids))
        if len(self.journal_ids) > 0:
            buscar.append(('journal_id','in',self.journal_ids.ids))
        else :
            buscar.append(('type', '=', 'out_invoice'))
        if len(self.user_ids) >0:
            buscar.append(('create_uid','in',self.user_ids.ids))

        xfind = self.env['account.move'].search(buscar)
        journal_id_temp = self.env['closing.sales.journal'].search([
                            ('report_id','=',self.id)
                            ])
        journal_id_temp.unlink()
        for item in xfind:
            # Tasa y montos en bs/$
            rate = 1
            efectivo_bs = 0
            efectivo_dollar = 0
            banco_bs = 0
            banco_dollar = 0
            asiento_dollar = 0
            asiento_bs = 0
            

            if item.custom_rate:
                rate = item.os_currency_rate
            else:
                rates = item.env['res.currency.rate'].search([
                    ('name', '<=', item.invoice_date)
                ], limit=1).sell_rate
                if rates > 0:
                    rate = rates
            
            if item.invoice_payments_widget :
                parse_dict = json.loads(item.invoice_payments_widget)
                if parse_dict:
                    for pay in parse_dict.get('content'):
                        move_id = self.env['account.move'].search([('id', '=', pay['move_id'])])
                        journal_id = self.env['closing.sales.journal'].search([
                            ('journal_id', '=', move_id.journal_id.id),
                            ('report_id','=',self.id)
                            ])
                        if len(journal_id) == 0 :
                             journal_id = self.env['closing.sales.journal'].create({
                                 'journal_id':move_id.journal_id.id,
                                 'report_id':self.id
                             })

                        if move_id.journal_id.type == 'cash':

                            if move_id.journal_id.currency_id.id == False and item.currency_id.id != item.company_id.currency_id.id:
                                efectivo_bs = pay['amount'] * move_id.os_currency_rate
                                journal_id.amount += efectivo_bs
                                journal_id.amount_dollar += pay['amount'] 
                            
                            elif move_id.journal_id.currency_id.id  and item.currency_id.id != item.company_id.currency_id.id:
                                efectivo_dollar = pay['amount']
                                journal_id.amount += efectivo_dollar * move_id.os_currency_rate
                                journal_id.amount_dollar += efectivo_dollar 
                            
                            elif move_id.journal_id.currency_id.id == False  and item.currency_id.id == item.company_id.currency_id.id:
                                efectivo_bs = pay['amount']
                                journal_id.amount += efectivo_bs
                                journal_id.amount_dollar += efectivo_dollar / move_id.os_currency_rate

                        elif move_id.journal_id.type == 'bank':
                            if move_id.journal_id.currency_id.id == False and item.currency_id.id != item.company_id.currency_id.id:
                                banco_bs = pay['amount'] * move_id.os_currency_rate
                                journal_id.amount += banco_bs
                                journal_id.amount_dollar += pay['amount']
                            
                            elif move_id.journal_id.currency_id.id  and item.currency_id.id != item.company_id.currency_id.id:
                                banco_dollar = pay['amount']
                                journal_id.amount += banco_dollar 
                                journal_id.amount_dollar += pay['amount']  / move_id.os_currency_rate

                            elif move_id.journal_id.currency_id.id == False  and item.currency_id.id == item.company_id.currency_id.id:
                                banco_bs = pay['amount']
                                journal_id.amount += banco_bs
                                journal_id.amount_dollar += pay['amount']  / move_id.os_currency_rate
                            else :
                               # banco_dollar = pay['amount'] / move_id.os_currency_rate
                                journal_id.amount += pay['amount']
                                journal_id.amount_dollar += pay['amount']  / move_id.os_currency_rate
                        else:
                            if move_id.journal_id.currency_id.id == False and item.currency_id.id != item.company_id.currency_id.id:
                                asiento_bs = pay['amount'] / move_id.os_currency_rate
                                journal_id.amount += asiento_bs
                                journal_id.amount_dollar += pay['amount'] 
                            
                            elif move_id.journal_id.currency_id.id  and item.currency_id.id != item.company_id.currency_id.id:
                                asiento_dollar = pay['amount']
                                journal_id.amount += asiento_dollar * move_id.os_currency_rate
                                journal_id.amount_dollar += pay['amount']
                            
                            elif move_id.journal_id.currency_id.id == False  and item.currency_id.id == item.company_id.currency_id.id:
                                asiento_bs = pay['amount'] 
                                journal_id.amount += asiento_bs
                                journal_id.amount_dollar += pay['amount'] * move_id.os_currency_rate
                            else :
                                asiento_dollar = pay['amount'] / move_id.os_currency_rate
                                journal_id.amount += pay['amount']
                                journal_id.amount_dollar += pay['amount'] / move_id.os_currency_rate

          
            #Valores finales para crear
            values = {
                'name': item.invoice_date,
                'last_update': item.fecha_efectiva,
                'invoice_num': item.invoice_number_cli,
                'partner_id': item.partner_id.id,
                'currency_rate': rate,
                'efectivo_bs':efectivo_bs,
                'efectivo_dollar':efectivo_dollar,
                'banco_bs': banco_bs,
                'banco_dollar':banco_dollar,
                'asiento_bs': asiento_bs,
                'asiento_dollar':asiento_dollar,
                'journal_id': item.journal_id.id,
                'amount': item.amount_total,
                'currency_id': item.currency_id.id,
            }
            self.env['closing.sales'].create(values)

    def get_lines(self):
        xfind = self.env['closing.sales'].search([])
        return xfind

    def show_closing_records(self):
        self.env['closing.sales'].search([]).unlink()
        self.get_invoice()
        self.ensure_one()
        res = self.env.ref('reporte_cobranza.closing_sales_action').read()[0]
        return res

    # *******************  REPORTE EN EXCEL ****************************

    def generate_xls_report(self):
        self.env['closing.sales'].search([]).unlink()
        self.get_invoice()

        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet(_('Reporte de Cierre de Cobranza'))
        fp = BytesIO()

        header_tittle_style = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170; align: horiz center, vert centre;")
        header_content_style = xlwt.easyxf("font: name Helvetica size 16 px, bold 1, height 170; align: horiz center, vert centre; pattern:pattern solid, fore_colour silver_ega;")
        lines_style_center = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: bottom thin; align: horiz center, vert centre;")
        lines_style_right = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: bottom thin; align: horiz right, vert centre;")
        
        row = 0
        col = 0
        ws1.row(row).height = 500
        ws1.write_merge(row,row, 3, 5, _("Reporte de Cierre de Cobranza"), header_tittle_style)
        xdate = self.date_now.strftime('%d/%m/%Y %I:%M:%S %p')
        xdate = datetime.strptime(xdate,'%d/%m/%Y %I:%M:%S %p') - timedelta(hours=4)
        ws1.write_merge(row,row, 6, 8, xdate.strftime('%d/%m/%Y %I:%M:%S %p'), header_tittle_style)
        row += 2

        #CABECERA DE LA TABLA 
        ws1.write(row,col+0, _("Fecha"),header_content_style)
        ws1.col(col+0).width = int((len('xx/xx/xxxx')+2)*256)
        ws1.write(row,col+1, _("Número de Factura"),header_content_style)
        ws1.col(col+1).width = int((len('Número de Factura')+5)*256)
        ws1.write(row,col+2, _("Cliente"),header_content_style)
        ws1.col(col+2).width = int((len('Cliente')+40)*256)
        ws1.write(row,col+3, _("Tasa"),header_content_style)
        ws1.col(col+3).width = int(len('xxx.xxx.xxx,xx')*256)
        col_auto = 3
        for item in self.get_journals():
            col_auto += 1
            ws1.write(row,col_auto, item.name,header_content_style)

        #####
        total_final_bs = 0

        for item in self.get_lines():
            row += 1
            # Date
            if item.name:
                ws1.write(row,col+0, item.name.strftime('%d/%m/%Y'),lines_style_center)
            else:
                ws1.write(row,col+0, '',lines_style_center)
            # Invoice Number
            if item.invoice_num:
                ws1.write(row,col+1, item.invoice_num,lines_style_center)
            else:
                ws1.write(row,col+1, '',lines_style_center)
            # Customer
            if item.partner_id.name:
                ws1.write(row,col+2, item.partner_id.name,lines_style_center)
            else:
                ws1.write(row,col+2, item.name,lines_style_center)
            # Rate
            if item.currency_rate:
                ws1.write(row,col+3, self.float_format(item.currency_rate),lines_style_right)
            else:
                ws1.write(row,col+3, '',lines_style_right)

            col_auto = 3
            for line in self.get_journals():
                col_auto += 1
                if item.journal_id.id == line.id:
                    ws1.write(row,col_auto, self.float_format(item.amount),lines_style_right)
                    ws1.col(col_auto).width = int(len('xxx.xxx.xxx,xx')*256)
                else:
                    ws1.write(row,col_auto, self.float_format(0.00),lines_style_right)
                    ws1.col(col_auto).width = int(len('xxx.xxx.xxx,xx')*256)
            
                
        row += 1
        col_auto = 3
        for line in self.get_journals():
            total_amount = 0
            col_auto += 1
            for item in self.get_lines():
                if item.journal_id.id == line.id:
                    total_amount += item.amount
            ws1.write(row,col_auto, total_amount,lines_style_right)

        row += 2
        ws1.write(row,col+3, '',lines_style_center)
        ws1.write(row,col+4, _('Monto $'),lines_style_center)
        ws1.write(row,col+5, _('Monto Bs.'),lines_style_center)
        for line in self.get_journals():
            total_bs = 0
            total_usd = 0
            for item in self.get_lines():
                if item.journal_id.id == line.id:
                    total_bs += item.total_bs
                    total_usd += item.total_usd
                    total_final_bs += item.total_bs
            row += 1
            ws1.write(row,col+3, line.name,lines_style_center)
            ws1.write(row,col+4, self.float_format(total_usd),lines_style_right)
            ws1.write(row,col+5, self.float_format(total_bs),lines_style_right)
        row += 1
        ws1.write_merge(row,row,col+3,col+4, _('Total Bs.'),lines_style_center)
        ws1.write(row,col+5, self.float_format(total_final_bs),lines_style_right)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name': _('Reporte de Cierre de Cobranza ')+ fecha +'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'closing.sales.report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }