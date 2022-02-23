# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.account.models.account_move import AccountMove

INTEGRITY_HASH_MOVE_FIELDS = ('date', 'journal_id', 'company_id')

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _check_reconciliation(self):
        for line in self:
            if line.matched_debit_ids or line.matched_credit_ids:
                pass
                # raise UserError(_("You cannot do this modification on a reconciled journal entry. "
                #                   "You can just change some non legal fields or you must unreconcile first.\n"
                #                   "Journal Entry (id): %s (%s)") % (line.move_id.name, line.move_id.id))


class AccountMove(models.Model):
    _inherit = "account.move"

    sucursal_id = fields.Many2one('res.sucursal', string='Sucursal')
    lista_sucursales = fields.Char(compute='_lista_sucursal_permitidas')

    def change_company_extend(self):
        res = self.env.ref('multiple_sucursales.action_wizards_transfer_account_move').read()[0]
        return res

    def action_transferecia(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return ''

        return {
            'name': _('Transferencia Asiento'),
            'res_model': 'wizards.transfer.account_move',
            'view_mode': 'form',
            'view_id': self.env.ref('multiple_sucursales.wizards_transfer_account_move').id,
            'context': self.env.context,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    @api.onchange('partner_id')
    def _lista_sucursal_permitidas(self):
        cont=0
        concatena="('0')"
        if self.invoice_user_id.id:
            #raise UserError(_('%s')%self.invoice_user_id.sucursal_ids)
            if self.invoice_user_id.sucursal_ids:
                for det in self.invoice_user_id.sucursal_ids:
                    cont=cont+1
                    if cont==1:
                        concatena="('"
                    else:
                        concatena=concatena+",'"
                    concatena=concatena+str(det.id)
                    concatena=concatena+"'"
                concatena=concatena+")"
        self.lista_sucursales=concatena

    ################### esto e para los diarios  ##########################

    def get_invoice_number_cli(self):
        '''metodo que crea el Nombre del asiento contable si la secuencia no esta creada, crea una con el
        nombre: 'l10n_ve_cuenta_retencion_iva'''
        name=''
        if self.act_nota_entre==False:
           name=self.get_invoice_number_unico()
        return name

    
    def get_refuld_number_cli(self):# nota de credito cliente
        '''metodo que crea el Nombre del asiento contable si la secuencia no esta creada, crea una con el
        nombre: 'l10n_ve_cuenta_retencion_iva'''
        name=''
        if self.act_nota_entre==False:
             name=self.get_invoice_number_unico()
        return name

    
    def get_refuld_number_pro(self): #nota de debito Cliente
        '''metodo que crea el Nombre del asiento contable si la secuencia no esta creada, crea una con el
        nombre: 'l10n_ve_cuenta_retencion_iva'''
        name=''
        if self.act_nota_entre==False:
             name=self.get_invoice_number_unico()
        return name

    def get_invoice_number_unico(self):
        name=''
        if not self.journal_id.doc_sequence_id:
            raise UserError(_('Este diario no tiene configurado el Nro de Documento. Vaya al diario, pestaña *Configuracion sec. Facturación* y en el campo *Proximo Nro Documento* agregue uno'))
        else:
            if not self.journal_id.doc_sequence_id.code:
                raise UserError(_('La secuencia del Nro documento llamado * %s * de este diario, no tiene configurada el Código se secuencias')%self.journal_id.doc_sequence_id.name)
            else:
                SEQUENCE_CODE=self.journal_id.doc_sequence_id.code
                company_id = self.company_id.id
                IrSequence = self.env['ir.sequence'].with_context(force_company=company_id)
                name = IrSequence.next_by_code(SEQUENCE_CODE)
        return name
    

    def get_invoice_ctrl_number_unico(self):
        '''metodo que crea el Nombre del asiento contable si la secuencia no esta creada, crea una con el
        nombre: 'l10n_ve_cuenta_retencion_iva'''
        name=''
        if self.act_nota_entre==False:
            #raise UserError(_('Ever %s')%self.company_id.confg_nro_control)
            
            if not self.journal_id.ctrl_sequence_id:
                raise UserError(_('Este diario no tiene configurado el Nro de control. vaya al diario, pestaña *Configuracion sec. Facturación* y en el campo *Proximo Nro control* agregue uno'))
            else:
                if not self.journal_id.ctrl_sequence_id.code:
                    raise UserError(_('La secuencia del Nro control llamado * %s * de este diario, no tiene configurada el Código se secuencias')%self.journal_id.ctrl_sequence_id.name)
                else:
                    SEQUENCE_CODE=self.journal_id.ctrl_sequence_id.code
                    company_id = self.company_id.id
                    IrSequence = self.env['ir.sequence'].with_context(force_company=company_id)
                    name = IrSequence.next_by_code(SEQUENCE_CODE)

        return name
############################################

    def demo(self):
        pass
