from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import base64
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.tools.float_utils import float_round

class AccountMovePromotions(models.Model):
    _inherit = 'account.move'

    promos = fields.Selection(string='Reason', selection=[('pronto_pago', 'Pronto Pago'), ('super_promo', 'Super Promo'),])
    tipo_doc_promo = fields.Selection(string='Tipo Doc', related='journal_id.tipo_doc')
    