from odoo import api, fields, models
from datetime import datetime, timedelta
import xlsxwriter
import shutil
import base64
import csv
import xlwt


class ProductPricesList(models.Model):
    _inherit = 'product.product'

    prices_list_item_ids = fields.Many2many('product.pricelist.item', string=' Prices', compute='_compute_prices_list_item')

    def _compute_prices_list_item(self):
        for item in self:
            item.prices_list_item_ids = False
            xfind = self.env['product.pricelist.item'].search([])
            for line in xfind:
                if line.applied_on == '3_global':
                    item.prices_list_item_ids += line
                elif line.applied_on == '2_product_category' and item.categ_id in (line.categ_id):
                    item.prices_list_item_ids += line
                elif line.applied_on == '2_product_category' and item.categ_id in (line.categ_id.parent_id):
                    item.prices_list_item_ids += line
                elif line.applied_on == '1_product' and item.product_tmpl_id in (line.product_tmpl_id):
                    item.prices_list_item_ids += line
                elif line.applied_on == '0_product_variant' and item in (line.product_id):
                    item.prices_list_item_ids += line

class TemplatePricesList(models.Model):
    _inherit = 'product.template'

    prices_list_item_ids = fields.Many2many('product.pricelist.item', string=' Prices', compute='_compute_prices_list_item')
    
    def _compute_prices_list_item(self):
        for item in self:
            item.prices_list_item_ids = False
            xfind = self.env['product.pricelist.item'].search([])
            for line in xfind:
                if line.applied_on == '3_global':
                    item.prices_list_item_ids += line
                elif line.applied_on == '2_product_category' and item.categ_id in (line.categ_id):
                    item.prices_list_item_ids += line
                elif line.applied_on == '2_product_category' and item.categ_id in (line.categ_id.parent_id):
                    item.prices_list_item_ids += line
                elif line.applied_on == '1_product' and item in (line.product_tmpl_id):
                    item.prices_list_item_ids += line

class ProductCategory(models.Model):
    _inherit = 'product.category'

    sequence_report = fields.Float(string='Secuencia de lista de precios')

class ProductBrand(models.Model):
    _inherit = 'product.brand'

    sequence_report = fields.Integer(string='Secuencia de lista de precios')
