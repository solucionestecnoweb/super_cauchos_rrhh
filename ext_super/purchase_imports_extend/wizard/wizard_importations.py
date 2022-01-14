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

class ImportationCycle(models.TransientModel):
    _name = 'wizard.importation.cycle'

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())
    group_field = fields.Selection(string='Group By', selection=[('supplier', 'Supplier'), ('importation_brand', 'Brand'), ('prof', 'Prof'), ('importation_type', 'Type')])
    
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=60)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.user.company_id.id)

    def print_pdf(self):
        return {'type': 'ir.actions.report','report_name': 'purchase_imports_extend.importation_cycle','report_type':"qweb-pdf"}

    def get_imports(self):
        xfind = self.env['purchase.order.imports.importations'].search([
            ('f_prof', '>=', self.date_from),
            ('f_prof', '<=', self.date_to),
        ])
        return xfind

    # *******************  REPORTE EN EXCEL ****************************
    def generate_xls_report(self):

        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet(_('Importation cycle'))
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
        ws1.write_merge(row,row, 4, 9, _("Importation cycle"), header_content_style)
        xdate = self.date_now.strftime('%d/%m/%Y %I:%M:%S %p')
        xdate = datetime.strptime(xdate,'%d/%m/%Y %I:%M:%S %p') - timedelta(hours=4)
        ws1.write_merge(row,row, 10, 13, xdate.strftime('%d/%m/%Y %I:%M:%S %p'), header_content_style)
        row += 2
        ws1.write(row, 5, _("From:"), sub_header_style_r)
        ws1.write(row, 6, self.date_from.strftime('%d/%m/%Y'), sub_header_style_r)
        ws1.write(row, 7, _("To:"), sub_header_style_r)
        ws1.write(row, 8, self.date_to.strftime('%d/%m/%Y'), sub_header_style_r)
        row += 2

        #CABECERA DE LA TABLA 
        ws1.write(row,col+0,_("Supplier"),sub_header_style_c)
        ws1.col(col+0).width = int((len(_('Supplier'))+16)*256)
        ws1.write(row,col+1,_("Brand"),sub_header_style_c)
        ws1.col(col+1).width = int((len(_('Brand'))+16)*256)
        ws1.write(row,col+2,_("Prof"),sub_header_style_c)
        ws1.col(col+2).width = int((len(_('Prof'))+26)*256)
        ws1.write(row,col+3,_("Type"),sub_header_style_c)
        ws1.col(col+3).width = int((len(_('Type'))+15)*256)
        ws1.write(row,col+4,_("F/Prof"),sub_header_style_c)
        ws1.col(col+3).width = int(len(' xx/xx/xxxx ')*256)
        ws1.write(row,col+5,_("Invoice"),sub_header_style_c)
        ws1.col(col+5).width = int((len(_('Invoice'))+10)*256)
        ws1.write(row,col+6,_("Cont"),sub_header_style_c)
        ws1.col(col+6).width = int((len(_('Cont')) + 10)*256)
        ws1.write(row,col+7,_("BL Date"),sub_header_style_c)
        ws1.col(col+7).width = int(len(' xx/xx/xxxx ')*256)
        ws1.write(row,col+8,_("Transc"),sub_header_style_c)
        ws1.col(col+8).width = int((len(_('Transc'))+7)*256)
        ws1.write(row,col+9,_("Accumulated"),sub_header_style_c)
        ws1.col(col+9).width = int((len(_('Accumulated')) + 5)*256)
        ws1.write(row,col+10,_("ETA"),sub_header_style_c)
        ws1.col(col+10).width = int(len(' xx/xx/xxxx ')*256)
        ws1.write(row,col+11,_("Transit"),sub_header_style_c)
        ws1.col(col+11).width = int(len(_('Transit'))*256)
        ws1.write(row,col+12,_("NAC"),sub_header_style_c)
        ws1.col(col+12).width = int((len(_('NAC')) + 3)*256)
        ws1.write(row,col+13,_("Total"),sub_header_style_c)
        ws1.col(col+13).width = int((len(_('Total')) + 5)*256)

        center = xlwt.easyxf("align: horiz center")
        right = xlwt.easyxf("align: horiz right")

        #Totals
        t_cont = 0
        t_accumulated = 0
        t_transit = 0
        t_nac = 0
        t_total = 0

        if self.group_field == 'supplier':
            for item in self.get_imports().sorted(key=lambda x: x.name.id):
                row += 1
                # Supplier
                if item.name:
                    ws1.write(row,col+0, item.name.name,center)
                else:
                    ws1.write(row,col+0, '',center)
                # Brand
                if item.importation_brand:
                    ws1.write(row,col+1, item.importation_brand.name,center)
                else:
                    ws1.write(row,col+1, '',center)
                # Prof
                if item.prof:
                    ws1.write(row,col+2, item.prof,center)
                else:
                    ws1.write(row,col+2, item.name,center)
                # Type
                if item.importation_type:
                    ws1.write(row,col+3, item.importation_type,center)
                else:
                    ws1.write(row,col+3, '',center)
                # Prof Date
                if item.f_prof:
                    ws1.write(row,col+4, item.f_prof.strftime('%d/%m/%Y'),center)
                else:
                    ws1.write(row,col+4, '',center)
                # Invoice
                if item.invoice_id:
                    ws1.write(row,col+5,item.invoice_id.name,center)
                else :
                    ws1.write(row,col+5,'',center)
                # Container
                if item.container:
                    ws1.write(row,col+6,item.container,center)
                else :
                    ws1.write(row,col+6,'',center)
                # BL Date
                if item.bl_date:
                    ws1.write(row,col+7,item.bl_date.strftime('%d/%m/%Y'),center)
                else :
                    ws1.write(row,col+7,'',center)
                # Transac
                if item.transc:
                    ws1.write(row,col+8,item.transc,center)
                else :
                    ws1.write(row,col+8,'',center)
                # Accumulated
                if item.accumulated:
                    ws1.write(row,col+9,item.accumulated,center)
                else :
                    ws1.write(row,col+9,'',center)
                # ETA
                if item.eta:
                    ws1.write(row,col+10,item.eta.strftime('%d/%m/%Y'),center)
                else :
                    ws1.write(row,col+10,'',center)
                # Transit
                if item.transit:
                    ws1.write(row,col+11,item.transit,center)
                else :
                    ws1.write(row,col+11,'',center)
                # NAC
                if item.nac:
                    ws1.write(row,col+12,item.nac,center)
                else :
                    ws1.write(row,col+12,'',center)
                # Total
                if item.total:
                    ws1.write(row,col+13,item.total,center)
                else :
                    ws1.write(row,col+13,'',center)

                t_cont += item.container
                if item.eta:
                    t_accumulated = item.accumulated
                t_transit += item.transit
                t_nac += item.nac
                t_total += item.total
        
        elif self.group_field == 'importation_brand':
            for item in self.get_imports().sorted(key=lambda x: x.importation_brand.id):
                row += 1
                # Supplier
                if item.name:
                    ws1.write(row,col+0, item.name.name,center)
                else:
                    ws1.write(row,col+0, '',center)
                # Brand
                if item.importation_brand:
                    ws1.write(row,col+1, item.importation_brand.name,center)
                else:
                    ws1.write(row,col+1, '',center)
                # Prof
                if item.prof:
                    ws1.write(row,col+2, item.prof,center)
                else:
                    ws1.write(row,col+2, item.name,center)
                # Type
                if item.importation_type:
                    ws1.write(row,col+3, item.importation_type,center)
                else:
                    ws1.write(row,col+3, '',center)
                # Prof Date
                if item.f_prof:
                    ws1.write(row,col+4, item.f_prof.strftime('%d/%m/%Y'),center)
                else:
                    ws1.write(row,col+4, '',center)
                # Invoice
                if item.invoice_id:
                    ws1.write(row,col+5,item.invoice_id.name,center)
                else :
                    ws1.write(row,col+5,'',center)
                # Container
                if item.container:
                    ws1.write(row,col+6,item.container,center)
                else :
                    ws1.write(row,col+6,'',center)
                # BL Date
                if item.bl_date:
                    ws1.write(row,col+7,item.bl_date.strftime('%d/%m/%Y'),center)
                else :
                    ws1.write(row,col+7,'',center)
                # Transac
                if item.transc:
                    ws1.write(row,col+8,item.transc,center)
                else :
                    ws1.write(row,col+8,'',center)
                # Accumulated
                if item.accumulated:
                    ws1.write(row,col+9,item.accumulated,center)
                else :
                    ws1.write(row,col+9,'',center)
                # ETA
                if item.eta:
                    ws1.write(row,col+10,item.eta.strftime('%d/%m/%Y'),center)
                else :
                    ws1.write(row,col+10,'',center)
                # Transit
                if item.transit:
                    ws1.write(row,col+11,item.transit,center)
                else :
                    ws1.write(row,col+11,'',center)
                # NAC
                if item.nac:
                    ws1.write(row,col+12,item.nac,center)
                else :
                    ws1.write(row,col+12,'',center)
                # Total
                if item.total:
                    ws1.write(row,col+13,item.total,center)
                else :
                    ws1.write(row,col+13,'',center)

                t_cont += item.container
                if item.eta:
                    t_accumulated = item.accumulated
                t_transit += item.transit
                t_nac += item.nac
                t_total += item.total
        
        elif self.group_field == 'prof':
            for item in self.get_imports().sorted(key=lambda x: x.prof):
                row += 1
                # Supplier
                if item.name:
                    ws1.write(row,col+0, item.name.name,center)
                else:
                    ws1.write(row,col+0, '',center)
                # Brand
                if item.importation_brand:
                    ws1.write(row,col+1, item.importation_brand.name,center)
                else:
                    ws1.write(row,col+1, '',center)
                # Prof
                if item.prof:
                    ws1.write(row,col+2, item.prof,center)
                else:
                    ws1.write(row,col+2, item.name,center)
                # Type
                if item.importation_type:
                    ws1.write(row,col+3, item.importation_type,center)
                else:
                    ws1.write(row,col+3, '',center)
                # Prof Date
                if item.f_prof:
                    ws1.write(row,col+4, item.f_prof.strftime('%d/%m/%Y'),center)
                else:
                    ws1.write(row,col+4, '',center)
                # Invoice
                if item.invoice_id:
                    ws1.write(row,col+5,item.invoice_id.name,center)
                else :
                    ws1.write(row,col+5,'',center)
                # Container
                if item.container:
                    ws1.write(row,col+6,item.container,center)
                else :
                    ws1.write(row,col+6,'',center)
                # BL Date
                if item.bl_date:
                    ws1.write(row,col+7,item.bl_date.strftime('%d/%m/%Y'),center)
                else :
                    ws1.write(row,col+7,'',center)
                # Transac
                if item.transc:
                    ws1.write(row,col+8,item.transc,center)
                else :
                    ws1.write(row,col+8,'',center)
                # Accumulated
                if item.accumulated:
                    ws1.write(row,col+9,item.accumulated,center)
                else :
                    ws1.write(row,col+9,'',center)
                # ETA
                if item.eta:
                    ws1.write(row,col+10,item.eta.strftime('%d/%m/%Y'),center)
                else :
                    ws1.write(row,col+10,'',center)
                # Transit
                if item.transit:
                    ws1.write(row,col+11,item.transit,center)
                else :
                    ws1.write(row,col+11,'',center)
                # NAC
                if item.nac:
                    ws1.write(row,col+12,item.nac,center)
                else :
                    ws1.write(row,col+12,'',center)
                # Total
                if item.total:
                    ws1.write(row,col+13,item.total,center)
                else :
                    ws1.write(row,col+13,'',center)

                t_cont += item.container
                if item.eta:
                    t_accumulated = item.accumulated
                t_transit += item.transit
                t_nac += item.nac
                t_total += item.total
        
        elif self.group_field == 'importation_type':
            for item in self.get_imports().sorted(key=lambda x: x.importation_type):
                row += 1
                # Supplier
                if item.name:
                    ws1.write(row,col+0, item.name.name,center)
                else:
                    ws1.write(row,col+0, '',center)
                # Brand
                if item.importation_brand:
                    ws1.write(row,col+1, item.importation_brand.name,center)
                else:
                    ws1.write(row,col+1, '',center)
                # Prof
                if item.prof:
                    ws1.write(row,col+2, item.prof,center)
                else:
                    ws1.write(row,col+2, item.name,center)
                # Type
                if item.importation_type:
                    ws1.write(row,col+3, item.importation_type,center)
                else:
                    ws1.write(row,col+3, '',center)
                # Prof Date
                if item.f_prof:
                    ws1.write(row,col+4, item.f_prof.strftime('%d/%m/%Y'),center)
                else:
                    ws1.write(row,col+4, '',center)
                # Invoice
                if item.invoice_id:
                    ws1.write(row,col+5,item.invoice_id.name,center)
                else :
                    ws1.write(row,col+5,'',center)
                # Container
                if item.container:
                    ws1.write(row,col+6,item.container,center)
                else :
                    ws1.write(row,col+6,'',center)
                # BL Date
                if item.bl_date:
                    ws1.write(row,col+7,item.bl_date.strftime('%d/%m/%Y'),center)
                else :
                    ws1.write(row,col+7,'',center)
                # Transac
                if item.transc:
                    ws1.write(row,col+8,item.transc,center)
                else :
                    ws1.write(row,col+8,'',center)
                # Accumulated
                if item.accumulated:
                    ws1.write(row,col+9,item.accumulated,center)
                else :
                    ws1.write(row,col+9,'',center)
                # ETA
                if item.eta:
                    ws1.write(row,col+10,item.eta.strftime('%d/%m/%Y'),center)
                else :
                    ws1.write(row,col+10,'',center)
                # Transit
                if item.transit:
                    ws1.write(row,col+11,item.transit,center)
                else :
                    ws1.write(row,col+11,'',center)
                # NAC
                if item.nac:
                    ws1.write(row,col+12,item.nac,center)
                else :
                    ws1.write(row,col+12,'',center)
                # Total
                if item.total:
                    ws1.write(row,col+13,item.total,center)
                else :
                    ws1.write(row,col+13,'',center)

                t_cont += item.container
                if item.eta:
                    t_accumulated = item.accumulated
                t_transit += item.transit
                t_nac += item.nac
                t_total += item.total
        
        else:
            for item in self.get_imports():
                row += 1
                # Supplier
                if item.name:
                    ws1.write(row,col+0, item.name.name,center)
                else:
                    ws1.write(row,col+0, '',center)
                # Brand
                if item.importation_brand:
                    ws1.write(row,col+1, item.importation_brand.name,center)
                else:
                    ws1.write(row,col+1, '',center)
                # Prof
                if item.prof:
                    ws1.write(row,col+2, item.prof,center)
                else:
                    ws1.write(row,col+2, item.name,center)
                # Type
                if item.importation_type:
                    ws1.write(row,col+3, item.importation_type,center)
                else:
                    ws1.write(row,col+3, '',center)
                # Prof Date
                if item.f_prof:
                    ws1.write(row,col+4, item.f_prof.strftime('%d/%m/%Y'),center)
                else:
                    ws1.write(row,col+4, '',center)
                # Invoice
                if item.invoice_id:
                    ws1.write(row,col+5,item.invoice_id.name,center)
                else :
                    ws1.write(row,col+5,'',center)
                # Container
                if item.container:
                    ws1.write(row,col+6,item.container,center)
                else :
                    ws1.write(row,col+6,'',center)
                # BL Date
                if item.bl_date:
                    ws1.write(row,col+7,item.bl_date.strftime('%d/%m/%Y'),center)
                else :
                    ws1.write(row,col+7,'',center)
                # Transac
                if item.transc:
                    ws1.write(row,col+8,item.transc,center)
                else :
                    ws1.write(row,col+8,'',center)
                # Accumulated
                if item.accumulated:
                    ws1.write(row,col+9,item.accumulated,center)
                else :
                    ws1.write(row,col+9,'',center)
                # ETA
                if item.eta:
                    ws1.write(row,col+10,item.eta.strftime('%d/%m/%Y'),center)
                else :
                    ws1.write(row,col+10,'',center)
                # Transit
                if item.transit:
                    ws1.write(row,col+11,item.transit,center)
                else :
                    ws1.write(row,col+11,'',center)
                # NAC
                if item.nac:
                    ws1.write(row,col+12,item.nac,center)
                else :
                    ws1.write(row,col+12,'',center)
                # Total
                if item.total:
                    ws1.write(row,col+13,item.total,center)
                else :
                    ws1.write(row,col+13,'',center)

                t_cont += item.container
                if item.eta:
                    t_accumulated = item.accumulated
                t_transit += item.transit
                t_nac += item.nac
                t_total += item.total

        row += 1

        ws1.write(row,col+5,_('Totals...'),center)
        ws1.write(row,col+6,t_cont,center)
        ws1.write(row,col+11,t_transit,center)
        ws1.write(row,col+12,t_nac,center)
        ws1.write(row,col+13,t_total,center)

        row += 1
        ws1.write_merge(row,row, 11, 12, t_transit + t_nac, center)

        row += 1
        ws1.write(row,col+0,_('Average Production'),sub_header_style_c)
        ws1.write(row,col+1,round(t_accumulated / t_cont, 2),sub_header_style_c)
        row += 1
        ws1.write(row,col+0,_('Average Transit'),sub_header_style_c)
        ws1.write(row,col+1,round((t_transit + t_nac) / len(self.get_imports()), 2),sub_header_style_c)
        row += 1
        ws1.write(row,col+0,_('Total Average Days'),sub_header_style_c)
        ws1.write(row,col+1,round((t_accumulated / t_cont) + ((t_transit + t_nac) / len(self.get_imports())), 2),sub_header_style_c)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name':_('Importation cycle ')+ fecha+'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.importation.cycle',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

        