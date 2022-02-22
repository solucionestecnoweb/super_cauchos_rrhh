# coding: utf-8
###########################################################################

import logging

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.exceptions import Warning

#_logger = logging.getLogger(__name__)


class account_payment(models.Model):
    _name = 'account.payment'
    _inherit = 'account.payment'
    #name =fields.Char(compute='_valor_anticipo')


    #Estos Campos son para el modulo de anticipo
    tipo = fields.Char()
    anticipo = fields.Boolean(defaul=False)
    usado = fields.Boolean(defaul=False)
    anticipo_move_id = fields.Many2one('account.move', 'Id de Movimiento de anticipo donde pertenece dicho pago')
    saldo_disponible = fields.Monetary(string='Saldo Disponible') # valor en bs/$
    saldo_disponible_signed = fields.Float() # valor solo en bs #fields.Float(compute='_compute_saldo')
    move_id = fields.Many2one('account.move', 'Id de Movimiento o factura donde pertenece dicho pago')

    """def _compute_saldo(self):
        for selff in self:
            if selff.currency_id.id!=self.env.company.currency_id.id:
                selff.saldo_disponible_signed=selff.saldo_disponible*selff.rate
            else:
                selff.saldo_disponible_signed=selff.saldo_disponible"""

    def _valor_anticipo(self):
        nombre=self.name
        saldo=self.saldo_disponible
        self.name=nombre
       
        

    def post(self):
        super().post()
        for selff in self:
            pago_id=selff.id
            selff.direccionar_cuenta_anticipo(pago_id)
        


    def direccionar_cuenta_anticipo(self,id_pago):
        cuenta_anti_cliente = self.partner_id.account_anti_receivable_id.id
        cuenta_anti_proveedor = self.partner_id.account_anti_payable_id.id
        cuenta_cobrar = self.partner_id.property_account_receivable_id.id
        cuenta_pagar = self.partner_id.property_account_payable_id.id
        anticipo = self.anticipo
        tipo_persona = self.partner_type
        tipo_pago = self.payment_type
        #raise UserError(_('tipo = %s')%tipo_pago)
        if anticipo==True:
            if tipo_persona=="supplier":
                tipoo='in_invoice'
            if tipo_persona=="customer":
                tipoo='out_invoice'
            self.tipo=tipoo
            if not cuenta_anti_proveedor:
                raise UserError(_('Esta Empresa no tiene asociado una cuenta de anticipo para proveedores/clientes. Vaya al modelo res.partner, pestaña contabilidad y configure'))
            if not cuenta_anti_cliente:
                raise UserError(_('Esta Empresa no tiene asociado una cuenta de anticipo para proveedores/clientes. Vaya al modelo res.partner, pestaña contabilidad y configure'))
            if cuenta_anti_cliente and cuenta_anti_proveedor:
                if tipo_persona=="supplier":
                    cursor_move_line = self.env['account.move.line'].search([('payment_id','=',self.id),('account_id','=',cuenta_pagar)])
                    for det_cursor in cursor_move_line:
                        self.env['account.move.line'].browse(det_cursor.id).write({
                            'account_id':cuenta_anti_proveedor,
                            })
                    #raise UserError(_('cuenta id = %s')%cursor_move_line.account_id.id)
                if tipo_persona=="customer":
                    cursor_move_line = self.env['account.move.line'].search([('payment_id','=',self.id),('account_id','=',cuenta_cobrar)])
                    for det_cursor in cursor_move_line:
                        self.env['account.move.line'].browse(det_cursor.id).write({
                            'account_id':cuenta_anti_cliente,
                            })
                    #raise UserError(_('cuenta id = %s')%cursor_move_line.account_id.id)
                self.saldo_disponible=self.amount
                ##self.saldo_disponible_signed=self.amount if self.currency_id.id==self.env.company.currency_id.id else self.amount*self.rate
        else:
            return 0
