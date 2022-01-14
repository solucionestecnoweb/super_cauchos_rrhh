# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re
from odoo.exceptions import Warning

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    asiento_pagado = fields.Char(default="no")

    @api.depends('debit', 'credit', 'account_id', 'amount_currency', 'currency_id', 'matched_debit_ids', 'matched_credit_ids', 'matched_debit_ids.amount', 'matched_credit_ids.amount', 'move_id.state', 'company_id')
    def _amount_residual(self):
        """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:
            if (not line.account_id.reconcile and line.account_id.internal_type != 'liquidity') or line.asiento_pagado=='si':
                line.reconciled = False
                line.amount_residual = 0
                line.amount_residual_currency = 0
                continue
            #amounts in the partial reconcile table aren't signed, so we need to use abs()
            amount = abs(line.debit - line.credit)
            amount_residual_currency = abs(line.amount_currency) or 0.0
            sign = 1 if (line.debit - line.credit) > 0 else -1
            if not line.debit and not line.credit and line.amount_currency and line.currency_id:
                #residual for exchange rate entries
                sign = 1 if float_compare(line.amount_currency, 0, precision_rounding=line.currency_id.rounding) == 1 else -1

            for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                # If line is a credit (sign = -1) we:
                #  - subtract matched_debit_ids (partial_line.credit_move_id == line)
                #  - add matched_credit_ids (partial_line.credit_move_id != line)
                # If line is a debit (sign = 1), do the opposite.
                sign_partial_line = sign if partial_line.credit_move_id == line else (-1 * sign)

                amount += sign_partial_line * partial_line.amount
                #getting the date of the matched item to compute the amount_residual in currency
                if line.currency_id and line.amount_currency:
                    if partial_line.currency_id and partial_line.currency_id == line.currency_id:
                        amount_residual_currency += sign_partial_line * partial_line.amount_currency
                    else:
                        if line.balance and line.amount_currency:
                            rate = line.amount_currency / line.balance
                        else:
                            date = partial_line.credit_move_id.date if partial_line.debit_move_id == line else partial_line.debit_move_id.date
                            rate = line.currency_id.with_context(date=date).rate
                        amount_residual_currency += sign_partial_line * line.currency_id.round(partial_line.amount * rate)

            #computing the `reconciled` field.
            reconciled = False
            digits_rounding_precision = line.move_id.company_id.currency_id.rounding
            if float_is_zero(amount, precision_rounding=digits_rounding_precision):
                if line.currency_id and line.amount_currency:
                    if float_is_zero(amount_residual_currency, precision_rounding=line.currency_id.rounding):
                        reconciled = True
                else:
                    reconciled = True
            line.reconciled = reconciled
            """if amount!=0:
                amount=abs(line.move_id.amount_residual_signed)"""
            line.amount_residual = line.move_id.company_id.currency_id.round(amount * sign) if line.move_id.company_id else amount * sign
            line.amount_residual_currency = line.currency_id and line.currency_id.round(amount_residual_currency * sign) or 0.0

class AccontPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    consi_secu_move_id=fields.Many2one('account.move', string='Asiento secundario de la factura')

class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    #_rec_name = payment_id

    payment_id = fields.Many2one('account.payment', string='Anticipos Pendientes Bs.')
    monto_anticipo = fields.Monetary(string='Anticipo Disponible', compute='_compute_monto')
    payment_ids = fields.Many2many('account.payment', string='Anticipos')
    usar_anticipo = fields.Boolean(defaul=False)
    es_igtf = fields.Boolean(default=False)
    payment_origen_igtf_id = fields.Many2one('account.payment', string='Pogo origen para el igtf.')

    #rel_field = fields.Char(string='Name', related='payment_id.amount')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        xfind = self.env['account.payment'].search([
            ('partner_id', '=', self.partner_id.id),
            ('anticipo', '=', True),
            ('state', '=', 'posted')
        ])
        if len(xfind) > 0:
            return {'warning': {'message':'Este Cliente/Proveedor posee un anticipo disponible'}}

    def _compute_monto(self):
        self.monto_anticipo = self.payment_id.saldo_disponible
        #return monto_retencion

    def cambio(self,det):
        if self.currency_id.id==det.currency_id.id:
            valor=det.saldo_disponible
        else:
            if det.currency_id.id==self.company_id.currency_id.id:
                valor=det.saldo_disponible # det.rate
            else:
                valor=(det.saldo_disponible*self.os_currency_rate)

        return valor


    def action_post(self):
        super().action_post()
        # Acciones a realizar validar fechas contables en la factura
        # Verificar si existe el impuesto al iva (lo voy a crear y cargar en xml)
        # Verificar si la empresa como el cliente o proveedor son agentes de retencion
        #if self.payment_id.id:
        self.crea_asiento_anticipo_v2()

    def crea_asiento_anticipo_v2(self):
        monto_factura=abs(self.amount_residual_signed) # valores en bs
        #raise UserError(_('det =%s')%self.payment_ids)
        for det in self.payment_ids:
            nombre_anti=self.get_name_anticipo()
            monto_anticipo=det.saldo_disponible_signed # valores en bs
            pasa='si'
            if monto_factura==0:
                raise UserError(_('Existe un anticipo que no es necesario usarlo, por favor excluirlo de este movimiento'))
            if pasa=='si':
                if monto_factura>monto_anticipo:
                    #raise UserError(_('opcion 11 =%s')%monto_anticipo)
                    id_move=self.registro_movimiento_anticipo(monto_anticipo,nombre_anti)
                    idv_move=id_move.id
                    valor=self.registro_movimiento_linea_anticipo(idv_move,monto_anticipo,nombre_anti,det)
                    moves= self.env['account.move'].search([('id','=',idv_move)])
                    #######self.valida_saldo_pendiente(det)
                    id_move.action_post()
                    #moves.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post()
                    self.concilio_saldo_pendiente_anti(idv_move,det,monto_anticipo)

                    monto_factura=monto_factura-monto_anticipo
                    usado=True
                    disponible=0.0
                    det.usado=usado
                    det.saldo_disponible_signed=disponible
                    det.saldo_disponible=disponible
                    det.anticipo_move_id=idv_move
                    det.move_id=self.id
                    pasa='no'
                    ######## cuando el anticipo es en bs o $ y la factura es en $
                    if self.currency_id.id!=self.env.company.currency_id.id:  #self.env.company.currency_id.id==det.currency_id.id and 
                        if self.type=='in_invoice':
                            signo=1
                        if self.type=='out_invoice':
                            signo=-1
                        self.amount_residual=signo*(monto_factura/self.os_currency_rate)
                        self.amount_residual_signed=signo*(monto_factura)
            if pasa=='si':    
                if monto_factura<monto_anticipo:
                    #raise UserError(_('opcion 2'))
                    id_move=self.registro_movimiento_anticipo(monto_factura,nombre_anti)
                    idv_move=id_move.id
                    valor=self.registro_movimiento_linea_anticipo(idv_move,monto_factura,nombre_anti,det)
                    moves= self.env['account.move'].search([('id','=',idv_move)])
                    #######self.valida_saldo_pendiente(det)
                    id_move.action_post()
                    #moves.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post()
                    self.concilio_saldo_pendiente_anti(idv_move,det,monto_factura)

                    usado=False
                    disponible=monto_anticipo-monto_factura
                    det.usado=usado
                    det.saldo_disponible_signed=disponible
                    det.saldo_disponible=disponible if det.currency_id.id==self.env.company.currency_id.id else disponible/det.rate
                    monto_factura=0
                    self.invoice_payment_state='paid'
                    det.anticipo_move_id=idv_move
                    det.move_id=self.id
                    pasa='no'
                    ######## cuando el anticipo es en bs o $ y la factura es en $
                    if self.currency_id.id!=self.env.company.currency_id.id:
                        if self.type=='in_invoice':
                            signo=1
                        if self.type=='out_invoice':
                            signo=-1
                        self.amount_residual=0.0
                        self.amount_residual_signed=0.0
            if pasa=='si':
                if monto_factura==monto_anticipo:
                    #raise UserError(_('opcion 3'))
                    id_move=self.registro_movimiento_anticipo(monto_factura,nombre_anti)
                    idv_move=id_move.id
                    valor=self.registro_movimiento_linea_anticipo(idv_move,monto_factura,nombre_anti,det)
                    moves= self.env['account.move'].search([('id','=',idv_move)])
                    #######self.valida_saldo_pendiente(det)
                    id_move.action_post()
                    #moves.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post()
                    self.concilio_saldo_pendiente_anti(idv_move,det,monto_anticipo)

                    monto_factura=monto_factura-monto_anticipo
                    usado=True
                    disponible=0.0
                    det.usado=usado
                    det.saldo_disponible_signed=disponible
                    det.saldo_disponible=disponible
                    self.invoice_payment_state='paid'
                    self.amount_residual=0
                    self.amount_residual_signed=0
                    det.anticipo_move_id=idv_move
                    det.move_id=self.id
                    pasa='no'



    def crea_asiento_anticipo(self):
        if self.usar_anticipo==True:
            if not self.payment_ids:
                raise UserError(_('Debe agregar Lineas de Pagos de Anticipo'))
            cont=0
            acum=0
            for det in self.payment_ids:
                #cont=cont+1
                acum=acum+det.saldo_disponible_signed # disponible en bs #self.cambio(det) 
                #nombre_anti=self.get_name_anticipo()
                monto_factura=abs(self.amount_residual_signed) # valor en bs  #self.amount_total
                monto_anticipo=det.saldo_disponible_signed #self.cambio(det) 
                #id_move=self.registro_movimiento_anticipo(monto_anticipo,nombre_anti)
                #idv_move=id_move.id
                #valor=self.registro_movimiento_linea_anticipo(idv_move,monto_anticipo,nombre_anti,det,acum)
                #moves= self.env['account.move'].search([('id','=',idv_move)])
                #######self.valida_saldo_pendiente(det)
                #moves.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post()
                #self.concilio_saldo_pendiente_anti(idv_move,det,cont,acum)
                ######raise UserError(_('acum= %s monto factura =%s')%(acum,monto_factura))
                if acum<monto_factura:
                    usuado=True
                    disponible=0.0
                if acum>monto_factura:
                    usuado=False
                    disponible=(acum-monto_factura)
                    self.invoice_payment_state='paid'
                if acum==monto_factura:
                    usuado=True
                    disponible=0.0
                    self.invoice_payment_state='paid'
                #raise UserError(_('disponible = %s')%disponible)
                if det.currency_id.id!=self.env.company.currency_id.id:
                    disponible=disponible/self.os_currency_rate
                #raise UserError(_('disponible 2 = %s')%disponible)
                cursor_payment = self.env['account.payment'].search([('id','=',det.id)])
                for det_payment in cursor_payment:
                    self.env['account.payment'].browse(det_payment.id).write({
                                'usado':usuado,
                                'anticipo_move_id':idv_move,
                                'saldo_disponible':disponible,
                                'move_id':self.id,
                                })
            #raise UserError(_('monto_anticipo = %s')%monto_anticipo)

    def registro_movimiento_anticipo(self,total_monto,anti_nombre):
        name = anti_nombre
        #raise UserError(_('monto xx = %s')%amount_itf)
        value = {
            'name': name,
            'date': self.date,
            'journal_id': self.journal_id.id,
            'line_ids': False,
            'state': 'draft',
            'type': 'entry',# estte campo es el que te deja cambiar y almacenar valores 
            'amount_total':total_monto,# revisar
            'amount_total_signed':total_monto,# revisar
            'partner_id': self.partner_id.id,
            #'partner_id': 45,
            'ref': "Pago de Anticipo Documento Nro: %s " % (self.name),
            'custom_rate':self.custom_rate,
            'os_currency_rate':self.os_currency_rate,
            'amount_residual':0.0,
            'amount_residual_signed':0.0,
            #'name': "Comisión del %s %% del pago %s por comisión" % (igtf_porcentage,name),

        }
        if self.amount_residual>0:

            move_obj = self.env['account.move']
            move_id = move_obj.create(value)     
            return move_id
        else:
            move_id=self.env['account.move'].search([('id','=',0)])
            return move_id

    def registro_movimiento_linea_anticipo(self,id_movv,total_monto,anti_nombre,id_payment):
        cuenta_anti_cliente = self.partner_id.account_anti_receivable_id.id
        cuenta_anti_proveedor = self.partner_id.account_anti_payable_id.id
        cuenta_cobrar = self.partner_id.property_account_receivable_id.id
        cuenta_pagar = self.partner_id.property_account_payable_id.id
        tipo_persona=self.type

        """factura_monto=self.amount_total_signed #self.amount_total
        anticipo_monto=id_payment.saldo_disponible_signed #=self.cambio(id_payment)
        if acum_anti<factura_monto:  #funciona cundo anticipo > factura
            residual=anticipo_monto
        if acum_anti>=factura_monto:
            residual=anticipo_monto+(factura_monto-acum_anti)"""

        residual=total_monto


        #valores=total_monto
        valores=abs(residual)
        name = anti_nombre
        #raise UserError(_('valores linea 206 = %s')%valores)
        if tipo_persona=="in_invoice":
            cuenta_a=cuenta_anti_proveedor
            cuenta_b=cuenta_pagar
        if tipo_persona=="out_invoice":
            cuenta_a=cuenta_cobrar
            cuenta_b=cuenta_anti_cliente
        #raise UserError(_('cuenta_a = %s')%cuenta_a)
        ##if self.amount_residual>0:
        value = {
            'name': name,
            'ref' : "Pago de Anticipo Documento Nro: %s " % (self.name),
            'move_id': int(id_movv),
            'date': self.date,
            'partner_id': self.partner_id.id,
            #'partner_id': 45,
            'journal_id': self.journal_id.id,
            'account_id': cuenta_a,# aqui va cuenta de anticipo 
            'date_maturity': False,
            'credit': valores,#self.conv_div_extranjera(valores),#loca14
            'debit': 0.0, # aqi va cero
            'balance':-1*valores,#self.conv_div_extranjera(valores),#loca14
            'currency_id':self.moneda(), #loca14
            'asiento_pagado':"si",
            #'amount_currency': -1*self.amount_currency(valores), #loca14
            #'amount_residual_currency': -1*self.amount_currency(valores), #loca14

        }
            

        move_line_obj = self.env['account.move.line']
        move_line_id1 = move_line_obj.create(value)

        value['account_id'] = cuenta_b # aqui va cuenta pxp proveedores
        value['credit'] = 0.0 # aqui va cero
        value['debit'] = valores #self.conv_div_extranjera(valores)#loca14
        value['balance'] = valores #self.conv_div_extranjera(valores)#loca14
        #value['balance'] = self.currency_id.id #loca14
        value['currency_id'] = self.moneda() #loca14
        value['asiento_pagado'] = "si"
        #value['amount_currency'] = self.amount_currency(valores) #loca14
        #value['amount_residual_currency'] = self.amount_currency(valores) #loca14
        move_line_id2 = move_line_obj.create(value)

    def conv_div_extranjera(self,valor):#loca14 COPIAR ESTE CODIGO COMPLETO
        self.currency_id.id
        fecha_contable_doc=self.date
        monto_factura=self.amount_total
        valor_aux=0
        #raise UserError(_('moneda compañia: %s')%self.company_id.currency_id.id)
        if self.currency_id.id!=self.env.company.currency_id.id:
            if self.custom_rate!=True:
                tasa= self.env['res.currency.rate'].search([('currency_id','=',self.currency_id.id),('name','<=',self.date)],order="name asc")
                for det_tasa in tasa:
                    if fecha_contable_doc>=det_tasa.name:
                        valor_aux=det_tasa.rate
                rate=round(1/valor_aux,2)  # LANTA
                #rate=round(valor_aux,2)  # ODOO SH
                resultado=valor*rate
            else:
                resultado=valor*self.os_currency_rate
        else:
            resultado=valor
        #raise UserError(_('moneda compañia: %s')%resultado)
        return resultado

    def trampa(self,valor):
        self.currency_id.id
        fecha_contable_doc=self.date
        monto_factura=self.amount_total_signed
        valor_aux=0
        #raise UserError(_('moneda compañia: %s')%self.company_id.currency_id.id)
        if self.currency_id.id!=self.env.company.currency_id.id:
            tasa= self.env['res.currency.rate'].search([('currency_id','=',self.currency_id.id),('name','<=',self.date)],order="name asc")
            for det_tasa in tasa:
                if fecha_contable_doc>=det_tasa.name:
                    valor_aux=det_tasa.rate
            rate=round(1/valor_aux,2)  # LANTA
            #rate=round(valor_aux,2)  # ODOO SH
            resultado=valor*rate/self.os_currency_rate
        else:
            resultado=valor
        #raise UserError(_('moneda compañia linea 238: %s')%resultado)
        #reultado=77
        return resultado

    def amount_currency(self,valor): #loca14 COPIAR ESTE CODIGO COMPLETO
        if self.currency_id.id!=self.env.company.currency_id.id:
            resultado=valor
        else:
            resultado=0.0
        return resultado

    def moneda(self): #loca14 COPIAR ESTE CODIGO COMPLETO
        resultado=''
        if self.currency_id.id!=self.env.company.currency_id.id:
            resultado=self.currency_id.id
            return resultado




    def valida_saldo_pendiente(self,id_payment):
        factura_monto=self.amount_residual #self.amount_total
        anticipo_monto=id_payment.saldo_disponible
        if anticipo_monto<factura_monto:
            residual=(anticipo_monto-factura_monto)
        if anticipo_monto>=factura_monto:
            residual=0.0
        #raise UserError(_('residual:%s')%residual)
        cursor_move = self.env['account.move'].search([('id','=',self.id)])
        for det_mov in cursor_move:
            self.env['account.move'].browse(det_mov.id).write({
                            'amount_residual':-1*residual,
                            'amount_residual_signed':residual,
                            })
    
    def button_draft(self):
        super().button_draft()
        #raise UserError(_('Mi Bebe:%s')%self)
        # LINEA DE CODIGO QUE ELIMINA LAS CONSILIACIONES SECUNDARIAS DE ANTICIPO
        for selff in self:
            conciliacion=selff.env['account.partial.reconcile'].search([('consi_secu_move_id','=',selff.id)])
            #raise UserError(_('Mi Bebe:%s')%conciliacion)
            conciliacion.with_context(force_delete=True).unlink()
            # FIN LINEA DE CODIGO QUE ELIMINA LAS CONSILIACIONES SECUNDARIAS DE ANTICIPO

            monto_factura=selff.amount_total
            monto_residual=selff.amount_residual
            saldo_actual=selff.payment_id.saldo_disponible
            #saldo_inicial=monto_factura-monto_residual
            if selff.type!="entry":
                #raise UserError(_('Mi Bebe2:'))
                #raise UserError(_('Mi Bebe:%s')%self.payment_id.anticipo)
                #if self.payment_id.anticipo==True:
                cursor_payment = selff.env['account.payment'].search([('move_id','=',selff.id)])
                #raise UserError(_('Mi Bebe:%s')%cursor_payment)
                if cursor_payment:
                    for det_payment in cursor_payment:
                        id_mov_anti=det_payment.anticipo_move_id.id
                        #raise UserError(_('Mi Bebe:%s')%det_payment.amount)
                        saldo_inicial=det_payment.anticipo_move_id.amount_total+saldo_actual
                        selff.env['account.payment'].browse(det_payment.id).write({
                                        'usado':False,
                                        #'saldo_disponible':saldo_inicial,
                                        'saldo_disponible':det_payment.amount,
                                        'saldo_disponible_signed':det_payment.amount if det_payment.currency_id.id==self.env.company.currency_id.id else det_payment.amount*det_payment.rate
                                        })
                        cursor_anticipo = selff.env['account.move'].search([('id','=',id_mov_anti)])
                        #cursor_anticipo.filtered(lambda move: move.state == 'posted').button_draft()
                        cursor_anticipo.with_context(force_delete=True).unlink()


#************ funcionpara que funcione en lanta *************
    def concilio_saldo_pendiente_anti(self,id_move_conci,id_payment,acum_anti):
        #id_retention=self.id
        #raise UserError(_('yujuuuuu'))
        id_move=self.id
        #raise UserError(_('ID Factura=%s')%self.id)
        #raise UserError(_('id_move_conci=%s')%id_move_conci)
        """factura_monto=self.amount_total_signed #self.amount_total
        anticipo_monto= id_payment.saldo_disponible_signed #self.cambio(id_payment)
        if anticipo_monto<factura_monto:
            monto=anticipo_monto
        if anticipo_monto>=factura_monto:
            monto=anticipo_monto+(factura_monto-acum_anti)"""
        monto=acum_anti
        #raise UserError(_('monto line 322 = %s')%monto)

        if self.amount_residual>0:  #self.amount_residual_signed

            tipo_empresa=self.type
            if tipo_empresa=="in_invoice" or tipo_empresa=="out_refund":#aqui si la empresa es un proveedor
                type_internal="payable"
            if tipo_empresa=="out_invoice" or tipo_empresa=="in_refund":# aqui si la empresa es un cliente
                type_internal="receivable"
            busca_movimientos = self.env['account.move'].search([('id','=',id_move)])
            for det_movimientos in busca_movimientos:
                busca_line_mov1 = self.env['account.move.line'].search([('move_id','=',id_move),('account_internal_type','=',type_internal),('parent_state','!=','cancel')])
                #raise UserError(_('busca_line_mov1 = %s')%busca_line_mov1)
                for det_line_move1 in busca_line_mov1:
                    if det_line_move1.credit==0:
                        id_move_debit=det_line_move1.id
                        monto_debit=det_line_move1.debit
                    if det_line_move1.debit==0:
                        id_move_credit=det_line_move1.id
                        monto_credit=det_line_move1.credit

                busca_line_mov2 = self.env['account.move.line'].search([('move_id','=',id_move_conci),('account_internal_type','=',type_internal),('parent_state','!=','cancel')])
                #raise UserError(_('busca_line_mov2 = %s')%busca_line_mov2)
                cont=0
                for det_line_move2 in busca_line_mov2:
                    cont=cont+1
                    if det_line_move1.debit==0:
                        if det_line_move2.credit==0:
                            id_move_debit=det_line_move2.id
                            monto_debit=det_line_move2.debit
                    if det_line_move1.credit==0:
                        if det_line_move2.debit==0:
                            id_move_credit=det_line_move2.id
                            monto_credit=det_line_move2.credit

                    #if det_line_move2.debit==0:
                        #id_move_credit=det_line_move2.id
                        #monto_credit=det_line_move2.credit
                    #if cont==2:
                        #pass
                        #raise UserError(_('cont=%s, det_line_move2.debit = %s')%(cont,det_line_move2.parent_state))

            #raise UserError(_('monto_credit = %s, monto_debit= %s ')%(monto_credit,monto_debit))       
            if tipo_empresa=="in_invoice" or tipo_empresa=="out_refund":
                monto=monto_debit
            if tipo_empresa=="out_invoice" or tipo_empresa=="in_refund":
                monto=monto_credit
            #raise UserError(_('monto line 369 = %s')%monto)
            value = {
                 'debit_move_id':id_move_debit,
                 'credit_move_id':id_move_credit,
                 'amount':self.trampa(monto),
                 'max_date':self.date,
                 #'currency_id':2,
            }
            #raise UserError(_('value = %s')%value)
            id_conciliacion=self.env['account.partial.reconcile'].create(value)
            valor=monto
            ##self.amount_residual=0

            #self.reajusta(id_conciliacion.id,valor)

            # NUEVO CODIGO PARA CONCILIAR MOVIMIENTOS SECUNDARIOS 
            id_payment.id
            busca_line_mov3 = self.env['account.move.line'].search([('payment_id','=',id_payment.id),('account_internal_type','=',type_internal),('parent_state','!=','cancel')])
            #raise UserError(_('valor = %s')%id_payment)
            for det_line_move3 in busca_line_mov3:
                if det_line_move3.credit==0:
                    id_move_debit=det_line_move3.id
                    monto_debit=det_line_move3.debit
                if det_line_move3.debit==0:
                    id_move_credit=det_line_move3.id
                    monto_credit=det_line_move3.credit
            busca_line_mov4 = self.env['account.move.line'].search([('move_id','=',id_move_conci),('account_internal_type','=',type_internal),('parent_state','!=','cancel')])
            for det_line_move4 in busca_line_mov4:
                if det_line_move3.debit==0:
                    if det_line_move4.credit==0:
                        id_move_debit=det_line_move4.id
                        monto_debit=det_line_move4.debit
                if det_line_move3.credit==0:
                    if det_line_move4.debit==0:
                        id_move_credit=det_line_move4.id
                        monto_credit=det_line_move4.credit

            if tipo_empresa=="in_invoice" or tipo_empresa=="out_refund":
                monto=monto_debit
            if tipo_empresa=="out_invoice" or tipo_empresa=="in_refund":
                monto=monto_credit
            value = {
            'debit_move_id':id_move_debit,
            'credit_move_id':id_move_credit,
            'amount':monto,
            'max_date':self.date,
            'consi_secu_move_id':self.id,
            }
            self.env['account.partial.reconcile'].create(value)
            #raise UserError(_('value = %s')%self.env['account.partial.reconcile'].create(value))

#************ funcionpara que funcione en odoo sh *************
    """def concilio_saldo_pendiente_anti(self,id_move_conci,id_payment,cont2,acum_anti):
        #id_retention=self.id
        #raise UserError(_('yujuuuuu'))
        id_move=self.id
        factura_monto=self.amount_total #self.amount_total
        anticipo_monto=id_payment.saldo_disponible
        if acum_anti<factura_monto:
            monto=anticipo_monto
        if acum_anti>=factura_monto:
            monto=anticipo_monto+(factura_monto-acum_anti)
        #if cont2==3:
        #raise UserError(_('self.amount_residual = %s')%self.amount_residual)

        if self.amount_residual>0:

            tipo_empresa=self.type
            if tipo_empresa=="in_invoice" or tipo_empresa=="out_refund":#aqui si la empresa es un proveedor
                type_internal="payable"
            if tipo_empresa=="out_invoice" or tipo_empresa=="in_refund":# aqui si la empresa es cliente
                type_internal="receivable"
            busca_movimientos = self.env['account.move'].search([('id','=',id_move)])
            for det_movimientos in busca_movimientos:
                busca_line_mov = self.env['account.move.line'].search([('move_id','in',(det_movimientos.id,id_move_conci)),('account_internal_type','=',type_internal)])
                #raise UserError(_('busca_line_mov = %s')%busca_line_mov)
                for det_line_move in busca_line_mov:
                    if det_line_move.credit==0:
                        id_move_debit=det_line_move.id
                        monto_debit=det_line_move.debit
                    if det_line_move.debit==0:
                        id_move_credit=det_line_move.id
                        monto_credit=det_line_move.credit
            if tipo_empresa=="in_invoice" or tipo_empresa=="out_refund":
                monto=monto_debit
            if tipo_empresa=="out_invoice" or tipo_empresa=="in_refund":
                monto=monto_credit
            value = {
                 'debit_move_id':id_move_debit,
                 'credit_move_id':id_move_credit,
                 'amount':monto,
                 'max_date':self.date,
            }
            self.env['account.partial.reconcile'].create(value)"""

    def reajusta(self,id_conciliacion,valor):
        #raise UserError(_("hgghgh=%s")%valor)
        busca=self.env[('account.partial.reconcile')].search([('id','=',id_conciliacion)])
        if busca:
            for rec in busca:
                resultado=(valor/5)*4.74
                rec.amount=resultado


    def get_name_anticipo(self):
        '''metodo que crea el Nombre del asiento contable si la secuencia no esta creada, crea una con el
        nombre: 'l10n_account_withholding_itf'''

        self.ensure_one()
        SEQUENCE_CODE = 'l10n_ve_cuenta_anticipo'
        company_id = self.company_id
        IrSequence = self.env['ir.sequence'].with_context(force_company=company_id.id)
        name = IrSequence.next_by_code(SEQUENCE_CODE)

        # si aún no existe una secuencia para esta empresa, cree una
        if not name:
            IrSequence.sudo().create({
                'prefix': 'Anticipo/',
                'name': 'Localización Venezolana Pagos de anticipos %s' % company_id.id,
                'code': SEQUENCE_CODE,
                'implementation': 'no_gap',
                'padding': 8,
                'number_increment': 1,
                'company_id': company_id.id,
            })
            name = IrSequence.next_by_code(SEQUENCE_CODE)
        return name


    """def unlink(self):
        for move in self:
            if move.name != '/' and not self._context.get('force_delete'):
                raise UserError(_("hgghgh"))
            move.line_ids.unlink()
        return super(AccountMove, self).unlink()"""
 

    def _check_balanced(self):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        moves = self.filtered(lambda move: move.line_ids)
        if not moves:
            return

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
        # It happens as the ORM makes the create with the 'no_recompute' statement.
        self.env['account.move.line'].flush(['debit', 'credit', 'move_id'])
        self.env['account.move'].flush(['journal_id'])
        self._cr.execute('''
            SELECT line.move_id, ROUND(SUM(debit - credit), currency.decimal_places)
            FROM account_move_line line
            JOIN account_move move ON move.id = line.move_id
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_company company ON company.id = journal.company_id
            JOIN res_currency currency ON currency.id = company.currency_id
            WHERE line.move_id IN %s
            GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(debit - credit), currency.decimal_places) != 0.0;
        ''', [tuple(self.ids)])

        query_res = self._cr.fetchall()
        if query_res:
            ids = [res[0] for res in query_res]
            sums = [res[1] for res in query_res]
            #raise UserError(_("Cannot create unbalanced journal entry. Ids: %s\nDifferences debit - credit: %s") % (ids, sums))


class Currency(models.Model):
    _inherit = "res.currency"

    def _convert(self, from_amount, to_currency, company, date, round=True):
        """Returns the converted amount of ``from_amount``` from the currency
           ``self`` to the currency ``to_currency`` for the given ``date`` and
           company.

           :param company: The company from which we retrieve the convertion rate
           :param date: The nearest date from which we retriev the conversion rate.
           :param round: Round the result or not
        """
        self, to_currency = self or to_currency, to_currency or self
        assert self, "convert amount from unknown currency"
        assert to_currency, "convert amount to unknown currency"
        assert company, "convert amount from unknown company"
        assert date, "convert amount from unknown date"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount
        else:
            to_amount = from_amount* self._get_conversion_rate(self, to_currency, company, date)
        # apply rounding
        ##to_amount=19.20
        return to_currency.round(to_amount) if round else to_amount
        