# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning

import time

class ResCompanyPaperFormat(models.Model):
    _inherit = 'res.company'

    paperformat = fields.Selection(string='Invoice Format', selection=[('letter', 'Multirepuestos'), ('half', 'Supercauchos'), ('long_letter', 'Matrix')], default='letter')
