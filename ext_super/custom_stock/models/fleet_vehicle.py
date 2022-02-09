# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError, except_orm, Warning


class FleetVehicleLogAssigmentControl(models.Model):
    _inherit = 'fleet.vehicle.log.assignment.control'

    delivery_date = fields.Date('Fecha entrega')

    @api.onchange('vehicle_id','date_ini','date_end')
    def _onchange_date_to(self):
        if self.vehicle_id:
            if self.driver_id:
                assig = self.env['fleet.vehicle.log.assignment.control'].search([])
                a = [a.id for a in assig.vehicle_id]
                v = self.env['fleet.vehicle.log.assignment.control'].search([('vehicle_id','in',a),('status','=','confirmed')])
                for item in v:
                    if self.date_end and self.date_ini:
                        if self.date_end <= item.date_end:
                            raise UserError(
                                "El Vehiculo seleccionado '{}' ya está ocupado en ese rango de fechas.\n Seleccione otra fecha o otro vehiculo en la asignación.".format(
                                    ''.join(self.vehicle_id.mapped('name'))))

    def get_user_active(self):
        return self.env['res.users'].browse(self._uid).name