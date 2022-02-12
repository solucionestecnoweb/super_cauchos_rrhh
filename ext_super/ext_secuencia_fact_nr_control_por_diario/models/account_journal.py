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

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    doc_sequence_id = fields.Many2one('ir.sequence', string='Secuencia Nro Documento',
        help="Este campo asigna el nro a un documento sea factura, NC, ND", copy=False)
    doc_sequence_number_next = fields.Char(compute='_compute_proximo_valor_doc')

    ctrl_sequence_id = fields.Many2one('ir.sequence', string='Secuencia Nro Control',
        help="Este campo asigna el nro de control de un documento sea factura, NC, ND", copy=False)
    ctrl_sequence_number_next = fields.Char(compute='_compute_proximo_valor')

    def _compute_proximo_valor_doc(self):
        self.doc_sequence_number_next=self.doc_sequence_id.number_next_actual

    def _compute_proximo_valor(self):
        self.ctrl_sequence_number_next=self.ctrl_sequence_id.number_next_actual