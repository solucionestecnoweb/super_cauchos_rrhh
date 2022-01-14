import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models, _
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning
import time
import json


class Reports(models.Model):
    _inherit ='account.move'

    agent_id = fields.Many2one('res.partner', string="Agente de Ventas")
    team_id = fields.Many2one('crm.team', string="Equipo de Ventas")
    date_due_slack = fields.Date(compute='_compute_due_slack', string='Fecha de Vencimiento con Holgura')
    rate = fields.Float(compute='_compute_rate', string="Tasa")
    amount_currency = fields.Monetary(compute='_compute_amount_currency', currency_field='currency_usd_id')
    currency_bs_id = fields.Many2one('res.currency', string="Moneda", default=lambda self: self.env.user.company_id.currency_id.id)
    currency_usd_id = fields.Many2one('res.currency', string="Moneda", default= lambda self: self.env['res.currency'].search([('id', '=', 2)]))
    days = fields.Integer(compute='_compute_days', string="Días Promedio")
    slack = fields.Integer(compute='_compute_slack', string="Días Promedio sin Holgura")
    street_days = fields.Integer(compute='_compute_street_days', string="Días Calle")
    payment_date = fields.Date(compute='_compute_payment_date', string='Fecha', required=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False, tracking=True)

    def _compute_payment_date(self):
        for item in self:
            item.payment_date = False
            parse_dict = json.loads(item.invoice_payments_widget)
            if parse_dict:
                for pay in parse_dict.get('content'):
                    date = pay['date']
                    print(date)
                item.payment_date = date
        
    def _compute_due_slack(self):
        for item in self:
            item.date_due_slack = item.invoice_date_due

    def _compute_days(self):
        for item in self:
            item.days = 0
            days_value = 0
            date1 = item.invoice_date_due
            date2 = item.payment_date
            if (date1 and date2):
                days_value = abs(date1 - date2).days
            item.days = days_value

    def _compute_slack(self):
        for item in self:
            item.slack = 0
            slack_value = 0
            date1 = item.date_due_slack
            date2 = item.payment_date
            if (date1 and date2):
                slack_value = abs(date1 - date2).days
            item.slack = slack_value

    def _compute_street_days(self):
        for item in self:
            item.street_days = 0
            street_days_value = 0
            date1 = item.invoice_date
            date2 = item.payment_date
            if (date1 and date2):
                street_days_value = abs(date1 - date2).days
            item.street_days = street_days_value

    def _compute_rate(self):
        for item in self:
            rate_value = 1
            rate = item.env['res.currency.rate'].search([('name','=', item.invoice_date)], limit=1).sell_rate
            if rate:
                rate_value = rate
            item.rate = rate_value

    def _compute_amount_currency(self):
        for item in self:
            item.amount_currency = 0
            if (item.currency_usd_id.name == 'USD'):
                item.amount_currency = item.amount_total / item.rate
            if (item.currency_usd_id.name == 'VES'):
                item.amount_currency = item.amount_total * item.rate