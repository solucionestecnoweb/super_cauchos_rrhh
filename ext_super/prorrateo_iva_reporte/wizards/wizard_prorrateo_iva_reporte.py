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

class DataProrrateoIVA(models.TransientModel):
    _name = 'data.prorrateo.iva'

    cliente = fields.Char(string='Cliente')
    n_factura = fields.Char(string='Nro Factura')
    cuenta = fields.Char(string='Cuenta')
    credito_fiscal = fields.Float(string='Credito Fiscal')
    deducible = fields.Float(string='Deducible')
    no_deducible = fields.Float(string='No Deducible')
    tipo = fields.Selection(string='Tipo', selection=[('nd', 'nd'), ('pd', 'pd'), ('td', 'td')])

class WizardProrrateoIVA(models.TransientModel):
    _name = 'wizard.prorrateo.iva'

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency')

    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=60)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.user.company_id.id)
    lines_ids = fields.Many2many(comodel_name='data.prorrateo.iva', string='Lines')

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

    # *******************  REPORTE EN PDF ****************************

    def print_pdf(self):
        self.env['data.prorrateo.iva'].search([]).unlink()
        self.get_data()
        return {
            'type': 'ir.actions.report',
            'report_name': 'prorrateo_iva_reporte.prorrateo_iva_reporte',
            'report_type':"qweb-pdf"
            }

    # *******************  BÚSQUEDA DE DATOS ****************************



    # *******************  REPORTE EN EXCEL ****************************

    # def generate_xls_report(self):
    #     self.env['data.prorrateo.iva'].search([]).unlink()
    #     self.get_data()

    #     wb1 = xlwt.Workbook(encoding='utf-8')
    #     ws1 = wb1.add_sheet(_('Libro Mayor Legal'))
    #     fp = BytesIO()

    #     header_tittle_style = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170; align: horiz center, vert centre;")
    #     header_content_style = xlwt.easyxf("font: name Helvetica size 16 px, bold 1, height 170; align: horiz center, vert centre; pattern:pattern solid, fore_colour silver_ega;")
    #     lines_style_center = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: bottom thin; align: horiz center, vert centre;")
    #     lines_style_right = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: bottom thin; align: horiz right, vert centre;")
        
    #     table_style_center = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz center, vert centre;")
    #     table_style_right = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz right, vert centre;")

    #     row = 0
    #     col = 0
    #     ws1.row(row).height = 500

    #     #CABECERA DEL REPORTE
    #     ws1.write_merge(row,row, 2, 3, self.company_id.name, header_tittle_style)
    #     xdate = self.date_now.strftime('%d/%m/%Y %I:%M:%S %p')
    #     xdate = datetime.strptime(xdate,'%d/%m/%Y %I:%M:%S %p') - timedelta(hours=4)
    #     ws1.write_merge(row,row, 4, 5, xdate.strftime('%d/%m/%Y %I:%M:%S %p'), header_tittle_style)
    #     row += 1
    #     ws1.write_merge(row,row, 2, 3, 'R.I.F. ' + self.company_id.vat, header_tittle_style)
    #     row += 1
    #     ws1.write_merge(row,row, 2, 3, _("Libro Mayor Legal"), header_tittle_style)
    #     row += 1
    #     ws1.write_merge(row,row, 2, 3, _('Desde: ') + self.date_from.strftime('%d/%m/%Y') + _(' Hasta: ') + self.date_to.strftime('%d/%m/%Y'), header_tittle_style)
    #     row += 2

    #     #CABECERA DE LA TABLA 
    #     ws1.write(row,col+0, _("Código"),header_content_style)
    #     ws1.col(col+0).width = int((len('x.x.x.xx.xxx')+2)*256)
    #     ws1.write(row,col+1, _("Descripción de la Cuenta"),header_content_style)
    #     ws1.col(col+1).width = int((len('Descripción de la Cuenta')+20)*256)
    #     ws1.write(row,col+2, _("Saldo Anterior"),header_content_style)
    #     ws1.col(col+2).width = int((len('xxx.xxx.xxx,xx xxx')+2)*256)
    #     ws1.write(row,col+3, _("Débitos"),header_content_style)
    #     ws1.col(col+3).width = int((len('xxx.xxx.xxx,xx xxx')+2)*256)
    #     ws1.write(row,col+4, _("Créditos"),header_content_style)
    #     ws1.col(col+4).width = int((len('xxx.xxx.xxx,xx xxx')+2)*256)
    #     ws1.write(row,col+5, _("Saldo Actual"),header_content_style)
    #     ws1.col(col+5).width = int((len('xxx.xxx.xxx,xx xxx')+2)*256)

    #     #VARIABLES TOTALES
    #     total_previous = 0
    #     total_debit = 0
    #     total_credit = 0
    #     total_current = 0

    #     #LINEAS
    #     for item in self.lines_ids:
    #         row += 1
    #         # Código
    #         if item.code:
    #             ws1.write(row,col+0, item.code,lines_style_center)
    #         else:
    #             ws1.write(row,col+0, '',lines_style_center)
    #         # Descripción de la Cuenta
    #         if item.description:
    #             ws1.write(row,col+1, item.description,lines_style_center)
    #         else:
    #             ws1.write(row,col+1, '',lines_style_center)
    #         # Saldo Anterior
    #         ws1.write(row,col+2, self.float_format(item.previous),lines_style_right)
    #         # Débitos
    #         ws1.write(row,col+4, self.float_format(item.debit),lines_style_right)
    #         # Créditos
    #         ws1.write(row,col+3, self.float_format(item.credit),lines_style_right)
    #         # Saldo Actual
    #         ws1.write(row,col+5, self.float_format(item.current),lines_style_right)

    #         total_previous += item.previous
    #         total_debit += item.credit
    #         total_credit += item.debit
    #         total_current += item.current

    #     #TOTALES
    #     row += 1
    #     ws1.write_merge(row,row,col+0,col+1, _('Total general'), lines_style_center)
    #     ws1.write(row,col+2, self.float_format(total_previous), lines_style_right)
    #     ws1.write(row,col+3, self.float_format(total_debit), lines_style_right)
    #     ws1.write(row,col+4, self.float_format(total_credit), lines_style_right)
    #     ws1.write(row,col+5, self.float_format(total_current), lines_style_right)

    #     #IMPRESIÓN
    #     wb1.save(fp)
    #     out = base64.encodestring(fp.getvalue())
    #     fecha  = datetime.now().strftime('%d/%m/%Y') 
    #     self.write({'state': 'get', 'report': out, 'name': _('Libro Mayor Legal ')+ fecha +'.xls'})
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'wizard.prorrateo.iva',
    #         'view_mode': 'form',
    #         'view_type': 'form',
    #         'res_id': self.id,
    #         'views': [(False, 'form')],
    #         'target': 'new',
    #     }

