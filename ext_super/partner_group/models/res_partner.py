# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    group_company_ids = fields.Many2many('res.partner','group_company_rel','group_id','company_id', string='Representantes de la Empresa')

    group_represent_ids = fields.One2many('res.partner', compute='_os_group_partner_ids', string='Grupo de Empresa')

    def _os_group_partner_ids(self):
        for item in self:
            item.group_represent_ids = self.env['res.partner']
            temp = self.env['res.partner'].search([('group_company_ids', 'in', item.ids)])
            if len(temp) > 0:
                item.group_represent_ids = temp
