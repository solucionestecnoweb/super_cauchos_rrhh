# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models, _
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning

import time


class CrmTeam(models.Model):
	_inherit = "crm.team"

	sellers_id = fields.Many2many('res.partner', string='Vendedores')