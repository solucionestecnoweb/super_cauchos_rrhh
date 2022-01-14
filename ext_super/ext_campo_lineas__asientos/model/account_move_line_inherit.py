# -*- coding: utf-8 -*-


import logging
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        super().action_post()
        nro_factura=self.invoice_number
        for det_line_asiento in self.line_ids:
            if det_line_asiento.account_id.user_type_id.type in ('receivable','payable'):
                det_line_asiento.name=nro_factura
                det_line_asiento.nro_doc=nro_factura
                #raise UserError(_(' El valor :%s ya se uso en otro documento')%det_line_asiento.name)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    nro_doc=fields.Char(string="Nro Documento")
    nro_doc_aux=fields.Char(compute='_compute_nro_doc')

    def _compute_nro_doc(self):
        for rec in self:
            rec.nro_doc_aux=rec.nro_doc

    #@api.onchange('state')
    #@api.depent('state')
    #@api.constrains('move_id')
    """def _nro_doc(self):
        var=self.move_id.invoice_number
        self.nro_doc=self.move_id.invoice_number
        return var"""

    
    #nro_doc_aux=fields.Char(compute='_compute_nro_doc')

    #@api.depent('parent_state')
    """@api.onchange('parent_state')
    def _compute_nro_doc(self):
        for selff in self:
            if selff.move_id.invoice_number:
                if selff.account_id.user_type_id.type in ('receivable','payable'):
                    selff.nro_doc_aux=selff.move_id.invoice_number
                    selff.nro_doc=selff.move_id.invoice_number
                else:
                    selff.nro_doc_aux=selff.move_id.invoice_number
            else:
                selff.nro_doc_aux=selff.move_id.invoice_number"""