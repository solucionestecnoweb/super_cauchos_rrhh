# -*- coding: utf-8 -*-
from odoo import models, fields, api
from bs4 import BeautifulSoup
from datetime import date
from datetime import datetime
from pytz import timezone
from odoo.tools.translate import _
import requests

class FleetVehicle(models.Model):

    _inherit = "fleet.vehicle"

    campo_prueba = fields.Char()
    