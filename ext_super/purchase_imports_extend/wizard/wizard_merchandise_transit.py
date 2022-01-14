from datetime import datetime, timedelta
from itertools import product
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

class MerchandiseTransitTemp(models.Model):
    _name = 'temp.merchandise.transit'

    compra_id = fields.Many2one(comodel_name='purchase.order')
    cantidad = fields.Float()
    unidades_id = fields.Many2one(comodel_name='uom.uom')
    pr = fields.Char()
    producto_id = fields.Many2one(comodel_name='product.product')
    modelo = fields.Char()
    precio = fields.Float()
    pronto_pago = fields.Char()
    super_promo = fields.Char()
    c_apartada = fields.Float()
    amount_ids = fields.Many2many(comodel_name='seller.amount')
    c_disponible = fields.Float()
    moneda_id = fields.Many2one(comodel_name='res.currency')
    fecha_planeada = fields.Datetime()

    # @api.constrains('cantidad','unidades_id','pr','producto_id','modelo','precio','pronto_pago','super_promo','fecha_planeada')
    # def constrains_factura(self):
    #     self.actualizar_datos()

    # def actualizar_datos(self):
    #     purchases = self.env['purchase.order.line'].sudo().search([
    #         ('order_id', '=', self.compra_id.id),
    #     ])
    #     purchases.product_qty = self.cantidad
    #     purchases.product_uom = self.unidades_id.id
    #     purchases.pr = self.pr
    #     purchases.product_id = self.producto_id.id
    #     purchases.modelo = self.modelo
    #     purchases.price_unit = self.precio
    #     purchases.pronto_pago = self.pronto_pago
    #     purchases.super_promo = self.super_promo
    #     purchases.date_planned = self.fecha_planeada

class SellerAmount(models.TransientModel):
    _name = 'seller.amount'

    seller_id = fields.Many2one(comodel_name='res.partner')
    amount = fields.Float(string='amount')
      
class WizardMerchandiseTransit(models.TransientModel):
    _name = 'wizard.merchandise.transit'

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())
    
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=60)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.user.company_id.id)

    line_ids = fields.Many2many(comodel_name='temp.merchandise.transit')
    
    def date_fix(self):
        new_date = self.date_now - timedelta(hours=4)
        return new_date
        
    def print_pdf(self):
        self.get_data()
        return {'type': 'ir.actions.report','report_name': 'purchase_imports_extend.merchandise_in_transit','report_type':"qweb-pdf"}
    
    def get_merchandise(self):
        xfind = self.env['purchase.order.line'].sudo().search([
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('state', 'in', ('draft', 'sent', 'purchase')),
            ('qty_received', '=', 0),
            ('company_id.imports_company', '=', True),
            ('order_id.purchase_type', '=', 'international')
        ])
        return xfind

    def get_data(self):
        t = self.env['temp.merchandise.transit']
        q = self.env['seller.amount']
        t.search([]).unlink()
        product = ''
        cantidad = 0
        cantidad_dis = 0
        amounts = []
        regs = len(self.get_merchandise())
        for item in self.get_merchandise().sorted(key= lambda x: x.product_id.id):
            regs -= 1
            if product != item.product_id.id:
                
                product = item.product_id.id
                orden = item.order_id.id
                unidades = item.product_uom.id
                pr = item.pr
                modelo = item.product_id.modelo
                precio = item.price_unit
                pronto_pago = item.pronto_pago
                super_promo = item.super_promo
                cantidad_apa = item.apart_to_seller
                moneda = item.currency_id.id
                fecha_plan = item.date_planned

                ### Cantidad
                cfind = self.env['purchase.order.line'].sudo().search([
                    ('date_order', '>=', self.date_from),
                    ('date_order', '<=', self.date_to),
                    ('state', 'in', ('draft', 'sent', 'purchase')),
                    ('qty_received', '=', 0),
                    ('company_id.imports_company', '=', True),
                    ('product_id', '=', product),
                    ('order_id.purchase_type', '=', 'international')
                ])
                for line in cfind:
                    cantidad += item.product_qty
                    cantidad_dis += item.product_qty
                    
                ### Apartado por Vendedor
                xfind = self.env['sale.order.line'].sudo().search([
                    ('state', 'in', ('draft', 'sent')),
                    ('product_id', '=', product),
                    ('is_transit_merch', '=', True),
                    ('order_id.seller_id', '!=', False),
                ])
                seller_n = ''
                ### Vendedores
                for seller in xfind.sorted(key=lambda x: x.order_id.seller_id.id):
                    amount = 0
                    if seller_n != seller.order_id.seller_id.id:
                        seller_n = seller.order_id.seller_id.id
                        ### Cantidad Apartada
                        sfind = self.env['sale.order.line'].sudo().search([
                            ('state', 'in', ('draft', 'sent')),
                            ('product_id', '=', product),
                            ('is_transit_merch', '=', True),
                            ('order_id.seller_id', '=', seller_n),
                        ])
                        for line in sfind:
                            amount += line.product_uom_qty
                        val = {
                            'seller_id': seller_n,
                            'amount': amount
                        }
                        amounts.append(q.create(val).id)
                values = {
                    'compra_id': orden,
                    'cantidad': cantidad,
                    'unidades_id': unidades,
                    'pr': pr,
                    'producto_id': product,
                    'modelo': modelo,
                    'precio': precio,
                    'pronto_pago': pronto_pago,
                    'super_promo': super_promo,
                    'c_apartada': cantidad_apa,
                    'amount_ids': amounts,
                    'c_disponible': (cantidad_dis - cantidad_apa),
                    'moneda_id': moneda,
                    'fecha_planeada': fecha_plan,
                }
                t.create(values)
                cantidad = 0
                cantidad_dis = 0
                amounts = []
            
            
        self.line_ids = t.search([])
        
    def show_list(self):
        self.get_data()
        return {
            "type": "ir.actions.act_window",
            "res_model": "temp.merchandise.transit",
            "views": [[self.env.ref('purchase_imports_extend.imports_merchandise_transit_view_tree').id, "tree"],[False, "form"]],
            "name": "Mercancía en Tránsito",
        }