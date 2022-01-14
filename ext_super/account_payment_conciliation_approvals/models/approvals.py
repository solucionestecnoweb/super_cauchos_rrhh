from odoo import api, fields, models


class ApprovalsCategoryConciliationExtend(models.Model):
    _inherit = 'approval.category'

    has_conciliation = fields.Selection(string='Conciliation', selection=[('required', 'Required'), ('optional', 'Optional'), ('no', 'None')], default='no')

class ApprovalsRequestConciliationExtend(models.Model):
    _inherit = 'approval.request'

    conciliation_id = fields.Many2one(comodel_name='account.payment', string='Payment')
    has_conciliation = fields.Selection(related="category_id.has_conciliation")
