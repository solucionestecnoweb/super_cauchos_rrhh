# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockLocationRoute(models.Model):
    _inherit = "stock.location.route"
    maintenance_selectable = fields.Boolean("Selectable in the maintenance line")


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    maintenance_id = fields.Many2one('maintenance.request', ' Maintenance')


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_custom_move_fields(self):
        fields = super(StockRule, self)._get_custom_move_fields()
        fields += ['maintenance_line_id']
        return fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    maintenance_id = fields.Many2one(related="group_id.maintenance_id", string="Maintenance", store=True,
                                     readonly=False)
    fleet_assign = fields.Many2one('fleet.vehicle.log.assignment.control', string='Asignación de Flota',
                                   domain=[('status', '=', 'confirmed')])
    fleet_driver_id = fields.Many2one('res.partner', string='Conductor', related='fleet_assign.driver_id')
    fleet_vehicle_id = fields.Many2one('fleet.vehicle', string='Vehiculo', related='fleet_assign.vehicle_id')


class StockMove(models.Model):
    _inherit = "stock.move"
    maintenance_line_id = fields.Many2one('maintenance.line.request', 'Maintenance Line', index=True)

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
        distinct_fields.append('maintenance_line_id')
        return distinct_fields

    @api.model
    def _prepare_merge_move_sort_method(self, move):
        move.ensure_one()
        keys_sorted = super(StockMove, self)._prepare_merge_move_sort_method(move)
        keys_sorted.append(move.maintenance_line_id.id)
        return keys_sorted

    def _assign_picking_post_process(self, new=False):
        super(StockMove, self)._assign_picking_post_process(new=new)
        if new:
            picking_id = self.mapped('picking_id')
            maintenance_ids = self.mapped('maintenance_line_id.maintenance_id')
            for maintenance_id in maintenance_ids:
                picking_id.message_post_with_view(
                    'mail.message_origin_link',
                    values={'self': picking_id, 'origin': maintenance_id},
                    subtype_id=self.env.ref('mail.mt_note').id)