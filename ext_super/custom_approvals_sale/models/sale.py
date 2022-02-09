# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import UserError, ValidationError, except_orm, Warning


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    approvals_ids = fields.One2many('approval.request', 'sale_id', string='aprobaciones')
    approver_ids = fields.Many2many('res.users', string='Aprobadores')
    is_approval = fields.Boolean(string="Tiene aprobacion")
    
    def approvals_request_sale(self):
        for sale in self:
            if sale.is_approval and not sale.order_line:
                raise UserError(
                    "No puede enviar una orden de venta sin lineas de pedidos. Por favor agregue lineas a la orden")
            approvers = len(sale.approver_ids)
            category_obj = self.env['approval.category'].search([('is_sale', '=', 'required')], limit=1)
            if approvers > len(category_obj.user_ids):
                raise UserError(
                    "No puede agregar mas arpobadores de lo estipulado."
                     "Vaya a Aprobaciones / Configuración / Tipo de aprobación.")
            for aproval in sale.approvals_ids:
                if aproval.request_status in ['new', 'pending', 'approved']:
                    raise ValidationError("Existe una aprobacion en curso")
                if aproval.request_status == "refused":
                    raise ValidationError("Verifique si no existe una solicitud Rechazada antes de generar una nueva")
            values = {
                'name': category_obj.name + " " + sale.name,
                'category_id': category_obj.id,
                'date': datetime.now(),
                'request_owner_id': sale.env.user.id,
                'reference': sale.payment_condition_id.name,
                'partner_id': sale.partner_id.id,
                'amount': sale.amount_total,
                'sale_id': sale.id,
                'request_status': 'pending'
            }
            t = self.env['approval.request'].create(values)
            for item in sale.approver_ids:
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
    
    @api.depends('payment_condition_id')
    def _compute_approver(self):
        category_obj = self.env['approval.category'].search([('is_sale', '=', 'required')], limit=1)
        if category_obj:
            self.approver_ids = category_obj.user_ids
        if not category_obj.user_ids:
            raise ValidationError(
                "Disculpe no tiene Aprobadores Configurados"
                "Vaya a Aprobaciones / Configuración / Tipo de aprobación.")

    @api.onchange('payment_condition_id')
    def onchange_payment_condition(self):
        self.check_payment_condition()

    @api.constrains('payment_condition_id')
    def check_payment_condition(self):
        self.is_approval = self.payment_condition_id.is_approval
        if len(self.payment_condition_id.approver_ids) > 0:
            self.approver_ids = self.payment_condition_id.approver_ids
        else:
            self._compute_approver()

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        if self.payment_condition_id.is_approval:
            self.approvals_request_sale()
        return res

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if self.approvals_ids and vals['state'] in ['draft', 'sent']:
            raise ValidationError(
                "Disculpe no puede modificar el registro ya que posee Aprobacion")
        return res
