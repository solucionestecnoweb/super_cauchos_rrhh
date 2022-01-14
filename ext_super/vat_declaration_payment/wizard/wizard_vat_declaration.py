from datetime import datetime, timedelta
from operator import mod
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

_logger = logging.getLogger(__name__)

class VatDeclarationPayment(models.TransientModel):
    _name = 'vat.declaration.payment'

    date = fields.Date(string='date')
    p_vat_included = fields.Float(string='VAT Included')
    p_tax_base = fields.Float(string='Tax Base')
    p_vat_withheld = fields.Float(string='VAT Withheld')
    p_vat = fields.Float(string='VAT')
    s_vat_included = fields.Float(string='VAT Included')
    s_tax_base = fields.Float(string='Tax Base')
    s_vat_withheld = fields.Float(string='VAT Withheld')
    s_vat = fields.Float(string='VAT')
    difference = fields.Float(string='Difference')
    wizard_id = fields.Many2one(comodel_name='wizard.vat.declaration.payment', string='Wizard')

class WizardVatDeclarationPayment(models.TransientModel):
    _name = 'wizard.vat.declaration.payment'

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency')
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())

    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=50)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.user.company_id.id)
    lines_ids = fields.One2many(comodel_name='vat.declaration.payment', inverse_name='wizard_id', string='Lines')
    

    def print_pdf(self):
        self.env['vat.declaration.payment'].search([]).unlink()
        self.get_data()
        self.lines_ids = self.env['vat.declaration.payment'].search([])
        return {
            'type': 'ir.actions.report',
            'report_name': 'vat_declaration_payment.vat_declaration_payment_report',
            'report_type':"qweb-pdf"
            }

    def get_data(self):
        xfind = self.env['account.move'].search([
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('type', 'in', ('out_invoice', 'out_refund','in_invoice', 'in_refund'))
        ])

        temp_date = ''
        t = self.env['vat.declaration.payment']

        for item in xfind.sorted(key=lambda x: x.invoice_date):
            if temp_date != item.invoice_date:
                temp_date = item.invoice_date
                p_vat_included =  0
                p_tax_base =  0
                p_vat_withheld =  0
                p_vat =  0
                s_vat_included =  0
                s_tax_base =  0
                s_vat_withheld =  0
                s_vat =  0
                difference =  0

                invoices = self.env['account.move'].search([
                    ('invoice_date', '=', item.invoice_date),
                    ('state', '=', 'posted'),
                    ('type', 'in', ('out_invoice', 'out_refund','in_invoice', 'in_refund'))
                ])

                rate = self.env['res.currency.rate'].search([('name', '=', item.invoice_date)]).sell_rate
                if not rate:
                    rate = 1

                for line in invoices:
                    if self.currency_id.id == 3:
                        if line.currency_id.id == 3:
                            if line.type in ('in_invoice', 'in_refund'):
                                p_vat_included += line.amount_total
                                p_tax_base += line.amount_untaxed
                                p_vat_withheld += line.vat_ret_id.vat_retentioned
                                p_vat += line.amount_tax
                            else:
                                s_vat_included += line.amount_total
                                s_tax_base += line.amount_untaxed
                                s_vat_withheld += line.vat_ret_id.vat_retentioned
                                s_vat += line.amount_tax
                        else:
                            if line.type in ('in_invoice', 'in_refund'):
                                p_vat_included += (line.amount_total * rate)
                                p_tax_base += (line.amount_untaxed * rate)
                                p_vat_withheld += (line.vat_ret_id.vat_retentioned * rate)
                                p_vat += (line.amount_tax * rate)
                            else:
                                s_vat_included += (line.amount_total * rate)
                                s_tax_base += (line.amount_untaxed * rate)
                                s_vat_withheld += (line.vat_ret_id.vat_retentioned * rate)
                                s_vat += (line.amount_tax * rate)
                    else:
                        if line.currency_id.id == 3:
                            if line.type in ('in_invoice', 'in_refund'):
                                p_vat_included += (line.amount_total / rate)
                                p_tax_base += (line.amount_untaxed / rate)
                                p_vat_withheld += (line.vat_ret_id.vat_retentioned / rate)
                                p_vat += (line.amount_tax / rate)
                            else:
                                s_vat_included += (line.amount_total / rate)
                                s_tax_base += (line.amount_untaxed / rate)
                                s_vat_withheld += (line.vat_ret_id.vat_retentioned / rate)
                                s_vat += (line.amount_tax / rate)
                        else:
                            if line.type in ('in_invoice', 'in_refund'):
                                p_vat_included += line.amount_total
                                p_tax_base += line.amount_untaxed
                                p_vat_withheld += line.vat_ret_id.vat_retentioned
                                p_vat += line.amount_tax
                            else:
                                s_vat_included += line.amount_total
                                s_tax_base += line.amount_untaxed
                                s_vat_withheld += line.vat_ret_id.vat_retentioned
                                s_vat += line.amount_tax

                difference = s_vat - p_vat
                values={
                    'date': item.invoice_date,
                    'p_vat_included': p_vat_included,
                    'p_tax_base': p_tax_base,
                    'p_vat_withheld': p_vat_withheld,
                    'p_vat': p_vat,
                    's_vat_included': s_vat_included,
                    's_tax_base': s_tax_base,
                    's_vat_withheld': s_vat_withheld,
                    's_vat': s_vat,
                    'difference': difference,
                    'wizard_id': self.id,
                }
                t.create(values)

    def get_credits(self):
        t = self.env['temporal.credits.amounts']
        t.search([]).unlink()
        xfind = self.env['account.move'].search([
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('type', 'in', ('in_invoice', 'in_refund'))
        ])
        for item in xfind:
            rate = self.env['res.currency.rate'].search([('name', '=', item.invoice_date)], limit=1).sell_rate
            if not rate:
                rate = 1

            if self.currency_id.id == 3:
                if item.currency_id.id == 3:
                    if item.partner_id.vendor == 'national':
                        base = item.amount_untaxed
                        credit = item.amount_tax
                        iva_with = item.vat_ret_id.vat_retentioned
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento
                        supplier_type = 'national'
                    else:
                        base = item.amount_untaxed
                        credit = item.amount_tax
                        iva_with = item.vat_ret_id.vat_retentioned
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento
                        supplier_type = 'international'
                else:
                    if item.partner_id.vendor == 'national':
                        base = item.amount_untaxed
                        credit = item.amount_tax
                        iva_with = item.vat_ret_id.vat_retentioned
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento
                        supplier_type = 'national'
                    else:
                        base = item.amount_untaxed * rate
                        credit = item.amount_tax * rate
                        iva_with = item.vat_ret_id.vat_retentioned * rate
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento * rate
                        supplier_type = 'international'
            else:
                if item.currency_id.id == 3:
                    if item.partner_id.vendor == 'national':
                        base = item.amount_untaxed / rate
                        credit = item.amount_tax / rate
                        iva_with = item.vat_ret_id.vat_retentioned / rate
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento / rate
                        supplier_type = 'national'
                    else:
                        base = item.amount_untaxed / rate
                        credit = item.amount_tax / rate
                        iva_with = item.vat_ret_id.vat_retentioned / rate
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento / rate
                        supplier_type = 'international'
                else:
                    if item.partner_id.vendor == 'national':
                        base = item.amount_untaxed
                        credit = item.amount_tax
                        iva_with = item.vat_ret_id.vat_retentioned
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento
                        supplier_type = 'national'
                    else:
                        base = item.amount_untaxed * rate
                        credit = item.amount_tax * rate
                        iva_with = item.vat_ret_id.vat_retentioned * rate
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento * rate
                        supplier_type = 'international'

            values = {
                'base': base,
                'credit': credit,
                'iva_with': iva_with,
                'iva_exempt': iva_exempt,
                'supplier_type': supplier_type
            }
            t.create(values)

    def credit_values(self):
        self.get_credits()
        xfind = self.env['temporal.credits.amounts'].search([])
        return xfind
    
    def get_debits(self):
        t = self.env['temporal.debits.amounts']
        t.search([]).unlink()
        xfind = self.env['account.move'].search([
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('type', 'in', ('out_invoice', 'out_refund'))
        ])
        for item in xfind:
            rate = self.env['res.currency.rate'].search([('name', '=', item.invoice_date)], limit=1).sell_rate
            if not rate:
                rate = 1

            if self.currency_id.id == 3:
                if item.currency_id.id == 3:
                    if item.partner_id.contribuyente:
                        base = item.amount_untaxed
                        debit = item.amount_tax
                        iva_with = item.vat_ret_id.vat_retentioned
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento
                        supplier_type = 'taxpayer'
                    else:
                        base = item.amount_untaxed
                        debit = item.amount_tax
                        iva_with = item.vat_ret_id.vat_retentioned
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento
                        supplier_type = 'international'
                else:
                    if item.partner_id.contribuyente:
                        base = item.amount_untaxed
                        debit = item.amount_tax
                        iva_with = item.vat_ret_id.vat_retentioned
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento
                        supplier_type = 'taxpayer'
                    else:
                        base = item.amount_untaxed * rate
                        debit = item.amount_tax * rate
                        iva_with = item.vat_ret_id.vat_retentioned * rate
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento * rate
                        supplier_type = 'international'
            else:
                if item.currency_id.id == 3:
                    if item.partner_id.contribuyente:
                        base = item.amount_untaxed / rate
                        debit = item.amount_tax / rate
                        iva_with = item.vat_ret_id.vat_retentioned / rate
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento / rate
                        supplier_type = 'national'
                    else:
                        base = item.amount_untaxed / rate
                        debit = item.amount_tax / rate
                        iva_with = item.vat_ret_id.vat_retentioned / rate
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento / rate
                        supplier_type = 'international'
                else:
                    if item.partner_id.contribuyente:
                        base = item.amount_untaxed
                        debit = item.amount_tax
                        iva_with = item.vat_ret_id.vat_retentioned
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento
                        supplier_type = 'national'
                    else:
                        base = item.amount_untaxed * rate
                        debit = item.amount_tax * rate
                        iva_with = item.vat_ret_id.vat_retentioned * rate
                        iva_exempt = 0
                        for line in item.alicuota_line_ids:
                            iva_exempt += line.total_exento * rate
                        supplier_type = 'international'

            values = {
                'base': base,
                'debit': debit,
                'iva_with': iva_with,
                'iva_exempt': iva_exempt,
                'supplier_type': supplier_type
            }
            t.create(values)

    def debit_values(self):
        self.get_debits()
        xfind = self.env['temporal.debits.amounts'].search([])
        return xfind
        
class VatDeclarationPayment(models.TransientModel):
    _name = 'temporal.credits.amounts'

    base = fields.Float()
    credit = fields.Float()
    iva_with = fields.Float()
    iva_exempt = fields.Float()
    supplier_type = fields.Selection(selection=[('national', 'National'), ('international', 'International')])
            
class VatDeclarationPayment(models.TransientModel):
    _name = 'temporal.debits.amounts'

    base = fields.Float()
    debit = fields.Float()
    iva_with = fields.Float()
    iva_exempt = fields.Float()
    supplier_type = fields.Selection(selection=[('exempt', 'Exempt'), ('exportation', 'Exportation'), ('taxpayer', 'Taxpayer'), ('user', 'Final User')])
    