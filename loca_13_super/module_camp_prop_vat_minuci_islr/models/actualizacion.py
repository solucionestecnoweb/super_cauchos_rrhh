# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


_logger = logging.getLogger('__name__')



class Partners(models.Model):
    _inherit = 'res.partner'

    ret_agent = fields.Boolean(string='Retention agent', help='True if your partner is retention agent',company_dependent=True)
    purchase_jrl_id = fields.Many2one('account.journal', string='Diario de Compra',company_dependent=True)
    sale_jrl_id = fields.Many2one('account.journal', string='Diario de Venta',company_dependent=True)
    ret_jrl_id = fields.Many2one('account.journal', string='Diario de Retenciones',company_dependent=True)
    account_ret_receivable_id = fields.Many2one('account.account', string='Cuenta Retencion a Cobrar (Clientes)',company_dependent=True)
    account_ret_payable_id = fields.Many2one('account.account', string='Cuenta Retencion a Pagar (Proveedores)',company_dependent=True)

    muni_wh_agent = fields.Boolean(string='Retention agent', help='True if your partner is a municipal retention agent',company_dependent=True)
    purchase_jrl_id = fields.Many2one('account.journal', string='Dario de Compras',company_dependent=True)
    sale_jrl_id = fields.Many2one('account.journal', string='Diario de Ventas',company_dependent=True)
    account_ret_muni_receivable_id = fields.Many2one('account.account', string='Cuenta Retencion Clientes',company_dependent=True)
    account_ret_muni_payable_id = fields.Many2one('account.account', string='Cuenta Retencion Proveedores',company_dependent=True)

    ret_agent_isrl= fields.Boolean(string='Retention agent ISLR', help='True if your partner is retention agent',company_dependent=True)
    sale_isrl_id = fields.Many2one('account.journal', string='Diario',company_dependent=True)
    account_isrl_receivable_id = fields.Many2one('account.account', string='Cuenta ISLR Retencion a Cobrar (Clientes)',company_dependent=True)
    account_isrl_payable_id = fields.Many2one('account.account', string='Cuenta ISLR Retencion a Pagar (Proveedores)',company_dependent=True)
    vat_retention_rate = fields.Float(string='Retention rate', 
        help='VAT retention rate according to the Seniat for this contributes', 
        required=True, default="" ,company_dependent=True
    )

    account_anti_receivable_id = fields.Many2one('account.account', string='Cuenta Anticipo a Cobrar (Clientes)',company_dependent=True)
    account_anti_payable_id = fields.Many2one('account.account', string='Cuenta Anticipo a Pagar (Proveedores)',company_dependent=True)