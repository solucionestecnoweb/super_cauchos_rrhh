from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    def cost_set_currency_usd_id(self):
        usd = self.env.ref('base.USD')
        return usd

    cost_price_usd = fields.Float('coste USD', digits='Product Price', default=0.0, company_dependent=True)
    cost_currency_usd_id = fields.Many2one('res.currency', 'USD', default=cost_set_currency_usd_id)