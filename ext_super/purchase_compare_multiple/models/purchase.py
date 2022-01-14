from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, date


class PurchaseCompareMultiple(models.Model):
    _name = 'purchase.compare.multiple'
    _description = 'Model for comparations of multiple purchase order prices'

    name = fields.Char(string='Reference', default='/', copy=False)
    purchase_order_ids = fields.Many2many(comodel_name='purchase.order', string='Purchase Orders')
    purchase_compared_prices_ids = fields.One2many(comodel_name='purchase.compared.prices', inverse_name='purchase_compare_multiple_id', string='Purchase Compared Prices')
    state = fields.Selection(string='State', selection=[('draft', 'Draft'), ('done', 'Done'), ('cancel', 'Cancel')], default='draft', copy=False)
    currency_bs = fields.Many2one(comodel_name='res.currency', string='Bs.', default=lambda self: self.env.user.company_id.currency_id)
    currency_usd = fields.Many2one(comodel_name='res.currency', string='$', default=2)
    
    
    def state_draft(self):
        self.state = 'draft'

    def state_done(self):
        self.state = 'done'

    def state_cancel(self):
        self.state = 'cancel'

    @api.constrains('state')
    def _compute_name(self):
        if self.name == '/':
            self.name = self.env['ir.sequence'].next_by_code('purchase.compare.multiple.sequence')
    
    def _return_date_today(self):
        today_date = datetime.now() - timedelta(hours=4)
        return today_date
    
    def compare_price(self):
        if len(self.purchase_order_ids) != 3:
            raise ValidationError(_("There must be three records in the purchase orders to be able to compare"))
        else:
            t = self.env['purchase.compared.prices.lines']
            t.search([]).unlink()
            for item in self.purchase_order_ids: #Inicia el ciclo para comparar precios
                for line in item.order_line: #Ubica en las lineas de productos
                    values = {
                        'product_id': line.product_id.id,
                        'provider_id': item.partner_id.id,
                        'qty': line.product_qty,
                        'price': line.price_unit,
                        'currency_id': line.currency_id.id,
                        'rate': item.rate
                    }
                    t.create(values)
            self._compare_lines()

    def _compare_lines(self):
        self.env['purchase.compared.prices'].search([('purchase_compare_multiple_id', '=', self.id)]).unlink()
        xfind = self.env['purchase.compared.prices.lines'].search([])

        provider_l = 0
        qtyl = 0
        price_l = 0
        currency_l = 0
        rate_l = 0

        provider_m = 0
        qtym = 0
        price_m = 0
        currency_m = 0
        rate_m = 0

        provider_h = 0
        qtyh = 0
        price_h = 0
        currency_h = 0
        rate_h = 0

        product_temporal = ''

        for item in xfind.sorted(key=lambda a: a.product_id.id): #Recorremos las lineas y asignamos valor a las variables
            #Evaluación de Registro de Lineas

            provider_l = 0
            price_l = 0
            currency_l = 0
            provider_m = 0
            price_m = 0
            currency_m = 0
            provider_h = 0
            price_h = 0
            currency_h = 0

            temp_currency = 0
            temp_price1 = 0
            temp_price2 = 0
            temp_price3 = 0
            temp_price4 = 0
            if product_temporal != item.product_id.id: #Aseguramos si cambio de producto
                product_temporal = item.product_id.id #Asignamos nuevo producto

                pfind = self.env['purchase.compared.prices.lines'].search([('product_id', '=', product_temporal)])
                
                for line in pfind:
                    if line.currency_id.id == 3:
                        if line.currency_id.id == currency_l or currency_l == 0:
                            temp_price1 = line.price
                        else:
                            temp_price2 = line.price / line.rate
                    else:
                        if line.currency_id.id == currency_l or currency_l == 0:
                            temp_price1 = line.price
                        else:
                            temp_price2 = line.price * line.rate

                    if line.currency_id.id == 3:
                        if line.currency_id.id == currency_h or currency_h == 0:
                            temp_price3 = line.price
                        else:
                            temp_price4 = line.price / line.rate
                    else:
                        if line.currency_id.id == currency_h or currency_h == 0:
                            temp_price3 = line.price
                        else:
                            temp_price4 = line.price * line.rate
                    

                    #Comparativa de precios
                    
                    if currency_l == 3:
                        if temp_price1 == price_l and temp_price3 == price_h:
                            price_h = line.price
                            provider_h = line.provider_id.id
                            qtyh = line.qty
                            currency_h = line.currency_id.id
                            rate_h = line.rate                            
                    else:
                        if temp_price2 == price_l and temp_price4 == price_h:
                            price_h = line.price
                            provider_h = line.provider_id.id
                            qtyh = line.qty
                            currency_h = line.currency_id.id
                            rate_h = line.rate


                    if currency_l == line.currency_id.id or currency_l == 0:
                        if temp_price1 < price_l or price_l == 0:
                            price_l = line.price
                            provider_l = line.provider_id.id
                            qtyl = line.qty
                            currency_l = line.currency_id.id
                            rate_l = line.rate
                    else:
                        if temp_price2 < price_l or price_l == 0:
                            price_l = line.price
                            provider_l = line.provider_id.id
                            qtyl = line.qty
                            currency_l = line.currency_id.id
                            rate_l = line.rate

                    if currency_h == line.currency_id.id or currency_h == 0:
                        if temp_price3 > price_h or price_h == 0:
                            price_h = line.price
                            provider_h = line.provider_id.id
                            qtyh = line.qty
                            currency_h = line.currency_id.id
                            rate_h = line.rate
                    else:
                        if temp_price4 > price_h or price_h == 0:
                            price_h = line.price
                            provider_h = line.provider_id.id
                            qtyh = line.qty
                            currency_h = line.currency_id.id
                            rate_h = line.rate

                #Calculo de precio promedio
                if price_m == 0:
                    price_count = 0
                    find_lines = self.env['purchase.compared.prices.lines'].search([('product_id', '=', product_temporal)])
                    for line in find_lines:
                        price_count += line.price
                    price_count = price_count / len(find_lines)
                    find_mid_price = self.env['purchase.compared.prices.lines'].search([('product_id', '=', product_temporal), ('provider_id', 'not in', (provider_l,provider_h))], limit=1)
                    for lines in find_mid_price:
                        price_m = lines.price
                        provider_m = lines.provider_id.id
                        qtym = lines.qty
                        currency_m = lines.currency_id.id
                        rate_m = lines.rate

                values ={
                    'product_id': product_temporal,
                    'provider_id1': provider_l,
                    'qty1': qtyl,
                    'price1': price_l,
                    'currency_id1': currency_l,
                    'rate1': rate_l,
                    'provider_id2': provider_m,
                    'qty2': qtym,
                    'price2': price_m,
                    'currency_id2': currency_m,
                    'rate2': rate_m,
                    'provider_id3': provider_h,
                    'qty3': qtyh,
                    'price3': price_h,
                    'currency_id3': currency_h,
                    'rate3': rate_h,
                    'purchase_compare_multiple_id': self.id,
                }
                self.env['purchase.compared.prices'].create(values)     

class PurchaseComparedPrices(models.Model):
    _name = 'purchase.compared.prices'

    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    provider_id1 = fields.Many2one(comodel_name='res.partner', string='Provider')
    qty1 = fields.Integer(string='Quantity')
    price1 = fields.Float(string='Lower price')
    currency_id1 = fields.Many2one(comodel_name='res.currency', string='Currency')
    rate1 = fields.Float(string='Rate')
    provider_id2 = fields.Many2one(comodel_name='res.partner', string='Provider')
    qty2 = fields.Integer(string='Quantity')
    price2 = fields.Float(string='Half price')
    currency_id2 = fields.Many2one(comodel_name='res.currency', string='Currency')
    rate2 = fields.Float(string='Rate')
    provider_id3 = fields.Many2one(comodel_name='res.partner', string='Provider')
    qty3 = fields.Integer(string='Quantity')
    price3 = fields.Float(string='Higher price')
    currency_id3 = fields.Many2one(comodel_name='res.currency', string='Currency')
    rate3 = fields.Float(string='Rate')
    purchase_compare_multiple_id = fields.Many2one(comodel_name='purchase.compare.multiple', string='Purchase Compare')

class PurchaseComparedPricesLines(models.Model):
    _name = 'purchase.compared.prices.lines'

    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    provider_id = fields.Many2one(comodel_name='res.partner', string='Provider')
    qty = fields.Integer(string='Quantity')
    price = fields.Float(string='Price')
    currency_id = fields.Many2one('res.currency', string='Currency')
    rate = fields.Float(string='Rate')
    
