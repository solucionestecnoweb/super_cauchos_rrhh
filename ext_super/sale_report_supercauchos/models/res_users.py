import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models, _
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning

import time

class ResUsersBoss(models.Model):
    _inherit = 'res.users'
    
    is_boss = fields.Boolean(string='Is vice-president?')
    the_boss = fields.Boolean(compute='compute_boss')

    def compute_boss(self):
        for item in self:
            xfind = item.env['res.users'].search([
                ('is_boss', '=', True)
            ])
            if len(xfind) > 0:
                if item.is_boss == True:
                    item.the_boss = True
                else:
                    item.the_boss = False
            else:
                item.the_boss = True
    