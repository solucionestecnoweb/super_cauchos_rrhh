# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Sucursales(models.Model):
    _name = "res.sucursal"
    
    name = fields.Char('Nombre')
    address = fields.Text('Direccion')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Activa'),
        ('cancel','Cancelado'),
    ], string='Estado', default='draft')

    company_id = fields.Many2one('res.company')


    def action_post(self):
        self.state = 'done'
    
    def action_cancel(self):
        self.state = 'cancel'
    
    def action_draft(self):
        self.state = 'draft'


class ResUser(models.Model):
    _inherit = "res.users"

    sucursal_ids = fields.Many2many('res.sucursal', string='Sucursales')

