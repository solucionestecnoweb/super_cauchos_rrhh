# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _

from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from datetime import date, timedelta
from itertools import groupby
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import json
import re

class AccountMove(models.Model):
    _inherit = "account.move"
    
    os_currency_rate = fields.Float(string='Tipo de Cambio', default=1 ,digits=(12, 4))
    custom_rate = fields.Boolean(string='¿Usar Tasa de Cambio Personalizada?')
    move_aux_id=fields.Integer(compute='_compute_move_id')

    def _compute_move_id(self):
        self.move_aux_id=self.id
    
    @api.constrains('os_currency_rate','amount_total','currency_id','journal_id','state')
    def _os_constrains_currency(self):
        self.set_os_currency_rate()

    @api.onchange('os_currency_rate','amount_total','currency_id','journal_id')
    def _os_onchange_currency(self):
        self.set_os_currency_rate()
    
    def set_os_currency_rate(self): 
        for invoice in self:
            tipos  = ('out_invoice','out_refund','out_receipt','in_invoice','in_refund','in_receipt')
            if invoice.type in tipos:
                for line in invoice.line_ids :
                    line._recompute_debit_credit_from_amount_currency()

    @api.constrains('amount_total','amount_residual')
    def amount_residual_anadir(self):
        pago=monto=0
        for selff in self:
            cuenta_pro=selff.partner_id.property_account_payable_id.id
            cuenta_cli=selff.partner_id.property_account_receivable_id.id
            # CLIENTES
            if selff.type in ('out_invoice','out_refund'): 
                for rec in selff.line_ids:
                    if rec.account_id.id==cuenta_cli:
                        id_move=rec.id
                cursor=selff.env['account.partial.reconcile'].search([('debit_move_id','=',id_move)])
                if cursor:
                    for det in cursor:
                        ####
                        busca_tasa=selff.env['account.move.line'].search([('id','=',det.credit_move_id.id)])
                        if busca_tasa:
                            for tasa in busca_tasa:
                                valor_tasa=tasa.move_id.os_currency_rate
                        ####
                        monto=monto+(det.amount/valor_tasa)
                        det.amount_currency=(det.amount/valor_tasa)
                aux=selff.amount_total
                selff.amount_residual=aux-monto
            # PROVEEDOES
            if selff.type in ('in_invoice','in_refund'): 
                for rec in selff.line_ids:
                    if rec.account_id.id==cuenta_pro:
                        id_move=rec.id
                cursor=selff.env['account.partial.reconcile'].search([('credit_move_id','=',id_move)])
                if cursor:
                    for det in cursor:
                        ####
                        busca_tasa=selff.env['account.move.line'].search([('id','=',det.debit_move_id.id)])
                        if busca_tasa:
                            for tasa in busca_tasa:
                                valor_tasa=tasa.move_id.os_currency_rate
                        ####
                        monto=monto+(det.amount_currency/valor_tasa)
                        det.amount_currency=(det.amount/valor_tasa)
                aux=selff.amount_total
                selff.amount_residual=aux-monto
            
    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = json.dumps(False)
            move.invoice_has_outstanding = False

            if move.state != 'posted' or move.invoice_payment_state != 'not_paid' or not move.is_invoice(include_receipts=True):
                continue
            pay_term_line_ids = move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))

            domain = [('account_id', 'in', pay_term_line_ids.mapped('account_id').ids),
                      '|', ('move_id.state', '=', 'posted'), '&', ('move_id.state', '=', 'draft'), ('journal_id.post_at', '=', 'bank_rec'),
                      ('partner_id', '=', move.commercial_partner_id.id),
                      ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0),
                      ('amount_residual_currency', '!=', 0.0)]

            if move.is_inbound():
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'move_id': move.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = move.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency

                    if line.currency_id and line.currency_id == move.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        ## INICIO MODIFICACION CODIGO PARA TASA PERSONALIZADA
                        if line.move_id.custom_rate!=True:
                            currency = line.company_id.currency_id
                            amount_to_show = currency._convert(abs(line.amount_residual), move.currency_id, move.company_id,
                                                               line.date or fields.Date.today())
                        else: 
                            amount_to_show=abs(line.amount_residual/line.move_id.os_currency_rate)
                        ## FIN MODIFICACION CODIGO PARA TASA PERSONALIZADA
                    if float_is_zero(amount_to_show, precision_rounding=move.currency_id.rounding):
                        continue
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, move.currency_id.decimal_places],
                        'payment_date': fields.Date.to_string(line.date),
                    })
                info['title'] = type_payment
                move.invoice_outstanding_credits_debits_widget = json.dumps(info)
                move.invoice_has_outstanding = True
                #move.amount_residual=amount_to_show

    def _get_reconciled_info_JSON_values(self):
        self.ensure_one()
        foreign_currency = self.currency_id if self.currency_id != self.company_id.currency_id else False

        reconciled_vals = []
        pay_term_line_ids = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        partials = pay_term_line_ids.mapped('matched_debit_ids') + pay_term_line_ids.mapped('matched_credit_ids')
        for partial in partials:
            counterpart_lines = partial.debit_move_id + partial.credit_move_id
            counterpart_line = counterpart_lines.filtered(lambda line: line not in self.line_ids)

            if foreign_currency and partial.currency_id == foreign_currency:
                ##  INICIO MODIFICACION CODIGO PARA TASA PERSONALIZADA
                if counterpart_line.move_id.custom_rate!=True:
                    amount = partial.amount_currency
                else:
                    amount = abs(counterpart_line.move_id.amount_total_signed/counterpart_line.move_id.os_currency_rate)
                ## FIN MODIFICACION CODIGO PARA TASA PERSONALIZADA
            else:
                amount = partial.company_currency_id._convert(partial.amount, self.currency_id, self.company_id, self.date)

            if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                continue
            #raise UserError(_('partials: %s')%counterpart_line.move_id.id)
            ref = counterpart_line.move_id.name
            if counterpart_line.move_id.ref:
                ref += ' (' + counterpart_line.move_id.ref + ')'

            reconciled_vals.append({
                'name': counterpart_line.name,
                'journal_name': counterpart_line.journal_id.name,
                'amount': amount,
                'currency': self.currency_id.symbol,
                'digits': [69, self.currency_id.decimal_places],
                'position': self.currency_id.position,
                'date': counterpart_line.date,
                'payment_id': counterpart_line.id,
                'account_payment_id': counterpart_line.payment_id.id,
                'payment_method_name': counterpart_line.payment_id.payment_method_id.name if counterpart_line.journal_id.type == 'bank' else None,
                'move_id': counterpart_line.move_id.id,
                'ref': ref,
            })
            #self.amount_residual_anadir(amount)
        return reconciled_vals

    """@api.depends('type', 'line_ids.amount_residual')
    def _compute_payments_widget_reconciled_info(self):
        for move in self:
            if move.state != 'posted' or not move.is_invoice(include_receipts=True):
                move.invoice_payments_widget = json.dumps(False)
                continue
            reconciled_vals = move._get_reconciled_info_JSON_values()
            if reconciled_vals:
                info = {
                    'title': _('Less Payment'),
                    'outstanding': False,
                    'content': reconciled_vals,
                }
                move.invoice_payments_widget = json.dumps(info, default=date_utils.json_default)
            else:
                move.invoice_payments_widget = json.dumps(False)"""

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _recompute_debit_credit_from_amount_currency(self):
        for line in self:
            # Recompute the debit/credit based on amount_currency/currency_id and date.

            company_currency = line.account_id.company_id.currency_id
            balance = line.amount_currency
            if line.currency_id and company_currency and line.currency_id != company_currency:
                if line.move_id.custom_rate :
                    balance = balance * line.move_id.os_currency_rate
                else : 
                    balance = line.currency_id._convert(balance, company_currency, line.account_id.company_id, line.move_id.date or fields.Date.today())
                line.debit = balance > 0 and balance or 0.0
                line.credit = balance < 0 and -balance or 0.0

    # def action_post(self):
    #     res = super().action_post()
    #     self.actualizar_balance()
    #     return res 
        
    # def set_os_currency_rate(self):
    #     for selff in self:
    #         if selff.invoice_date:
    #             if not selff.custom_rate: 
    #                 rate = selff.env['res.currency.rate'].search([('currency_id', '=', selff.currency_id.id),('name','=',selff.invoice_date)], limit=1).sorted(lambda x: x.name)

    #                 if selff.currency_id.id != selff.company_currency_id.id:
    #                     if rate:
    #                         pass
    #                     else :
    #                         raise UserError(_("No existe tasa de cambio para  " + str(selff.invoice_date) + " registre el la siguiente ruta Contabilidad/Configuracion/Contabilidad/Monedas" ))

    #                 if rate :
    #                     exchange_rate =  1 / rate.rate
    #                     selff.os_currency_rate = exchange_rate
    
    # @api.constrains('invoice_date','currency_id','')
    # def _check_os_currency_rate(self):
    #     self.set_os_currency_rate()
    
    # @api.onchange('invoice_date','currency_id')
    # def _onchange_os_currency_rate(self):
    #     self.set_os_currency_rate()
    
    # @api.onchange('os_currency_rate','amount_total')
    # def _onchange_custom_rate(self):
    #     self.actualizar_balance()

    # @api.constrains('os_currency_rate','amount_total')
    # def _constrains_custom_rate(self):
    #     self.actualizar_balance()

    # def actualizar_balance(self):
    #     for move in self:
    #         for item in move.line_ids:
    #             tasa = move.os_currency_rate
    #             if item.amount_currency > 0:
    #                 if move.currency_id.id == move.company_id.currency_id.id:
    #                     item.debit = item.amount_currency
    #                     item.debit_aux = item.amount_currency / tasa
    #                     ##item.amount_currency=item.amount_currency/tasa
    #                 else:

    #                     item.debit = item.amount_currency * tasa
    #                     item.debit_aux = item.amount_currency
    #             elif item.amount_currency < 0:
    #                 if move.currency_id.id == move.company_id.currency_id.id:
    #                     item.credit = (item.amount_currency) * (-1)
    #                     item.credit_aux = (item.amount_currency / tasa) * (-1)
    #                     ##item.amount_currency=(item.amount_currency/tasa)*(-1)
    #                 else:
    #                     item.credit = (item.amount_currency * tasa) * (-1)
    #                     item.credit_aux = (item.amount_currency) * (-1)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def post(self):
        res = super().post()
        return res    

    @api.constrains('move_id','state')
    def _os_constrains_move_id_rate(self):
        if len(self.move_line_ids) > 0:
            self.move_line_ids[0].move_id.os_currency_rate = self.rate
            self.move_line_ids[0].move_id.custom_rate = True

    @api.onchange('invoice_ids', 'amount', 'payment_date', 'currency_id', 'payment_type','rate')
    def _onchange_os_currency_rate(self):
        self._compute_payment_difference()
        
    @api.depends('invoice_ids', 'amount', 'payment_date', 'currency_id', 'payment_type','rate')
    def _compute_payment_difference(self):
        draft_payments = self.filtered(lambda p: p.invoice_ids and p.state == 'draft')
        for pay in draft_payments:
            payment_amount = -pay.amount if pay.payment_type == 'outbound' else pay.amount
            pay.payment_difference = pay._compute_payment_amount(pay.invoice_ids, pay.currency_id, pay.journal_id, pay.payment_date) - payment_amount
        (self - draft_payments).payment_difference = 0
    
    def _prepare_payment_moves(self):
        ''' Prepare the creation of journal entries (account.move) by creating a list of python dictionary to be passed
        to the 'create' method.

        Example 1: outbound with write-off:

        Account             | Debit     | Credit
        ---------------------------------------------------------
        BANK                |   900.0   |
        RECEIVABLE          |           |   1000.0
        WRITE-OFF ACCOUNT   |   100.0   |

        Example 2: internal transfer from BANK to CASH:

        Account             | Debit     | Credit
        ---------------------------------------------------------
        BANK                |           |   1000.0
        TRANSFER            |   1000.0  |
        CASH                |   1000.0  |
        TRANSFER            |           |   1000.0

        :return: A list of Python dictionary to be passed to env['account.move'].create.
        '''
        all_move_vals = []
        for payment in self:
            company_currency = payment.company_id.currency_id
            move_names = payment.move_name.split(payment._get_move_name_transfer_separator()) if payment.move_name else None

            # Compute amounts.
            write_off_amount = payment.payment_difference_handling == 'reconcile' and -payment.payment_difference or 0.0
            if payment.payment_type in ('outbound', 'transfer'):
                counterpart_amount = payment.amount
                liquidity_line_account = payment.journal_id.default_debit_account_id
            else:
                counterpart_amount = -payment.amount
                liquidity_line_account = payment.journal_id.default_credit_account_id

            # Manage currency.
            if payment.currency_id == company_currency:
                # Single-currency.
                balance = counterpart_amount
                write_off_balance = write_off_amount
                counterpart_amount = write_off_amount = 0.0
                currency_id = False
            else:
                # Multi-currencies.

                #balance = payment.currency_id._convert(counterpart_amount, company_currency, payment.company_id, payment.payment_date)
                #write_off_balance = payment.currency_id._convert(write_off_amount, company_currency, payment.company_id, payment.payment_date)
                currency_id = payment.currency_id.id
                #Jose Blanco
                balance = counterpart_amount * payment.rate
                write_off_balance =  write_off_amount  * payment.rate
            # Manage custom currency on journal for liquidity line.
            if payment.journal_id.currency_id and payment.currency_id != payment.journal_id.currency_id:
                # Custom currency on journal.
                if payment.journal_id.currency_id == company_currency:
                    # Single-currency
                    liquidity_line_currency_id = False
                else:
                    liquidity_line_currency_id = payment.journal_id.currency_id.id
                #liquidity_amount = company_currency._convert(
                #   balance, payment.journal_id.currency_id, payment.company_id, payment.payment_date)
                # 
                liquidity_amount = balance / payment.rate
            else: 
                # Use the payment currency.
                liquidity_line_currency_id = currency_id
                liquidity_amount = counterpart_amount

            # Compute 'name' to be used in receivable/payable line.
            rec_pay_line_name = ''
            if payment.payment_type == 'transfer':
                rec_pay_line_name = payment.name
            else:
                if payment.partner_type == 'customer':
                    if payment.payment_type == 'inbound':
                        rec_pay_line_name += _("Customer Payment")
                    elif payment.payment_type == 'outbound':
                        rec_pay_line_name += _("Customer Credit Note")
                elif payment.partner_type == 'supplier':
                    if payment.payment_type == 'inbound':
                        rec_pay_line_name += _("Vendor Credit Note")
                    elif payment.payment_type == 'outbound':
                        rec_pay_line_name += _("Vendor Payment")
                if payment.invoice_ids:
                    rec_pay_line_name += ': %s' % ', '.join(payment.invoice_ids.mapped('name'))

            # Compute 'name' to be used in liquidity line.
            if payment.payment_type == 'transfer':
                liquidity_line_name = _('Transfer to %s') % payment.destination_journal_id.name
            else:
                liquidity_line_name = payment.name

            invoice_currency =  payment.invoice_ids[0].currency_id.id if len(payment.invoice_ids) > 0 else False
            # ==== 'inbound' / 'outbound' ====
            if  len(payment.invoice_ids) > 0 and payment.currency_id.id == payment.company_id.currency_id.id and  invoice_currency != payment.company_id.currency_id.id:
                
                move_vals = {
                    'date': payment.payment_date,
                    'ref': payment.communication,
                    'journal_id': payment.journal_id.id,
                    'currency_id': payment.journal_id.currency_id.id or payment.company_id.currency_id.id,
                    'partner_id': payment.partner_id.id,
                    'line_ids': [
                        # Receivable / Payable / Transfer line.
                        (0, 0, {
                            'name': rec_pay_line_name,
                            'amount_currency': (payment.amount / payment.rate) * -1 if payment.payment_type == "inbound" else   (payment.amount / payment.rate),
                            'currency_id': payment.invoice_ids[0].currency_id.id if payment.invoice_ids[0] else payment.journal_id.currency_id.id   ,
                            'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                            'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': payment.destination_account_id.id,
                            'payment_id': payment.id,
                        }),
                        # Liquidity line.
                        (0, 0, {
                            'name': liquidity_line_name,
                            'amount_currency': -liquidity_amount if liquidity_line_currency_id else 0.0,
                            'currency_id': liquidity_line_currency_id,
                            'debit': balance < 0.0 and -balance or 0.0,
                            'credit': balance > 0.0 and balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': liquidity_line_account.id,
                            'payment_id': payment.id,
                        }),
                    ],
                }
            else :
                move_vals = {
                    'date': payment.payment_date,
                    'ref': payment.communication,
                    'journal_id': payment.journal_id.id,
                    'currency_id': payment.journal_id.currency_id.id or payment.company_id.currency_id.id,
                    'partner_id': payment.partner_id.id,
                    'line_ids': [
                        # Receivable / Payable / Transfer line.
                        (0, 0, {
                            'name': rec_pay_line_name,
                            'amount_currency': counterpart_amount + write_off_amount if payment.invoice_ids.currency_id != payment.company_id.currency_id.id else 0.0,
                            'currency_id': payment.invoice_ids.currency_id.id if payment.invoice_ids.currency_id != payment.company_id.currency_id.id else False,
                            'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                            'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': payment.destination_account_id.id,
                            'payment_id': payment.id,
                        }),
                        # Liquidity line.
                        (0, 0, {
                            'name': liquidity_line_name,
                            'amount_currency': -liquidity_amount if liquidity_line_currency_id else 0.0,
                            'currency_id': liquidity_line_currency_id,
                            'debit': balance < 0.0 and -balance or 0.0,
                            'credit': balance > 0.0 and balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': liquidity_line_account.id,
                            'payment_id': payment.id,
                        }),
                    ],
                }
            if write_off_balance:
                # Write-off line.
                move_vals['line_ids'].append((0, 0, {
                    'name': payment.writeoff_label,
                    'amount_currency': -write_off_amount,
                    'currency_id': currency_id,
                    'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
                    'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
                    'date_maturity': payment.payment_date,
                    'partner_id': payment.partner_id.commercial_partner_id.id,
                    'account_id': payment.writeoff_account_id.id,
                    'payment_id': payment.id,
                }))

            if move_names:
                move_vals['name'] = move_names[0]

            all_move_vals.append(move_vals)

            # ==== 'transfer' ====
            if payment.payment_type == 'transfer':
                journal = payment.destination_journal_id

                # Manage custom currency on journal for liquidity line.
                if journal.currency_id and payment.currency_id != journal.currency_id:
                    # Custom currency on journal.
                    liquidity_line_currency_id = journal.currency_id.id
                    transfer_amount = company_currency._convert(balance, journal.currency_id, payment.company_id, payment.payment_date)
                else:
                    # Use the payment currency.
                    liquidity_line_currency_id = currency_id
                    transfer_amount = counterpart_amount

                transfer_move_vals = {
                    'date': payment.payment_date,
                    'ref': payment.communication,
                    'partner_id': payment.partner_id.id,
                    'journal_id': payment.destination_journal_id.id,
                    'line_ids': [
                        # Transfer debit line.
                        (0, 0, {
                            'name': payment.name,
                            'amount_currency': -counterpart_amount if currency_id else 0.0,
                            'currency_id': currency_id,
                            'debit': balance < 0.0 and -balance or 0.0,
                            'credit': balance > 0.0 and balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': payment.company_id.transfer_account_id.id,
                            'payment_id': payment.id,
                        }),
                        # Liquidity credit line.
                        (0, 0, {
                            'name': _('Transfer from %s') % payment.journal_id.name,
                            'amount_currency': transfer_amount if liquidity_line_currency_id else 0.0,
                            'currency_id': liquidity_line_currency_id,
                            'debit': balance > 0.0 and balance or 0.0,
                            'credit': balance < 0.0 and -balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': payment.destination_journal_id.default_credit_account_id.id,
                            'payment_id': payment.id,
                        }),
                    ],
                }

                if move_names and len(move_names) == 2:
                    transfer_move_vals['name'] = move_names[1]

                all_move_vals.append(transfer_move_vals)
        return all_move_vals


    @api.model
    def _compute_payment_amount(self, invoices, currency, journal, date):
        '''Compute the total amount for the payment wizard.

        :param invoices:    Invoices on which compute the total as an account.invoice recordset.
        :param currency:    The payment's currency as a res.currency record.
        :param journal:     The payment's journal as an account.journal record.
        :param date:        The payment's date as a datetime.date object.
        :return:            The total amount to pay the invoices.
        '''
        company = journal.company_id
        currency = currency or journal.currency_id or company.currency_id
        date = date or fields.Date.today()

        if not invoices:
            return 0.0

        self.env['account.move'].flush(['type', 'currency_id'])
        self.env['account.move.line'].flush(['amount_residual', 'amount_residual_currency', 'move_id', 'account_id'])
        self.env['account.account'].flush(['user_type_id'])
        self.env['account.account.type'].flush(['type'])
        self._cr.execute('''
            SELECT
                move.type AS type,
                move.currency_id AS currency_id,
                SUM(line.amount_residual) AS amount_residual,
                SUM(line.amount_residual_currency) AS residual_currency
            FROM account_move move
            LEFT JOIN account_move_line line ON line.move_id = move.id
            LEFT JOIN account_account account ON account.id = line.account_id
            LEFT JOIN account_account_type account_type ON account_type.id = account.user_type_id
            WHERE move.id IN %s
            AND account_type.type IN ('receivable', 'payable')
            GROUP BY move.id, move.type
        ''', [tuple(invoices.ids)])
        query_res = self._cr.dictfetchall()

        total = 0.0
        for res in query_res:
            move_currency = self.env['res.currency'].browse(res['currency_id'])
            if move_currency == currency and move_currency != company.currency_id:
                total += res['residual_currency']
            else:
                invoices.currency_id
                if self.rate == 1:
                    total += company.currency_id._convert(res['amount_residual'], currency, company, date)
                elif self.rate == 0:
                    total += company.currency_id._convert(res['amount_residual'], currency, company, date)
                elif invoices[0].currency_id != company.currency_id and self.currency_id == company.currency_id: 
                    total += res['residual_currency'] * self.rate
                else :
                    total += res['amount_residual'] / self.rate
        return total