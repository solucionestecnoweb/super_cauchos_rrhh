# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime, date, time
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    def _get_available_contracts_domain(self):
        return [('contract_ids.state', 'in', ('open', 'close')), ('company_id', '=', self.env.company.id)]

    def _get_employees(self):
        # YTI check dates too
        return self.env['hr.employee'].search(self._get_available_contracts_domain())
        #return self.env['hr.employee'].search([])

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees',
                                    default=lambda self: self._get_employees(), required=True)
    structure_id = fields.Many2one('hr.payroll.structure', string='Salary Structure')


    @api.onchange('structure_id')
    def employees_nom(self):
        # YTI check dates too
        retorno=0
        if self.structure_id:
        	busca = self.structure_id.employee_ids
        	if busca:
        		self.employee_ids=busca.empleado_id
        	else:
        		raise UserError(_('La Nómina *_%s_* no tiene asociado ningun Empleado activo')%self.structure_id.name)