from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import base64
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning


class PurchaseOrderApproval(models.Model):
    _inherit = 'purchase.order'

    is_approved = fields.Boolean(string='Solicitud aprobada', copy=False)
    is_rejected = fields.Boolean(string='Solicitud rechazada', copy=False)
    approver_ids = fields.Many2many(comodel_name='res.users', string='Approvers')
    #
    # def button_confirm(self):
    #     if not self.order_line:
    #         raise UserError(_("No puede enviar una orden de compra sin lineas de pedidos. Por favor agregue lineas a la orden"))
    #     else:
    #         for item in self:
    #             xfind = item.env['approval.request'].search([('purchase_order_id', '=', item.id)])
    #             is_company =  item.env['res.company'].search([('partner_id', '=', item.partner_id.id)])
    #             if len(xfind) > 0:
    #                 for line in xfind:
    #                     if line.request_status == 'approved':
    #                         item.is_approved = True
    #                     else:
    #                         item.is_approved = False
    #             elif len(is_company) > 0:
    #                 item.is_approved = True
    #             else:
    #                 item.is_approved = False
    #             if item.is_approved:
    #                 super(PurchaseOrderApproval, self).button_confirm()
    #             else:
    #                 raise ValidationError(_("Cannot confirm until an approval request is approved for this purchase order."))

    def approvals_request_purchase(self):
        if not self.order_line:
            raise UserError(_("No puede enviar una orden de compra sin lineas de pedidos. Por favor agregue lineas a la orden"))
        else:
            approvers = len(self.approver_ids)
            xfind = self.env['approval.request'].search([('purchase_order_id', '=', self.id), ('request_status', 'not in', ['refused', 'cancel']),('approval_minimum', '=', approvers)])
            if len(xfind) == 0:
                approval = self.env['approval.category'].search([
                    ('has_purchase_order', '=', 'required'),
                    ('approval_minimum', '=', approvers),
                ], limit=1)
                if len(approval) > 0:
                    values = {
                        'name': approval.name,
                        'category_id': approval.id,
                        'date': datetime.now(),
                        'request_owner_id': self.env.user.id,
                        'amount': self.amount_total,
                        'purchase_order_id': self.id,
                        'request_status': 'pending'
                    }
                    t = self.env['approval.request'].create(values)
                    for item in self.approver_ids:
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
                    raise ValidationError(_("There is an approval request approved for this purchase order."))
                else:
                    raise ValidationError(_("There is an approval request ongoing for this purchase order."))