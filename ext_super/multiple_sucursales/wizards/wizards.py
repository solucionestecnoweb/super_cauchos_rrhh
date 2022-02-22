# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class TransferMove(models.TransientModel):
    _name = "wizards.transfer.account_move"

    company_from = fields.Many2one('res.company', string='Empresa Origen')
    company_to   = fields.Many2one('res.company', string='Empresa Destino')
    sucursal_id = fields.Many2one('res.sucursal', string='Sucursal Destino')

    def post(self):
        move_ids = self.env['account.move'].sudo().browse(self.env.context['active_ids'])
        for item in move_ids:
            self.mover_asiento(item)

    def mover_asiento(self, item):
        item.sucursal_id = self.sucursal_id.id
        journal = self.env['account.journal'].search([
              ('name', '=', item.journal_id.name),
              ('company_id', '=', self.company_to.id)
              ])
        temp_name = item.name
        if len(journal) > 0:
            item.name = '/'
            item.restrict_mode_hash_table = False
            item.company_id = self.company_to.id
            item.journal_id = journal

        else:
            raise UserError(
                _('Diario no encontrado : ' + item.journal_id.name))
        for line in item.line_ids:
            account = self.env['account.account'].search([
                ('code', '=', line.account_id.code),
                ('company_id', '=', self.company_to.id)
            ])
            if len(account) > 0:
                line.account_id = account.id
                for con in line.full_reconcile_id:
                    if con.move_id.id !=item.id:
                        self.mover_asiento(con.move_id)
            else:
                raise UserError(_('Cuenta contable no encontrado : ' +
                                line.account_id.code + " " + line.account_id.name))
        item.name = temp_name
        item.restrict_mode_hash_table = True
