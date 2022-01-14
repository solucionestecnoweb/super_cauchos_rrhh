from odoo import models,fields

class ResPartnerAgents(models.Model):
    _inherit ='res.partner'

    is_agent = fields.Boolean(string="Are you a commission agent?")
    commission_category_id = fields.Many2one('commission.category', string="Category")
    commission_type_id = fields.Many2one('commission.type', string="Commission Type")
    commission_period_id = fields.Many2one('commission.settlement.period', string="Settlement Period")
    commission_base_id = fields.Many2one ('commission.base.type', string="Base Type")

class CommissionCategory(models.Model):
    _name = 'commission.category'

    name = fields.Char("Name")

class CommissionSettlementPeriod(models.Model):
    _name="commission.settlement.period"

    name = fields.Char("Name")

class CommissionBaseType(models.Model):
    _name ="commission.base.type"

    name = fields.Char("Name")
    
class CommissionType(models.Model):
    _name = 'commission.type'

    name = fields.Char("Name")
    is_active = fields.Boolean(string='Is this commission type active?')
    type_id = fields.Many2one(comodel_name='commission.type.type', string='Type')
    base_id = fields.Many2one(comodel_name='commission.type.base', string='Base')
    invoice_state_id = fields.Many2one(comodel_name='commission.type.invoice', string='Invoice State')
    fixed_percentage = fields.Float(string='Fixed Percentage')

class CommissionTypeType(models.Model):
    _name = 'commission.type.type'

    name = fields.Char("Name")

class CommissionTypeBase(models.Model):
    _name = 'commission.type.base'

    name = fields.Char("Name")

class CommissionTypeInvoice(models.Model):
    _name = 'commission.type.invoice'

    name = fields.Char("Name")

