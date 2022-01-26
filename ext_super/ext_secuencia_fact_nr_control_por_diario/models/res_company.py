from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
import openerp.addons.decimal_precision as dp
import logging

import io
from io import BytesIO

import xlsxwriter
import shutil
import base64
import csv
import xlwt
import xml.etree.ElementTree as ET

class ResCompany(models.Model):
    _inherit = 'res.company'

    confg_nro_control = fields.Selection([
        ('c','Nro control unico por Compañia'),
        ('d','Nro Control por diario'),
    ], string='Conf. Nro control', default="d")