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

class Exchange(models.TransientModel):
    _name = "transaction.exchange"

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())

    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Archivo Preparado', filters='.xls', readonly=True)
    name = fields.Char('Nombre del Archivo', size=50)
    company_id = fields.Many2one('res.company','Compañía',default=lambda self: self.env.user.company_id.id)

    def get_lines(self):
        xfind = self.env['account.exchange'].search([('state', 'in', ('confirmed', 'done')), ('request', '>=', self.date_from), ('request', '<=', self.date_to)])
        return xfind

    def generate_xls_report(self):

        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet(_('Transacciones de Cambio'))
        fp = BytesIO()

        header_content_style = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170; align: horiz center;")
        sub_header_style = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170")
        sub_header_style_c = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz center")
        sub_header_style_r = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz right")
        sub_header_content_style = xlwt.easyxf("font: name Helvetica size 10 px, height 170;")
        line_content_style = xlwt.easyxf("font: name Helvetica, height 170;")

        def float_format(self,valor):
            if valor:
                result = '{:,.2f}'.format(valor)
                result = result.replace(',','*')
                result = result.replace('.',',')
                result = result.replace('*','.')
            else:
                result="0,00"
            return result

        row = 0
        col = 0
        ws1.row(row).height = 500
        ws1.write_merge(row,row, 4, 5, _("Transacciones de Cambio"), header_content_style)
        xdate = self.date_now.strftime('%d/%m/%Y %I:%M:%S %p')
        xdate = datetime.strptime(xdate,'%d/%m/%Y %I:%M:%S %p') - timedelta(hours=4)
        xname = self.company_id.name
        xvat = self.company_id.vat
        ws1.write_merge(row,row, 0, 1, xname, header_content_style)
        ws1.write_merge(row,row, 2, 3, xvat, header_content_style)
        ws1.write_merge(row,row, 6, 7, xdate.strftime('%d/%m/%Y %I:%M:%S %p'), header_content_style)
        row += 2

        #CABECERA DE LA TABLA 
        ws1.col(col).width = 250
        ws1.write(row,col+0, _("Fecha de Solicitud"),sub_header_style_c)
        ws1.col(col+0).width = int((len('xx/xx/xxxx')+10)*256)
        ws1.write(row,col+1, _("Monto"),sub_header_style_c)
        ws1.col(col+1).width = int((len('xxx.xxx.xxx,xx')+10)*256)
        ws1.write(row,col+2, _("Moneda Origen"),sub_header_style_c)
        ws1.col(col+2).width = int((len('Moneda Origen')+10)*256)
        ws1.write(row,col+3, _("Transacción"),sub_header_style_c)
        ws1.col(col+3).width = int((len('Transacción')+10)*256)
        ws1.write(row,col+4, _("Tasa"),sub_header_style_c)
        ws1.col(col+4).width = int((len('Tasa')+20)*256)
        ws1.write(row,col+5, _("Monto Convertido"),sub_header_style_c)
        ws1.col(col+5).width = int((len('Monto Convertido')+20)*256)
        ws1.write(row,col+6, _("Moneda Final"),sub_header_style_c)
        ws1.col(col+6).width = int((len('Moneda Final')+26)*256)
        ws1.write(row,col+7, _("Referencia"),sub_header_style_c)
        ws1.col(col+7).width = int((len('Referencia')+10)*256)

        center = xlwt.easyxf("align: horiz center")
        right = xlwt.easyxf("align: horiz right")

        for item in self.get_lines():
            row += 1
            # Date of Request
            if item.request:
                ws1.write(row,col+0, item.request.strftime('%d/%m/%Y'),center)
            else:
                ws1.write(row,col+0, '',center)
            # Amount
            if item.amount:
                ws1.write(row,col+1, float_format(self, item.amount),right)
            else:
                ws1.write(row,col+1, '0,00',right)
            # Origin Currency
            if item.origin_currency_id:
                ws1.write(row,col+2, item.origin_currency_id.name,center)
            else:
                ws1.write(row,col+2, '0,00',center)
            # Transaction
            if item.transaction == 'buy':
                ws1.write(row,col+3, 'Compra',center)
            else:
                ws1.write(row,col+3, 'Venta',center)
            # Rate
            if item.rate:
                ws1.write(row,col+4, float_format(self, item.rate),right)
            else:
                ws1.write(row,col+4, '',right)
            # Converted Amount
            if item.final_amount:
                ws1.write(row,col+5, float_format(self, item.final_amount),right)
            else:
                ws1.write(row,col+5, '',center)
            # Final Currency
            if item.final_currency_id:
                ws1.write(row,col+6, item.final_currency_id.name,center)
            else:
                ws1.write(row,col+6, '',center)
            # Reference
            if item.reference:
                ws1.write(row,col+7, item.reference,center)
            else:
                ws1.write(row,col+7, '',center)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name': _('Transacciones de Cambio ')+ fecha +'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'transaction.exchange',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }