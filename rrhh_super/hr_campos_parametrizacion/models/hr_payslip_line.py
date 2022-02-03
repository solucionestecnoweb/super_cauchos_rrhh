# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError


class HrPauslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    dias = fields.Float(default=1)


    @api.depends('quantity', 'amount', 'rate','dias')
    def _compute_total(self):
        for line in self:
            line.total = line.dias*float(line.quantity) * line.amount * line.rate / 100