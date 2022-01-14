from operator import index
from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import base64
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.tools.float_utils import float_round

class AccountMoveInvoicePayment(models.Model):
    _inherit = 'account.move.line'

    exp_date_today = fields.Date(string='Exp. Date', compute='_compute_delay', index=True)
    delay_1_30 = fields.Float(string='1 - 30')
    delay_31_60 = fields.Float(string='31 - 60')
    delay_61_90 = fields.Float(string='61 - 90')
    delay_91_120 = fields.Float(string='91 - 120')
    delay_older = fields.Float(string='Older')
    delay_total = fields.Float(string='Total')
    delay_total_usd = fields.Float(string='Total $')
    rate = fields.Float(string='Tasa', related='move_id.os_currency_rate')
    amount_payed = fields.Float(string='Abono')
    amount_payed_usd = fields.Float(string='Abono $')
    seller_id = fields.Many2one(comodel_name='res.partner', string='Seller')
    seller_true = fields.Boolean(compute='_compute_seller')
    
    def _compute_seller(self):
        for item in self:
            if item.seller_id:
                item.seller_true = True
            else:
                item.seller_id = item.move_id.seller_id.id
                item.seller_true = False

    @api.onchange('move_id')
    def _onchange_seller(self):
        self.seller_id = self.move_id.seller_id.id

    ### Compute Functions ###
    def _compute_delay(self):
        for item in self:
            item.exp_date_today = fields.Date.today()
            item.delay_1_30 = 0
            item.delay_31_60 = 0
            item.delay_61_90 = 0
            item.delay_91_120 = 0
            item.delay_older = 0
            item.delay_total = 0
            item.delay_total_usd = 0
            item.amount_payed = 0
            item.amount_payed_usd = 0
            n_delay = 0
            amount = item.debit + item.credit

            if item.date_maturity and item.exp_date_today:
                #item.amount_residual=item.move_id.amount_residual_signed
                days = (item.exp_date_today - item.date_maturity)
                if days.days >= 0 and days.days <=30:
                    item.delay_1_30 = item.amount_residual
                elif days.days >= 31 and days.days <=60:
                    item.delay_31_60 = item.amount_residual
                elif days.days >= 61 and days.days <=90:
                    item.delay_61_90 = item.amount_residual
                elif days.days >= 91 and days.days <=120:
                    item.delay_91_120 = item.amount_residual
                elif days.days > 120:
                    item.delay_older = item.amount_residual
                else:
                    n_delay = item.amount_residual

                if item.move_id.currency_id.id == 3:
                    item.amount_payed = amount - item.amount_residual
                    item.amount_payed_usd = (amount - item.amount_residual) / item.rate
                else:
                    item.amount_payed = (amount - item.amount_residual) * item.rate
                    item.amount_payed_usd = amount - item.amount_residual
                item.delay_total = item.delay_1_30 + item.delay_31_60 + item.delay_61_90 + item.delay_91_120 + item.delay_older + n_delay
                item.delay_total_usd = item.delay_total / item.rate
            else:
                if item.move_id.currency_id.id == 3:
                    item.amount_payed = amount - item.amount_residual
                    item.amount_payed_usd = (amount - item.amount_residual) / item.rate
                else:
                    item.amount_payed = (amount - item.amount_residual) * item.rate
                    item.amount_payed_usd = amount - item.amount_residual
                item.delay_total = item.amount_residual
                item.delay_total_usd = item.delay_total / item.rate

