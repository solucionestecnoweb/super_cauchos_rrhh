# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError, except_orm, Warning


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    invoice_ids = fields.Many2many("account.move", compute="_compute_picking_invoice_ids",
                                copy=False, string="Facturas", readonly=True)
    is_invoice = fields.Boolean(string="Tiene Factura", compute="_compute_picking_invoice_ids", store=True,
                                default=False)
    street = fields.Char(related="partner_id.street", string="Direccion")
    street2 = fields.Char(related="partner_id.street2", string="Direccion #2")
    city = fields.Char(related="partner_id.city", string="Ciudad")
    state_id = fields.Many2one(related="partner_id.state_id", string="Estado")
    zip = fields.Char(related="partner_id.zip", string="Codigo Postal")
    country_id = fields.Many2one(related="partner_id.country_id", string="Pais")
    date_delivered = fields.Date(string='Fecha de entrega')

    @api.depends('sale_id.invoice_ids')
    def _compute_picking_invoice_ids(self):
        for picking in self:
            invoices = picking.sale_id.invoice_ids
            picking.invoice_ids = self.env['account.move']
            if invoices:
                for invoice in invoices:
                    if invoice.state == 'posted':
                        picking.write({
                            'invoice_ids': [(4, invoice.id)]})
                        picking.is_invoice = True
            else:
                picking.is_invoice = False
                
                
    @api.constrains('date_delivered')
    def generate_date_venc(self):
        strf = datetime.strptime
        for picking in self:
            for fact in picking.invoice_ids:
                fact.date_delivered = self.date_delivered
                fecha_factura = strf(str(fact.invoice_date), "%Y-%m-%d")
                fecha_plazos = strf(str(fact.invoice_date_due), "%Y-%m-%d")
                dias_credito = fecha_plazos - fecha_factura
                dias_diferencia = dias_credito.days
                fecha_vecimiento_real = strf(
                    str(picking.date_delivered), "%Y-%m-%d") + timedelta(
                    days=dias_diferencia)
                fact.date_venc = fecha_vecimiento_real
