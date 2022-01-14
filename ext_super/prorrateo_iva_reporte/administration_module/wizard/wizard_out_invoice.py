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

class WizardOutInvoice(models.TransientModel):
    _name = "wizard.out.invoice"

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())
    partner_ids = fields.Many2many(comodel_name='res.partner', string='Clientes')
    
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=60)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.user.company_id.id)

    def print_pdf(self):
        return {'type': 'ir.actions.report','report_name': 'administration_module.out_invoice_report','report_type':"qweb-pdf"}

    def _get_data(self):
        if self.partner_ids:
            xfind = self.env['account.move.line'].search([
                ('date','>=',self.date_from),
                ('date','<=',self.date_to),
                ('partner_id', 'in', self.partner_ids.ids),
                ('display_type', 'not in', ('line_section', 'line_note')),
                ('move_id.state', '!=', 'cancel'),
                # ('move_id.invoice_payment_state', '!=', 'paid'),
                # ('move_id.type', 'in', ('out_invoice', 'entry')),
                # ('move_id.journal_id.type', 'in', ('bank', 'sale')),
                ('move_id.state', '=', 'posted'),
                ('amount_residual', '!=', 0),
                ('full_reconcile_id', '=', False),
                ('balance', '!=', 0),
                ('account_id.reconcile', '=', True),
                ('account_id.internal_type', '=', 'receivable'),
                # ('account_id.user_type_id.type', '=', 'receivable'),
            ])
        else:
            xfind = self.env['account.move.line'].search([
                ('date','>=',self.date_from),
                ('date','<=',self.date_to),
                ('display_type', 'not in', ('line_section', 'line_note')),
                ('move_id.state', '!=', 'cancel'),
                # ('move_id.invoice_payment_state', '!=', 'paid'),
                # ('move_id.type', 'in', ('out_invoice', 'entry')),
                # ('move_id.journal_id.type', 'in', ('bank', 'sale')),
                ('move_id.state', '=', 'posted'),
                ('amount_residual', '!=', 0),
                ('full_reconcile_id', '=', False),
                ('balance', '!=', 0),
                ('account_id.reconcile', '=', True),
                ('account_id.internal_type', '=', 'receivable'),
            ])
        return xfind
    
    # *******************  REPORTE EN EXCEL ****************************

    def float_format(self,valor):
        if valor:
            result = '{:,.2f}'.format(valor)
            result = result.replace(',','*')
            result = result.replace('.',',')
            result = result.replace('*','.')
        else:
            result="0,00"
        return result

    def generate_xls_report(self):
        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet(_('Past Due Accounts Receivable Report'))
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
        ws1.write_merge(row,row, 4, 9, _("Past Due Accounts Receivable Report"), header_content_style)
        xdate = self.date_now.strftime('%d/%m/%Y %I:%M:%S %p')
        xdate = datetime.strptime(xdate,'%d/%m/%Y %I:%M:%S %p') - timedelta(hours=4)
        ws1.write_merge(row,row, 10, 13, xdate.strftime('%d/%m/%Y %I:%M:%S %p'), header_content_style)
        row += 1
        ws1.write_merge(row,row, 4, 9, _("From ") + self.date_from.strftime('%d/%m/%Y') + _(" To ") + self.date_to.strftime('%d/%m/%Y'), header_content_style)
        row += 2

        #CABECERA DE LA TABLA 
        ws1.write(row,col+0, _("Customer"),sub_header_style_c)
        ws1.col(col+0).width = int((len('xxxx/xxxx/xxxx')+2)*256)
        ws1.write(row,col+1, _("Date"),sub_header_style_c)
        ws1.col(col+1).width = int((len('xx/xx/xxxx')+5)*256)
        ws1.write(row,col+2, _("Journal"),sub_header_style_c)
        ws1.col(col+2).width = int((len('Journal')+16)*256)
        ws1.write(row,col+3, _("Account"),sub_header_style_c)
        ws1.col(col+3).width = int((len('Account')+25)*256)
        ws1.write(row,col+4,_("Exp. Date"),sub_header_style_c)
        ws1.col(col+4).width = int((len('xx/xx/xxxx')+2)*256)
        ws1.write(row,col+5, _("1 - 30"),sub_header_style_c)
        ws1.col(col+5).width = int((len('xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+6, _("31 - 60"),sub_header_style_c)
        ws1.col(col+6).width = int((len('xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+7, _("61 - 90"),sub_header_style_c)
        ws1.col(col+7).width = int((len('xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+8, _("91 - 120"),sub_header_style_c)
        ws1.col(col+8).width = int((len('xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+9, _("Older"),sub_header_style_c)
        ws1.col(col+9).width = int((len('xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+10, _("Total"),sub_header_style_c)
        ws1.col(col+10).width = int((len('xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+11, _("Total $"),sub_header_style_c)
        ws1.col(col+11).width = int((len('xxx.xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+12, _("Tasa"),sub_header_style_c)
        ws1.col(col+12).width = int((len('xxx.xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+13, _("Abono"),sub_header_style_c)
        ws1.col(col+13).width = int((len('xxx.xxx.xxx.xxx,xx')+2)*256)
        ws1.write(row,col+14, _("Abono $"),sub_header_style_c)
        ws1.col(col+14).width = int((len('xxx.xxx.xxx.xxx,xx')+2)*256)

        center = xlwt.easyxf("align: horiz center")
        right = xlwt.easyxf("align: horiz right")

        #Totales
        t_1_30 = 0
        t_31_60 = 0
        t_61_90 = 0
        t_91_120 = 0
        t_older = 0
        t_total = 0
        t_total_usd = 0
        t_total_abono = 0
        t_total_abono_usd = 0
        ###
        temp_1_30 = 0
        temp_31_60 = 0
        temp_61_90 = 0
        temp_91_120 = 0
        temp_older = 0
        temp_total = 0
        temp_total_usd = 0
        temp_total_abono = 0
        temp_total_abono_usd = 0

        partner = False
        counter = len(self._get_data())

        for item in self._get_data().sorted(key=lambda x: x.partner_id.id):
            counter -= 1

            if partner != item.partner_id.name:
                row += 1
                if partner:
                    ws1.write(row,col+5, temp_1_30,right)
                    ws1.write(row,col+6, temp_31_60,right)
                    ws1.write(row,col+7, temp_61_90,right)
                    ws1.write(row,col+8, temp_91_120,right)
                    ws1.write(row,col+9, temp_older,right)
                    ws1.write(row,col+10, temp_total,right)
                    ws1.write(row,col+11, temp_total_usd,right)
                    ws1.write(row,col+13, temp_total_abono,right)
                    ws1.write(row,col+14, temp_total_abono_usd,right)
                    row += 1
                ws1.write_merge(row,row, 0, 11, item.partner_id.name, sub_header_style)
                partner = item.partner_id.name
                temp_1_30 = 0
                temp_31_60 = 0
                temp_61_90 = 0
                temp_91_120 = 0
                temp_older = 0
                temp_total = 0
                temp_total_usd = 0
                temp_total_abono = 0
                temp_total_abono_usd = 0

            row += 1
            # Journal Item
            if item.move_id:
                ws1.write(row,col+0, item.move_id.name,center)
            else:
                ws1.write(row,col+0, '',center)
            # Date
            if item.date:
                ws1.write(row,col+1, item.date.strftime('%d/%m/%Y'),center)
            else:
                ws1.write(row,col+1, '',center)
            # Journal
            if item.journal_id:
                ws1.write(row,col+2, item.journal_id.name,center)
            else:
                ws1.write(row,col+2, '',center)
            # Account
            if item.account_id:
                ws1.write(row,col+3, item.account_id.name,center)
            else:
                ws1.write(row,col+3, '',center)
            # Exp. Date
            if item.exp_date_today:
                ws1.write(row,col+4, item.exp_date_today.strftime('%d/%m/%Y'),center)
            else:
                ws1.write(row,col+4, '',center)
            # 1 - 30
            ws1.write(row,col+5, self.float_format(item.delay_1_30),right)
            # 31 - 60
            ws1.write(row,col+6, self.float_format(item.delay_31_60),right)
            # 61 - 90
            ws1.write(row,col+7,self.float_format(item.delay_61_90),right)
            # 91 - 120
            ws1.write(row,col+8,self.float_format(item.delay_91_120),right)
            # Older
            ws1.write(row,col+9,self.float_format(item.delay_older),right)
            # Total
            ws1.write(row,col+10,self.float_format(item.delay_total),right)
            # Total $
            ws1.write(row,col+11,self.float_format(item.delay_total_usd),right)
            # Tasa
            ws1.write(row,col+12,self.float_format(item.rate),right)
            # Abono
            ws1.write(row,col+13,self.float_format(item.amount_payed),right)
            # Abono $
            ws1.write(row,col+14,self.float_format(item.amount_payed_usd),right)
            
            t_1_30 += item.delay_1_30 
            t_31_60 += item.delay_31_60 
            t_61_90 += item.delay_61_90 
            t_91_120 += item.delay_91_120 
            t_older += item.delay_older 
            t_total += item.delay_total 
            t_total_usd += item.delay_total_usd
            t_total_abono += item.amount_payed
            t_total_abono_usd += item.amount_payed_usd

            temp_1_30 += item.delay_1_30 
            temp_31_60 += item.delay_31_60 
            temp_61_90 += item.delay_61_90 
            temp_91_120 += item.delay_91_120 
            temp_older += item.delay_older 
            temp_total += item.delay_total
            temp_total_usd += item.delay_total_usd
            temp_total_abono += item.amount_payed
            temp_total_abono_usd += item.amount_payed_usd

            if counter == 0:
                row += 1
                ws1.write(row,col+5, self.float_format(temp_1_30),right)
                ws1.write(row,col+6, self.float_format(temp_31_60),right)
                ws1.write(row,col+7, self.float_format(temp_61_90),right)
                ws1.write(row,col+8, self.float_format(temp_91_120),right)
                ws1.write(row,col+9, self.float_format(temp_older),right)
                ws1.write(row,col+10, self.float_format(temp_total),right)
                ws1.write(row,col+11, self.float_format(temp_total_usd),right)
                ws1.write(row,col+13,self.float_format(temp_total_abono),right)
                ws1.write(row,col+14,self.float_format(temp_total_abono_usd),right)

        row += 1
        ws1.write(row,col+4, _('Totals...'),right)
        ws1.write(row,col+5, self.float_format(t_1_30),right)
        ws1.write(row,col+6, self.float_format(t_31_60),right)
        ws1.write(row,col+7, self.float_format(t_61_90),right)
        ws1.write(row,col+8, self.float_format(t_91_120),right)
        ws1.write(row,col+9, self.float_format(t_older),right)
        ws1.write(row,col+10, self.float_format(t_total),right)
        ws1.write(row,col+11, self.float_format(t_total_usd),right)
        ws1.write(row,col+13, self.float_format(t_total_abono),right)
        ws1.write(row,col+14, self.float_format(t_total_abono_usd),right)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name': _('Past Due Accounts Receivable Report ')+ fecha +'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.out.invoice',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
