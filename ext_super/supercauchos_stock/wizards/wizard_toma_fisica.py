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

class TomaFisica(models.TransientModel):
    _name = "stock.wizard.toma.fisica"

    # date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    # date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())
    warehouse = fields.Many2one('stock.warehouse', string='Almacen')
    category_id = fields.Many2many(comodel_name='product.category', string='Categoría')

    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=40)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.user.company_id.id)

    def print_inventario(self):
        return {'type': 'ir.actions.report','report_name': 'supercauchos_stock.inventario_toma_fisica','report_type':"qweb-pdf"}

    def _get_products(self):
        categ = []
        temp = []
        for item in self.category_id:
            if item.parent_id:
                temp.append(item.id)
            else:
                xfind = self.env['product.category'].search([('parent_id', '=', item.id)])
                for line in xfind:
                    temp.append(line.id)
        temp = set(temp)
        for item in temp:
            categ.append(item)
        
        if categ != [] and self.warehouse:
            xfind = self.env['product.product'].search([
                ('warehouse_id', '=', self.warehouse),
                ('type', '=', 'product'),
                ('categ_id', 'in', categ)
            ])
        elif categ != []:
            xfind = self.env['product.product'].search([
                ('type', '=', 'product'),
                ('categ_id', 'in', categ)
            ])
        elif self.warehouse:
            xfind = self.env['product.product'].search([
                ('warehouse_id', '=', self.warehouse),
                ('type', '=', 'product'),
            ])
        else:
            xfind = self.env['product.product'].search([
                ('type', '=', 'product'),
            ])
        return xfind

    def _get_orders(self, product_id):
        if self.warehouse:
            xfind = self.env['stock.picking'].search([
                ('product_id', '=', product_id),
                ('picking_type_id.code', '=', 'outgoing'),
                ('location_dest_id.usage', '=', 'customer'),
                ('state','=','done'),
                ('move_ids_without_package.product_id.warehouse_id', '=', self.warehouse)
            ])
        else:
            xfind = self.env['stock.picking'].search([
                ('product_id', '=', product_id),
                ('picking_type_id.code', '=', 'outgoing'),
                ('location_dest_id.usage', '=', 'customer'),
                ('state','=','done')
            ])
        return xfind

    def _not_dispatched(self, product_id):
        if self.warehouse:
            xfind = self.env['stock.picking'].search([
                ('product_id', '=', product_id),
                ('picking_type_id.code', '=', 'outgoing'),
                ('location_dest_id.usage', '=', 'customer'),
                ('state','in',('waiting', 'confirmed', 'assigned')),
                ('move_ids_without_package.product_id.warehouse_id', '=', self.warehouse)
            ])
        else:
            xfind = self.env['stock.picking'].search([
                ('product_id', '=', product_id),
                ('picking_type_id.code', '=', 'outgoing'),
                ('location_dest_id.usage', '=', 'customer'),
                ('state','in',('waiting', 'confirmed', 'assigned'))
            ])
        return xfind

    def _initial_stock(self, product_id):
        product_id.ver_kardex()
        xdate = self.date_now.month
        xdate = str(self.date_now.year) + '-' + str(xdate) + '-01' 
        xfind = self.env['product.product.kardex.line'].search([('name', '=', product_id.id), ('fecha', '<', xdate)], limit=1, order='fecha desc, id desc')
        if len(xfind) == 0:
            xdate = self.date_now.month + 1
            years = self.date_now.year
            if xdate == 13:
                xdate = 1
                years += 1
            xdate = str(years) + '-' + str(xdate) + '-01' 
            xfind = self.env['product.product.kardex.line'].search([('name', '=', product_id.id), ('fecha', '<', xdate)], limit=1, order='fecha asc, id asc')
        
        return xfind

    # *******************  REPORTE EN EXCEL ****************************

    def generate_xls_report(self):

        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet('Toma Física')
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
        ws1.write_merge(row,row, 3, 6, "Toma Física de Inventario", header_content_style)
        xdate = self.date_now.strftime('%d/%m/%Y %I:%M:%S %p')
        xdate = datetime.strptime(xdate,'%d/%m/%Y %I:%M:%S %p') - timedelta(hours=4)
        ws1.write_merge(row,row, 7, 9, xdate.strftime('%d/%m/%Y %I:%M:%S %p'), header_content_style)
        row += 2
        ws1.write(row, 3, "Deposito:", sub_header_style_r)
        ws1.col(3).width = int((len('Deposito: ')+8)*256)
        ws1.write_merge(row, row, 4, 6,  self.warehouse.name, sub_header_content_style)
        row += 2

        #CABECERA DE LA TABLA 
        ws1.write(row,col+0,"Categoría",sub_header_style_c)
        ws1.col(col+0).width = int((len('Categoría')+16)*256)
        ws1.write(row,col+1,"Código",sub_header_style_c)
        ws1.write(row,col+2,"Descripción",sub_header_style_c)
        ws1.col(col+2).width = int((len('Descripción')+36)*256)
        ws1.write(row,col+3,"Modelo",sub_header_style_c)
        ws1.col(col+3).width = int((len('Modelo')+15)*256)
        ws1.write(row,col+4,"Marca",sub_header_style_c)
        ws1.write(row,col+5,"Lonas",sub_header_style_c)
        ws1.col(col+5).width = int((len('Lonas')+2)*256)

        ws1.write(row,col+6,"Stock Inicial",sub_header_style_c)
        ws1.col(col+6).width = int(len('Stock Inicial')*256)
        ws1.write(row,col+7,"Pedido Cliente",sub_header_style_c)
        ws1.col(col+7).width = int(len('Pedido Cliente')*256)
        ws1.write(row,col+8,"No Despachado",sub_header_style_c)
        ws1.col(col+8).width = int((len('No Despachado')+2)*256)
        ws1.write(row,col+9,"FillerT",sub_header_style_c)
        ws1.col(col+9).width = int(len('FillerT')*256)
        ws1.write(row,col+10,"Stock Final",sub_header_style_c)
        ws1.col(col+10).width = int(len('Stock Final')*256)
        ws1.write(row,col+11,"Conteo Físico",sub_header_style_c)
        ws1.col(col+11).width = int(len('Conteo Físico')*256)

        center = xlwt.easyxf("align: horiz center")
        right = xlwt.easyxf("align: horiz right")


        for product in self._get_products():
            row += 1
            # Code
            if product.categ_id:
                ws1.write(row,col+0, product.categ_id.name,center)
            else:
                ws1.write(row,col+0, '',center)
            # Code
            if product.default_code:
                ws1.write(row,col+1, product.default_code,center)
            else:
                ws1.write(row,col+1, '',center)
            # Description
            if product.name:
                ws1.write(row,col+2, product.name,center)
            else:
                ws1.write(row,col+2, product.name,center)
            # Model
            if product.modelo:
                ws1.write(row,col+3, product.modelo,center)
            else:
                ws1.write(row,col+3, '',center)
            # Brand
            if product.brand_id:
                ws1.write(row,col+4, product.brand_id.name,center)
            else:
                ws1.write(row,col+4, '',center)
            # Tarps
            if product.tarps == 0:
                ws1.write(row,col+5,'N/A',center)
            else :
                ws1.write(row,col+5,product.tarps,center)
            # Initial Stock
            stock_ini = 0
            for item in self._initial_stock(product):
                stock_ini = item.total
            ws1.write(row,col+6,stock_ini,center)
            # Client Order
            total_order = 0
            for item in self._get_orders(product.id).move_ids_without_package:
                total_order = total_order + item.quantity_done
            ws1.write(row,col+7, total_order,center)
            # Not Dispatched Order
            total_not_dis = 0
            for item in self._not_dispatched(product.id).move_ids_without_package:
                total_not_dis = total_not_dis + item.product_uom_qty
            ws1.write(row,col+8, total_not_dis,center)
            # FillerT
            if total_not_dis == 0:
                ws1.write(row,col+9, round(product.filler, 3),center)
            else:
                ws1.write(row,col+9, round(product.filler * total_not_dis, 3),center)
            # Final Stock
            ws1.write(row,col+10, product.qty_available,center)
            # Physical Count
            ws1.write(row,col+11, product.physical_count,center)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name':'Toma física de inventario '+ fecha+'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.wizard.toma.fisica',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

        