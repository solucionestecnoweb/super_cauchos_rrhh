# -*- coding: utf-8 -*-


import logging
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError




class MailingContact(models.Model):
    _inherit = 'mailing.contact'

    fecha_nacimiento = fields.Date()
    email_aux = fields.Char(compute='_compute_email_viejo')

    #@api.model
    #@api.depends('email')
    @api.onchange('email')
    def _compute_email_viejo(self):
        self.email_aux="darrell"
        if self.email:
            if not self.id:
                busca_email = self.env['mailing.contact'].search([('email','=',self.email)])
                if busca_email:
                    for det in busca_email:
                        nombre=det.name
                    raise UserError(_('Este correo ya esta siendo utilizado por otro Contacto: %s')%nombre)
        self.email_aux=self.email

    @api.model
    def create(self, vals):
        valor=vals['email']
        if valor==False:
            raise UserError(_('Tiene que ingresar un correo no registrado en el sistema'))
        else:
            return super().create(vals)