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
    promocion_ids = fields.One2many('hr.promocion', 'employee_id', string='Promociones')
    rif = fields.Char()
    tipo_contribuyente = fields.Selection([('V','V'),('E','E'),('J','J'),('G','G'),('P','P'),('C','C'),])

    direccion = fields.Text()
    ciudad = fields.Char()
    country_id = fields.Many2one('res.country')
    state_id = fields.Many2one('res.country.state')
    cod_post = fields.Char()
    municipality_id = fields.Many2one('res.country.state.municipality')
    parish_id = fields.Many2one('res.country.state.municipality.parish')

    direccion_trabajo = fields.Char(compute='_compute_direccion')

    constancia_trab = fields.Char(default="Jefe HHRR")
    gerente_rrhh_id = fields.Many2one('hr.employee')
    fecha_hoy = fields.Date(compute='_compute_hoy')

    def _compute_hoy(self):
        for selff in self:
            hoy=datetime.now().strftime('%Y-%m-%d')
            selff.fecha_hoy=hoy

    @api.onchange('company_id')
    def _compute_direccion(self):
        self.direccion_trabajo=self.company_id.street+" "+self.company_id.street2+". "+self.company_id.city+"/"+self.company_id.state_id.name

    def formato_fecha(self,date):
        resultado="0000/00/00"
        if date:
            fecha = str(date)
            fecha_aux=fecha
            ano=fecha_aux[0:4]
            mes=fecha[5:7]
            dia=fecha[8:10]  
            resultado=dia+"/"+mes+"/"+ano
        return resultado

    def float_format(self,valor):
        #valor=self.base_tax
        if valor:
            result = '{:,.2f}'.format(valor)
            result = result.replace(',','*')
            result = result.replace('.',',')
            result = result.replace('*','.')
        else:
            result="0,00"
        return result

    def dia(self,date):
        fecha = str(date)
        fecha_aux=fecha
        dia=fecha[8:10]  
        resultado=dia
        return int(resultado)

    def mes(self,date):
        fecha = str(date)
        fecha_aux=fecha
        mes=fecha[5:7]
        if mes=='01':
            month="Enero"
        if mes=='02':
            month="Febrero"
        if mes=='03':
            month="Marzo"
        if mes=='04':
            month="Abril"
        if mes=='05':
            month="Mayo"
        if mes=='06':
            month="Junio"
        if mes=='07':
            month="Julio"
        if mes=='08':
            month="Agosto"
        if mes=='09':
            month="Septiembre"
        if mes=='10':
            month="Octubre"
        if mes=='11':
            month="Noviembre"
        if mes=='12':
            month="Diciembre"
        resultado=month
        return resultado

    def ano(self,date):
        fecha = str(date)
        fecha_aux=fecha
        ano=fecha_aux[0:4]  
        resultado=ano
        return int(resultado)

    def get_literal_amount(self,amount):
        indicador = [("",""),("MIL","MIL"),("MILLON","MILLONES"),("MIL","MIL"),("BILLON","BILLONES")]
        entero = int(amount)
        decimal = int(round((amount - entero)*100))
        contador = 0
        numero_letras = ""
        while entero >0:
            a = entero % 1000
            if contador == 0:
                en_letras = self.convierte_cifra(a,1).strip()
            else:
                en_letras = self.convierte_cifra(a,0).strip()
            if a==0:
                numero_letras = en_letras+" "+numero_letras
            elif a==1:
                if contador in (1,3):
                    numero_letras = indicador[contador][0]+" "+numero_letras
                else:
                    numero_letras = en_letras+" "+indicador[contador][0]+" "+numero_letras
            else:
                numero_letras = en_letras+" "+indicador[contador][1]+" "+numero_letras
            numero_letras = numero_letras.strip()
            contador = contador + 1
            entero = int(entero / 1000)
        numero_letras = numero_letras+" con " + str(decimal) +"/100"
        print('numero: ',amount)
        print(numero_letras)
        return numero_letras
        
    def convierte_cifra(self, numero, sw):
        lista_centana = ["",("CIEN","CIENTO"),"DOSCIENTOS","TRESCIENTOS","CUATROCIENTOS","QUINIENTOS","SEISCIENTOS","SETECIENTOS","OCHOCIENTOS","NOVECIENTOS"]
        lista_decena =  ["",("DIEZ","ONCE","DOCE","TRECE","CATORCE","QUINCE","DIECISEIS","DIECISIETE","DIECIOCHO","DIECINUEVE"),
                        ("VEINTE","VEINTI"),("TREINTA","TREINTA Y "),("CUARENTA" , "CUARENTA Y "),
                        ("CINCUENTA" , "CINCUENTA Y "),("SESENTA" , "SESENTA Y "),
                        ("SETENTA" , "SETENTA Y "),("OCHENTA" , "OCHENTA Y "),
                        ("NOVENTA" , "NOVENTA Y ")
                        ]
        lista_unidad = ["",("UN" , "UNO"),"DOS","TRES","CUATRO","CINCO","SEIS","SIETE","OCHO","NUEVE"]
        centena = int (numero / 100)
        decena = int((numero -(centena * 100))/10)
        unidad = int(numero - (centena * 100 + decena * 10))
        
        texto_centena = ""
        texto_decena = ""
        texto_unidad = ""
        
        #Validad las centenas
        texto_centena = lista_centana[centena]
        if centena == 1:
            if (decena + unidad)!=0:
                texto_centena = texto_centena[1]
            else:
                texto_centena = texto_centena[0]
        
        #Valida las decenas
        texto_decena = lista_decena[decena]
        if decena == 1:
            texto_decena = texto_decena[unidad]
        elif decena > 1:
            if unidad != 0:
                texto_decena = texto_decena[1]
            else:
                texto_decena = texto_decena[0]
        
        #Validar las unidades
        if decena != 1:
            texto_unidad = lista_unidad[unidad]
            if unidad == 1:
                texto_unidad = texto_unidad[sw]
        
        return "%s %s %s" %(texto_centena,texto_decena,texto_unidad)

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

class HrPromosiones(models.Model):

    _name = 'hr.promocion'

    employee_id = fields.Many2one('hr.employee', string='Cursos')
    job_id = fields.Many2one('hr.job')
    motivo = fields.Char()
    fecha = fields.Date()
    autorizor_id = fields.Many2one('hr.employee')


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