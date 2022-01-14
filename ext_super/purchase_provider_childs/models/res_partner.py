from odoo import api, fields, models


class ResPartnerSubProvider(models.Model):
    _inherit = 'res.partner'

    provider_parent_id = fields.Many2one(comodel_name='res.partner', string='Provider')
    provider_childs_ids = fields.One2many(comodel_name='res.partner', inverse_name='provider_parent_id', string=' Sub Provider')
    
class ResPartnerCategorySubProvider(models.Model):
    _inherit = 'res.partner.category'

    provider_parent_id = fields.Many2one(comodel_name='res.partner.category', string='Provider')
    provider_childs_ids = fields.One2many(comodel_name='res.partner.category', inverse_name='provider_parent_id', string=' Sub Provider')
    bank_ids = fields.One2many(comodel_name='res.partner.bank', inverse_name='bank_id', string=' Bank Accounts')
    