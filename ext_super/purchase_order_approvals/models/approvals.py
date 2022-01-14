from odoo import api, fields, models


class ApprovalsCategoryPurchaseExtend(models.Model):
    _inherit = 'approval.category'

    has_purchase_order = fields.Selection(string='Purchase Order', selection=[('required', 'Required'), ('optional', 'Optional'), ('no', 'None')], default='no')


class ApprovalsRequestPurchaseExtend(models.Model):
    _inherit = 'approval.request'

    purchase_order_id = fields.Many2one(comodel_name='purchase.order', string='Purchase Order')
    has_purchase_order = fields.Selection(related="category_id.has_purchase_order")

    def action_approve(self):
        # res = super(ApprovalsRequestPurchaseExtend, self).action_approve()
        for ap in self:
            if ap.purchase_order_id.id:
                order_obj = ap.env['purchase.order'].search([('id', '=', ap.purchase_order_id.id)])
                order_obj.write({'is_approved': True})
        return super(ApprovalsRequestPurchaseExtend, self).action_approve()

    def action_refuse(self):
        # res = super(ApprovalsRequestPurchaseExtend, self).action_refuse()
        for ap in self:
            if ap.purchase_order_id.id:
                order_obj = ap.env['sale.order'].search([('id', '=', ap.purchase_order_id.id)])
                order_obj.write({'is_approved': False, 'is_rejected': True})
        return super(ApprovalsRequestPurchaseExtend, self).action_approve()

    def action_cancel(self):
        #res = super(ApprovalsRequestPurchaseExtend, self).action_cancel()
        for ap in self:
            if ap.purchase_order_id.id:
                order_obj = ap.env['sale.order'].search([('id', '=', ap.purchase_order_id.id)])
                order_obj.write({'is_approved': False, 'is_rejected': True})
        return super(ApprovalsRequestPurchaseExtend, self).action_approve()