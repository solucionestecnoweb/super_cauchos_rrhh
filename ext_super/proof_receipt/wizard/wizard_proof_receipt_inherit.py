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

class ProofReceiptPDF(models.TransientModel):
    _name = "proof.receipt.wizard.pdf"

    fecha_desde=fields.Date()
    fecha_hasta=fields.Date()
    account_id=fields.Many2one('account.account')
    name=fields.Char()
    total_deber=fields.Float()
    total_haber=fields.Float()
    total_deber_usd=fields.Float()
    total_haber_usd=fields.Float()

class ProofReceipt(models.TransientModel):
    _name = 'wizard.proof.receipt'

    date_from  = fields.Date('Date From', default=lambda *a:(datetime.now() - timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_to = fields.Date(string='Date To', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))

    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.user.company_id.id)
    line  = fields.Many2many(comodel_name='proof.receipt.wizard.pdf', string='Lineas')

    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=50)
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())

    def get_convertion(self, monto, fecha, moneda):
        tasa = self.env['res.currency.rate'].search([('name', '=', fecha), ('currency_id', '=', moneda)], limit=1).sell_rate
        if not tasa:
            tasa = 1
        conversion = monto / tasa
        return conversion

    def float_format2(self,valor):
        if valor:
            result = '{:,.2f}'.format(valor)
            result = result.replace(',','*')
            result = result.replace('.',',')
            result = result.replace('*','.')
        else:
            result="0,00"
        return result

    def get_data(self):
        t=self.env['proof.receipt.wizard.pdf'].search([])
        w=self.env['wizard.proof.receipt'].search([('id','!=',self.id)])
        t.unlink()
        w.unlink()
        cur_account=self.env['account.account'].search([],order="code asc")
        for det_account in cur_account:
            acum_deber=0
            acum_haber=0
            acum_deber_usd = 0
            acum_haber_usd = 0
            cursor = self.env['account.move.line'].search([('date', '>=', self.date_from),('date','<=',self.date_to),('account_id','=',det_account.id),('parent_state','=','posted')])
            """if cursor:
                raise UserError(_('cursor = %s')%cursor)"""
            if cursor:
                for det in cursor:
                    acum_deber += det.debit
                    acum_haber += det.credit
                    acum_deber_usd += self.get_convertion(det.debit,det.date, 2)
                    acum_haber_usd += self.get_convertion(det.credit,det.date, 2)
                    #raise UserError(_('lista_mov_line = %s')%acum_deber)
                values=({
                'account_id':det_account.id,
                'total_deber':acum_deber,
                'total_haber':acum_haber,
                'total_deber_usd':acum_deber_usd,
                'total_haber_usd':acum_haber_usd,
                'name':det_account.name,
                'fecha_desde':self.date_from,
                'fecha_hasta':self.date_to,
                })
                t.create(values)
        self.line=self.env['proof.receipt.wizard.pdf'].search([])
    
    def generate_pdf_report(self):
        self.get_data()
        return {'type': 'ir.actions.report','report_name': 'proof_receipt.proof_receipt_report','report_type':"qweb-pdf"}
    
    def generate_xls_report(self):
        self.get_data()
        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet(_('Comprobante Mayorizado'))
        fp = BytesIO()

        header_tittle_style = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170; align: horiz center, vert centre;")
        header_content_style = xlwt.easyxf("font: name Helvetica size 16 px, bold 1, height 170; align: horiz center, vert centre; pattern:pattern solid, fore_colour silver_ega;")
        header_content_style_left = xlwt.easyxf("font: name Helvetica size 16 px, bold 1, height 170; align: vert centre; pattern:pattern solid, fore_colour silver_ega;")
        lines_style_center = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: bottom thin; align: horiz center, vert centre;")
        lines_style_left = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: bottom thin; align: vert centre;")
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
        ws1.write_merge(row,row, 2, 3, _("Comprobante Mayorizado"), header_tittle_style)
        row += 1
        ws1.write_merge(row,row, 2, 3, _('Desde: ') + self.date_from.strftime('%d/%m/%Y') + _(' Hasta: ') + self.date_to.strftime('%d/%m/%Y'), header_tittle_style)
        row += 2

        #CABECERA DE LA TABLA
        row += 2 
        ws1.write(row,col+1, _("Código"),header_content_style)
        ws1.col(col+1).width = int((len('Código')+16)*256)
        ws1.write(row,col+2, _("Descripción de la cuenta"),header_content_style)
        ws1.col(col+2).width = int((len('Descripción de la cuenta')+26)*256)
        ws1.write(row,col+3, _("Débitos"),header_content_style)
        ws1.col(col+3).width = int((len('xxx.xxx.xxx.xxx,xx')+10)*256)
        ws1.write(row,col+4,_("Créditos"),header_content_style)
        ws1.col(col+4).width = int((len('xxx.xxx.xxx.xxx,xx')+10)*256)

        #Totales
        deber = 0
        haber= 0
        deber_usd = 0
        haber_usd= 0
        #####

        for item in self.line:
            row += 1
            # codigo
            if item.account_id.code:
                ws1.write(row,col+1, item.account_id.code, lines_style_center)
            else:
                ws1.write(row,col+1, '', lines_style_center)
            # descripcion
            if item.name:
                ws1.write(row,col+2, item.name, lines_style_center)
            else:
                ws1.write(row,col+2, '', lines_style_center)
            # debito
            ws1.write(row,col+3, self.float_format2(item.total_deber), lines_style_right)
            # credito
            ws1.write(row,col+4, self.float_format2(item.total_haber), lines_style_right)
    
            

            deber += item.total_deber
            haber += item.total_haber
            deber_usd += item.total_deber_usd
            haber_usd += item.total_haber_usd
                
        row += 1
        ws1.write_merge(row,row, 1, 2, 'Total Bs', lines_style_center)
        ws1.write(row,col+3, self.float_format2(deber), lines_style_right)
        ws1.write(row,col+4, self.float_format2(haber), lines_style_right)

        row += 1
        ws1.write_merge(row,row, 1, 2, 'Total $', lines_style_center)
        ws1.write(row,col+3, self.float_format2(deber_usd), lines_style_right)
        ws1.write(row,col+4, self.float_format2(haber_usd), lines_style_right)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name': _('Comprobante Mayorizado ')+ fecha +'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.proof.receipt',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }