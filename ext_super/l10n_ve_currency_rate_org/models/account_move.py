# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"
    
    os_currency_rate = fields.Float(string='Tipo de Cambio', default=1 ,digits=(12, 4))
    custom_rate = fields.Boolean(string='¿Usar Tasa de Cambio Personalizada?')
    move_aux_id=fields.Integer(compute='_compute_move_id')

    def _compute_move_id(self):
        self.move_aux_id=self.id

    def action_post(self):
        res = super().action_post()
        self.actualizar_balance()
        return res 
        
    def set_os_currency_rate(self):
        for selff in self:
            if selff.invoice_date:
                if not selff.custom_rate: 
                    rate = selff.env['res.currency.rate'].search([('currency_id', '=', selff.currency_id.id),('name','=',selff.invoice_date)], limit=1).sorted(lambda x: x.name)

                    if selff.currency_id.id != selff.company_currency_id.id:
                        if rate:
                            pass
                        else :
                            raise UserError(_("No existe tasa de cambio para  " + str(selff.invoice_date) + " registre el la siguiente ruta Contabilidad/Configuracion/Contabilidad/Monedas" ))

                    if rate :
                        exchange_rate =  1 / rate.rate
                        selff.os_currency_rate = exchange_rate
    
    @api.constrains('invoice_date','currency_id','')
    def _check_os_currency_rate(self):
        self.set_os_currency_rate()
    
    @api.onchange('invoice_date','currency_id')
    def _onchange_os_currency_rate(self):
        self.set_os_currency_rate()
    
    @api.onchange('os_currency_rate','amount_total')
    def _onchange_custom_rate(self):
        self.actualizar_balance()

    @api.constrains('os_currency_rate','amount_total')
    def _constrains_custom_rate(self):
        self.actualizar_balance()

    def actualizar_balance(self):
        for move in self:
            for item in move.line_ids:
                tasa = move.os_currency_rate
                if item.amount_currency > 0:
                    if move.currency_id.id == move.company_id.currency_id.id:
                        item.debit = item.amount_currency
                        item.debit_aux = item.amount_currency / tasa
                        ##item.amount_currency=item.amount_currency/tasa
                    else:

                        item.debit = item.amount_currency * tasa
                        item.debit_aux = item.amount_currency
                elif item.amount_currency < 0:
                    if move.currency_id.id == move.company_id.currency_id.id:
                        item.credit = (item.amount_currency) * (-1)
                        item.credit_aux = (item.amount_currency / tasa) * (-1)
                        ##item.amount_currency=(item.amount_currency/tasa)*(-1)
                    else:
                        item.credit = (item.amount_currency * tasa) * (-1)
                        item.credit_aux = (item.amount_currency) * (-1)


class AccountPayment(models.Model):
    _inherit = "account.payment"

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
                
                if self.rate == 1:
                    total += company.currency_id._convert(res['amount_residual'], currency, company, date)
                elif self.rate == 0:
                    total += company.currency_id._convert(res['amount_residual'], currency, company, date)
                else :
                    total += res['amount_residual'] / self.rate
        return total
