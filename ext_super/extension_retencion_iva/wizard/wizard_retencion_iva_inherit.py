from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
import logging

import io
from io import BytesIO

import xlsxwriter
import shutil
import base64
import csv
import xlwt
import xml.etree.ElementTree as ET

class LibroDiario(models.TransientModel):
    _inherit = 'wizard.resumen.iva'

    date_now = fields.Datetime(string='Fecha Actual', default=lambda *a:datetime.now())
    currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda')
    type = fields.Selection(string='Tipo', selection=[('in_invoice', 'Proveedor'), ('out_invoice', 'Cliente')], default='in_invoice')

    def get_convertion(self, monto, fecha, moneda):
        tasa = self.env['res.currency.rate'].search([('name', '=', fecha)], limit=1).sell_rate
        if not tasa:
            tasa = 1
        if self.currency_id.id == 3:
            if moneda == self.currency_id.id:
                conversion = monto
            else:
                conversion = monto * tasa
        else:
            if moneda == 3:
                conversion = monto / tasa
            else:
                conversion = monto
        return conversion

    def get_invoice_extended(self):
        t=self.env['resumen.iva.wizard.pdf']
        d=t.search([])
        d.unlink()
        if self.type == 'in_invoice':
            cursor_resumen = self.env['account.move.line.resumen'].search([
                ('fecha_fact','>=',self.date_from),
                ('fecha_fact','<=',self.date_to),
                ('state_voucher_iva','=','posted'),
                ('state','in',('posted','cancel' )),
                ('type', 'in', ('in_invoice','in_refund','in_receipt')),
                #('company_id','=',self.env.company.id)#loca14 aqui se quito porque en isneiker daba peo
                ])
        else:
            cursor_resumen = self.env['account.move.line.resumen'].search([
                ('fecha_fact','>=',self.date_from),
                ('fecha_fact','<=',self.date_to),
                ('state_voucher_iva','=','posted'),
                ('state','in',('posted','cancel' )),
                ('type', 'in', ('out_invoice','out_refund','out_receipt')),
                #('company_id','=',self.env.company.id)#loca14 aqui se quito porque en isneiker daba peo
                ])
        for det in cursor_resumen:
            values={
            'name':det.fecha_fact,
            'document':det.invoice_id.name,
            'partner':det.invoice_id.partner_id.id,
            'invoice_number': det.invoice_id.invoice_number,#darrell
            'tipo_doc': det.tipo_doc,
            'invoice_ctrl_number': det.invoice_id.invoice_ctrl_number,
            'sale_total': self.get_convertion(det.total_con_iva, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'base_imponible': self.get_convertion(det.total_base, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'iva' : self.get_convertion(det.total_valor_iva, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'iva_retenido': self.get_convertion(det.total_ret_iva, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'retenido': det.vat_ret_id.name,
            'retenido_date':det.vat_ret_id.voucher_delivery_date,
            'state_retantion': det.vat_ret_id.state,
            'state': det.invoice_id.state,
            'currency_id':det.invoice_id.currency_id.id,
            'ref':det.invoice_id.ref,
            'total_exento':self.get_convertion(det.total_exento, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'alicuota_reducida':self.get_convertion(det.alicuota_reducida, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'alicuota_general':self.get_convertion(det.alicuota_general, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'alicuota_adicional':self.get_convertion(det.alicuota_adicional, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'base_adicional':self.get_convertion(det.base_adicional, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'base_reducida':self.get_convertion(det.base_reducida, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'base_general':self.get_convertion(det.base_general, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'retenido_reducida':self.get_convertion(det.retenido_reducida, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'retenido_adicional':self.get_convertion(det.retenido_adicional, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'retenido_general':self.get_convertion(det.retenido_general, det.invoice_id.invoice_date, det.invoice_id.currency_id.id),
            'vat_ret_id':det.vat_ret_id.id,
            'invoice_id':det.invoice_id.id,
            'tax_id':det.tax_id.id,
            #'company_id':self.env.company.id,#loca14
            }
            pdf_id = t.create(values)
        #   temp = self.env['account.wizard.pdf.ventas'].search([])
        self.line = self.env['resumen.iva.wizard.pdf'].search([])

    def generate_pdf_report(self):
        self.get_invoice_extended()
        return {'type': 'ir.actions.report','report_name': 'extension_retencion_iva.extension_retencion_iva_report','report_type':"qweb-pdf"}