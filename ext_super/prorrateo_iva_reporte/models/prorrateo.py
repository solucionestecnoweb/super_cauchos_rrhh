from operator import index
from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import base64
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.tools.float_utils import float_round

class ProrrateoIva(models.Model):
    _name = "prorrateo.iva"

    name = fields.Char(string='Código', default='Borrador')
    desde = fields.Date(string='Desde')
    hasta = fields.Date(string='Hasta')
    deducible = fields.Float(string='% Deducible', compute='_compute_deducible')
    no_deducible = fields.Float(string='% No Deducible', compute='_compute_no_deducible')
    state = fields.Selection(string='Estado', selection=[('draft', 'Borrador'), ('posted', 'Publicado')], default='draft')
    company_id = fields.Many2one('res.company','Compañía',default=lambda self: self.env.company.id)
    
    prorrateo_ids = fields.Many2many(comodel_name='data.prorrateo.iva', string='Datos Prorrateo')
    purchase_invoice_ids = fields.Many2many(comodel_name='account.move', string='Facturas de Compras')
    # sale_invoice_ids = fields.Many2many(comodel_name='account.move', string='Facturas de Ventas')
    move_ids = fields.Many2many(comodel_name='account.move.line', string='Asientos Contables')
    
    ### Nombre Código ###

    @api.constrains('state')
    def constraint_name(self):
        if self.name == 'Borrador':
            self.name = self.env['ir.sequence'].next_by_code('prorrateo.iva.seq')

    ### Estados ###

    def post(self):
        self.state = 'posted'
    
    def draft(self):
        self.state = 'draft'

    ### Buscar Datos ###

    def get_data(self):
        self.get_sales()
        self.get_purchases()
        self.get_prorrateo()

    def get_sales(self):
        xfind = self.env['account.move'].search([
            ('date', '>=', self.desde),
            ('date', '<=', self.hasta),
            ('state', '=', 'posted'),
            ('type', 'in', ('out_invoice', 'out_refund', 'out_receipt')),
            ('company_id', '=', self.company_id.id),
        ])
        self.sale_invoice_ids = xfind

    def get_purchases(self):
        xfind = self.env['account.move'].search([
            ('date', '>=', self.desde),
            ('date', '<=', self.hasta),
            ('state', '=', 'posted'),
            ('type', 'in', ('in_invoice', 'in_refund', 'in_receipt')),
            ('company_id', '=', self.company_id.id),
        ])
        self.purchases_invoice_ids = xfind

    def get_prorrateo(self):
        t = self.env['data.prorrateo.iva']
        t.search([('prorrateo_id', '=', self.id)]).unlink()
        xfind = self.env['account.move'].search([
            ('date', '>=', self.desde),
            ('date', '<=', self.hasta),
            ('state', '=', 'posted'),
            ('type', '!=', 'entry'),
            ('company_id', '=', self.company_id.id),
        ])
        for item in xfind:
            a = ''
            values = {
                'cliente': a,
                'n_factura': a,
                'cuenta': a,
                'credito_fiscal': a,
                'deducible': a,
                'no_deducible': a,
                'tipo': a,
                'prorrateo_id': self.id
            }
            t.create(values)

    ### Formatos ###

    def float_format(self,valor):
        if valor:
            result = '{:,.2f}'.format(valor)
            result = result.replace(',','*')
            result = result.replace('.',',')
            result = result.replace('*','.')
        else:
            result="0,00"
        return result

    ### Campos Computados ###

    def _compute_deducible(self):
        for item in self:
            deducible = 0
            iva = 0
            monto = 0
            for line in item.invoice_ids:
                for value in line.alicuota_line_ids:
                    iva += value.total_valor_iva_nd + value.total_base_nd
                monto += line.amount_total
            if iva:
                deducible = round((monto * iva) / 100, 2)
            else:
                deducible = 100
            item.deducible = deducible
    
    def _compute_no_deducible(self):
        for item in self:
            no_deducible = 0
            iva = 0
            monto = 0
            for line in item.invoice_ids:
                for value in line.alicuota_line_ids:
                    iva += value.total_valor_iva_nd + value.total_base_nd
                monto += line.amount_total
            if iva:
                no_deducible = round((100 * iva) / line.amount_total, 2)
            else:
                no_deducible = 0
            item.no_deducible = no_deducible

class DataProrrateoIVA(models.Model):
    _name = 'data.prorrateo.iva'

    cliente = fields.Char(string='Cliente')
    n_factura = fields.Char(string='Nro Factura')
    cuenta = fields.Char(string='Cuenta')
    credito_fiscal = fields.Float(string='Credito Fiscal')
    deducible = fields.Float(string='Deducible')
    no_deducible = fields.Float(string='No Deducible')
    tipo = fields.Selection(string='Tipo', selection=[('nd', 'nd'), ('pd', 'pd'), ('td', 'td')])
    prorrateo_id = fields.Many2one(comodel_name='prorrateo.iva', string='Prorrateo')
    