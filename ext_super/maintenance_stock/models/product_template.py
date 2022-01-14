# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP


_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    maintenance_line_warn = fields.Selection(WARNING_MESSAGE, 'maintenance Line', help=WARNING_HELP, required=True,
                                      default="no-message")
    maintenance_line_warn_msg = fields.Text('Message for maintenance Line')
    maintenance_invoice_policy = fields.Selection([
        ('order', 'Cantidades pedidas'),
        ('delivery', 'Cantidades entregadas')], string='Política de mantenimiento',
        help='Ordered Quantity: Invoice quantities ordered by the customer.\n'
             'Delivered Quantity: Invoice quantities delivered to the customer.',
        default='order')

    @api.onchange('type')
    def _onchange_type(self):
        """ Force values to stay consistent with integrity constraints """
        res = super(ProductTemplate, self)._onchange_type()
        if self.type == 'consu':
            if not self.maintenance_invoice_policy:
                self.maintenance_invoice_policy = 'order'
            self.service_type = 'manual'
        return res


class ProductCategory(models.Model):
    _inherit = "product.category"
    combustible_check = fields.Boolean('Combustible', help='Marque éste campo si el producto es un combustible')

    def action_combustible_check(self):
        if not self.combustible_check:
            self.combustible_check = True
        else:
            self.combustible_check = False