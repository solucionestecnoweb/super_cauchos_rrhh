from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
import openerp.addons.decimal_precision as dp
import logging

import io
from io import BytesIO

import xlsxwriter
import shutil
import base64
import csv
import xlwt
import xml.etree.ElementTree as ET

class LibroDiario(models.TransientModel):
    _inherit = 'wizard.libro.diario'

    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=50)
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())

    def get_data(self):
        t=self.env['libro.diario.wizard.pdf'].search([])
        w=self.env['wizard.libro.diario'].search([('id','!=',self.id)])
        t.unlink()
        w.unlink()
        cur_account=self.env['account.account'].search([],order="code asc")
        for det_account in cur_account:
            acum_deber=0
            acum_haber=0
            cursor = self.env['account.move.line'].search([('date', '>=', self.date_from),('date','<=',self.date_to),('account_id','=',det_account.id),('parent_state','=','posted')])
            """if cursor:
                raise UserError(_('cursor = %s')%cursor)"""
            if cursor:
                for det in cursor:
                    acum_deber=acum_deber+det.debit
                    acum_haber=acum_haber+det.credit
                    #raise UserError(_('lista_mov_line = %s')%acum_deber)
                    values=({
                    'account_id':det_account.id,
                    'total_deber':acum_deber,
                    'total_haber':acum_haber,
                    'name':det_account.name,
                    'fecha_desde':self.date_from,
                    'fecha_hasta':self.date_to,
                    })
                    diario_id = t.create(values)
        self.line=self.env['libro.diario.wizard.pdf'].search([])
    
    def generate_pdf_report(self):
        self.get_data()
        return {'type': 'ir.actions.report','report_name': 'daily_book.daily_book_report','report_type':"qweb-pdf"}
    
    def generate_xls_report(self):
        self.get_data()
        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet(_('Libro Diario'))
        fp = BytesIO()

        header_tittle_style = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170; align: horiz center, vert centre;")
        header_content_style = xlwt.easyxf("font: name Helvetica size 16 px, bold 1, height 170; align: horiz center, vert centre; pattern:pattern solid, fore_colour silver_ega;")
        lines_style_center = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: bottom thin; align: horiz center, vert centre;")
        lines_style_right = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: bottom thin; align: horiz right, vert centre;")
        
        table_style_center = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz center, vert centre;")
        table_style_right = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz right, vert centre;")

        row = 0
        col = 0
        ws1.row(row).height = 500
        ws1.write_merge(row,row, 2, 3, self.company_id.name, header_tittle_style)
        xdate = self.date_now.strftime('%d/%m/%Y %I:%M:%S %p')
        xdate = datetime.strptime(xdate,'%d/%m/%Y %I:%M:%S %p') - timedelta(hours=4)
        ws1.write_merge(row,row, 4, 5, xdate.strftime('%d/%m/%Y %I:%M:%S %p'), header_tittle_style)
        row += 1
        ws1.write_merge(row,row, 2, 3, 'R.I.F. ' + self.company_id.vat, header_tittle_style)
        row += 1
        ws1.write_merge(row,row, 2, 3, _("Libro Diario"), header_tittle_style)
        row += 1
        ws1.write_merge(row,row, 2, 3, _('Desde: ') + self.date_from.strftime('%d/%m/%Y') + _(' Hasta: ') + self.date_to.strftime('%d/%m/%Y'), header_tittle_style)
        row += 2


        #CABECERA DE LA TABLA 
        ws1.write(row,col+1, _("Código"),header_content_style)
        ws1.col(col+1).width = int((len('Código')+16)*256)
        ws1.write(row,col+2, _("Descripción de la cuenta"),header_content_style)
        ws1.col(col+2).width = int((len('Descripción de la cuenta')+26)*256)
        ws1.write(row,col+3, _("Débitos"),header_content_style)
        ws1.col(col+3).width = int((len('xxx.xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+4,_("Créditos"),header_content_style)
        ws1.col(col+4).width = int((len('xxx.xxx.xxx.xxx,xx')+2)*256)

        #Totales
        deber = 0
        haber= 0
        #####

        for item in self.line:
            row += 1
            # codigo
            if item.account_id.code:
                ws1.write(row,col+2, item.account_id.code, lines_style_center)
            else:
                ws1.write(row,col+2, '', lines_style_center)
            # descripcion
            if item.name:
                ws1.write(row,col+1, item.name, lines_style_center)
            else:
                ws1.write(row,col+1, '', lines_style_center)
            # debito
            ws1.write(row,col+3, self.float_format2(item.total_deber), lines_style_right)
            # credito
            ws1.write(row,col+4, self.float_format2(item.total_haber), lines_style_right)
    
            

            deber += item.total_deber
            haber += item.total_haber
                
        row += 1
        ws1.write_merge(row,row, 1, 2, 'Total General', lines_style_center)
        ws1.write(row,col+3, self.float_format2(deber), lines_style_right)
        ws1.write(row,col+4, self.float_format2(haber), lines_style_right)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name': _('Libro Diario ')+ fecha +'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.libro.diario',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }