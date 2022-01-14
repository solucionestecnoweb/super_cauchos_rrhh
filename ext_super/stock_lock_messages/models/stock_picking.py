# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


# class StockPiking(models.Model):
#     _inherit = 'stock.picking'
#
#     def button_validate(self):
#         t = 0.0
#         cant = 0.0
#         quantity = self.env['stock.quant']
#         if self.picking_type_id.code in ['outgoing', 'internal']:
#             if not self.move_ids_without_package:
#                 return ''
#             for move in self.move_ids_without_package:
#                 domain = [
#                     ('location_id', '=', move.location_id.id),
#                     ('product_id', '=', move.product_id.id)
#                 ]
#                 quant = quantity.search(domain)
#                 t += move.quantity_done
#                 for q in quant:
#                     cant += (q.quantity - t)
#                     if cant < 0:
#                         raise UserError(_("No se puede validar, ya que el producto seleccionado posee una cantidad: %s "
#                                           "para la Ubicacion: %s/%s") %
#                                         (cant, move.location_id.location_id.name, move.location_id.name))
#         return super(StockPiking, self).button_validate()


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.onchange('move_line_ids')
    def onchange_qty_warning(self):
        t = 0.0
        cant = 0.0
        quantity = self.env['stock.quant']
        if self.picking_type_id.code in ['outgoing', 'internal']:
            if not self.move_line_ids:
                return ''
            for move in self.move_line_ids:
                if move.qty_done:
                    domain = [
                         ('location_id', '=', move.location_id.id),
                         ('product_id', '=', move.product_id.id)
                    ]
                    print(move.qty_done)

                    quant = quantity.search(domain)
                    if not quant:
                        raise UserError(_("El producto: %s  no posee una ubicacion") % (move.product_id.id))
                t += move.qty_done
                for q in quant:
                     cant += (q.quantity - t)
                     if cant < 0:
                         raise UserError(_("No se puede validar, ya que el producto seleccionado posee una cantidad: %s"
                                           "para la Ubicacion: %s/%s") % (cant, move.location_id.location_id.name, move.location_id.name))
                     if t == 0.0 and q.quantity == 0.0:
                         raise UserError(_("No se puede validar, ya que el producto seleccionado posee una cantidad: %s"
                                           "para la Ubicacion: %s/%s") %
                                         (q.quantity, move.location_id.location_id.name, move.location_id.name))



