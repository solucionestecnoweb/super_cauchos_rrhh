# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id', 'product_uom_qty')
    def onchange_qty_stock(self):
        quant = self.env['stock.quant']
        stock_move = self.env['stock.move']
        stock_location = self.env['stock.location']
        cant = 0.0
        if not self.product_id.id and not self.order_id.is_transit_merch and self.product_id.type != "service":
            return ''
        if self.product_uom_qty == 0.0:
            raise UserError(_("No puede Generar un Presupuesto con cantidad 0 "))
        locations = stock_location.search([('location_id', '=', self.order_id.warehouse_id.view_location_id.id)])
        for l in locations:
            domain = [
                ('product_id', '=', self.product_id.id),
                ('location_id', '=', l.id),
            ]
            q = quant.search(domain)
            if not q:
                raise UserError(_("No existe el producto: %s en la ubicacion: %s de la bodega: %s") %
                                (self.product_id.name, self.order_id.warehouse_id.view_location_id.name,
                                 self.order_id.warehouse_id.name
                ))
            else:
                for det in q:
                    disponible = det.quantity
                    cant += (disponible - q.reserved_quantity)
                if cant == 0.0 and self.product_uom_qty == 0.0:
                    raise UserError(_("El producto: %s con la cantidad: %s  en la ubicacion: %s no tiene stock ") % (
                        self.product_id.name, self.product_uom_qty, self.order_id.warehouse_id.view_location_id.name))
                if disponible < self.product_uom_qty:
                    raise UserError(_("La cantidad  solicitada para el producto: %s  es mayor a la disponible "
                                      "en la ubicacion: %s") % (self.product_id.name,
                                                                self.order_id.warehouse_id.view_location_id.name))

