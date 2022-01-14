# -*- coding: utf-8 -*-


import logging
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError




class ResPartner(models.Model):
    _inherit = 'res.partner'

    account_payable_aux_id = fields.Many2one('account.account',default=lambda self: self.env.company.account_payable_aux_id.id,company_dependent=True)
    account_receivable_aux_id = fields.Many2one('account.account',default=lambda self: self.env.company.account_receivable_aux_id.id,company_dependent=True)
    property_account_payable_id = fields.Many2one('account.account',default=lambda self: self.env.company.account_payable_aux_id.id,company_dependent=True)
    property_account_receivable_id = fields.Many2one('account.account',default=lambda self: self.env.company.account_receivable_aux_id.id,company_dependent=True)

    account_anti_receivable_id = fields.Many2one('account.account', string='Cuenta Anticipo a Cobrar (Clientes)',default=lambda self: self.env.company.account_anti_receivable_aux_id.id,company_dependent=True)
    account_anti_payable_id = fields.Many2one('account.account', string='Cuenta Anticipo a Pagar (Proveedores)',default=lambda self: self.env.company.account_anti_payable_aux_id.id,company_dependent=True)
    vat_retention_rate = fields.Float(string='Retention rate', 
        help='VAT retention rate according to the Seniat for this contributes', 
        required=True, default="" ,company_dependent=True
    )
   
    """def _compute_payable(self):
        self.account_payable_aux_id=self.env.company.account_payable_aux_id.id
        self.property_account_payable_id=self.env.company.account_payable_aux_id.id

    def _compute_receivable(self):
        self.account_receivable_aux_id=self.env.company.account_receivable_aux_id.id
        self.property_account_receivable_id=self.env.company.account_receivable_aux_id.id"""