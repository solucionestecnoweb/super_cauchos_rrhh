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

   
class AccontPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    consi_secu_move_id=fields.Many2one('account.move', string='Asiento secundario de la factura')

class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    #_rec_name = payment_id

    payment_id = fields.Many2one('account.payment', string='Anticipos Pendientes Bs.')
    monto_anticipo = fields.Monetary(string='Anticipo Disponible', compute='_compute_monto')
    #payment_ids = fields.Many2many('account.payment', string='Anticipos')
    payment_ids=fields.One2many('account.payment.anticipo', 'move_id', string='Anticipos')
    usar_anticipo = fields.Selection([('no', 'No'),('si','Si')],default='no') #fields.Boolean(defaul=False)
    es_igtf = fields.Boolean(default=False)
    payment_origen_igtf_id = fields.Many2one('account.payment', string='Pogo origen para el igtf.')

    #rel_field = fields.Char(string='Name', related='payment_id.amount')

    def conf_anti(self):
        self.crea_asiento_anticipo_v3()
        #raise UserError(_('tipo = %s')%self.id)

    @api.onchange('payment_ids')
    def asigna_partner(self):
        self.payment_ids.partner_id=self.partner_id.id
        self.payment_ids.move_id=self.id

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        xfind = self.env['account.payment'].search([
            ('partner_id', '=', self.partner_id.id),
            ('anticipo', '=', True),
            ('state', '=', 'posted'),
            ('usado','!=',True),
        ])
        if len(xfind) > 0:
            return {'warning': {'message':'Este Cliente/Proveedor posee un anticipo disponible'}}


    @api.onchange('usar_anticipo')
    def _no_hay_anticipo(self):
        xfind = self.env['account.payment'].search([
            ('partner_id', '=', self.partner_id.id),
            ('anticipo', '=', True),
            ('state', '=', 'posted'),
            ('usado','!=',True),
            ])
        if len(xfind)==0 and self.usar_anticipo=='si':
            self.usar_anticipo='no'
            return {'warning': {'message':'No posee anticipo disponible Este Cliente/Proveedor '}}

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
        if self.usar_anticipo=='si':
            self.crea_asiento_anticipo_v3()

    def crea_asiento_anticipo_v3(self):

        #CREA LA CABECERA DEL ASIENTO DEL ANTICIPO
        valores=0
        valores_uds=0
        nro_si=0
        if not self.payment_ids:
            raise UserError(_('Debe agregar Lineas de Pagos de Anticipo'))
        else:
            for det_anti in self.payment_ids:
                if det_anti.confirmado=='no':
                    nro_si=nro_si+1
                    nombre_anti=self.get_name_anticipo()
                    valores=det_anti.monto_usar
                    fecha_doc=det_anti.payment_id.payment_date
                    #fecha_doc=self.date
                    if det_anti.payment_id.currency_id.id!=self.env.company.currency_id.id:
                        valores_uds=valores
                        #raise UserError(_('valores= %s')%valores)
                        #tasa= self.env['res.currency.rate'].search([('currency_id','=',det_anti.payment_id.currency_id.id),('name','<=',self.date)],order="name asc")
                        """tasa= self.env['res.currency.rate'].search([('currency_id','=',det_anti.payment_id.currency_id.id),('name','<=',fecha_doc)],order="name asc")
                        for det_tasa in tasa:
                            if self.date>=det_tasa.name:
                                valor_aux=det_tasa.rate
                        rate=round(1/valor_aux,2)
                        resultado=valores*rate
                        valores=resultado"""

                        resultado=valores*det_anti.payment_id.rate
                        valores=resultado
                        
                    
                    value = {
                        'name': nombre_anti,
                        'date': fecha_doc, #self.date,
                        'journal_id': self.journal_id.id,
                        'line_ids': False,
                        'state': 'draft',
                        'type': 'entry',# estte campo es el que te deja cambiar y almacenar valores 
                        'amount_total':valores,# revisar
                        ##'amount_total_signed':total_monto,# revisar
                        'partner_id': self.partner_id.id,
                        #'partner_id': 45,
                        'ref': "Pago Anticipo Factura Nro: %s " % (self.invoice_number),
                        'custom_rate':True,
                        'os_currency_rate':det_anti.payment_id.rate,
                        'amount_residual':0.0,
                        'amount_residual_signed':0.0,
                        #'name': "Comisión del %s %% del pago %s por comisión" % (igtf_porcentage,name),

                    }
                    move_obj = self.env['account.move']
                    move_id = move_obj.create(value)    

                    # CREA LAS LINEAS DE LOS ASIENTOS DE LOS ANTICIPOS
                    cuenta_anti_cliente = self.partner_id.account_anti_receivable_id.id
                    cuenta_anti_proveedor = self.partner_id.account_anti_payable_id.id
                    cuenta_cobrar = self.partner_id.property_account_receivable_id.id
                    cuenta_pagar = self.partner_id.property_account_payable_id.id
                    tipo_persona=self.type
                    if tipo_persona=="in_invoice":
                        cuenta_a=cuenta_anti_proveedor
                        cuenta_b=cuenta_pagar
                    if tipo_persona=="out_invoice":
                        cuenta_a=cuenta_cobrar
                        cuenta_b=cuenta_anti_cliente
                    #raise UserError(_('cuenta a=%s')%cuenta_anti_proveedor)
                    value = {
                        'name': nombre_anti,
                        'ref' : "Anticipo Documento Nro: %s " % (self.invoice_number),
                        'move_id': int(move_id.id),
                        'date': fecha_doc, #self.date,
                        'partner_id': self.partner_id.id,
                        #'partner_id': 45,
                        'journal_id': self.journal_id.id,
                        'account_id': cuenta_a,# aqui va cuenta de anticipo 
                        'date_maturity': False,
                        'credit': valores,#self.conv_div_extranjera(valores),#loca14
                        'debit': 0.0, # aqi va cero
                        'balance':-1*valores,#self.conv_div_extranjera(valores),#loca14
                        'asiento_pagado':"si",
                        'amount_currency': -1*valores_uds if det_anti.payment_id.currency_id.id!=self.env.company.currency_id.id else '',#-1*self.amount_currency(valores), #loca14
                        'currency_id':2 if det_anti.payment_id.currency_id.id!=self.env.company.currency_id.id else '',#self.moneda(), #loca14
                        ##'amount_residual_currency': -1*self.amount_currency(valores), #loca14

                    }
                   
                    move_line_obj = self.env['account.move.line']
                    move_line_id1 = move_line_obj.create(value)

                    value['account_id'] = cuenta_b # aqui va cuenta pxp proveedores
                    value['credit'] = 0.0 # aqui va cero
                    value['debit'] = valores #self.conv_div_extranjera(valores)#loca14
                    value['balance'] = valores #self.conv_div_extranjera(valores)#loca14
                    value['asiento_pagado'] = "si"
                    value['amount_currency'] = valores_uds if det_anti.payment_id.currency_id.id!=self.env.company.currency_id.id else '' #self.amount_currency(valores) #loca14
                    value['currency_id'] =2 if det_anti.payment_id.currency_id.id!=self.env.company.currency_id.id else ''# self.moneda() #loca14
                    ##value['amount_residual_currency'] = self.amount_currency(valores) #loca14
                   
                    move_line_id2 = move_line_obj.create(value)

                    moves= self.env['account.move'].search([('id','=',move_id.id)])
                    moves.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post() # aqui SE PUBLICA DICHO ASIENTO
                    #moves.action_post()  

                    ### AQUI ASOCIA EL ANTICIPO CON SU RESPECTIVO ASIENTO
                    det_anti.asiento_anticipo=move_id.id

                    ### AQUI COMIENZA A DESCONTAR EL MONTO USADO DEL ANTICIPO DE LO DISPONIBLE
                    disponible=det_anti.payment_id.saldo_disponible
                    det_anti.payment_id.saldo_disponible=disponible-det_anti.monto_usar
                    det_anti.payment_id.usado=True if det_anti.payment_id.saldo_disponible==0 else False
                    det_anti.confirmado='si'

            if nro_si==0:
                raise UserError(_('No hay nuevos anticipos para cruzar'))



    
    def button_draft(self):
        super().button_draft()
        if self.usar_anticipo=='si':
            if self.payment_ids:
                for rec in self.payment_ids:
                    if rec.asiento_anticipo:
                        rec.asiento_anticipo.with_context(force_delete=True).unlink()
                    valor=rec.saldo_disponible+rec.monto_usar
                    rec.saldo_disponible=valor
                    rec.payment_id.saldo_disponible=valor
                    rec.payment_id.usado=False
                    rec.monto_usar=valor
                    rec.confirmado='no'



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
                'name': 'Localización Venezolana asientos Pagos de anticipos %s' % company_id.id,
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
        
class AccountPaymentAnticipo(models.Model):

    _name = 'account.payment.anticipo'

    move_id = fields.Many2one('account.move')
    payment_id = fields.Many2one('account.payment', string='Anticipos Pendientes.')
    monto_original = fields.Monetary()
    saldo_disponible = fields.Monetary(compute='_compute_saldo_disponible')
    monto_usar=fields.Monetary(default=0)
    currency_id=fields.Many2one('res.currency')
    partner_id=fields.Many2one('res.partner')
    asiento_anticipo = fields.Many2one('account.move')
    tipo = fields.Selection(related='move_id.type',store=True)
    confirmado=fields.Char(default='no')

    @api.onchange('payment_id','move_id.state')
    def _compute_saldo_disponible(self):
        for rec in self:
            if rec.payment_id:
                rec.monto_original=rec.payment_id.amount
                rec.saldo_disponible=rec.payment_id.saldo_disponible
                rec.currency_id=rec.payment_id.currency_id.id
                rec.partner_id=rec.move_id.partner_id.id
                if rec.monto_usar==0:
                    rec.monto_usar=rec.payment_id.saldo_disponible
            if not rec.payment_id:
                rec.saldo_disponible=0

    def unlink(self):
        for rec in self:
            if rec.confirmado=='si':
                raise UserError(_("No se pueden eliminar anticipos ya confirmados para esta factura"))
        super().unlink()
