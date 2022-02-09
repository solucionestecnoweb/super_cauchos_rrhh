from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError, except_orm, Warning


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        for picking in self.pick_ids:
            if picking.is_approval:
                for aproval in picking.approvals_ids:
                    if aproval.request_status not in ['approved']:
                        raise ValidationError("Disculpe!!! No tiene ninguna aprobaciones aceptada")
        return super(StockImmediateTransfer, self).process()