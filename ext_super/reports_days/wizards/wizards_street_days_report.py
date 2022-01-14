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

class StreetDaysReport(models.TransientModel):
    _name = "street_days.report"

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
            'report_name': 'reports_days.street_days_report',
            'report_type':"qweb-pdf"
            }

    def get_lines(self):
        xfind = self.env['account.move'].search([('type', '=', 'out_invoice'), ('invoice_date', '>=', self.date_from), ('invoice_date', '<=', self.date_to), ('invoice_payment_state', '=', 'paid')])
        return xfind

    def show_street_days(self):
        self.env['account.move'].search([])
        self.ensure_one()
        res = self.env.ref('reports_days.type_street_name_action').read()[0]
        return res

    # *******************  REPORTE EN EXCEL ****************************

    def generate_xls_report(self):

        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet(_('Reporte de Días Calle'))
        fp = BytesIO()

        header_content_style = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170; align: horiz center;")
        sub_header_style = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170")
        sub_header_style_c = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz center")
        sub_header_style_r = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz right")
        sub_header_content_style = xlwt.easyxf("font: name Helvetica size 10 px, height 170;")
        line_content_style = xlwt.easyxf("font: name Helvetica, height 170;")

        row = 0
        col = 0
        ws1.row(row).height = 500
        ws1.write_merge(row,row, 4, 5, _("Reporte de Días Calle"), header_content_style)
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
        ws1.write(row,col+0, _("Fecha de Vencimiento"),sub_header_style_c)
        ws1.col(col+0).width = int((len('xx/xx/xxxx')+10)*256)
        ws1.write(row,col+1, _("Fecha de Pago"),sub_header_style_c)
        ws1.col(col+1).width = int((len('xx/xx/xxxx')+10)*256)
        ws1.write(row,col+2, _("Días Calle"),sub_header_style_c)
        ws1.col(col+2).width = int((len('Días Calle')+15)*256)
        ws1.write(row,col+3, _("Factura"),sub_header_style_c)
        ws1.col(col+3).width = int((len('Factura')+20)*256)
        ws1.write(row,col+4, _("Cliente"),sub_header_style_c)
        ws1.col(col+4).width = int((len('Cliente')+26)*256)
        ws1.write(row,col+5, _("Monto en Bs"),sub_header_style_c)
        ws1.col(col+5).width = int((len('Monto en Bs')+10)*256)
        ws1.write(row,col+6, _("Tasa"),sub_header_style_c)
        ws1.col(col+6).width = int((len('Tasa')+15)*256)
        ws1.write(row,col+7, _("Monto en $"),sub_header_style_c)
        ws1.col(col+7).width = int((len('Monto en $')+10)*256)

        center = xlwt.easyxf("align: horiz center")
        right = xlwt.easyxf("align: horiz right")

        #Totales
        total_street_days = 0
        total_bs = 0
        total_usd = 0

        for item in self.get_lines():
            row += 1
            # Date of Expiration
            if item.invoice_date_due:
                ws1.write(row,col+0, item.invoice_date_due.strftime('%d/%m/%Y'),center)
            else:
                ws1.write(row,col+0, '',center)
            # Date of Payment
            if item.payment_date:
                ws1.write(row,col+1, item.payment_date.strftime('%d/%m/%Y'),center)
            else:
                ws1.write(row,col+1, '',center)
            # Street Days
            if item.street_days:
                ws1.write(row,col+2, item.street_days,center)
            else:
                ws1.write(row,col+2, '0',center)
            # Bill
            if item.name:
                ws1.write(row,col+3, item.name,center)
            else:
                ws1.write(row,col+3, '',center)
            # Customer
            if item.invoice_partner_display_name:
                ws1.write(row,col+4, item.invoice_partner_display_name,center)
            else:
                ws1.write(row,col+4, '',center)
            # Amount in Bs
            if item.amount_total_signed:
                ws1.write(row,col+5, item.amount_total,right)
            else:
                ws1.write(row,col+5, '',right)
            # Rate
            if item.rate:
                ws1.write(row,col+6, item.rate,right)
            else:
                ws1.write(row,col+6, '',right)
            # Amount in $
            if item.amount_currency:
                ws1.write(row,col+7, item.amount_currency,right)
            else:
                ws1.write(row,col+7, '',right)

            total_street_days += item.street_days
            total_bs += item.amount_total
            total_usd += item.amount_currency
                
        row += 1
        ws1.write_merge(row,row, 0, 1, ("Totales..."), sub_header_style_c)
        ws1.write(row,col+2, total_street_days,center)
        ws1.write(row,col+5, total_bs,right)
        ws1.write(row,col+7, total_usd,right)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name': _('Reporte de Días Calle ')+ fecha +'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'street_days.report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }