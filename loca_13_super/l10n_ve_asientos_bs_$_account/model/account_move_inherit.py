# -*- coding: utf-8 -*-


import logging
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError




class AccountMove(models.Model):
    _inherit = 'account.move'

    amount_total_signed_aux_bs=fields.Float(compute="_compute_monto_conversion")
    amount_total_signed_bs=fields.Float()
    amount_untaxed_signed_bs=fields.Float(compute="_compute_monto_conversion_untaxed")
    amount_residual_signed_bs=fields.Float(compute="_compute_monto_conversion_residual")
    amount_tax_bs = fields.Float(compute="_compute_monto_conversion_tax")

    def _compute_monto_conversion(self):
        valor=0
        self.env.company.currency_secundaria_id.id
        for selff in self:
            if self.env.company.currency_secundaria_id.id==selff.currency_id.id:
                #valor=selff.amount_total
                valor=abs(selff.amount_total_signed/(selff.os_currency_rate+0.00000000000000000001)) # campo para jose gregorio
            if self.env.company.currency_id.id==selff.currency_id.id:
                if selff.custom_rate!=True:
                    lista_tasa = selff.env['res.currency.rate'].search([('currency_id', '=', self.env.company.currency_secundaria_id.id),('name','<=',selff.date)],order='id ASC')
                    if lista_tasa:
                        for det in lista_tasa:
                            valor=selff.amount_total_signed*det.rate
                else:
                    valor=abs(selff.amount_total_signed/(selff.os_currency_rate+0.0000000000000000001))
            selff.amount_total_signed_aux_bs=valor
            selff.amount_total_signed_bs=valor

    def _compute_monto_conversion_untaxed(self):
        valor=0
        self.env.company.currency_secundaria_id.id
        for selff in self:
            if self.env.company.currency_secundaria_id.id==selff.currency_id.id:
                #valor=selff.amount_untaxed
                valor=abs(selff.amount_untaxed_signed/(selff.os_currency_rate+0.000000000000001)) # campo para jose gregorio
            if self.env.company.currency_id.id==selff.currency_id.id:
                if selff.custom_rate!=True:
                    lista_tasa = selff.env['res.currency.rate'].search([('currency_id', '=', self.env.company.currency_secundaria_id.id),('name','<=',selff.date)],order='id ASC')
                    if lista_tasa:
                        for det in lista_tasa:
                            valor=selff.amount_untaxed_signed*det.rate
                else:
                    valor=abs(selff.amount_untaxed_signed/(selff.os_currency_rate+0.0000000000000000001))
            selff.amount_untaxed_signed_bs=valor

    def _compute_monto_conversion_residual(self):
        valor=0
        self.env.company.currency_secundaria_id.id
        for selff in self:
            if self.env.company.currency_secundaria_id.id==selff.currency_id.id:
                #valor=selff.amount_residual
                valor=abs(selff.amount_residual_signed/(selff.os_currency_rate+0.0000000000000000001)) # campo para jose gregorio
            if self.env.company.currency_id.id==selff.currency_id.id:
                if selff.custom_rate!=True:
                    lista_tasa = selff.env['res.currency.rate'].search([('currency_id', '=', self.env.company.currency_secundaria_id.id),('name','<=',selff.date)],order='id ASC')
                    if lista_tasa:
                        for det in lista_tasa:
                            valor=selff.amount_residual_signed*det.rate
                else:
                    valor=abs(selff.amount_residual_signed/(selff.os_currency_rate+0.0000000000000000001))
            selff.amount_residual_signed_bs=valor

    def _compute_monto_conversion_tax(self):
        valor=0
        self.env.company.currency_secundaria_id.id
        for selff in self:
            if self.env.company.currency_secundaria_id.id==selff.currency_id.id:
                #valor=selff.amount_tax
                valor=abs(selff.amount_tax_signed/(selff.os_currency_rate+0.000000000000000001)) # campo para jose gregorio
            if self.env.company.currency_id.id==selff.currency_id.id:
                if selff.custom_rate!=True:
                    lista_tasa = selff.env['res.currency.rate'].search([('currency_id', '=', self.env.company.currency_secundaria_id.id),('name','<=',selff.date)],order='id ASC')
                    if lista_tasa:
                        for det in lista_tasa:
                            valor=selff.amount_tax_signed*det.rate
                else:
                    valor=abs(selff.amount_tax_signed/(selff.os_currency_rate+0.0000000000000000001))
            selff.amount_tax_bs=valor



class  AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    balance_aux=fields.Float(compute='_compute_balance_conversion')
    credit_aux=fields.Float(compute='_compute_monto_credit_conversion')
    debit_aux=fields.Float(compute='_compute_monto_debit_conversion')
    asiento_gastos = fields.Boolean()
    tasa_gastos = fields.Float()

    def _compute_monto_credit_conversion(self):
        valor=0
        self.env.company.currency_secundaria_id.id
        for selff in self:
            if selff.asiento_gastos!=True:
                if selff.currency_id.id==self.env.company.currency_secundaria_id.id:
                    if selff.credit!=0:
                        #tasa= abs(selff.balance / selff.amount_currency )if  abs(selff.amount_currency) > 0 else selff.balance
                        tasa= selff.move_id.os_currency_rate
                        valor=tasa
                else:
                    if selff.move_id.custom_rate!=True:
                        lista_tasa = selff.env['res.currency.rate'].search([('currency_id', '=', self.env.company.currency_secundaria_id.id),('name','<=',selff.move_id.date)],order='id ASC')
                        if lista_tasa:
                            for det in lista_tasa:
                                valor=(1/det.rate)
                    else:
                        if selff.credit!=0:
                            tasa= selff.move_id.os_currency_rate
                            valor=tasa
                selff.credit_aux=selff.credit/(valor+0.0000000000001)
            else:
                selff.credit_aux=selff.credit/selff.tasa_gastos


    def _compute_monto_debit_conversion(self):
        valor=0
        #self.debit_aux=0
        self.env.company.currency_secundaria_id.id
        for selff in self:
            if selff.asiento_gastos!=True:
                if selff.currency_id.id==self.env.company.currency_secundaria_id.id:
                    if selff.debit!=0:
                        #tasa= abs(selff.balance / selff.amount_currency ) if  abs(selff.amount_currency) > 0 else selff.balance
                        tasa= selff.move_id.os_currency_rate
                        valor=tasa
                else:
                    if selff.move_id.custom_rate!=True:
                        lista_tasa = selff.env['res.currency.rate'].search([('currency_id', '=', self.env.company.currency_secundaria_id.id),('name','<=',selff.move_id.date)],order='id ASC')
                        if lista_tasa:
                            for det in lista_tasa:
                                valor=(1/det.rate)
                    else:
                        if selff.debit!=0:
                            tasa= selff.move_id.os_currency_rate
                            valor=tasa
                selff.debit_aux=selff.debit/(valor+0.0000000000001)
            else:
                selff.debit_aux=selff.debit/selff.tasa_gastos

    def _compute_balance_conversion(self):
        valor=0
        self.env.company.currency_secundaria_id.id
        for selff in self:
            if selff.currency_id.id==self.env.company.currency_secundaria_id.id:
                valor=selff.amount_currency
            else:
                lista_tasa = selff.env['res.currency.rate'].search([('currency_id', '=', selff.env.company.currency_secundaria_id.id),('name','<=',selff.move_id.date)],order='id ASC')
                if lista_tasa:
                    for det in lista_tasa:
                        valor=(selff.debit*det.rate)
            selff.balance_aux=abs(valor)
        