from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
import openerp.addons.decimal_precision as dp
import logging

import io
from io import BytesIO

import xlsxwriter
import shutil
import base64
import csv
import xlwt
import xml.etree.ElementTree as ET

class AccountMove(models.Model):
    _inherit = 'account.move'


    """def get_nro_nota_entrega(self):
        '''metodo que crea el Nombre del asiento contable si la secuencia no esta creada, crea una con el
        nombre: 'l10n_ve_cuenta_retencion_iva'''

        self.ensure_one()
        SEQUENCE_CODE = 'l10n_ve_nro_control_nota_entrega'+str(self.company_id.id) # loca 14
        company_id = self.company_id.id # loca 14
        IrSequence = self.env['ir.sequence'].with_context(force_company=company_id) # loca 14
        name = IrSequence.next_by_code(SEQUENCE_CODE)

        # si aún no existe una secuencia para esta empresa, cree una
        if not name:
            IrSequence.sudo().create({
                'prefix': '00-',
                'name': 'Localización Venezolana Nro control Nota entrega %s' % 1,
                'code': SEQUENCE_CODE,
                'implementation': 'no_gap',
                'padding': 4,
                'number_increment': 1,
                'company_id': company_id, # loca 14
            })
            name = IrSequence.next_by_code(SEQUENCE_CODE)
        #self.refuld_number_pro=name
        return name"""

    

    def get_invoice_number_cli(self):
        
        name=''
        if self.act_nota_entre==False:
           name=self.name
        return name

    
    def get_refuld_number_cli(self):# nota de credito cliente
       
        name=''
        if self.act_nota_entre==False:
             name=self.name
        return name

    
    def get_refuld_number_pro(self): #nota de debito Cliente
        
        name=''
        if self.act_nota_entre==False:
             name=self.name
        return name


    

    def get_invoice_ctrl_number_unico(self):
        '''metodo que crea el Nombre del asiento contable si la secuencia no esta creada, crea una con el
        nombre: 'l10n_ve_cuenta_retencion_iva'''
        name=''
        if self.act_nota_entre==False:
            #raise UserError(_('Ever %s')%self.company_id.confg_nro_control)
            if self.company_id.confg_nro_control=='d':
                if not self.journal_id.ctrl_sequence_id:
                    raise UserError(_('Este diario no tiene configurado el Nro de control. vaya al diario y en el campo *Proximo Nro control* agregue uno'))
                else:
                    if not self.journal_id.ctrl_sequence_id.code and self.journal_id.type=='sale':
                        raise UserError(_('La secuencia del Nro control llamado * %s * de este diario, no tiene configurada el Código se secuencias')%self.journal_id.ctrl_sequence_id.name)
                    else:
                        SEQUENCE_CODE=self.journal_id.ctrl_sequence_id.code
                        company_id = self.company_id.id
                        IrSequence = self.env['ir.sequence'].with_context(force_company=company_id)
                        name = IrSequence.next_by_code(SEQUENCE_CODE)

            #--------------------------------#
            if self.company_id.confg_nro_control=='c':
                self.ensure_one()
                SEQUENCE_CODE = 'l10n_ve_nro_control_unico_formato_libre'+str(self.company_id.id) #loca 14
                company_id = self.company_id.id #loca 14
                IrSequence = self.env['ir.sequence'].with_context(force_company=company_id) #loca 14
                #raise UserError(_('IrSequence: %s')%IrSequence)
                name = IrSequence.next_by_code(SEQUENCE_CODE)

                # si aún no existe una secuencia para esta empresa, cree una
                if not name:
                    IrSequence.sudo().create({
                        'prefix': '00-',
                        'name': 'Localización Venezolana nro control Unico Factura Forma Libre %s' % 1,
                        'code': SEQUENCE_CODE,
                        'implementation': 'no_gap',
                        'padding': 4,
                        'number_increment': 1,
                        'company_id': company_id, #loca 14
                    })
                    name = IrSequence.next_by_code(SEQUENCE_CODE)
        return name
