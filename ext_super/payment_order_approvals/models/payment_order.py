from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import base64
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning


class PaymentOrderApproval(models.Model):
    _inherit = 'purchase.pay.order'

    is_approved = fields.Boolean(string='Solicitud aprobada', copy=False)
    is_rejected = fields.Boolean(string='Solicitud rechazada', copy=False)
    approver_id = fields.Many2one(comodel_name='res.users', string='Approver')

    # def action_confirmed(self):
    #     for item in self:
    #         xfind = item.env['approval.request'].search([('payment_order_id', '=', item.id)])
    #         is_company =  item.env['res.company'].search([('partner_id', '=', item.employee_id.address_id.id)])
    #         if len(xfind) > 0:
    #             for line in xfind:
    #                 if line.request_status == 'approved':
    #                     item.is_approved = True
    #                 else:
    #                     item.is_approved = False
    #         elif len(is_company) > 0:
    #             item.is_approved = True
    #         else:
    #             item.is_approved = False
    #         if item.is_approved:
    #             super(PaymentOrderApproval, self).action_confirmed()
    #         else:
    #             raise ValidationError(_("Cannot confirm until an approval request is approved for this payment order."))

    def approvals_request_payment(self):
        xfind = self.env['approval.request'].search([('payment_order_id', '=', self.id), ('request_status', 'not in', ['refused', 'cancel'])])
        if len(xfind) == 0:
            approval = self.env['approval.category'].search([
                ('has_payment_order', '=', 'required')
            ], limit=1)
            amount_total = 0
            for item in self.pay_order_lines_ids:
                amount_total += item.amount
            if len(approval) > 0:
                values = {
                    'name': approval.name,
                    'category_id': approval.id,
                    'date': datetime.now(),
                    'request_owner_id': self.env.user.id,
                    'amount': amount_total,
                    'payment_order_id': self.id,
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
                raise ValidationError(_("There is an approval request approved for this payment order."))
            else:
                raise ValidationError(_("There is an approval request ongoing for this payment order."))