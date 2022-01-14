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

_logger = logging.getLogger(__name__)

class FlotaConsumoCombustible(models.TransientModel):
    _name = "fleet.wizard.fuel"

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())

    def print_ordenes(self):
        return {'type': 'ir.actions.report','report_name': 'supercauchos_fleet.flota_consumo_combustible','report_type':"qweb-pdf"}

    def combustible(self):
        busqueda = self.env['fleet.vehicle.log.fuel'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ])
        return busqueda

    def vehiculos(self):
        busqueda = self.env['fleet.vehicle'].search([])
        #print(len(busqueda))
        return busqueda

    def  totales(self, fcont2):
        busqueda = self.env['fleet.vehicle.log.fuel'].search([
            ('date', '=', fcont2)
        ])