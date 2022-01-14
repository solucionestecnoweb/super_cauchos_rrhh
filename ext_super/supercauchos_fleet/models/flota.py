# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
import json
from datetime import datetime, date, timedelta
import base64
from io import StringIO
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning

import time

class Flota(models.Model):
    _inherit = "fleet.vehicle"

    type_vehicle = fields.Selection(string='Tipo de Transporte', selection=[('propio', 'Propio'), ('externo', 'Externo')], default="propio")

class FlotaCombustible(models.Model):
    _inherit = "fleet.vehicle.log.fuel"

    fuel_type = fields.Selection(string='Tipo de Combustible', selection=[('gasolina', 'Gasolina'), ('gasoil', 'Gasoil')])
    cistern_lts = fields.Float(string='Litros Cisterna')
    vehicle_consume = fields.Float(string='Consumo Vehículo')
    cistern_lts_ava = fields.Float(string='Disponible Litros Cisterna')
    lts_cistern = fields.Float(string='Cisterna Litros')

    @api.onchange('cistern_lts', 'vehicle_consume')
    def _onchange_cistern_lts_ava(self):
        self.cistern_lts_ava = self.cistern_lts - self.vehicle_consume

    @api.onchange('lts_cistern', 'price_per_liter')
    def _onchange_amount(self):
        self.amount = self.lts_cistern * self.price_per_liter

class FlotaMantenimiento(models.Model):
    _inherit = "maintenance.request"

    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Vehicle')
    license_plate = fields.Char(string='License Plate', related='vehicle_id.license_plate')
    mileage = fields.Float(string='Mileage')
    driver_id = fields.Many2one(comodel_name='res.partner', string='Driver')

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        self.driver_id = self.vehicle_id.driver_id.id    

class FlotaOrdenesEntrega(models.Model):
    _inherit = 'stock.picking'

    fleet_assign = fields.Many2one('fleet.vehicle.log.assignment.control',string='Asignación de Flota', domain="[('status', '=', 'confirmed'), ('date_ini', '<=', scheduled_date), ('date_end', '>=', scheduled_date)]")
    fleet_driver_id = fields.Many2one('res.partner',string='Conductor', related='fleet_assign.driver_id')
    fleet_vehicle_id = fields.Many2one('fleet.vehicle',string='Vehiculo', related='fleet_assign.vehicle_id')
    

class FlotaAsignaciones(models.Model):
    _name = "fleet.vehicle.log.assignment.control"

    name = fields.Char(string='Referencia')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehículo')
    driver_id = fields.Many2one('res.partner', string='Conductor')
    date_ini = fields.Date(string='Desde')
    date_end = fields.Date(string='Hasta')
    duration = fields.Float(string='Duración')
    stock_picking_ids = fields.One2many('stock.picking', 'fleet_assign', string=' Ordenes de Entrega')
    vehicle_odometer_ids = fields.Many2many('fleet.vehicle.odometer', string=' Odómetro del Vehículo', compute='_compute_odometer')
    status = fields.Selection(string='Estado', selection=[('draft', 'Borrador'), ('confirmed', 'Confirmado'), ('done', 'Realizado'), ('cancel', 'Cancelado')], default="draft")

    @api.onchange('vehicle_id')
    def _onchange_driver(self):
        self.driver_id = self.vehicle_id.driver_id

    @api.onchange('date_ini')
    def _onchange_date_from(self):
        if self.date_end:
            self.date_end = False

    @api.onchange('date_end')
    def _onchange_date_to(self):
        if self.date_ini:
            if self.date_end:
                if self.date_end < self.date_ini:
                    raise UserError("El rango de fecha establecido es inválido.\nPor favor ingrese una fecha final que sea mayor a la inicial.")

    @api.constrains('status')
    def _compute_name(self):
        if self.status == 'confirmed' and self.name == False:
            self.name = self.env['ir.sequence'].next_by_code('assignment.fleet.sequence')
        
    def status_draft(self):
        self.status = 'draft'

    def status_confirmed(self):
        self.status = 'confirmed'

    def status_done(self):
        self.status = 'done'

    def status_cancel(self):
        self.status = 'cancel'

    def _compute_odometer(self):
        busqueda = self.env['fleet.vehicle.odometer'].search([
            ('date', '>=', self.date_ini),
            ('date', '<=', self.date_end),
            ('vehicle_id', '=', self.vehicle_id.id),
            ('driver_id', '=', self.driver_id.id)
        ])
        self.vehicle_odometer_ids = busqueda