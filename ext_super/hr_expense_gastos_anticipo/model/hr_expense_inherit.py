# -*- coding: utf-8 -*-


import logging
from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import datetime


class Partner(models.Model):
    _inherit = 'res.partner'

    vat_retention_rate = fields.Float(string='Retention rate',required=True, default=0)


class AccountMove(models.Model):
    _inherit = 'account.move'

    anticipo_gastos_employee_id=fields.Many2one('account.gasto.anticipo')
    asiento_gastos_anticipo=fields.Boolean(default=False)

    @api.depends('partner_id')
    def _concatena(self):
        for selff in self:
            if selff.partner_id.doc_type=="v":
                tipo_doc="V"
            if selff.partner_id.doc_type=="e":
                #self.partner_id.doc_type="E"
                tipo_doc="E"
            if selff.partner_id.doc_type=="g":
                tipo_doc="G"
            if selff.partner_id.doc_type=="j":
                tipo_doc="J"
            if selff.partner_id.doc_type=="p":
                tipo_doc="P"
            if selff.partner_id.doc_type=="c":
                tipo_doc="C"
            if not selff.partner_id.doc_type:
                tipo_doc="?"
            if not selff.partner_id.vat:
                vat=str(00000000)
            else:
                vat=selff.partner_id.vat
            selff.rif=str(tipo_doc)+"-"+str(vat)

class AccountMoveLineResumen(models.Model):
    _inherit="account.move.line.resumen"
    proveedor_id=fields.Many2one('res.partner')

class HrExpense(models.Model):
    _inherit = "hr.expense"

    proveedor_id = fields.Many2one('res.partner')
    mostrar_libro = fields.Boolean(default=True)
    invoice_number=fields.Char()
    invoice_ctrl_number=fields.Char()
    tasa_personalizada = fields.Boolean()
    rate = fields.Float(default=1,digits=(12, 4))
    rate_aux = fields.Float(compute='_compute_tasa',digits=(12, 4))
    unit_amount = fields.Monetary(digits=(12, 4))
    date_bill =fields.Date()
    payment_mode = fields.Selection([
        ("own_account", "Employee (to reimburse)"),
        ("company_account", "Company")
    ], default='company_account', states={'done': [('readonly', True)], 'approved': [('readonly', True)], 'reported': [('readonly', True)]}, string="Paid By")
    #informe_gasto_id = fields.Many2one('hr.expense.sheet')

    #@api.onchange('state')
    def _compute_tasa(self):
        tasas=1
        if self.tasa_personalizada!=True:
            lista_tasa = self.env['res.currency.rate'].search([('currency_id', '=', 2),('name','<=',self.date)],order='id asc')
            for det in lista_tasa:
                tasas=(1/det.rate)
            self.rate=tasas
        self.rate_aux=tasas

    def _get_account_move_line_values(self):
        move_line_values_by_expense = {}
        for expense in self:
            move_line_name = expense.employee_id.name + ': ' + expense.name.split('\n')[0][:64]
            account_src = expense._get_expense_account_source()
            account_dst = expense._get_expense_account_destination()
            account_date = expense.sheet_id.accounting_date or expense.date or fields.Date.context_today(expense)

            company_currency = expense.company_id.currency_id
            different_currency = expense.currency_id and expense.currency_id != company_currency

            move_line_values = []
            taxes = expense.tax_ids.with_context(round=True).compute_all(expense.unit_amount, expense.currency_id, expense.quantity, expense.product_id)
            total_amount = 0.0
            total_amount_currency = 0.0
            partner_id = expense.employee_id.address_home_id.commercial_partner_id.id

            # source move line
            amount = taxes['total_excluded']
            amount_currency = False
            if different_currency:
                if expense.tasa_personalizada!=True:
                    amount = expense.currency_id._convert(amount, company_currency, expense.company_id, account_date)
                    amount_currency = taxes['total_excluded']
                else:
                    amount=expense.unit_amount*expense.quantity*expense.rate
                    amount_currency = taxes['total_excluded']
            move_line_src = {
                'name': move_line_name,
                'quantity': expense.quantity or 1,
                'debit': amount if amount > 0 else 0,
                'credit': -amount if amount < 0 else 0,
                'amount_currency': amount_currency if different_currency else 0.0,
                'account_id': account_src.id,
                'product_id': expense.product_id.id,
                'product_uom_id': expense.product_uom_id.id,
                'analytic_account_id': expense.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, expense.analytic_tag_ids.ids)],
                'expense_id': expense.id,
                'partner_id': partner_id,
                'tax_ids': [(6, 0, expense.tax_ids.ids)],
                'tag_ids': [(6, 0, taxes['base_tags'])],
                'currency_id': expense.currency_id.id if different_currency else False,
                'asiento_gastos':True,
                'tasa_gastos':expense.rate,
            }
            move_line_values.append(move_line_src)
            total_amount += -move_line_src['debit'] or move_line_src['credit']
            total_amount_currency += -move_line_src['amount_currency'] if move_line_src['currency_id'] else (-move_line_src['debit'] or move_line_src['credit'])

            # taxes move lines
            for tax in taxes['taxes']:
                amount = tax['amount']
                amount_currency = False
                if different_currency:
                    if expense.tasa_personalizada!=True:
                        amount = expense.currency_id._convert(amount, company_currency, expense.company_id, account_date)
                        amount_currency = tax['amount']
                    else:
                        amount = amount*expense.rate
                        amount_currency = tax['amount']
                move_line_tax_values = {
                    'name': tax['name'],
                    'quantity': 1,
                    'debit': amount if amount > 0 else 0,
                    'credit': -amount if amount < 0 else 0,
                    'amount_currency': amount_currency if different_currency else 0.0,
                    'account_id': tax['account_id'] or move_line_src['account_id'],
                    'tax_repartition_line_id': tax['tax_repartition_line_id'],
                    'tag_ids': tax['tag_ids'],
                    'tax_base_amount': tax['base'],
                    'expense_id': expense.id,
                    'partner_id': partner_id,
                    'currency_id': expense.currency_id.id if different_currency else False,
                    'asiento_gastos':True,
                    'tasa_gastos':expense.rate,
                }
                total_amount -= amount
                total_amount_currency -= move_line_tax_values['amount_currency'] or amount
                move_line_values.append(move_line_tax_values)

            # destination move line
            #raise UserError(_('id=%s')%self.sheet_id.payment_ids)
            #groups = self.env['hr.expense.sheet'].search([('')])
            sig=1
            if self.sheet_id.payment_ids:
                cuenta_id = self.env.company.account_anti_employee_payable_id.id
                if total_amount<0:
                    sig=-1
                total_amount=(total_amount-sig*self.sheet_id.monto_diferencia)
            else:
                cuenta_id=account_dst
            #raise UserError(_('total_amount=%s')%total_amount)
            move_line_dst = {
                'name': move_line_name,
                'debit': total_amount > 0 and total_amount,
                'credit': total_amount < 0 and -total_amount,
                'account_id': cuenta_id,
                'date_maturity': account_date,
                'amount_currency': total_amount_currency if different_currency else 0.0,
                'currency_id': expense.currency_id.id if different_currency else False,
                'expense_id': expense.id,
                'partner_id': partner_id,
                'asiento_gastos':True,
                'tasa_gastos':expense.rate,
            }
            move_line_values.append(move_line_dst)

            if self.sheet_id.monto_diferencia:
                move_line_dif_empl = {
                    'name': "DIFERENCIA DE GASTOS A PAGAR A EMPLEADO"+self.employee_id.name,
                    'debit':0.0,
                    'credit':self.sheet_id.monto_diferencia,
                    'account_id':self.env.company.account_remb_employee_receibale_id.id,
                    'date_maturity': account_date,
                    'amount_currency': total_amount_currency if different_currency else 0.0,
                    'currency_id': expense.currency_id.id if different_currency else False,
                    'expense_id': expense.id,
                    'partner_id': partner_id,
                    'asiento_gastos':True,
                    'tasa_gastos':expense.rate,
                }
                move_line_values.append(move_line_dif_empl)

            #raise UserError(_('id=%s')%self.sheet_id.monto_diferencia)

            move_line_values_by_expense[expense.id] = move_line_values

        return move_line_values_by_expense



    @api.onchange('employee_id')
    def _onchange_partner_id(self):
        xfind = self.env['account.gasto.anticipo'].search([
            ('employee_id', '=', self.employee_id.id),
            ('anticipo', '=', True),
            ('state', '=', 'posted'),
            ('usado','!=',True)
        ])
        if len(xfind) > 0:
            return {'warning': {'message':'Este empleado posee un anticipo disponible'}}

class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    type = fields.Char(default='in_invoice')
    partner_id=fields.Many2one('res.partner',compute='_compute_partner')
    payment_ids = fields.Many2many('account.gasto.anticipo', string='Anticipos')
    total_amount_signed = fields.Float(compute='_compute_total_div')

    monto_diferencia = fields.Monetary(digits=(12,4))
    monto_diferencia_uds = fields.Float(digits=(12,4))
    monto_dif_compute = fields.Float(compute='_compute_dif_pendiente')

    raya = fields.Char(default=" / ")
    uds = fields.Char(default=" $")
    paga_pendiente = fields.Boolean(default=False)
    status_saldo_pendiente = fields.Selection([('paid', 'Pagado'),('earring', 'Pendiente')], readonly=True, default='earring', string="Status Saldo Pendiente")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('post', 'Posted'),
        ('partially_done', 'Parcialmente Pagado'),
        ('done', 'Paid'),
        ('cancel', 'Refused')
    ], string='Status', index=True, readonly=True, tracking=True, copy=False, default='draft', required=True, help='Expense Report State')
    #asiento_gastos_id = fields.Many2one('account.move')

    @api.constrains('state','payment_ids')
    def _compute_dif_pendiente(self):
        acom=0
        acom2=0
        for anti in self.payment_ids:
            if anti.currency_id.id==self.env.company.currency_id.id:
                acom=acom+anti.saldo_disponible#anti.amount_signed
                acom2=acom2+(anti.saldo_disponible/anti.rate)
            else:
                acom=acom+anti.saldo_disponible*anti.rate
                acom2=acom2+anti.saldo_disponible
            """else:
                if anti.currency_id.id==self.env.company.currency_id.id:
                    acom=acom+anti.amount
                else:
                    acom=acom+anti.amount*anti.rate"""
        resultado=(acom-self.total_amount)
        if resultado>=0:
            if self.state in ('draft','submit','approve'):
                self.monto_diferencia=0
                self.monto_diferencia_uds=0
            self.monto_dif_compute=0
        else:
            if self.state in ('draft','submit','approve'):
                self.monto_diferencia=abs(acom-self.total_amount)
                self.monto_diferencia_uds=abs(acom2-self.total_amount_signed)
            self.monto_dif_compute=abs(acom-self.total_amount)
        """if self.paga_pendiente==True or self.monto_diferencia==0:
            self.status_saldo_pendiente='paid'
        if self.monto_diferencia!=0 and self.paga_pendiente==False:
            self.status_saldo_pendiente='earring'"""


    def _compute_total_div(self):
        acom=0
        for roc in self.expense_line_ids:
            tasa=roc.rate
            if roc.currency_id.id!=roc.company_currency_id.id:
                acom=acom+roc.total_amount
            else:
                acom=acom+(roc.total_amount/roc.rate)
        self.total_amount_signed=acom

    @api.onchange('employee_id')
    def _compute_partner(self):
        self.partner_id=self.employee_id.user_id.partner_id.id

    @api.onchange('employee_id')
    def _onchange_partner_id(self):
        xfind = self.env['account.gasto.anticipo'].search([
            ('employee_id', '=', self.employee_id.id),
            ('anticipo', '=', True),
            ('state', '=', 'posted'),
            ('usado','!=',True)
        ])
        if len(xfind) > 0:
            return {'warning': {'message':'Este empleado posee un anticipo disponible'}}

    def action_sheet_move_create(self): # aqui publica
        super().action_sheet_move_create()
        self.suma_alicuota_iguales_iva()
        self.cotea_anticipo()
        #self.asocia_asiento()
        xfind = self.env['account.gasto.anticipo'].search([
            ('employee_id', '=', self.employee_id.id),
            ('anticipo', '=', True),
            ('state', '=', 'posted'),
            ('usado','!=',True)
        ])
        if len(xfind) > 0 and not self.payment_ids:
            raise UserError(_('Este empleado posee anticipos disponibles. Asocie estos anticipos'))
        if self.monto_diferencia==0:
            self.status_saldo_pendiente='paid'
            self.state='done'
        else:
            self.status_saldo_pendiente='earring'
            self.state='partially_done'
        """for rac in self.expense_line_ids:
            if rac.tasa_personalizada==True and rac.currency_id.id!=rac.company_currency_id.id:
                rac.total_amount_company=rac.total_amount*rac.rate"""
        #### proveedor,company_id

    """def asocia_asiento(self):
        for rec in self.expense_line_ids:
            id_gastos=rec.id
            busca_lineas_mov=self.env['account.move.line'].search([('expense_id','=',id_gastos)])
            for det in busca_lineas_mov:
                self.asiento_gastos_id=det.move_id.id"""

    def cotea_anticipo(self):
        #raise UserError(_('anticipos: %s')%self.payment_ids)
        pendiente=self.total_amount_signed
        pendiente_bs=self.total_amount
        for rec in self.payment_ids:
            if rec.currency_id.id!=self.company_id.currency_id.id:
                #raise UserError(_('rec1=%s rec2=%s')%(rec.currency_id.id,self.company_id.currency_id.id))
                if pendiente >=0:
                    if rec.saldo_disponible<=pendiente:#self.total_amount_signed:
                        resultado = rec.saldo_disponible-pendiente #rec.amount-pendiente
                        pendiente=abs(resultado)
                        if resultado <= 0:
                            rec.saldo_disponible=0
                            rec.usado=True
                        if resultado>0:
                            rec.saldo_disponible=self.total_amount_signed-rec.saldo_disponible#self.total_amount_signed-rec.amount
                    else:
                        resultado=rec.saldo_disponible-pendiente
                        pendiente=abs(resultado)
                        if resultado>0:
                            rec.saldo_disponible=resultado #rec.saldo_disponible-self.total_amount_signed
                        else:
                            rec.saldo_disponible=0
                            rec.usado=True
            if rec.currency_id.id==self.company_id.currency_id.id:
                if pendiente_bs >=0:
                    if rec.saldo_disponible<=pendiente_bs: #self.total_amount:
                        resultado = rec.saldo_disponible-pendiente_bs #rec.amount-pendiente
                        pendiente_bs=abs(resultado)
                        if resultado <= 0:
                            rec.saldo_disponible=0
                            rec.usado=True
                        if resultado>0:
                            rec.saldo_disponible=self.total_amount-rec.saldo_disponible#self.total_amount_signed-rec.amount
                    else:
                        resultado=rec.saldo_disponible-pendiente_bs
                        pendiente_bs=abs(resultado)
                        if resultado>0:
                            rec.saldo_disponible=resultado #rec.saldo_disponible-self.total_amount
                        else:
                            rec.saldo_disponible=0
                            rec.usado=True


    def action_submit_sheet(self):
        super().action_submit_sheet()
        for rac in self.expense_line_ids:
            if rac.tasa_personalizada==True and rac.currency_id.id!=rac.company_currency_id.id:
                rac.total_amount_company=rac.total_amount*rac.rate
        #3self.asocia_informe()

    """def asocia_informe(self):
        for rec in self.expense_line_ids:
            rec.informe_gasto_id=self.id

    def reset_expense_sheets(self):
        super().reset_expense_sheets()
        for roc in self.expense_line_ids:
            roc.informe_gasto_id=0"""



    def crea_invoice_fisticio(self,proveedor_id,company_id,date,diario_id,dett):
        #raise UserError(_('tasa: %s')%proveedor_id)
        for selff in self:
            campos={
            'name':"/",#proveedor.name,
            'partner_id':proveedor_id,
            'company_id':company_id,
            'currency_id':dett.currency_id.id,
            'state':"draft",
            'type':"entry",
            'journal_id':diario_id,
            'date':date,
            'invoice_date':date,
            'invoice_number':dett.invoice_number,
            'invoice_ctrl_number':dett.invoice_ctrl_number,
            'os_currency_rate':dett.rate,
            'custom_rate':dett.tasa_personalizada,
            }
            idd=selff.env['account.move'].create(campos)
            return idd.id


    def suma_alicuota_iguales_iva(self):
        if self.type=='in_invoice' or self.type=='in_refund' or self.type=='in_receipt':
            type_tax_use='purchase'
            porcentaje_ret=self.company_id.partner_id.vat_retention_rate
        if self.type=='out_invoice' or self.type=='out_refund' or self.type=='out_receipt':
            type_tax_use='sale'
            porcentaje_ret=self.partner_id.vat_retention_rate
        if self.type=='in_invoice' or self.type=='out_invoice':
            tipo_doc="01"
        if self.type=='in_refund' or self.type=='out_refund':
            tipo_doc="03"
        if self.type=='in_receipt' or self.type=='out_receipt':
            tipo_doc="02"

        if self.type in ('in_invoice','in_refund','in_receipt','out_receipt','out_refund','out_invoice'):
            # ****** AQUI VERIFICA SI LAS LINEAS DE FACTURA TIENEN ALICUOTAS *****
            verf=self.expense_line_ids
            #raise UserError(_('verf= %s')%verf)
            for det_verf in verf:
                #raise UserError(_('det_verf.tax_ids.id= %s')%det_verf.tax_ids.id)
                if not det_verf.tax_ids.id:
                    raise UserError(_('Las Lineas de la Factura deben tener un tipo de alicuota o impuestos'))
            # ***** FIN VERIFICACION
            lista_impuesto = self.env['account.tax'].search([('type_tax_use','=',type_tax_use)])

            for det_tax in lista_impuesto:
                tipo_alicuota=det_tax.aliquot
                
                #raise UserError(_('tipo_alicuota: %s')%tipo_alicuota)

                det_lin=self.expense_line_ids.search([('tax_ids','=',det_tax.id),('sheet_id','=',self.id),('mostrar_libro','=','True')])
                if det_lin:
                    for det_fac in det_lin:
                        base=0
                        total=0
                        total_impuesto=0
                        total_exento=0
                        alicuota_adicional=0
                        alicuota_reducida=0
                        alicuota_general=0
                        base_general=0
                        base_reducida=0
                        base_adicional=0
                        retenido_general=0
                        retenido_reducida=0
                        retenido_adicional=0
                        valor_iva=0
                        if self.state!="cancel":
                            base=base+det_fac.untaxed_amount
                            total=total+det_fac.total_amount
                            id_impuesto=det_fac.tax_ids.id
                            total_impuesto=total_impuesto+(det_fac.total_amount-det_fac.untaxed_amount)
                            if tipo_alicuota=="general":
                                alicuota_general=alicuota_general+(det_fac.total_amount-det_fac.untaxed_amount)
                                base_general=base_general+det_fac.untaxed_amount
                                valor_iva=det_fac.tax_ids.amount
                            if tipo_alicuota=="exempt":
                                total_exento=total_exento+det_fac.untaxed_amount
                            if tipo_alicuota=="reduced":
                                alicuota_reducida=alicuota_reducida+(det_fac.total_amount-det_fac.untaxed_amount)
                                base_reducida=base_reducida+det_fac.untaxed_amount
                            if tipo_alicuota=="additional":
                                alicuota_adicional=alicuota_adicional+(det_fac.total_amount-det_fac.untaxed_amount)
                                base_adicional=base_adicional+det_fac.untaxed_amount
                        total_ret_iva=(total_impuesto*porcentaje_ret)/100
                        retenido_general=(alicuota_general*porcentaje_ret)/100
                        retenido_reducida=(alicuota_reducida*porcentaje_ret)/100
                        retenido_adicional=(alicuota_adicional*porcentaje_ret)/100
                        if self.type=='in_refund' or self.type=='out_refund':
                            base=-1*base
                            total=-1*total
                            total_impuesto=-1*total_impuesto
                            alicuota_general=-1*alicuota_general
                            valor_iva=-1*valor_iva
                            total_exento=-1*total_exento
                            alicuota_reducida=-1*alicuota_reducida
                            alicuota_adicional=-1*alicuota_adicional
                            total_ret_iva=-1*total_ret_iva
                            base_adicional=-1*base_adicional
                            base_reducida=-1*base_reducida
                            base_general=-1*base_general
                            retenido_general=-1*retenido_general
                            retenido_reducida=-1*retenido_reducida
                            retenido_adicional=-1*retenido_adicional
                        #raise UserError(_('cedula = %s')%det_fac.proveedor_id.id)

                        values={
                        'total_con_iva':total,#listo
                        'total_base':base,#listo
                        'total_valor_iva':total_impuesto,#listo
                        'tax_id':det_fac.tax_ids.id,
                        'invoice_id':self.crea_invoice_fisticio(det_fac.proveedor_id.id,self.company_id.id,det_fac.date,self.bank_journal_id.id,det_fac), #det_fac.proveedor_id,self.company_id.id
                        'porcentaje_ret':porcentaje_ret,
                        'total_ret_iva':total_ret_iva,
                        'type':self.type,
                        'state':'posted',
                        'tipo_doc':tipo_doc,
                        'total_exento':total_exento,#listo
                        'alicuota_reducida':alicuota_reducida,#listo
                        'alicuota_adicional':alicuota_adicional,#listo
                        'alicuota_general':alicuota_general,#listo
                        'fecha_fact':det_fac.date,
                        'base_adicional':base_adicional,#listo
                        'base_reducida':base_reducida,#listo
                        'base_general':base_general,#listo
                        'retenido_general':retenido_general,
                        'retenido_reducida':retenido_reducida,
                        'retenido_adicional':retenido_adicional,
                        'company_id':self.company_id.id,#loca14
                        'proveedor_id':det_fac.proveedor_id.id,
                        }
                        self.env['account.move.line.resumen'].create(values)

    def pago_pendiente(self):
        #raise UserError(_("id factura=%s")%self.id)
        return self.env['hr.ext.payment']\
            .with_context(active_ids=self.ids, active_model='hr.expense.sheet', active_id=self.id)\
            .action_register_ext_payment()

class AccountGastoAnticipo(models.Model):
    _name = 'account.gasto.anticipo'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    nro_recibo = fields.Char(default='/',track_visibility='onchange')
    name = fields.Char(compute="_compute_name",track_visibility='onchange') 
    payment_date = fields.Date(string='Date', default=fields.Date.context_today, required=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False, tracking=True,track_visibility='onchange')
    journal_id = fields.Many2one('account.journal',domain="[('type', 'in', ('bank', 'cash'))]", string='Journal', required=True, readonly=True, states={'draft': [('readonly', False)]})
    employee_id = fields.Many2one('hr.employee', string='Empleado',required=True,readonly=True,track_visibility='onchange' ,states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Borrador'), ('posted', 'Validado')], readonly=True, default='draft', string="Status")

    move_line_ids = fields.One2many('account.move.line', 'payment_id', readonly=True, copy=False, ondelete='restrict')
    payment_type = fields.Selection([('outbound', 'Entregar Anticipo'), ('inbound', 'Recibir Anticipo')], string='Payment Type',default="outbound", required=True, readonly=True)
    payment_method_id = fields.Many2one('account.payment.method',domain="[('payment_type', '=', 'inbound')]", string='Metodo de Pago', required=False, readonly=True, states={'draft': [('readonly', False)]})
    payment_method_code = fields.Char(related='payment_method_id.code',
        help="Technical field used to adapt the interface to the payment type selected.", readonly=False)

    amount = fields.Monetary(string='Monto Real Entregado', required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True,track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company.currency_id)
    company_currency_id = fields.Many2one('res.currency', string='Currency',readonly=True, default=lambda self: self.env.company.currency_id)
    amount_signed = fields.Float()
    
   
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True)
    #company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    hide_payment_method = fields.Boolean(compute='_compute_hide_payment_method',
                                         help="Technical field used to hide the payment method if the "
                                         "selected journal has only one available which is 'manual'")
    #Este campo es para el modulo IGTF
    move_itf_id = fields.Many2one('account.move', 'Asiento contable')

    #Estos Campos son para el modulo de anticipo
    tipo = fields.Char()
    anticipo = fields.Boolean(defaul=True)
    usado = fields.Boolean(defaul=False)
    anticipo_move_id = fields.Many2one('account.move', 'Id de Movimiento de anticipo donde pertenece dicho pago')
    saldo_disponible = fields.Monetary(string='Saldo Disponible')
    move_id = fields.Many2one('account.move', 'Id de Movimiento o factura donde pertenece dicho pago')
    tasa_personalizada = fields.Boolean(track_visibility='onchange')
    rate = fields.Float(default=1,digits=(12,4))
    monto_moneda_company=fields.Float(compute='_compute_monto_company',digits=(12,4))
    account_anti_employee_payable_id = fields.Many2one('account.account',company_dependent=True,default=lambda self: self.env.company.account_anti_employee_payable_id)
    nro_ref = fields.Char()
    asiento = fields.Many2one('account.move',track_visibility='onchange')
    #message_follower_ids=fields.Many2one('mail.followers')
    #activity_ids=fields.Many2one('mail.activity')
    #message_ids=fields.Many2one('mail.message')


    @api.onchange('state')
    def _compute_monto_company(self):
        valor=0
        tasas=1
        if self.tasa_personalizada==True:
            if self.currency_id.id!=self.company_currency_id.id:
                valor=self.amount*self.rate
            else:
                valor=self.amount
        else:
            lista_tasa = self.env['res.currency.rate'].search([('currency_id', '=', self.currency_id.id),('name','<=',self.payment_date)],order='id asc')
            for det in lista_tasa:
                tasas=(1/det.rate)
                if self.currency_id.id!=self.company_currency_id.id:
                    valor=self.amount*tasas
                else:
                    valor=self.amount
            self.rate=tasas
        self.monto_moneda_company=valor

    def _compute_name(self):
        for selff in self:
            selff.name=selff.employee_id.name

    @api.depends('payment_type', 'journal_id')
    def _compute_hide_payment_method(self):
        for payment in self:
            if not payment.journal_id or payment.journal_id.type not in ['bank', 'cash']:
                payment.hide_payment_method = True
                continue
            journal_payment_methods = payment.payment_type == 'inbound'\
                and payment.journal_id.inbound_payment_method_ids\
                or payment.journal_id.outbound_payment_method_ids
            payment.hide_payment_method = len(journal_payment_methods) == 1 and journal_payment_methods[0].code == 'manual'

    #@api.model
    def aprobar(self):
        self.amount_signedd()
        id_move=self.registro_movimiento_asiento()
        idv_move=id_move.id
        valor=self.registro_movimiento_linea(idv_move)
        moves= self.env['account.move'].search([('id','=',idv_move)])
        moves.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post()
        self.saldo_disponible=self.amount
        self.state="posted"
        self.anticipo=True
        self.asiento=moves.id
        if self.nro_recibo=="/" or not self.nro_recibo:
            self.nro_recibo=self.get_nro_anticipo()

    def amount_signedd(self):
        if self.env.company.currency_id.id!=self.currency_id.id:
            if self.tasa_personalizada==True:
                self.amount_signed=self.amount*self.rate
            else:
                lista_tasa = self.env['res.currency.rate'].search([('currency_id', '=', self.currency_id.id),('name','<=',self.payment_date)],order='id asc')
                for det in lista_tasa:
                    tas=det.rate
                self.amount_signed=round((self.amount/tas),2)
                self.rate=round((1/det.rate),2)
        else:
            self.amount_signed=self.amount
            #self.rate=1

    def registro_movimiento_asiento(self):
        #raise UserError(_('darrell = %s')%self.partner_id.vat_retention_rate)
        name = self.get_name() #"XXXXXXX"#consecutivo_asiento
        signed_amount_total=0
        amont_totall=self.amount #self.conv_div_extranjera(self.vat_retentioned)
        #amount_itf = round(float(total_monto) * float((igtf_porcentage / 100.00)),2)
        signed_amount_total=amont_totall
        id_journal=self.journal_id.id#loca14
        #raise UserError(_('papa = %s')%signed_amount_total)
        value = {
            'name': name,
            'date': self.payment_date,#listo
            #'amount_total':self.vat_retentioned,# LISTO
            'partner_id': self.company_id.partner_id.id, #LISTO
            'journal_id':id_journal,
            'ref': "Pago de anticipo viaticos al empleado %s" % (self.employee_id.name),
            #'amount_total':self.vat_retentioned,# LISTO
            'amount_total_signed':signed_amount_total,# LISTO
            'type': "entry",# estte campo es el que te deja cambiar y almacenar valores
            'company_id':self.env.company.id,#loca14
            'custom_rate':self.tasa_personalizada,
            'os_currency_rate':self.rate,
            'anticipo_gastos_employee_id':self.id,
            'asiento_gastos_anticipo':True,
        }
        #raise UserError(_('value= %s')%value)
        move_obj = self.env['account.move']
        move_id = move_obj.create(value)    
        if self.currency_id.id!=self.company_currency_id.id:
            actualiza=self.env['account.move'].search([('id', '=', move_id.id)]).write({
                'currency_id':self.currency_id.id,
                })
        #raise UserError(_('move_id= %s')%move_id) 
        return move_id

    def registro_movimiento_linea(self,id_movv):
        #raise UserError(_('ID MOVE = %s')%id_movv)
        name = "xxxx"#consecutivo_asiento
        valores = self.amount_signed #self.conv_div_extranjera(self.vat_retentioned) #VALIDAR CONDICION
        #raise UserError(_('valores = %s')%valores)
        cero = 0.0
       
        cuenta_ret_proveedor=self.account_anti_employee_payable_id.id# loca14 cuenta retencion proveedores
        cuenta_prove_pagar = self.journal_id.default_credit_account_id.id #loca14
              

        tipo_empresa="in_invoice"#self.move_id.type
        #raise UserError(_('papa = %s')%tipo_empresa)
        if tipo_empresa=="in_invoice" or tipo_empresa=="in_receipt":#aqui si la empresa es un proveedor
            cuenta_haber=cuenta_prove_pagar
            cuenta_debe=cuenta_ret_proveedor

        balances=cero-valores
        value = {
             'name': "Pago de anticipos",#name,
             'ref' : "Pago de Anticipo de viaticos a  %s" % (self.employee_id.name),
             'move_id': int(id_movv),
             'date': self.payment_date,
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
             'currency_id':self.currency_id.id if self.currency_id.id!=self.company_currency_id.id else "",
             'amount_currency': -1*self.amount if self.currency_id.id!=self.company_currency_id.id else "",

        }

        move_line_obj = self.env['account.move.line']
        move_line_id1 = move_line_obj.create(value)

        balances=valores-cero
        value['name'] = "Entrega de Anticipo"
        value['account_id'] = cuenta_debe
        value['credit'] = 0.0 # aqui va cero
        value['debit'] = valores
        value['balance'] = valores
        value['price_unit'] = balances
        value['price_subtotal'] = balances
        value['price_total'] = balances
        value['currency_id'] = self.currency_id.id if self.currency_id.id!=self.company_currency_id.id else ""
        value['amount_currency'] = self.amount if self.currency_id.id!=self.company_currency_id.id else ""

        move_line_id2 = move_line_obj.create(value)

        """if self.currency_id.id!=self.company_currency_id.id:
            self.env['account.move.line'].search([('id','=',move_line_id1.id)]).write({
               
                'currency_id':self.currency_id.id,
                })
            self.env['account.move.line'].search([('id','=',move_line_id2.id)]).write({
                'currency_id':self.currency_id.id,
                })"""

    def get_name(self):
        '''metodo que crea el Nombre del asiento contable si la secuencia no esta creada, crea una con el
        nombre: 'l10n_ve_cuenta_retencion_iva'''

        self.ensure_one()
        SEQUENCE_CODE = 'secuencia_anticipo_empleado'+str(self.company_id.id)
        company_id = self.env.company.id
        IrSequence = self.env['ir.sequence'].with_context(force_company=self.env.company.id)
        name = IrSequence.next_by_code(SEQUENCE_CODE)

        # si aún no existe una secuencia para esta empresa, cree una
        if not name:
            IrSequence.sudo().create({
                'prefix': 'Asiento Anticipo Viatico/',
                'name': 'Localización Venezolana asiento Anticipo Empleado %s' % self.env.company.name,
                'code': SEQUENCE_CODE,
                'implementation': 'no_gap',
                'padding': 8,
                'number_increment': 1,
                'company_id': self.env.company.id,#loca14
            })
            name = IrSequence.next_by_code(SEQUENCE_CODE)
        return name

    def get_nro_anticipo(self):
        '''metodo que crea el Nombre del asiento contable si la secuencia no esta creada, crea una con el
        nombre: 'l10n_ve_cuenta_retencion_iva'''

        self.ensure_one()
        SEQUENCE_CODE = 'secuencia_codigo_recibo_anticipo'+str(self.company_id.id)
        company_id = self.env.company.id
        IrSequence = self.env['ir.sequence'].with_context(force_company=self.env.company.id)
        name = IrSequence.next_by_code(SEQUENCE_CODE)

        # si aún no existe una secuencia para esta empresa, cree una
        if not name:
            IrSequence.sudo().create({
                'prefix': 'Doc/',
                'name': 'Localización Venezolana Doc Anticipo Empleado %s' % self.env.company.name,
                'code': SEQUENCE_CODE,
                'implementation': 'no_gap',
                'padding': 8,
                'number_increment': 1,
                'company_id': self.env.company.id,#loca14
            })
            name = IrSequence.next_by_code(SEQUENCE_CODE)
        return name

    def cancel(self):
        self.state="draft"
        self.asiento.filtered(lambda move: move.state == 'posted').button_draft()
        self.asiento.with_context(force_delete=True).unlink()


    def unlink(self):
        for vat in self:
            if vat.state=='posted':
                raise UserError(_("El anticipo, No se puede eliminar en estado Validado"))
        return super(AccountGastoAnticipo,self).unlink()


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



    #destination_account_id = fields.Many2one('account.account', compute='_compute_destination_account_id', readonly=True)
    # For money transfer, money goes from journal_id to a transfer account, then from the transfer account to destination_journal_id
    #destination_journal_id = fields.Many2one('account.journal', string='Transfer To', domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]", readonly=True, states={'draft': [('readonly', False)]})

class ResCompany(models.Model):
    _inherit = 'res.company'

    account_anti_employee_payable_id = fields.Many2one('account.account',company_dependent=True)
    account_remb_employee_receibale_id = fields.Many2one('account.account',company_dependent=True)
    