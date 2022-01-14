# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import copy
import ast

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.tools.misc import formatLang
from odoo.tools import float_is_zero, ustr
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class FormulaContext(dict):
    def __init__(self, reportLineObj, linesDict, currency_table, financial_report, curObj=None, only_sum=False, *data):
        self.reportLineObj = reportLineObj
        self.curObj = curObj
        self.linesDict = linesDict
        self.currency_table = currency_table
        self.only_sum = only_sum
        self.financial_report = financial_report
        return super(FormulaContext, self).__init__(data)

#class ReportAccountFinancialReport(models.Model):
    #_inherit = "account.financial.html.report"
    #_description = "Account Report (HTML)"


class FormulaLine(object):
    def __init__(self, obj, currency_table, financial_report, type='balance', linesDict=None):
        if linesDict is None:
            linesDict = {}
        fields = dict((fn, 0.0) for fn in ['debit', 'credit','balance','debit_aux','credit_aux','balance_aux'])
        if type == 'balance':
            fields = obj._get_balance(linesDict, currency_table, financial_report)[0]
            #raise UserError(_('fields = %s')%fields)
            linesDict[obj.code] = self
        elif type in ['sum', 'sum_if_pos', 'sum_if_neg']:
            if type == 'sum_if_neg':
                obj = obj.with_context(sum_if_neg=True)
            if type == 'sum_if_pos':
                obj = obj.with_context(sum_if_pos=True)
            if obj._name == 'account.financial.html.report.line':
                fields = obj._get_sum(currency_table, financial_report)
                #raise UserError(_('fields2 = %s')%fields)
                self.amount_residual = fields['amount_residual']
            elif obj._name == 'account.move.line':
                self.amount_residual = 0.0
                field_names = ['debit', 'credit','balance','debit_aux','credit_aux','balance_aux','amount_residual']
                res = obj.env['account.financial.html.report.line']._compute_line(currency_table, financial_report)
                for field in field_names:
                    fields[field] = res[field]
                self.amount_residual = fields['amount_residual']
        elif type == 'not_computed':
            for field in fields:
                fields[field] = obj.get(field, 0)
            self.amount_residual = obj.get('amount_residual', 0)
        elif type == 'null':
            self.amount_residual = 0.0
        self.balance = fields['balance'] # 66
        self.credit = fields['credit'] # darrell resumen ejecutivo
        self.debit = fields['debit'] # darrell resumen ejecutivo
        self.balance_aux=345




# ****************************************************************************************
class AccountFinancialReportLine(models.Model):
    _inherit = "account.financial.html.report.line"

    def total_balance(self):
    	acom_balance=0
    	lista_movline = self.env['account.move.line'].search([])
    	if lista_movline:
    		for rec in lista_movline:
    			if rec.account_id.user_type_id.name=="Ingreso":
    				acom_balance=acom_balance+abs(rec.balance_aux)
    	return acom_balance

    def total_lineas_balance_por_cuentas(self,id_cuenta):
    	acom_balance=0
    	lista_movline = self.env['account.move.line'].search([('account_id','=',id_cuenta)])
    	if lista_movline:
    		for rec in lista_movline:
    			#if rec.account_id.user_type_id.name=="Ingreso":
    			acom_balance=acom_balance+abs(rec.balance_aux)
    	return acom_balance

    def total_lineas_credit_por_cuentas(self,id_cuenta):
    	acom_credit=0
    	lista_movline = self.env['account.move.line'].search([('account_id','=',id_cuenta)])
    	if lista_movline:
    		for rec in lista_movline:
    			#if rec.account_id.user_type_id.name=="Ingreso":
    			acom_credit=acom_credit+abs(rec.credit_aux)
    	return acom_credit

    def total_lineas_debit_por_cuentas(self,id_cuenta):
    	acom_debit=0
    	lista_movline = self.env['account.move.line'].search([('account_id','=',id_cuenta)])
    	if lista_movline:
    		for rec in lista_movline:
    			#if rec.account_id.user_type_id.name=="Ingreso":
    			acom_debit=acom_debit+abs(rec.debit_aux)
    	return acom_debit

    def _eval_formula(self, financial_report, debit_credit, currency_table, linesDict_per_group, groups=False):
        groups = groups or {'fields': [], 'ids': [()]}
        debit_credit = debit_credit and financial_report.debit_credit
        formulas = self._split_formulas()
        currency = self.env.company.currency_id

        line_res_per_group = []

        if not groups['ids']:
            return [{'line': {'balance': 0.0}}]

        # this computes the results of the line itself
        for group_index, group in enumerate(groups['ids']):
            self_for_group = self.with_context(group_domain=self._get_group_domain(group, groups))
            linesDict = linesDict_per_group[group_index]
            line = False

            #if self.code!="INC" and self.code!="GRP" and self.code!="OPINC" and self.code!="COS" and self.code!="OIN":
            	#raise UserError(_('code = %s')%self.code)

            if self.code and self.code in linesDict:
                line = linesDict[self.code]
            elif formulas and formulas['balance'].strip() == 'count_rows' and self.groupby:
                line_res_per_group.append({'line': {'balance': self_for_group._get_rows_count()}})
            elif formulas and formulas['balance'].strip() == 'from_context':
                line_res_per_group.append({'line': {'balance': self_for_group._get_value_from_context()}})
            else:
                line = FormulaLine(self_for_group, currency_table, financial_report, linesDict=linesDict)

            if line:
                res = {}#self.total_balance()#
                res['balance'] = line.balance # darrell rep ganancia y perdida, balance de situacion
                res['balance'] = currency.round(line.balance) # 11 darrell rep ganancia y perdida, balance de situacion
                if debit_credit:
                    res['credit'] = currency.round(line.credit)
                    res['debit'] = currency.round(line.debit)
                line_res_per_group.append(res)

        # don't need any groupby lines for count_rows and from_context formulas
        if all('line' in val for val in line_res_per_group):
            return line_res_per_group

        columns = []
        # this computes children lines in case the groupby field is set
        if self.domain and self.groupby and self.show_domain != 'never':
            if self.groupby not in self.env['account.move.line']:
                raise ValueError(_('Groupby should be a field from account.move.line'))

            groupby = [self.groupby or 'id']
            if groups:
                groupby = groups['fields'] + groupby
            groupby = ', '.join(['"account_move_line".%s' % field for field in groupby])

            aml_obj = self.env['account.move.line']
            tables, where_clause, where_params = aml_obj._query_get(domain=self._get_aml_domain())
            if financial_report.tax_report:
                where_clause += ''' AND "account_move_line".tax_exigible = 't' '''

            select, params = self._query_get_select_sum(currency_table)
            params += where_params

            sql, params = self._build_query_eval_formula(groupby, select, tables, where_clause, params)
            self.env.cr.execute(sql, params)
            results = self.env.cr.fetchall()
            for group_index, group in enumerate(groups['ids']):
                linesDict = linesDict_per_group[group_index]
                results_for_group = [result for result in results if group == result[:len(group)]]
                if results_for_group:
                    results_for_group = [r[len(group):] for r in results_for_group] # aqui abajo modificar lineas
                    results_for_group = dict([(k[0], {'balance': self.total_lineas_balance_por_cuentas(k[0]), 'amount_residual': k[2], 'debit': self.total_lineas_debit_por_cuentas(k[0]), 'credit': self.total_lineas_credit_por_cuentas(k[0])}) for k in results_for_group])
                    c = FormulaContext(self.env['account.financial.html.report.line'].with_context(group_domain=self._get_group_domain(group, groups)),
                                       linesDict, currency_table, financial_report, only_sum=True)
                    if formulas:
                        for key in results_for_group:
                            c['sum'] = FormulaLine(results_for_group[key], currency_table, financial_report, type='not_computed')
                            c['sum_if_pos'] = FormulaLine(results_for_group[key]['balance'] >= 0.0 and results_for_group[key] or {'balance': 0.0},
                                                          currency_table, financial_report, type='not_computed')
                            c['sum_if_neg'] = FormulaLine(results_for_group[key]['balance'] <= 0.0 and results_for_group[key] or {'balance': 0.0},
                                                          currency_table, financial_report, type='not_computed')
                            for col, formula in formulas.items():
                                if col in results_for_group[key]:
                                    results_for_group[key][col] = safe_eval(formula, c, nocopy=True)
                    to_del = []
                    for key in results_for_group:
                        if self.env.company.currency_id.is_zero(results_for_group[key]['balance']):
                            to_del.append(key)
                    for key in to_del:
                        del results_for_group[key]
                    results_for_group.update({'line': line_res_per_group[group_index]})
                    columns.append(results_for_group)
                else:
                    res_vals = {'balance': 0.0}
                    if debit_credit:
                        res_vals.update({'debit': 0.0, 'credit': 0.0})
                    columns.append({'line': res_vals})

        return columns or [{'line': res} for res in line_res_per_group]