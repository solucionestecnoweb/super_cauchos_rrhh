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

class OrdenesSalida(models.TransientModel):
    _name = "stock.wizard.picking" ## = nombre de la carpeta.nombre del archivo deparado con puntos

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())
    warehouse = fields.Many2one('stock.warehouse', string='Almacen')
    
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=50)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.user.company_id.id)

    def print_ordenes(self):
        return {'type': 'ir.actions.report','report_name': 'supercauchos_stock.inventario_picking_salidas','report_type':"qweb-pdf"}

    def _get_pickings(self):
        xfind = self.env['stock.picking'].search([
            ('scheduled_date','>=',self.date_from),
            ('scheduled_date','<=',self.date_to),
            ('picking_type_id.code', '=', 'outgoing'),
            ('location_dest_id.usage', '=', 'customer'),
            ('move_ids_without_package.product_id.warehouse_id', '=', self.warehouse)
        ])
        return xfind
    
    def _get_seller(self, picking):
        xfind = self.env['sale.order'].search([
            ('picking_ids','=', picking)
        ])
        return xfind

    def generate_xls_report(self):

        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet('Ordenes de salida')
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
        ws1.write_merge(row,row, 2, 4, "Ordenes de salida", header_content_style)
        xdate = self.date_now.strftime('%d/%m/%Y %I:%M:%S %p')
        xdate = datetime.strptime(xdate,'%d/%m/%Y %I:%M:%S %p') - timedelta(hours=4)
        ws1.write_merge(row,row, 5, 8, xdate.strftime('%d/%m/%Y %I:%M:%S %p'), header_content_style)
        row += 2
        ws1.write(row, 2, "Deposito:", sub_header_style_r)
        ws1.write_merge(row, row, 3, 4,  self.warehouse.name, sub_header_content_style)
        row += 2

        #CABECERA DE LA TABLA 
        ws1.write(row,col+0,"Cliente",sub_header_style_c)
        ws1.col(col+0).width = int((len('Cliente')+15)*256)
        ws1.write(row,col+1,"Vendedor",sub_header_style_c)
        ws1.col(col+1).width = int((len('Vendedor')+15)*256)
        ws1.write(row,col+2,"Fecha Doc",sub_header_style_c)
        ws1.col(col+2).width = int((len('Fecha Doc')+2)*256)
        ws1.write(row,col+3,"N° Doc",sub_header_style_c)
        ws1.col(col+3).width = int((len('N° Doc')+2)*256)
        ws1.write(row,col+4,"Producto",sub_header_style_c)
        ws1.col(col+4).width = int((len('Producto')+35)*256)

        ws1.write(row,col+5,"Estado",sub_header_style_c)
        ws1.col(col+5).width = int(len('Stock Inicial')*256)
        ws1.write(row,col+6,"Cant. Vend",sub_header_style_c)
        ws1.col(col+6).width = int((len('Cant. Vend')+3)*256)
        ws1.write(row,col+7,"Filler",sub_header_style_c)
        ws1.col(col+7).width = int(len('Filler')*256)
        ws1.write(row,col+8,"FillerT",sub_header_style_c)
        ws1.col(col+8).width = int(len('FillerT')*256)

        center = xlwt.easyxf("align: horiz center")
        right = xlwt.easyxf("align: horiz right")


        for item in self._get_pickings():
            row += 1
            if len(item.move_ids_without_package) > 1:
                more_rows = len(item.move_ids_without_package)
                for line in item.move_ids_without_package:
                    # Client
                    ws1.write(row,col+0, item.partner_id.name,center)
                    # Seller
                    seller = self._get_seller(item.id)
                    ws1.write(row,col+1, seller.user_id.name,center)
                    # Doc Date
                    ws1.write(row,col+2, item.scheduled_date.strftime('%d/%m/%y'),center)
                    # Doc Number
                    ws1.write(row,col+3, item.origin,center)
                    # Product
                    ws1.write(row,col+4,line.product_id.name,center)
                    # State
                    if item.state == 'draft':
                        ws1.write(row,col+5,'Borrador',center)
                    elif item.state == 'waiting':
                        ws1.write(row,col+5,'Esperando otra operación',center)
                    elif item.state == 'confirmed':
                        ws1.write(row,col+5,'En espera',center)
                    elif item.state == 'assigned':
                        ws1.write(row,col+5,'Preparado',center)
                    elif item.state == 'done':
                        ws1.write(row,col+5,'Realizado',center)
                    elif item.state == 'cancel':
                        ws1.write(row,col+5,'Cancelada',center)
                    # Quantity Sell
                    ws1.write(row,col+6, line.quantity_done,center)
                    # Filler
                    ws1.write(row,col+7, round(line.product_id.filler, 3),center)
                    # FillerT
                    ws1.write(row,col+8, round(line.product_id.filler * line.quantity_done, 3),center)
                    if more_rows > 1:
                        row += 1
                        more_rows = more_rows - 1
            else:
                # Client
                ws1.write(row,col+0, item.partner_id.name,center)
                # Seller
                seller = self._get_seller(item.id)
                ws1.write(row,col+1, seller.user_id.name,center)
                # Doc Date
                ws1.write(row,col+2, item.scheduled_date.strftime('%d/%m/%y'),center)
                # Doc Number
                ws1.write(row,col+3, item.origin,center)
                # Product
                ws1.write(row,col+4,item.move_ids_without_package.product_id.name,center)
                # State
                if item.state == 'draft':
                    ws1.write(row,col+5,'Borrador',center)
                elif item.state == 'waiting':
                    ws1.write(row,col+5,'Esperando otra operación',center)
                elif item.state == 'confirmed':
                    ws1.write(row,col+5,'En espera',center)
                elif item.state == 'assigned':
                    ws1.write(row,col+5,'Preparado',center)
                elif item.state == 'done':
                    ws1.write(row,col+5,'Realizado',center)
                elif item.state == 'cancel':
                    ws1.write(row,col+5,'Cancelada',center)
                # Quantity Sell
                ws1.write(row,col+6, item.move_ids_without_package.quantity_done,center)
                # Filler
                ws1.write(row,col+7, round(item.move_ids_without_package.product_id.filler, 3),center)
                # FillerT
                ws1.write(row,col+8, round(item.move_ids_without_package.product_id.filler * item.move_ids_without_package.quantity_done, 3),center)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name':'Ordenes de salida '+ fecha+'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.wizard.picking',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
