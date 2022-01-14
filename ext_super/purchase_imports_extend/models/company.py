from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    imports_company = fields.Boolean(string='¿Es una compañía de Importaciones?')
    