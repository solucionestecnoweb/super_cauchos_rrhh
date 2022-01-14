# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class modificacion_name_get(models.Model):
    _inherit = 'res.currency.rate'

    #@api.multi
    def name_get(self):
        result = []
        for res in self:
            name = str(res.rate_real) + ' - ' + str(res.hora)
            result.append((res.id, name))
        return result

class AccountInvoice(models.Model):
    _inherit = 'account.move'

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  track_visibility='always')
    amount_untaxed_bs = fields.Float('Base Imponible Bs', digits=(12, 2), compute='_compute_amount')
    amount_tax_bs = fields.Float('Impuesto Bs', digits=(12, 2), compute='_compute_amount')
    amount_total_bs = fields.Float('Total Bs', digits=(12, 2), compute='_compute_amount')
    residual_bs = fields.Float('Saldo', digits=(12, 2), compute='_compute_amount')
    tasa = fields.Many2one('res.currency.rate', string="Tasa Monetaria")

    '''@api.onchange('date_invoice', 'currency_id')
    def tasa_me(self):
        date_invoice = self.env['res.currency.rate'].search([('name', '=', self.date_invoice),
                                                                 ('currency_id', '=', self.currency_id.id)])
        if date_invoice:
            for a in date_invoice:
                self.tasa = a'''

    #@api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def _compute_amount(self):
        fecha = []
        pay = []
        if self.type == 'out_invoice' or self.type == 'in_invoice':
            sign = 1
        else:
            sign = -1
        if self.currency_id.rate_ids:
            #for a in self.currency_id.rate_ids:
            if self.currency_id.id == 4:
                date_invoice = self.env['res.currency.rate'].search([('currency_id', '=', self.currency_id.id),
                                                                     ('company_id', '=', self.company_id.id)])
            else:
                date_invoice = self.env['res.currency.rate'].search([('name', '=', self.date_invoice),
                                                                     ('currency_id', '=', self.currency_id.id),
                                                                     ('company_id', '=', self.company_id.id)])
            if date_invoice:
                for a in date_invoice:
                    fecha.append(a.id)
                fecha.append(a.id)
                fecha.sort(reverse=True)
                fecha_rate = self.env['res.currency.rate'].search([('id', '=', fecha[0])])
                if fecha_rate:
                    currency = self.env['res.currency'].search([('id', '=', self.currency_id.id)])
                    #self.currency_id.date = fecha_rate.name
                    #self.currency_id.rate_real = fecha_rate.rate_real
                    #self.currency_id.rate = fecha_rate.rate

                    b = fecha_rate.rate_real

                    round_curr = self.currency_id.round
                    self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
                    self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
                    self.amount_total = self.amount_untaxed + self.amount_tax
                    amount_total_company_signed = self.amount_total
                    amount_untaxed_signed = self.amount_untaxed
                    if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
                        currency_id = self.currency_id.with_context(date=self.date_invoice)
                        if self.state == 'draft':
                            self.amount_total_bs = amount_total_company_signed = self.amount_total * fecha_rate.rate_real * sign
                            self.amount_tax_bs = self.amount_tax * fecha_rate.rate_real * sign
                            self.amount_untaxed_bs = amount_untaxed_signed = self.amount_untaxed * fecha_rate.rate_real * sign
                        else:
                            self.amount_total_bs = amount_total_company_signed = self.amount_total * self.tasa.rate_real * sign
                            self.amount_tax_bs = self.amount_tax * self.tasa.rate_real * sign
                            self.amount_untaxed_bs = amount_untaxed_signed = self.amount_untaxed * self.tasa.rate_real * sign
                    sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
                    self.amount_total_bs = self.amount_total_company_signed = amount_total_company_signed * sign
                    self.amount_total_signed = self.amount_total * sign
                    self.amount_untaxed_bs = self.amount_untaxed_signed = amount_untaxed_signed * sign
                    if self.state == 'draft':
                        self.residual_bs= self.residual * fecha_rate.rate_real
                    else:
                        self.residual_bs = self.residual * self.tasa.rate_real
                    '''if self.currency_id != 4:
                        move_line = self.env['account.move.line'].search([('invoice_id', '=', self.id)])
                        move = self.env['account.move'].search([('id', '=', move_line[0].move_id.id)])
                        payment = self.env['account.payment'].search([('communication', '=', move.name)])
                        if payment.currency_id != 4:
                            self.residual_bs = self.amount_total_bs - payment.amount'''
            else:
                raise UserError('No hay tasas en esta fecha')

    #@api.multi
    def action_invoice_open(self):
        move_line = []
        fecha = []
        taxes = []
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        date_invoice = self.env['res.currency.rate'].search([('name', '=', self.date_invoice),
                                                             ('currency_id', '=', self.currency_id.id),
                                                             ('company_id', '=', self.company_id.id)])
        if date_invoice:
            for a in date_invoice:
                fecha.append(a.id)
            fecha.append(a.id)
            fecha.sort(reverse=True)
            fecha_rate = self.env['res.currency.rate'].search([('id', '=', fecha[0])])
            if fecha_rate:
                self.tasa = fecha_rate
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.state != 'draft'):
            raise UserError(_("Invoice must be in draft state in order to validate it."))
        if to_open_invoices.filtered(lambda inv: inv.amount_total < 0):
            raise UserError(_(
                "You cannot validate an invoice with a negative total amount. You should create a credit note instead."))
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        a = self.move_id
      #  b = self.product_id
        c = self.id

        account_invoice_line = self.env['account.invoice.line'].search([('invoice_id', '=', self.id)])
        move_id = self.env['account.move.line'].search([('move_id', '=', self.move_id.id)])
        move = self.env['account.move'].search([('id', '=', self.move_id.id)])
        move.write({'amount': self.amount_total_bs,
                    'state': 'draft'})
        if self.type == 'out_invoice' or self.type == 'in_invoice':
            sign = 1
        else:
            sign = -1
        if self.type == 'out_invoice' or self.type == 'in_refund':

            for a in move_id:
                move_line.append(a.id)
            move_line.sort(reverse=True)

            for u in move_id:
                tax = 0.00
                for m in self.invoice_line_ids:
                    if u.product_id.id == m.product_id.id:
                        u.write({'debit': 0.00,
                                 'credit': m.price_subtotal_signed * sign})

                    if u.name == m.invoice_line_tax_ids.name:
                        tax += m.tax
                        u.write({'debit': 0.00,
                                 'credit': tax})

                    if move_line[0] == u.id:
                        u.write({'debit': self.amount_total_bs * sign,
                                 'credit': 0.00})

        elif self.type == 'in_invoice' or self.type == 'out_refund':
            for a in move_id:
                move_line.append(a.id)
            move_line.sort(reverse=True)

            for u in move_id:
                tax = 0.00
                for m in self.invoice_line_ids:
                    if u.product_id.id == m.product_id.id:
                        u.write({'credit': 0.00,
                                 'debit': m.price_subtotal_signed * sign})

                    if u.name == m.invoice_line_tax_ids.name:
                        tax += m.tax
                        u.write({'credit': 0.00,
                                 'debit': tax})

                    if move_line[0] == u.id:
                        u.write({'credit': self.amount_total_bs * sign,
                                 'debit': 0.00})


        move.write({'state': 'posted'})
        return to_open_invoices.invoice_validate()

#Heredamos la vista de las lineas para presentar los totales en moneda extranjera...
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    tasa_me = fields.Float('Precio Total  Bs.', digits=(12, 2), compute='_compute_price')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True, related_sudo=False)
    tax = fields.Float('Impuestos', digits=(12, 2), compute='_compute_price')
    tasa = fields.Many2one('res.currency.rate', string="Tasa Monetaria")

    #@api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
                 'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
                 'invoice_id.date_invoice', 'invoice_id.date')
    def _compute_price(self):
        fecha = []
        if self.invoice_id.currency_id.rate_ids:
            # for a in self.currency_id.rate_ids:
            if self.invoice_id.currency_id.id == 4:
                date_invoice = self.env['res.currency.rate'].search([('currency_id', '=', self.currency_id.id),
                                                                     ('company_id', '=', self.company_id.id)])
            else:
                date_invoice = self.env['res.currency.rate'].search([('name', '=', self.invoice_id.date_invoice),
                                                                     ('currency_id', '=', self.currency_id.id),
                                                                     ('company_id', '=', self.company_id.id)])

            if date_invoice:
                for a in date_invoice:
                    fecha.append(a.id)
                fecha.append(a.id)
                fecha.sort(reverse=True)
                fecha_rate = self.env['res.currency.rate'].search([('id', '=', fecha[0])])
                if fecha_rate:
                    date = self.invoice_id._get_currency_rate_date()
                    currency = self.invoice_id and self.invoice_id.currency_id or None
                    price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
                    taxes = False
                    if self.invoice_line_tax_ids:
                        taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id,
                                                                      partner=self.invoice_id.partner_id)
                    self.tasa_me = self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
                    self.price_total = taxes['total_included'] if taxes else self.price_subtotal
                    if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
                        if self.invoice_id.state == 'draft':
                            self.tasa_me = price_subtotal_signed = price_subtotal_signed * fecha_rate.rate_real
                        else:
                            self.tasa_me = price_subtotal_signed = price_subtotal_signed * self.invoice_id.tasa.rate_real
                    sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
                    self.price_subtotal_signed = price_subtotal_signed * sign
                    if self.invoice_line_tax_ids:
                        self.tax = (self.invoice_line_tax_ids.amount * self.tasa_me) / 100
