import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models, _
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning
import time

class Internal(models.Model):
    _inherit ='account.payment'

    transfer_to_id = fields.Many2one ('res.company', string='Compañía a Transferir')
    destination_journal_id = fields.Many2one('account.journal', domain="[('type', 'in', ('bank', 'cash')), ('company_id','=',transfer_to_id)]")
    
