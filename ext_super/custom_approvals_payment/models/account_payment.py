# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import UserError, ValidationError, except_orm, Warning


class account_payment_method(models.Model):
    _inherit = "account.payment.method"

    is_approval = fields.Boolean(string="Tiene aprobacion")
    

class account_payment(models.Model):
    _inherit = "account.payment"
    
    approvals_ids = fields.One2many('approval.request', 'payment_id', string='aprobaciones')
    approver_ids = fields.Many2many('res.users', string='Aprobadores', readonly=True, compute='_compute_approver',
                                    store=True)
    is_approval = fields.Boolean(string="Tiene aprobacion")

    def post(self):
        res = super(account_payment, self).post()
        if self.is_approval:
            if self.approvals_ids.filtered(lambda r: r.request_status == 'approved'):
                pass
            else:
                raise ValidationError("Disculpe!!! no puede validar si la aprobacion no esta aceptada.")
        return res

    def approvals_request_payment(self):
        for payment in self:
            approvers = len(payment.approver_ids)
            category_obj = self.env['approval.category'].search([('is_payment', '=', 'required')], limit=1)
            if approvers > len(category_obj.user_ids):
                raise UserError(
                    "No puede agregar mas arpobadores de lo estipulado."
                     "Vaya a Aprobaciones / Configuración / Tipo de aprobación.")
            for aproval in payment.approvals_ids:
                if aproval.request_status in ['new', 'pending', 'approved']:
                    raise ValidationError("Existe una aprobacion en curso")
                if aproval.request_status == "refused":
                    raise ValidationError("Verifique si no existe una solicitud Rechazada antes de generar una nueva")
            values = {
                'name': category_obj.name,
                'category_id': category_obj.id,
                'date': datetime.now(),
                'request_owner_id': payment.env.user.id,
                'amount': payment.amount,
                'reference': payment.communication,
                'partner_id': payment.partner_id.id,
                'payment_id': payment.id,
                'request_status': 'pending'
            }
            t = self.env['approval.request'].create(values)
            for item in payment.approver_ids:
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

    @api.onchange('payment_method_id')
    def _onchange_is_approval(self):
        if self.payment_method_id.is_approval:
            self.is_approval = True
        else:
            self.is_approval = False
            
    @api.depends('is_approval')
    def _compute_approver(self):
            category_obj = self.env['approval.category'].search([('is_payment', '=', 'required')], limit=1)
            if category_obj:
                self.approver_ids = category_obj.user_ids
            if not category_obj.user_ids:
                raise ValidationError(
                    "Disculpe no tiene Aprobadores Configurados"
                    "Vaya a Aprobaciones / Configuración / Tipo de aprobación.")
        

