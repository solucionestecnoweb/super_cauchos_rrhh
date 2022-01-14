# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from copy import deepcopy

from odoo import models, api, _, fields

class AccountChartOfAccountReport(models.AbstractModel):
    _inherit= "account.coa.report"
    #_inherit = "account.report"

    @api.model
    def _get_columns_name(self, options):
        columns = [
            {'name': '', 'style': 'width:40%'},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
        ]
        if options.get('comparison') and options['comparison'].get('periods'):
            columns += [
                {'name': _('Debit'), 'class': 'number '},
                {'name': _('Credit'), 'class': 'number'},
            ] * len(options['comparison']['periods'])
        return columns + [
            {'name': _('Debit'), 'class': 'number '},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('Debit'), 'class': 'number '},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('Debe $'), 'class': 'number '},
            {'name': _('Haber $'), 'class': 'number'},
        ]