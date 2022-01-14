# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    zapatos = fields.Selection([('32','32'),('33','33'),('34','34'),('35','35'),('36','36'),('37','37'),('38','38'),('39','39'),('40','40'),('41','41'),('42','42'),('43','43'),('44','44'),('45','45'),('46','46')])
    camisas = fields.Selection([('XS', 'XS'),('S', 'S'),('M', 'M'),('M-L', 'M-L'),('L', 'L'),('L-XL', 'L-XL'),('XL', 'XL'),('XL-XXL', 'XL-XXL'),('XXL', 'XXL')])
    pantalon = fields.Selection([('24','24'),('25','25'),('26','26'),('27','27'),('28','28'),('29','29'),('30','30'),('31','31'),('32','32'),('33','33'),('34','34'),('35','35'),('36','36'),('37','37'),('38','38'),('39','39'),('40','40'),('41','41'),('42','42'),('43','43'),('44','44'),('45','45'),('46','46')])
    chemise = fields.Selection([('XS', 'XS'),('S', 'S'),('M', 'M'),('M-L', 'M-L'),('L', 'L'),('L-XL', 'L-XL'),('XL', 'XL'),('XL-XXL', 'XL-XXL'),('XXL', 'XXL')])


    grado_instruccion = fields.Many2one('hr.grado.instruccion')
    profesion = fields.Many2one('hr.profesion')
    grupo_familiar_ids = fields.One2many('hr.grupo.familiar', 'employee_id', string='Grupo Familiar')
    cursos_ids = fields.One2many('hr.cursos', 'employee_id', string='Cursos')
    rif = fields.Char()
    tipo_contrinbuyente = fields.Selection([('v','V'),('e','E'),('j','J'),('g','G'),('p','P'),('c','C'),])
    direccion = fields.Text()

class HrNivelInstruccion(models.Model):

    _name = 'hr.grado.instruccion'

    name = fields.Char()
    activo = fields.Boolean(default=True)

class HrProfesion(models.Model):

    _name = 'hr.profesion'

    name = fields.Char()
    activo = fields.Boolean(default=True)

class HrCursos(models.Model):

    _name = 'hr.cursos'

    employee_id = fields.Many2one('hr.employee', string='Cursos')
    name = fields.Char()
    institucion = fields.Char()
    fecha = fields.Date()
    duracion = fields.Char()
    nro_telefono = fields.Char()
    contacto = fields.Char()


class HrGrupoFamiliar(models.Model):

    _name = 'hr.grupo.familiar'

    employee_id = fields.Many2one('hr.employee', string='Grupo Familiar')
    name = fields.Char()
    name2 = fields.Char()
    fecha_nac = fields.Date()
    edad = fields.Integer(compute='_compute_edad')
    sexo = fields.Selection([('F','Femenino'),('M','Masculino')])
    identificador = fields.Char(default="N/A")
    nro_telefono = fields.Char()
    parentesco = fields.Selection([('ma','Madre'),('pa','Padre'),('hi','Hijo(@)'),('ab','Abuelo@'),('ot','Otro')])
    date_actual = fields.Date(string='Date From', compute='_compute_fecha_hoy')

    @api.onchange('fecha_nac')
    def _compute_edad(self):
        tiempo=0
        for selff in self:
            if selff.employee_id.id:
                fecha_ing=selff.fecha_nac
                fecha_actual=selff.date_actual
                dias=selff.days_dife(fecha_actual,fecha_ing)
                tiempo=dias/365
            selff.edad=tiempo

    def days_dife(self,d1, d2):
       return abs((d2 - d1).days)

    @api.onchange('fecha_nac')
    def _compute_fecha_hoy(self):
        hoy=datetime.now().strftime('%Y-%m-%d')
        self.date_actual=hoy