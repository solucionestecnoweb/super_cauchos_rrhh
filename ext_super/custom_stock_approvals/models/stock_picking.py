# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import UserError, ValidationError, except_orm, Warning


class Picking(models.Model):
    _inherit = "stock.picking"
    
    approvals_ids = fields.One2many('approval.request', 'picking_id', string='aprobaciones')
    approver_ids = fields.Many2many('res.users', string='Aprobadores')
    is_approval = fields.Boolean(string="Tiene aprobacion")
    
    def approvals_request_picking(self):
        for picking in self:
            if picking.is_approval and not picking.move_ids_without_package:
                raise UserError(
                    "No puede enviar una orden de venta sin lineas de pedidos. Por favor agregue lineas a la orden")
            approvers = len(picking.approver_ids)
            category_obj = self.env['approval.category'].search([('is_picking', '=', 'required')], limit=1)
            if approvers > len(category_obj.user_ids):
                raise UserError(
                    "No puede agregar mas arpobadores de lo estipulado."
                     "Vaya a Aprobaciones / Configuración / Tipo de aprobación.")
            for aproval in picking.approvals_ids:
                if aproval.request_status in ['new', 'pending', 'approved']:
                    raise ValidationError("Existe una aprobacion en curso")
                if aproval.request_status == "refused":
                    raise ValidationError("Verifique si no existe una solicitud Rechazada antes de generar una nueva")
            values = {
                'name': category_obj.name,
                'category_id': category_obj.id,
                'date': datetime.now(),
                'request_owner_id': picking.env.user.id,
                'reference': picking.origin,
                'partner_id': stock.partner_id.id,
                'picking_id': picking.id,
                'request_status': 'pending'
            }
            t = self.env['approval.request'].create(values)
            for item in picking.approver_ids:
                self.env['approval.approver'].create({
                    'user_id': item.id,
                    'request_id': t.id,
                    'status': 'pending'
            })
            if not category_obj:
                raise ValidationError(
                    "No existe una categoría de aprobación para este tipo de registro."
                     "Vaya a Aprobaciones / Configuración / Tipo de aprobación.")
            if len(category_obj) > 2:
                raise ValidationError(
                    "Existe mas de dos categoría de aprobación para este tipo de registro."
                     "Vaya a Aprobaciones / Configuración / Tipo de aprobación.")
            
    def button_validate(self):
        sale_obj = self.env['sale.order'].search([('name', '=', self.origin)])
        purchase_obj = self.env['purchase.order'].search([('name', '=', self.origin)])
        if sale_obj.is_approval:
            if not sale_obj.approvals_ids:
                raise ValidationError(
                    "Disculpe!!! no puede validar la orden si no tiene un aprobacion del Pedido de Venta")
            if sale_obj.approvals_ids.filtered(lambda r: r.request_status == 'approved'):
                pass
            else:
                raise ValidationError("Disculpe!!! no puede validar si la aprobacion del pedido no esta aceptada.")
        if purchase_obj.is_approval:
            if not purchase_obj.approvals_ids:
                raise ValidationError(
                    "Disculpe!!! no puede validar la orden si no tiene un aprobacion del Pedido de Compra")
            if purchase_obj.approvals_ids.filtered(lambda r: r.request_status == 'approved'):
                pass
            else:
                raise ValidationError("Disculpe!!! no puede validar si la aprobacion del pedido no esta aceptada.")
        if self.is_approval:
            for aproval in self.approvals_ids:
                if aproval.request_status not in ['approved']:
                    raise ValidationError("Disculpe!!! No tiene ninguna aprobaciones aceptada")
        return super(Picking, self).button_validate()

