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
    state = fields.Selection([ ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('receive', 'Receive'), ('cancel', 'Cancelled'), ('reject', 'Rejected')], default='draft')
    is_approved = fields.Boolean(default=False)
    approver_id = fields.Many2one(comodel_name='res.users', string='Approver')

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
            item.state = 'draft'

    def requisition_confirm(self):
        for item in self:
            xfind = item.env['approval.request'].search([('requisition_id', '=', item.id)])
            is_company =  item.env['res.company'].search([('partner_id', '=', item.employee_id.address_id.id)])
            if len(xfind) > 0:
                for line in xfind:
                    if line.request_status == 'approved':
                        item.is_approved = True
                    else:
                        item.is_approved = False
            elif len(is_company) > 0:
                item.is_approved = True
            else:
                item.is_approved = False
            if item.is_approved:
                item.state = 'confirmed'
            else:
                raise ValidationError(_("Cannot confirm until an approval request is approved for this requisition."))
    
    def action_received(self):
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
        xfind = self.env['approval.request'].search([('requisition_id', '=', self.id), ('request_status', 'not in', ['refused', 'cancel'])])
        if len(xfind) == 0:
            approval = self.env['approval.category'].search([
                ('has_requisition', '=', 'required')
            ], limit=1)
            if len(approval) > 0:
                values = {
                    'name': approval.name,
                    'category_id': approval.id,
                    'date': datetime.now(),
                    'request_owner_id': self.env.user.id,
                    'requisition_id': self.id,
                    'request_status': 'pending'
                }
                t = self.env['approval.request'].create(values)
                for item in self.approver_id:
                    t.approver_ids += self.env['approval.approver'].new({
                        'user_id': item.id,
                        'request_id': t.id,
                        'status': 'new'
                    })
                t.action_confirm()
            else:
                raise ValidationError(_("There is no approval category for this type record. Go to Approvals/Config/Approval type."))
        else:
            if xfind['request_status'] == 'approved':
                raise ValidationError(_("There is an approval request approved for this requisition."))
            else:
                raise ValidationError(_("There is an approval request ongoing for this requisition."))

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
    
class PurchaseOrderPriority(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('requisition_id')
    def _set_priority(self):
        for item in self:
            item.priority = item.requisition_id.priority
    