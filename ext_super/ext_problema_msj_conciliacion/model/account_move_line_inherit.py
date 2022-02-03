# -*- coding: utf-8 -*-


import logging
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _check_reconciliation(self):
        for line in self:
            if line.matched_debit_ids or line.matched_credit_ids:
                x=0
                #raise UserError(_('valor = %s')%line)
                #raise UserError(_('valor = %s   --- %s')%(line.matched_debit_ids,line.matched_credit_ids))
                #raise UserError(_("You cannot do this modification on a reconciled journal entry. "
                                  #"You can just change some non legal fields or you must unreconcile first.\n"
                                  #"Journal Entry (id): %s (%s)") % (line.move_id.name, line.move_id.id))