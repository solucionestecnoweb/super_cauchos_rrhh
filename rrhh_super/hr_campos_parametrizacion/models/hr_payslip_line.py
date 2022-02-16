# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError


class HrPauslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    dias = fields.Char(compute='_compute_dias')


    """@api.depends('quantity', 'amount', 'rate','dias')
    def _compute_total(self):
        for line in self:
            line.total = line.dias*float(line.quantity) * line.amount * line.rate / 100"""

    def _compute_dias(self):
        valor="--"
        for rec in self:
            if rec.code=="BASIC":
                valor=rec.slip_id.days_attended
            if rec.code=='DIADES':
                valor=rec.slip_id.saturdays+rec.slip_id.sundays
            if rec.code=="DIAFE":
                valor=rec.slip_id.holydays
            if rec.code=="DIAFEL":
                valor=rec.slip_id.hollydays_ftr
            if rec.code=="LPP":
                valor=rec.slip_id.dias_peternidad
            if rec.code=="IRM":
                valor=rec.slip_id.dias_reposo_medico
            if rec.code=="IRML":
                valor=rec.slip_id.dias_reposo_medico_lab
            if rec.code=="PERE":
                valor=rec.slip_id.dias_permiso_remunerado
            if rec.code=="DPREPOS":
                valor=rec.slip_id.dias_pos_natal
            if rec.code=="PNR":
                valor=rec.slip_id.dias_no_remunerado
            if rec.code=="INASIS":
                valor=rec.slip_id.dias_ausencia_injus
            if rec.code=="BOAYEC":
                valor=rec.slip_id.days_attended
            if rec.code=="DSP":
                valor=int(rec.slip_id.dias_pen_d_value)
            rec.dias=str(valor)
            valor="--"