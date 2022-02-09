# -*- coding: utf-8

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, Warning


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    ultimo_mantenimiento = fields.Integer(string="Ultimo Mantenimiento Preventivo (Km)")
    frecuencia_Mantenimiento = fields.Integer(string='Frecuencia Mantenimiento Preventivo (Km)', default=5000)
    proximo_mantenimiento = fields.Integer(string="Próximo Mantenimiento Preventivo (Km)")
    technician_user_id = fields.Many2one('res.users',string='Técnico asignado')
    type_vehicle = fields.Selection(string='Tipo de Transporte',
                                    selection=[('propio', 'Propio'), ('externo', 'Externo')], default="propio")
    vehicle_filler = fields.Float(string='Filler del Vehículo')


class FleetVehicleLogFuel(models.Model):
    _inherit = 'fleet.vehicle.log.fuel'

    @api.model
    def _default_warehouse_id(self):
        company = self.env.company.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company), ('id', '=', 77)], limit=1)
        return warehouse_ids

    fuel_types = fields.Many2one('product.product', string='Tipo de combustible',
                                 domain=[('product_tmpl_id.categ_id.combustible_check', '=', True)],
                                 help="Se verán reflejados los productos que sean de sean combustible")
    cistern_lts = fields.Float(string='Litros Cisterna')
    vehicle_consume = fields.Float(string='Consumo Vehículo',default=0)
    cistern_lts_ava = fields.Float(string='Disponible Litros Cisterna')
    lts_cistern = fields.Float(string='Cisterna Litros')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    warehouse_id = fields.Many2one('stock.warehouse', string='Bodega', default=_default_warehouse_id, check_company=True)
    number_petition = fields.Char(string='N°')

    @api.model
    def create(self, vals):
        new_id = super(FleetVehicleLogFuel, self).create(vals)
        seq = self.env['ir.sequence'].get('fleet.vehicle.log.fuel')
        new_id.number_petition = seq
        return new_id

    @api.onchange('cistern_lts', 'vehicle_consume')
    def _onchange_cistern_lts_ava(self):
        self.cistern_lts_ava = self.cistern_lts - self.vehicle_consume

    @api.onchange('lts_cistern', 'price_per_liter')
    def _onchange_amount(self):
        self.amount = self.lts_cistern * self.price_per_liter

    @api.constrains('vehicle_consume')
    def fuel_consumption(self):
        stock_producto = self.env['stock.quant'].search([
            ('product_id', '=', self.fuel_types.id),
            ('location_id.usage', '=', 'internal')], order='quantity desc')
        if not len(stock_producto) or 0:
            raise Warning("No hay stock para éste poducto")
        else:
            note = "CONSUMO DE COMBUSTIBLE: {} | DESDE FLOTA POR EL VEHICULO: {} ".format(''.join(self.fuel_types.mapped('name')), self.vehicle_id.name)
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('company_id', '=', self.company_id.id),
                ('warehouse_id', '=', self.warehouse_id.id)], limit=1)
            transfer = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'origin': self.number_petition,
                'location_id': self.warehouse_id.view_location_id.id,
                'location_dest_id': self.env['stock.location'].search([('usage', '=', 'customer')])[0].id,
                'partner_id': self.company_id.partner_id.id,
                'note': note,
                'show_check_availability': False
                })

            transfer['move_lines'] = [(0, 0, {
                'name': note,
                'quantity_done': self.vehicle_consume,
                'product_id': self.fuel_types.id,
                "product_uom": self.fuel_types.product_tmpl_id.uom_id.id,
                "location_id": self.warehouse_id.view_location_id.id,
                "location_dest_id": self.env['stock.location'].search([('usage', '=', 'customer')])[0].id
                })]
            transfer.action_confirm()
            

class FlotaAsignaciones(models.Model):
    _name = "fleet.vehicle.log.assignment.control"

    name = fields.Char(string='Referencia', default='Nuevo')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehículo')
    driver_id = fields.Many2one('res.partner', string='Conductor')
    date_ini = fields.Date(string='Desde')
    date_end = fields.Date(string='Hasta')
    duration = fields.Float(string='Duración')
    stock_picking_ids = fields.One2many('stock.picking', 'fleet_assign', string=' Ordenes de Entrega')
    vehicle_odometer_ids = fields.Many2many('fleet.vehicle.odometer', string=' Odómetro del Vehículo',
                                            compute='_compute_odometer')
    status = fields.Selection(string='Estado', selection=[
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'), ('done', 'Realizado'), ('cancel', 'Cancelado')], default="draft")
    vehicle_filler = fields.Float(string='Filler del Vehículo', related='vehicle_id.vehicle_filler')
    loaded_filler = fields.Float(string='Filler Cargado')

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
                    raise UserError(
                        "El rango de fecha establecido es inválido.\n"
                        "Por favor ingrese una fecha final que sea mayor a la inicial.")

    @api.constrains('status')
    def _compute_name(self):
        if self.name == 'Nuevo':
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
        flee_odometer_obj = self.env['fleet.vehicle.odometer'].search([
            ('date', '>=', self.date_ini),
            ('date', '<=', self.date_end),
            ('vehicle_id', '=', self.vehicle_id.id),
            ('driver_id', '=', self.driver_id.id)
        ])
        self.vehicle_odometer_ids = flee_odometer_obj

    @api.onchange('stock_picking_ids')
    def onchange_filler(self):
        self.calculate_filler()
        
    @api.constrains('stock_picking_ids')
    def constrains_filler(self):
        self.calculate_filler()

    def calculate_filler(self):
        self.loaded_filler = 0
        qty = 0
        for item in self.stock_picking_ids:
            qty += item.filler_per
        if self.vehicle_filler < qty:
            raise ValidationError(f'El cargamento excede la cantidad máxima de filler del vehículo.\nFiller del vehículo: {self.vehicle_filler:.2f}\nFiller Cargado: {qty:.2f}')
        else:
            self.loaded_filler = qty

