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
import csv
import xlwt

_logger = logging.getLogger(__name__)

class ClosingReport(models.TransientModel):
    _name = "closing.report"

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())

    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=50)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.user.company_id.id)
    currency_bs_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id)
    currency_usd_id = fields.Many2one('res.currency', default= lambda self: self.env['res.currency'].search([('id', '=', 2)]))

    def print_report(self):
        return {
            'type': 'ir.actions.report',
            'report_name': 'closing_report.closing_report',
            'report_type':"qweb-pdf"
            }

    def get_lines(self):
        xfind = self.env['account.payment'].search([('partner_type', '=', 'customer'), ('payment_date', '>=', self.date_from), ('payment_date', '<=', self.date_to), ('state', '=', 'posted')])
        return xfind

    # *******************  REPORTE EN EXCEL ****************************

    def generate_xls_report(self):

        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet(_('Collections Closing Report'))
        fp = BytesIO()

        header_content_style = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170; align: horiz center;")
        sub_header_style = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170")
        sub_header_style_c = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz center")
        sub_header_style_m = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz right")
        sub_header_style_r = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: bottom thin; align: horiz right")
        sub_header_style_s = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: bottom thin; align: horiz left")
        sub_header_content_style = xlwt.easyxf("font: name Helvetica size 10 px, height 170;")
        line_content_style = xlwt.easyxf("font: name Helvetica, height 170;")

        row = 0
        col = 0
        ws1.row(row).height = 500
        ws1.write_merge(row,row, 4, 5, _("Collections Closing Report"), header_content_style)
        xdate = self.date_now.strftime('%d/%m/%Y %I:%M:%S %p')
        xdate = datetime.strptime(xdate,'%d/%m/%Y %I:%M:%S %p') - timedelta(hours=4)
        xname = self.company_id.name
        xvat = self.company_id.vat
        ws1.write_merge(row,row, 0, 1, xname, header_content_style)
        ws1.write_merge(row,row, 2, 3, xvat, header_content_style)
        ws1.write_merge(row,row, 7, 8, xdate.strftime('%d/%m/%Y %I:%M:%S %p'), header_content_style)
        row += 2

        #CABECERA DE LA TABLA 
        ws1.col(col).width = 250
        ws1.write(row,col+0, _("Date"),sub_header_style_c)
        ws1.col(col+0).width = int((len('xx/xx/xxxx')+10)*256)
        ws1.write(row,col+1, _("Bill"),sub_header_style_c)
        ws1.col(col+1).width = int((len('Bill')+20)*256)
        ws1.write(row,col+2, _("Customer"),sub_header_style_c)
        ws1.col(col+2).width = int((len('Customer')+26)*256)
        ws1.write(row,col+3, _("Detail"),sub_header_style_c)
        ws1.col(col+3).width = int((len('Detail')+26)*256)        
        ws1.write(row,col+4, _("Rate"),sub_header_style_c)
        ws1.col(col+4).width = int((len('Rate')+15)*256)
        ws1.write(row,col+5, _("Payment in Bs"),sub_header_style_c)
        ws1.col(col+5).width = int((len('Payment in Bs')+10)*256)
        ws1.write(row,col+6, _("Payment in Bs ME"),sub_header_style_c)
        ws1.col(col+6).width = int((len('Payment in Bs ME')+10)*256)
        ws1.write(row,col+7, _("Payment in Cash $"),sub_header_style_c)
        ws1.col(col+7).width = int((len('Payment in Cash $')+10)*256)
        ws1.write(row,col+8, _("Payment in Transfer $"),sub_header_style_c)
        ws1.col(col+8).width = int((len('Payment in Transfer $')+10)*256)

        center = xlwt.easyxf("align: horiz center")
        right = xlwt.easyxf("align: horiz right")

        #Totales
        total_bs = 0
        total_bs_me = 0
        total_cash_usd = 0
        total_transfer_usd = 0

        for item in self.get_lines():
            row += 1
            # Date
            if item.payment_date:
                ws1.write(row,col+0, item.payment_date.strftime('%d/%m/%Y'),center)
            else:
                ws1.write(row,col+0, '',center)
            # Bill
            if item.name:
                ws1.write(row,col+1, item.name,center)
            else:
                ws1.write(row,col+1, '',center)
            # Customer
            if item.partner_id:
                ws1.write(row,col+2, item.partner_id.name,center)
            else:
                ws1.write(row,col+2, '',center)
            # Detail
            if item.payment_concept:
                ws1.write(row,col+3, item.payment_concept,center)
            else:
                ws1.write(row,col+3, '',center)
            # Rate
            if item.rate:
                ws1.write(row,col+4, item.rate,right)
            else:
                ws1.write(row,col+4, '',right)
            # Payment in Bs
            if item.amount_bs:
                ws1.write(row,col+5, item.amount_bs,right)
            else:
                ws1.write(row,col+5, '0,00',right)
            # Payment in Bs ME
            if item.amount_currency:
                ws1.write(row,col+6, item.amount_currency,right)
            else:
                ws1.write(row,col+6, '0,00',right)
            # Payment in Cash $
            if item.amount_currency:
                ws1.write(row,col+7, item.amount_currency_cash,right)
            else:
                ws1.write(row,col+7, '0,00',right)
            # Payment in Bs ME
            if item.amount_currency:
                ws1.write(row,col+8, item.amount_currency_transfer,right)
            else:
                ws1.write(row,col+8, '0,00',right)
            
            for obj in item:
                row += 1
                ws1.write_merge(row,row, 0, 1, (""), sub_header_style_r)
                # Bank
                if item.partner_id:
                    ws1.write(row,col+2, (item.journal_id.default_credit_account_id.code, item.journal_id.default_credit_account_id.name) ,sub_header_style_s)
                else:
                    ws1.write(row,col+2, '',sub_header_style_s)
                ws1.write(row,col+3, (""), sub_header_style_r)
                # Reference
                if item.rate:
                    ws1.write(row,col+4, item.communication,sub_header_style_r)
                else:
                    ws1.write(row,col+4, '',sub_header_style_r)
                ws1.write(row,col+5, (""), sub_header_style_r)
                # Payment in Bs ME
                if item.amount_currency:
                    ws1.write(row,col+6, item.amount_bs,sub_header_style_r)
                else:
                    ws1.write(row,col+6, '0,00',sub_header_style_r)
                # Payment in Cash $
                if item.amount_currency:
                    ws1.write(row,col+7, item.amount_currency_cash,sub_header_style_r)
                else:
                    ws1.write(row,col+7, '0,00',sub_header_style_r)
                # Payment in Bs ME
                if item.amount_currency:
                    ws1.write(row,col+8, item.amount_currency_transfer,sub_header_style_r)
                else:
                    ws1.write(row,col+8, '0,00',sub_header_style_r)
        
            total_bs += item.amount_bs
            total_bs_me += item.amount_currency
            total_cash_usd += item.amount_currency_cash
            total_transfer_usd += item.amount_currency_transfer
                
        row += 1
        ws1.write_merge(row,row, 0, 4, ("Totals..."), sub_header_style_c)
        ws1.write(row,col+5, total_bs,sub_header_style_m)
        ws1.write(row,col+6, total_bs_me,sub_header_style_m)
        ws1.write(row,col+7, total_cash_usd,sub_header_style_m)
        ws1.write(row,col+8, total_transfer_usd,sub_header_style_m)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name': _('Collections Closing Report ')+ fecha +'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'closing.report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }