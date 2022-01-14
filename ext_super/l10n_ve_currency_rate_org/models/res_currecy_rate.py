# -*- coding: utf-8 -*-
from odoo import models, fields, api
from bs4 import BeautifulSoup
from datetime import date
from datetime import datetime
from pytz import timezone
from odoo.tools.translate import _
import requests

class ResCurrencyRateServer(models.Model):

    _name = "res.currency.rate.server"

    name = fields.Many2one(comodel_name='res.currency', string='Money')
    server = fields.Selection(string='Server', selection=[
        ('BCV', 'Banco Central de Venezuela'),
        ('dolar-today', 'DolarToday'),
        ('sunacrip', 'SUNACRIP'),])

    res_currency = fields.Many2many( comodel_name='res.currency.rate',
                                    compute='_compute_res_currency',
                                    string='Rate')

    @api.model
    def _compute_res_currency(self):
        for item in self:
            temp = self.env['res.currency.rate'].search([
                ('currency_id','=',item.name.id)
            ])
            item.res_currency = temp

    def sunacrip(self):

        headers = {'Content-type': 'application/json'}
        data = '{"coins":["' + self.name.name + '"], "fiats":["USD"]}'
        response = requests.post('https://petroapp-price.petro.gob.ve/price/',headers=headers,data=data)
        var = response.json()

        if var['status'] == 200 and var['success'] == True:
            var = float(var['data']['' + self.name.name + '']['USD'])
            return var
        else:
            return False

    def central_bank(self):
        url = "http://www.bcv.org.ve/"
        req = requests.get(url)

        status_code = req.status_code
        if status_code == 200:

            html = BeautifulSoup(req.text, "html.parser")
            # Dolar
            dolar = html.find('div', {'id': 'dolar'})
            dolar = str(dolar.find('strong')).split()
            dolar = str.replace(dolar[1], '.', '')
            dolar = float(str.replace(dolar, ',', '.'))
            # Euro
            euro = html.find('div', {'id': 'euro'})
            euro = str(euro.find('strong')).split()
            euro = str.replace(euro[1], '.', '')
            euro = float(str.replace(euro, ',', '.'))

            if self.name.name == 'USD':
                bcv = dolar
            elif self.name.name == 'EUR':
                bcv = euro
            else:
                bcv = False

            return bcv
        else:
            return False

    def dtoday(self):
        url = "https://s3.amazonaws.com/dolartoday/data.json"
        response = requests.get(url)
        status_code = response.status_code

        if status_code == 200:
            response = response.json()
            usd = float(response['USD']['transferencia'])
            eur = float(response['EUR']['transferencia'])

            if self.name.name == 'USD':
                data = usd
            elif self.name.name == 'EUR':
                data = eur
            else:
                data = False

            return data
        else:
            return False

    def set_rate(self):
        if self.server == 'BCV':
            currency = self.central_bank()
        elif self.server == 'dolar-today':
            currency = self.dtoday()
        elif self.server == 'sunacrip':
            currency = self.sunacrip()
        else:
            return False
        rate = self.env['res.currency.rate'].search([('name','=',datetime.now()) ,('currency_id','=',self.name.id)])
        if len(rate) == 0: 
            self.env['res.currency.rate'].create({
                'currency_id': self.name.id,
                'name': datetime.now(),
                'sell_rate':  round(currency, 2),
                'rate': 1 / round(currency, 2)
            })
        else :
            rate.rate = 1 / round(currency, 2)
            rate.sell_rate = round(currency, 2)
        if self.name.id == 2:
            self.update_product(round(currency, 2))
    
    def update_product(self,currency):

        product = self.env['product.template'].search([('list_price_usd','>',0)])
        for item in product:
            item.list_price = item.list_price_usd * currency
        
        product_attribute = self.env['product.template.attribute.value'].search([])
        for item in product_attribute:
            item.price_extra = item.list_price_usd * currency

    
    @api.model
    def _cron_update_product(self):
        update = self.env['res.currency.rate.server'].search([])
        for item in update:
            item.set_rate()

class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    sell_rate = fields.Float(string='Tasa de Cambio', digits=(12, 4))

    @api.constrains("sell_rate")
    def set_sell_rate(self):
        self.rate = 1 / self.sell_rate
        
    def get_systray_dict(self, date):
        from datetime import datetime
        tz_name = "America/Lima"
        today_utc =  datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
        context_today = today_utc.astimezone(timezone(tz_name))
        date = context_today.strftime("%Y-%m-%d")
        # date = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
        rate = self.env['res.currency.rate'].search([('currency_id', '=', 2),('name','=',date)], limit=1).sorted(lambda x: x.name)
        if rate:
            exchange_rate =  1 / rate.rate
            return {'date': _('Date : ') + rate.name.strftime("%d/%m/%Y"), 'rate': "Bs/USD: "+ str("{:,.2f}".format(exchange_rate))  }
        else:
            return {'date': _('No currency rate for ') + context_today.strftime("%d/%m/%Y"), 'rate': 'N/R'}