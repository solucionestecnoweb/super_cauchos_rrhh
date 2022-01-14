from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import base64
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.tools.float_utils import float_round


class account_payment(models.Model):
    _inherit = 'account.payment'

    is_approved = fields.Boolean(default=False)
    state = fields.Selection(selection_add=[('to_approve', 'To be Approved'), ('approved', 'Approved'), ('refused', 'Refused')])
    
    def post(self):
        xfind = self.env['approval.request'].search([('conciliation_id', '=', self.id)])
        is_company =  self.env['res.company'].search([('partner_id', '=', self.partner_id.id)])

        status = xfind.request_status
        if len(xfind) > 0:
            if status == 'approved':
                self.is_approved = True
            else:
                self.is_approved = False
        elif len(is_company) > 0:
            self.is_approved = True
        elif self.payment_method_id.aprobacion_requerida == False:
            self.is_approved = True
        else:
            self.is_approved = False

        if self.is_approved:
            super(account_payment, self).post()
        elif status == 'refused':
            self.state = 'refused'
        else:
            raise ValidationError(_("Cannot confirm until an approval request is approved for this payment."))

    def approved_post(self):
        xfind = self.env['approval.request'].search([('conciliation_id', '=', self.id)])

        status = xfind.request_status
        if len(xfind) > 0:
            if status == 'approved':
                self.is_approved = True
            else:
                self.is_approved = False
        elif self.payment_method_id.aprobacion_requerida == False:
            self.is_approved = True
        else:
            self.is_approved = False

        if self.is_approved:
            self.action_draft()
            self.post()
        elif status == 'refused':
            self.state = 'refused'
        else:
            raise ValidationError(_("Cannot confirm until an approval request is approved for this payment."))


    def approvals_request_conciliation(self):
        xfind = self.env['approval.request'].search([('conciliation_id', '=', self.id), ('request_status', 'not in', ['cancel'])])
        if len(xfind) == 0:
            approval = self.env['approval.category'].search([
                ('has_conciliation', '=', 'required')
            ], limit=1)
            if len(approval) > 0:
                values = {
                    'name': approval.name,
                    'category_id': approval.id,
                    'date': datetime.now(),
                    'request_owner_id': self.env.user.id,
                    'amount': self.amount,
                    'conciliation_id': self.id,
                    'request_status': 'pending'
                }
                t = self.env['approval.request'].create(values)
                for item in approval.user_ids:
                    t.approver_ids += self.env['approval.approver'].new({
                        'user_id': item.id,
                        'request_id': t.id,
                        'status': 'new'
                    })
                t.action_confirm()
                self.state = 'to_approve'
            else:
                raise ValidationError(_("There is no approval category for this type record. Go to Approvals/Config/Approval type."))
        else:
            raise ValidationError(_("There is an approval request ongoing for this payment."))

class AccountPaymentMethodApproval(models.Model):
    _inherit = 'account.payment.method'

    aprobacion_requerida = fields.Boolean(string='¿Necesita Aprobación?')
    