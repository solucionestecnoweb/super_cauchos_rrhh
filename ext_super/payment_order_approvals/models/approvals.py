from odoo import api, fields, models


class ApprovalsCategoryPaymentExtend(models.Model):
    _inherit = 'approval.category'

    has_payment_order = fields.Selection(string='Payment Order', selection=[('required', 'Required'), ('optional', 'Optional'), ('no', 'None')], default='no')


class ApprovalsRequestPaymentExtend(models.Model):
    _inherit = 'approval.request'

    payment_order_id = fields.Many2one(comodel_name='purchase.pay.order', string='Payment Order')
    has_payment_order = fields.Selection(related="category_id.has_payment_order")

    def action_approve(self):
        #res = super(ApprovalsRequestPaymentExtend, self).action_approve()
        for ap in self:
            if ap.payment_order_id.id:
                order_obj = ap.env['purchase.pay.order'].search([('id', '=', ap.payment_order_id.id)])
                order_obj.write({'is_approved': True})
        return super(ApprovalsRequestPaymentExtend, self).action_approve()

    def action_refuse(self):
        #res = super(ApprovalsRequestPaymentExtend, self).action_refuse()
        for ap in self:
            if ap.payment_order_id.id:
                order_obj = ap.env['purchase.pay.order'].search([('id', '=', ap.payment_order_id.id)])
                order_obj.write({'is_approved': False, 'is_rejected': True})
        return super(ApprovalsRequestPaymentExtend, self).action_approve()

    def action_cancel(self):
        #res = super(ApprovalsRequestPaymentExtend, self).action_cancel()
        for ap in self:
            if ap.payment_order_id.id:
                order_obj = ap.env['purchase.pay.order'].search([('id', '=', ap.payment_order_id.id)])
                order_obj.write({'is_approved': False, 'is_rejected': True})
        return super(ApprovalsRequestPaymentExtend, self).action_approve()
