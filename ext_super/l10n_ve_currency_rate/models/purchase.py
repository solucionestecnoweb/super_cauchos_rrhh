from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_view_invoice(self):
        data = super(PurchaseOrder, self).action_view_invoice()
        data['context']['default_os_currency_rate'] = self.rate
        data['context']['default_custom_rate'] = True
        return data