from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    rate = fields.Float(string='Tasa', default=lambda x: x.env['res.currency.rate'].search([('name', '<=', fields.Date.today()), ('currency_id', '=', 2)], limit=1).sell_rate ,digits=(12, 4))

    def _create_invoices(self, grouped=False, final=False):
        invoice = super(SaleOrder, self)._create_invoices(grouped, final)
        invoice['custom_rate'] = True
        invoice['os_currency_rate'] = self.rate
        invoice['payment_condition_id'] = self.payment_condition_id.id
        invoice['seller_id'] = self.seller_id.id
        return invoice