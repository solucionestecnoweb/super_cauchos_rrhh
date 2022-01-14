# -*- coding: utf-8 -*-


import logging
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vat_aux = fields.Integer()
    vat_compute = fields.Char()

    @api.constrains('vat')
    def compute_actualiza(self):
    	if self.vat:
    		j=len(self.vat)
    		#raise UserError(_(' El valor :%s ')%j)
    		for i in range(0,j):
    			vat=self.vat[i:i+1]
    			#raise UserError(_(' El valor :%s ')%vat)
    			if vat.isalpha():
    				raise UserError(_('No se admiten letras en campo RIF, Utilice el campo Tipo de contribuyente para colocar V/G/E/J/P/C'))


                #raise UserError(_(' El valor :%s ya se uso en otro documento')%det_line_asiento.name)

