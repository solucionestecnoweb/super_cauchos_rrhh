from odoo import api, fields, models


class ApprovalsCategoryRequisitionExtend(models.Model):
    _inherit = 'approval.category'

    has_requisition = fields.Selection(string='Requisition', selection=[('required', 'Required'), ('optional', 'Optional'), ('no', 'None')], default='no')

class ApprovalsRequestRequisitionExtend(models.Model):
    _inherit = 'approval.request'

    requisition_id = fields.Many2one(comodel_name='purchase.requisitions', string='Requisition')
    has_requisition = fields.Selection(related="category_id.has_requisition")
