# -*- coding: utf-8 -*-


import logging
from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import datetime


class Lead(models.Model):
    _inherit = "crm.lead"

    #company_currency = fields.Many2one('res.currency',string='Currency',default=2)
    company_currency_secundaria = fields.Many2one('res.currency',default=lambda self: self.env.company.currency_secundaria_id.id)
    planned_revenue = fields.Float('Expected Revenue')
    meta_facturacion = fields.Float()
    plazo_meta = fields.Many2one('crm.plazo.meta')
    fecha_cierre_plazo = fields.Datetime(compute='_calculo_cierre')
    #expected_revenue = fields.Float('Prorated Revenue', compute="_compute_expected_revenue")

    #@api.depends('plazo_meta')
    @api.onchange('plazo_meta')
    def _calculo_cierre(self):
        inicio = self.date_open #datetime.datetime.utcnow()
        dias=self.plazo_meta.valor_dias
        futuro = inicio + datetime.timedelta(days=dias)
        self.fecha_cierre_plazo=futuro

class Plazo(models.Model):
    _name = "crm.plazo.meta"

    name = fields.Char(string="Descripción")
    note = fields.Char(string="Nota")
    valor_dias = fields.Integer(string="Valor en Dias")

class CrmTeam(models.Model):
    _inherit="crm.team"

    company_currency_secundaria = fields.Many2one('res.currency',default=lambda self: self.env.company.currency_secundaria_id.id)
    plazo_meta = fields.Many2one('crm.plazo.meta')
    invoiced_target = fields.Float()
    #fecha_cierre_plazo = fields.Datetime()

