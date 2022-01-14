# -*- coding: utf-8 -*-


import logging
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError




class AccuntAcount(models.Model):
    _inherit = 'account.account'

    prorreatable = fields.Boolean(default=False)

class AccountGroup(models.Model):
    _inherit = 'account.group'

    prorreatable = fields.Boolean(default=False)