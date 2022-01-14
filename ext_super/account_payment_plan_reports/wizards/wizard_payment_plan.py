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

_logger = logging.getLogger(__name__)

class WizardPaymentPlan(models.TransientModel):
    _name = "wizard.payment.plan"

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())
    
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=60)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.user.company_id.id)

    def print_pdf(self):
        return {'type': 'ir.actions.report','report_name': 'account_payment_plan_reports.payment_plan_report','report_type':"qweb-pdf"}

    def _get_data(self):
        xfind = self.env['account.move.line'].search([
            ('date','>=',self.date_from),
            ('date','<=',self.date_to),
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('move_id.state', '!=', 'cancel'),
            ('move_id.invoice_payment_state', '!=', 'paid'),
            ('move_id.type', 'in', ('in_invoice', 'entry')),
            ('move_id.journal_id.type', 'in', ('bank', 'purchase')),
            ('move_id.state', '=', 'posted'),
            ('amount_residual', '!=', 0),
            ('full_reconcile_id', '=', False),
            ('balance', '!=', 0),
            ('account_id.reconcile', '=', True),
            ('account_id.internal_type', '=', 'payable'),
        ])
        return xfind
    
    # *******************  REPORTE EN EXCEL ****************************

    def generate_xls_report(self):
        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet(_('Payment Planning'))
        fp = BytesIO()

        header_content_style = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170; align: horiz center;")
        sub_header_style = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170")
        sub_header_style_c = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz center")
        sub_header_style_r = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz right")
        line_content_style = xlwt.easyxf("font: name Helvetica, height 170;")

        row = 0
        col = 0
        ws1.row(row).height = 500
        ws1.write_merge(row,row, 4, 8, _("Payment Planning"), header_content_style)
        xdate = self.date_now.strftime('%d/%m/%Y %I:%M:%S %p')
        xdate = datetime.strptime(xdate,'%d/%m/%Y %I:%M:%S %p') - timedelta(hours=4)
        ws1.write_merge(row,row, 9, 12, xdate.strftime('%d/%m/%Y %I:%M:%S %p'), header_content_style)
        row += 1
        ws1.write_merge(row,row, 4, 8, _("From ") + self.date_from.strftime('%d/%m/%Y') + _(" To ") + self.date_to.strftime('%d/%m/%Y'), header_content_style)
        row += 2

        #CABECERA DE LA TABLA 
        ws1.write(row,col+0, _("Item"),sub_header_style_c)
        ws1.col(col+0).width = int((len('Item')+2)*256)
        ws1.write(row,col+1, _("Doc Date"),sub_header_style_c)
        ws1.col(col+1).width = int((len('xx/xx/xxxx')+5)*256)
        ws1.write(row,col+2, _("Purchase Num"),sub_header_style_c)
        ws1.col(col+2).width = int((len('Purchase Num')+6)*256)
        ws1.write(row,col+3, _("Supplier"),sub_header_style_c)
        ws1.col(col+3).width = int((len('Supplier')+25)*256)
        ws1.write(row,col+4,_("Specs"),sub_header_style_c)
        ws1.col(col+4).width = int((len('Specs')+30)*256)
        ws1.write(row,col+5, _("Base"),sub_header_style_c)
        ws1.col(col+5).width = int((len('xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+6, _("Exempt"),sub_header_style_c)
        ws1.col(col+6).width = int((len('xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+7, _("IVA"),sub_header_style_c)
        ws1.col(col+7).width = int((len('xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+8, _("Total"),sub_header_style_c)
        ws1.col(col+8).width = int((len('xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+9, _("Currency Transf. $"),sub_header_style_c)
        ws1.col(col+9).width = int((len('xxx.xxx.xxx,xx')+6)*256)
        ws1.write(row,col+10, _("Amount to Cancel $"),sub_header_style_c)
        ws1.col(col+10).width = int((len('xxx.xxx.xxx,xx')+6)*256)
        ws1.write(row,col+11, _("Paid / Observation"),sub_header_style_c)
        ws1.col(col+11).width = int((len('Paid / Observation')+10)*256)
        ws1.write(row,col+12, _("Amount to Cancel Bs."),sub_header_style_c)
        ws1.col(col+12).width = int((len('xxx.xxx.xxx,xx')+8)*256)

        center = xlwt.easyxf("align: horiz center")
        right = xlwt.easyxf("align: horiz right")

        #Totales
        t_transfer = 0
        t_cancel_usd = 0
        t_cancel_bs = 0
        ###

        counter = 0

        for item in self._get_data():
            rate = self.env['res.currency.rate'].search([('name', '=', item.date)]).sell_rate
            if not rate:
                rate = 1
            for line in item.move_id.invoice_line_ids:
                counter += 1
                row += 1
                
                # Item
                ws1.write(row,col+0, counter,center)

                # Doc Date
                if item.date:
                    ws1.write(row,col+1, item.date.strftime('%d/%m/%Y'),center)
                else:
                    ws1.write(row,col+1, '',center)

                # Purchase Num
                if item.move_id:
                    ws1.write(row,col+2, item.move_id.name,center)
                else:
                    ws1.write(row,col+2, '',center)
                
                # Supplier
                if item.partner_id:
                    ws1.write(row,col+3, item.partner_id.name,center)
                else:
                    ws1.write(row,col+3, '',center)
                
                # Specs
                if line.name:
                    ws1.write(row,col+4, line.name,center)
                else:
                    ws1.write(row,col+4, '',center)
                
                # Base
                ws1.write(row,col+5, round(line.price_unit, 2),right)
                
                # IVA
                # Exempt
                tax = 0
                if line.tax_ids:
                    for taxes in line.tax_ids:
                        tax = (line.price_unit * taxes.amount) / 100
                        if taxes.aliquot == 'exempt':
                            ws1.write(row,col+6,round(tax, 2),right)
                            ws1.write(row,col+7,'',right)
                        else:
                            ws1.write(row,col+6,'',right)
                            ws1.write(row,col+7,round(tax, 2),right)
                else:
                    ws1.write(row,col+6,'',right)
                    ws1.write(row,col+7,'',right)

                # Total
                ws1.write(row,col+8,round((line.price_unit * line.quantity) + tax, 2),right)
                
                # Currency Transf. $
                if item.move_id.payment_condition_id not in ('contado', 'Contado', 'CONTADO') and item.move_id.payment_condition_id:
                    if item.move_id.currency_id.name == 'Bs.':
                        ws1.write(row,col+9,round(((line.price_unit * line.quantity) + tax) / rate, 2),right)
                        t_transfer += ((line.price_unit * line.quantity) + tax) / rate
                    else:
                        ws1.write(row,col+9,round((line.price_unit * line.quantity) + tax, 2),right)
                        t_transfer += (line.price_unit * line.quantity) + tax
                else:
                    ws1.write(row,col+9,'',right)

                # Amount to Cancel $
                # Paid / Observation
                # Amount to Cancel Bs.
                if item.move_id.currency_id.name == 'Bs.':
                    ws1.write(row,col+10,round(((line.price_unit * line.quantity) + tax) / rate, 2),right)
                    if item.move_id.narration:
                        ws1.write(row,col+11,item.move_id.narration,center)
                    else:
                        ws1.write(row,col+11,'',center)
                    ws1.write(row,col+12,round((line.price_unit * line.quantity) + tax, 2),right)
                    
                    t_cancel_usd += ((line.price_unit * line.quantity) + tax) / rate
                    t_cancel_bs += (line.price_unit * line.quantity) + tax
                else:
                    ws1.write(row,col+10,round((line.price_unit * line.quantity) + tax, 2),right)
                    if item.move_id.narration:
                        ws1.write(row,col+11,item.move_id.narration,center)
                    else:
                        ws1.write(row,col+11,'',center)
                    ws1.write(row,col+12,round(((line.price_unit * line.quantity) + tax) * rate, 2),right)
                    
                    t_cancel_usd += (line.price_unit * line.quantity) + tax
                    t_cancel_bs += ((line.price_unit * line.quantity) + tax) * rate
                
                
        row += 1
        ws1.write(row,col+9, round(t_transfer, 2),right)
        ws1.write(row,col+10, round(t_cancel_usd, 2),right)
        ws1.write(row,col+12, round(t_cancel_bs, 2),right)

        row += 1
        ws1.write_merge(row,row+1, 3, 4, _('Total Payment ') + self.company_id.name,sub_header_style_c)
        ws1.write(row,col+5, _('$'),sub_header_style_c)
        ws1.write_merge(row,row, 6, 7, round(t_cancel_usd + t_transfer, 2),sub_header_style_r)

        row += 1
        ws1.write(row,col+5, _('Bs.'),sub_header_style_c)
        ws1.write_merge(row,row, 6, 7, round(t_cancel_bs, 2),sub_header_style_r)

        row += 3
        ws1.write_merge(row,row, 1, 2, _('Made By: ') + self.env.user.name,sub_header_style)
        ws1.write_merge(row,row, 10, 11, _('Reviewed By: '),sub_header_style)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name': _('Payment Planning ')+ fecha +'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.payment.plan',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
