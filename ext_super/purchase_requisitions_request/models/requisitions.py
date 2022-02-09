from email.policy import default
from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import base64
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning

class PurchaseRequisitions(models.Model):
    _name = 'purchase.requisitions'
    _description = 'Requisitions Request for Purchase Orders'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', default='Nuevo', copy=False)
    
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))
    department_id = fields.Many2one(comodel_name='hr.department', string='Department', default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1).department_id.id)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.user.company_id)
    requisition_responsible_id = fields.Many2one(comodel_name='hr.employee', string='Requisition Responsable')
    
    request_date = fields.Date(string='Requisition Date', default=fields.Date.today())
    received_date = fields.Date(string='Received Date')
    date_end = fields.Date(string='Requisition Deadline')
    priority = fields.Selection(string='Priority', selection=[('very_low', 'Very Low'), ('low', 'Low'), ('meddium', 'Meddium'), ('high', 'High')], default="low")
    
    requisition_lines_ids = fields.One2many(comodel_name='purchase.requisitions.lines', inverse_name='requisition_id', string='Requisition Lines')
    reason = fields.Text(string='Reason for Requisition')
    state = fields.Selection([ ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('receive', 'Aprobado'), ('reject', 'Rejected'), ('cancel', 'Cancelled')], default='draft')
    approvals_ids = fields.One2many('approval.request', 'requisition_id', string='Aprobaciones')
    approver_ids = fields.Many2many('res.users', string='Aprobadores', default=lambda x: x.env['approval.category'].search([('has_requisition', '=', 'required')], limit=1).user_ids.ids)

    @api.constrains('state')
    def _compute_name(self):
        if self.name == 'Nuevo':
            self.name = self.env['ir.sequence'].next_by_code('purchase.requisition.seq')
    
    @api.onchange('employee_id')
    def set_department(self):
        for item in self:
            item.department_id = item.employee_id.department_id.id

    @api.onchange('date_end')
    def date_end_validate(self):
        if self.date_end and self.request_date:
            if self.date_end < self.request_date:
                raise ValidationError(_("Date end can't be minor than request date."))

    def reset_draft(self):
        for item in self:
            for aproval in item.approvals_ids:
                if aproval.request_status == 'approved':
                    raise ValidationError("Esta requisición ya fue aprobada, no puede restablecerse a borrador.")
                elif aproval.request_status == "refused":
                    raise ValidationError("Esta requisición ya fue rechazada, no puede restablecerse a borrador.")
                else:
                    aproval.request_status = "cancel"
                    item.state = 'draft'

    def validate_requisition(self):
        for item in self:
            for aproval in item.approvals_ids:
                if aproval.request_status == 'approved':
                    return item.action_approved()
                elif aproval.request_status == "refused":
                    return item.requisition_reject()
                elif aproval.request_status in ['new', 'pending']:
                    raise ValidationError("La aprobación se encuentra en curso")

            raise ValidationError("La aprobación se encuentra cancelada, solicite una nueva para validar la requisición")
    
    def action_approved(self):
        for item in self:
            item.received_date = fields.Date.today()
            item.state = 'receive'

    def action_cancel(self):
        for item in self:
            item.state = 'cancel'

    def requisition_reject(self):
        for item in self:
            item.state = 'reject'

    def show_orders(self):
        # self.ensure_one()
        # res = self.env.ref('purchase.purchase_form_action').read()[0]
        # res['domain'] = str([('requisition_id','=',self.id)])
        # return res
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "context" : "{'default_requisition_id':"+ str(self.id) + "}",
            "views": [[self.env.ref('purchase.purchase_order_view_tree').id, "tree"],[False, "form"]],
            "domain": [['requisition_id', '=', self.id]],
            "name": "Orden de Compra",
        }

    def approvals_request(self):
        for requisition in self:
            category_obj = self.env['approval.category'].search([('has_requisition', '=', 'required')], limit=1)
            is_company =  requisition.env['res.company'].search([('partner_id', '=', requisition.employee_id.address_id.id)])
            # approvers = len(requisition.approver_ids)
            # if approvers > len(category_obj.user_ids):
            #     raise UserError(
            #         "No puede agregar más aprobadores de lo estipulado."
            #         "Vaya a Aprobaciones / Configuración / Tipos de aprobación.")

            if len(is_company) == 0:
                for aproval in requisition.approvals_ids:
                    if aproval.request_status in ['new', 'pending', 'approved']:
                        raise ValidationError("Existe una aprobación en curso")
                    if aproval.request_status == "refused":
                        raise ValidationError("Verifique si no existe una solicitud rechazada antes de generar una nueva")
            
            values = {
                'name': category_obj.name + ' ' + requisition.name,
                'category_id': category_obj.id,
                'date': datetime.now(),
                'request_owner_id': requisition.env.user.id,
                'requisition_id': requisition.id,
                'request_status': 'pending'
            }
            t = self.env['approval.request'].create(values)
            for item in requisition.approver_ids:
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

            requisition.state = 'confirmed'

class PurchaseRequisitionsLines(models.Model):
    _name = 'purchase.requisitions.lines'
    _description = 'Lines for Requisitions Request'

    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    description = fields.Char(string='Description')
    qty = fields.Float(string='Quantity', default=1)
    uom = fields.Many2one(comodel_name='uom.uom', string='Unit of Measure')
    requisition_id = fields.Many2one(comodel_name='purchase.requisitions', string='Requisition')
    
    @api.onchange('product_id')
    def set_uom(self):
        for item in self:
            item.description = item.product_id.name
            item.uom = item.product_id.uom_id.id

class PurchaseOrdersRequisition(models.Model):
    _inherit = 'purchase.order'

    requisition_id = fields.Many2one(comodel_name='purchase.requisitions', string='Requisition')
    
    @api.onchange('requisition_id')
    def _set_priority(self):
        for item in self:
            item.priority = item.requisition_id.priority
    