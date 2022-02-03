# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields,models,api,_
import datetime
from odoo.exceptions import UserError, ValidationError

class AccountExtPayment(models.Model):
    _name = 'hr.ext.payment'

    name=fields.Char(default="/", string="Nro Transacción")
    monto=fields.Monetary()
    monto_signed=fields.Float()
    monto_signed_uds=fields.Float()
    currency_id = fields.Many2one('res.currency',default=lambda self: self.env.company.currency_id.id,string="Moneda de pago")
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    state = fields.Selection([('draft', 'Borrador'),('paid', 'Pagado')], readonly=True, default='draft', string="Status")
    account_journal_id = fields.Many2one('account.journal',string="Diario")
    fecha=fields.Datetime()
    #sale_ext_order_id=fields.Many2one('sale.ext.order',string="Doc Venta")
    tasa=fields.Float(digits=(12,4))
    monto_pendiente=fields.Char()
    moneda_venta=fields.Many2one('res.currency',string="Moneda doc venta")
    employee_id=fields.Many2one('hr.employee')
    #motivo=fields.Char(default="Pago para empleado")
    motivo=fields.Char()
    asiento_move_id = fields.Many2one('account.move', 'Id de Movimiento del reembolso donde pertenece dicho pago')
    informe_id = fields.Many2one('hr.expense.sheet')

    def action_register_ext_payment(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return ''
        #raise UserError(_('valor=%s')%active_ids[0])
        #self.sale_ext_order_id=active_ids[0]
        return {
            'name': _('Register Payment'),
            'res_model': len(active_ids) == 1 and 'hr.ext.payment',
            'view_mode': 'form',
            'view_id': len(active_ids) != 1 and self.env.ref('hr_expense_gastos_anticipo.vista_from_pago_employee').id,
            'context': self.env.context,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    @api.onchange('company_id')
    def default_nro_doc(self):
        id_expenxe=""
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        id_expenxe=active_ids[0]
        #raise UserError(_('valorxxx=%s')%id_expenxe)
        if id_expenxe:
            valida_1=self.env['hr.expense.sheet'].search([('id','=',id_expenxe)])
            #raise UserError(_('valida_1=%s')%valida_1)
            if valida_1:
                self.employee_id=valida_1.employee_id.id
                self.monto=valida_1.monto_diferencia
                self.monto_pendiente=str(valida_1.monto_diferencia)+" Bs/ $"+str(valida_1.monto_diferencia_uds)
                self.informe_id=id_expenxe


    def _compute_nb_cliente(self):
        for selff in self:
            selff.cliente_id=selff.sale_ext_order_id.cliente_id.id

    @api.onchange('sale_ext_order_id')
    def _compute_monto_pendiente(self):
        self.monto_pendiente=0


    def get_name(self):
        '''metodo que crea el Nombre del asiento contable si la secuencia no esta creada, crea una con el
        nombre: 'l10n_ve_cuenta_retencion_iva'''

        self.ensure_one()
        SEQUENCE_CODE = 'secuencia_pago_caja_dolar'
        company_id = self.env.company.id
        IrSequence = self.env['ir.sequence'].with_context(force_company=self.env.company.id)
        name = IrSequence.next_by_code(SEQUENCE_CODE)

        # si aún no existe una secuencia para esta empresa, cree una
        if not name:
            IrSequence.sudo().create({
                'prefix': 'Pago Nro: ',
                'name': 'Secuencia Pago Caja Dolar %s' % self.env.company.name,
                'code': SEQUENCE_CODE,
                'implementation': 'no_gap',
                'padding': 8,
                'number_increment': 1,
                'company_id': self.env.company.id,#loca14
            })
            name = IrSequence.next_by_code(SEQUENCE_CODE)
        return name

    def pagar(self):
        if self.tasa=="0" or not self.tasa:
            raise UserError(_('Tiene que registrar un valor de tasa cambiaria'))
        if not self.env.company.account_remb_employee_receibale_id.id:
            raise UserError(_('Debe registar una cuenta de pago para este empleado. Vaya a Ajustes>Usuarios y compañias>Compañias>Pestaña Config. Empleado y asigne una cuenta'))
        self.state="paid"
        if self.name=="/":
            self.name=self.get_name()
        id_move=self.asiento_pago()
        self.asiento_pago_line(id_move)
        self.asiento_move_id=id_move.id
        self.asiento_move_id.action_post()
        if self.company_id.currency_id.id!=self.currency_id.id:
            self.monto_signed=self.monto*self.tasa
            self.monto_signed_uds=self.monto
        else:
            self.monto_signed=self.monto
            self.monto_signed_uds=self.monto/self.tasa
        if self.informe_id:
            actualiza=self.env['hr.expense.sheet'].search([('id','=',self.informe_id.id)])
            #raise UserError(_('Tiene %s')%actualiza)
            if actualiza:
                for det in actualiza:
                    if det.monto_diferencia==self.monto_signed:
                        self.env['hr.expense.sheet'].browse(det.id).write({
                            'status_saldo_pendiente':"paid",
                            'paga_pendiente':True,
                            'state':"done",
                            'monto_diferencia':0.0,
                            'monto_diferencia_uds':0.0,
                            })
                    else:
                        self.env['hr.expense.sheet'].browse(det.id).write({
                            'monto_diferencia':(det.monto_diferencia-self.monto_signed),
                            'monto_diferencia_uds':(det.monto_diferencia_uds-self.monto_signed_uds),
                            })
        """valor=self.sale_ext_order_id.total_adeudado"""

        # Descuento cuanto la moneda de pago es igual a la moneda del registro de ventas
        """if self.currency_id.id==self.moneda_venta.id:
            self.sale_ext_order_id.total_adeudado=valor-self.monto"""
        # Descuento cuanto la moneda de pago es diferente a la moneda del registro de ventas
        """if self.currency_id.id!=self.moneda_venta.id:
            if self.moneda_venta.id!=self.company_id.currency_id.id:
                self.sale_ext_order_id.total_adeudado=(valor-(self.monto/self.tasa))
            else:
                self.sale_ext_order_id.total_adeudado=(valor-(self.monto*self.tasa))"""
        # Cambia el status del documento de venta

    def asiento_pago(self):
        #raise UserError(_('darrell = %s')%self.partner_id.vat_retention_rate)
        name = self.name 
        signed_amount_total=0
        amont_totall=self.monto if self.currency_id.id==self.env.company.currency_id.id else self.monto*self.tasa
        #amount_itf = round(float(total_monto) * float((igtf_porcentage / 100.00)),2)
        signed_amount_total=amont_totall
        id_journal=self.account_journal_id.id#loca14
        #raise UserError(_('papa = %s')%signed_amount_total)
        value = {
            'name': name,
            'date': self.fecha,#listo
            #'amount_total':self.vat_retentioned,# LISTO
            'partner_id': self.company_id.partner_id.id, #LISTO
            'journal_id':id_journal,
            'ref': "Pago al empleado %s" % (self.employee_id.name),
            #'amount_total':self.vat_retentioned,# LISTO
            'amount_total_signed':signed_amount_total,# LISTO
            'type': "entry",# estte campo es el que te deja cambiar y almacenar valores
            'company_id':self.env.company.id,#loca14
            'custom_rate':True,
            'os_currency_rate':self.tasa,
            'currency_id':self.currency_id.id,
        }
        #raise UserError(_('value= %s')%value)
        move_obj = self.env['account.move']
        move_id = move_obj.create(value)
        return move_id

    def asiento_pago_line(self,id_movv):
        name = "xxxx"#consecutivo_asiento
        valores = self.monto if self.currency_id.id==self.env.company.currency_id.id else self.monto*self.tasa
        #raise UserError(_('valores = %s')%valores)
        cero = 0.0
       
        cuenta_ret_proveedor=self.env.company.account_remb_employee_receibale_id.id# loca14 cuenta retencion proveedores
        cuenta_prove_pagar = self.account_journal_id.default_credit_account_id.id #loca14
        cuenta_haber=cuenta_prove_pagar
        cuenta_debe=cuenta_ret_proveedor

        balances=cero-valores
        value = {
             'name': self.motivo,#name,
             'ref' : "Pago al empleado  %s | Motivo: %s" % (self.employee_id.name,self.motivo),
             'move_id': int(id_movv),
             'date': self.fecha,
             'partner_id': self.env.company.partner_id.id,
             'account_id': cuenta_haber,
             #'currency_id':self.invoice_id.currency_id.id,
             #'amount_currency': 0.0,
             #'date_maturity': False,
             'credit': valores,
             'debit': 0.0, # aqi va cero   EL DEBITO CUNDO TIENE VALOR, ES QUE EN ACCOUNT_MOVE TOMA UN VALOR
             'balance':-valores, # signo negativo
             'price_unit':balances,
             'price_subtotal':balances,
             'price_total':balances,
             'currency_id':self.currency_id.id if self.currency_id.id!=self.env.company.currency_id.id else "",
             'amount_currency': -1*self.monto if self.currency_id.id!=self.env.company.currency_id.id else "",

        }

        move_line_obj = self.env['account.move.line']
        move_line_id1 = move_line_obj.create(value)

        balances=valores-cero
        value['name'] = self.motivo
        value['account_id'] = cuenta_debe
        value['credit'] = 0.0 # aqui va cero
        value['debit'] = valores
        value['balance'] = valores
        value['price_unit'] = balances
        value['price_subtotal'] = balances
        value['price_total'] = balances
        value['currency_id'] = self.currency_id.id if self.currency_id.id!=self.env.company.currency_id.id else ""
        value['amount_currency'] = self.monto if self.currency_id.id!=self.env.company.currency_id.id else ""

        move_line_id2 = move_line_obj.create(value)


    def cancel(self):
        self.state="draft"
        self.asiento_move_id.filtered(lambda move: move.state == 'posted').button_draft()
        self.asiento_move_id.with_context(force_delete=True).unlink()

    def _compute_total(self):
        for selff in self:
            acom=0
            for det in selff.line_ids:
                acom=acom+det.total
            selff.total=acom
            if selff.company_id.currency_id.id!=selff.currency_id.id:
                selff.total_signed=acom*selff.tasa
                #selff.total_signed_uds=acom
            else: 
                selff.total_signed=acom
                #selff.total_signed_uds=acom*selff.tasa
            selff.total_signed_uds=selff.total_signed/selff.tasa

    def get_literal_amount(self,amount):
        indicador = [("",""),("MIL","MIL"),("MILLON","MILLONES"),("MIL","MIL"),("BILLON","BILLONES")]
        entero = int(amount)
        decimal = int(round((amount - entero)*100))
        contador = 0
        numero_letras = ""
        while entero >0:
            a = entero % 1000
            if contador == 0:
                en_letras = self.convierte_cifra(a,1).strip()
            else:
                en_letras = self.convierte_cifra(a,0).strip()
            if a==0:
                numero_letras = en_letras+" "+numero_letras
            elif a==1:
                if contador in (1,3):
                    numero_letras = indicador[contador][0]+" "+numero_letras
                else:
                    numero_letras = en_letras+" "+indicador[contador][0]+" "+numero_letras
            else:
                numero_letras = en_letras+" "+indicador[contador][1]+" "+numero_letras
            numero_letras = numero_letras.strip()
            contador = contador + 1
            entero = int(entero / 1000)
        numero_letras = numero_letras+" con " + str(decimal) +"/100"
        print('numero: ',amount)
        print(numero_letras)
        return numero_letras
        
    def convierte_cifra(self, numero, sw):
        lista_centana = ["",("CIEN","CIENTO"),"DOSCIENTOS","TRESCIENTOS","CUATROCIENTOS","QUINIENTOS","SEISCIENTOS","SETECIENTOS","OCHOCIENTOS","NOVECIENTOS"]
        lista_decena =  ["",("DIEZ","ONCE","DOCE","TRECE","CATORCE","QUINCE","DIECISEIS","DIECISIETE","DIECIOCHO","DIECINUEVE"),
                        ("VEINTE","VEINTI"),("TREINTA","TREINTA Y "),("CUARENTA" , "CUARENTA Y "),
                        ("CINCUENTA" , "CINCUENTA Y "),("SESENTA" , "SESENTA Y "),
                        ("SETENTA" , "SETENTA Y "),("OCHENTA" , "OCHENTA Y "),
                        ("NOVENTA" , "NOVENTA Y ")
                        ]
        lista_unidad = ["",("UN" , "UNO"),"DOS","TRES","CUATRO","CINCO","SEIS","SIETE","OCHO","NUEVE"]
        centena = int (numero / 100)
        decena = int((numero -(centena * 100))/10)
        unidad = int(numero - (centena * 100 + decena * 10))
        
        texto_centena = ""
        texto_decena = ""
        texto_unidad = ""
        
        #Validad las centenas
        texto_centena = lista_centana[centena]
        if centena == 1:
            if (decena + unidad)!=0:
                texto_centena = texto_centena[1]
            else:
                texto_centena = texto_centena[0]
        
        #Valida las decenas
        texto_decena = lista_decena[decena]
        if decena == 1:
            texto_decena = texto_decena[unidad]
        elif decena > 1:
            if unidad != 0:
                texto_decena = texto_decena[1]
            else:
                texto_decena = texto_decena[0]
        
        #Validar las unidades
        if decena != 1:
            texto_unidad = lista_unidad[unidad]
            if unidad == 1:
                texto_unidad = texto_unidad[sw]
        
        return "%s %s %s" %(texto_centena,texto_decena,texto_unidad)