from datetime import datetime, timedelta, date
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

_logger = logging.getLogger(__name__)

class FlotaControlDisponibilidadLineas(models.TransientModel):
    _name = "fleet.wizard.available.lines"

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehículo')
    date_assign = fields.Datetime(string='Asignado')
    available = fields.Boolean(string='Disponibilidad')

class FlotaControlDisponibilidad(models.TransientModel):
    _name = "fleet.wizard.available"

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())

    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=60)
    company_id = fields.Many2many('res.company', string='Company',default=lambda self: self.env.context['allowed_company_ids'])

    lines_ids = fields.Many2many('fleet.wizard.available.lines',string='Lineas')

    def print_ordenes(self):
        self.env['fleet.wizard.available.lines'].search([]).unlink()

        self._get_lineas(self.date_from, self.date_to)

        return {'type': 'ir.actions.report','report_name': 'reports_fleet.flota_control_disponibilidad','report_type':"qweb-pdf"}


    #VEHICULOS
    def vehiculos(self):
        busqueda = self.env['fleet.vehicle'].search([])
        return busqueda

    #FECHAS
    def nueva_fecha(self, dia, mes, agno):
        bisiesto = self.es_bisiesto(agno)

        if mes in (4, 6, 9, 11):
            if dia > 30:
                temp = dia - 30
                dia = temp
                mes += 1
        elif mes == 2:
            if bisiesto:
                if dia > 29:
                    temp = dia - 29
                    dia = temp
                    mes += 1
            else:
                if dia > 28:
                    temp = dia - 28
                    dia = temp
                    mes += 1
        elif dia > 31:
            temp = dia - 31
            dia = temp
            mes += 1
        
        if mes > 12:
            mes = 1
            agno += 1
            
        fecha = str(dia)+'/'+str(mes)+'/'+str(agno)
        fecha = datetime.strptime(fecha, '%d/%m/%Y')
        return fecha

    def es_bisiesto(self, anio: int) -> bool:
        return anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)

    #LINEAS
    def _get_lineas(self, inicio, fin):
        t = self.env['fleet.wizard.available.lines']
        
        for item in self.vehiculos():
            assignments = self.env['fleet.vehicle.log.assignment.control'].search([
                ('date_ini', '>=', inicio),
                ('date_end', '<=', fin),
                ('vehicle_id', '=', item.id),
                ('status', 'in', ('confirmed','done'))
            ])
            xdate = inicio
            if len(assignments) > 0:
                while xdate <= fin:
                    temp = True
                    for line in assignments:
                        if xdate >= line.date_ini and xdate <= line.date_end:
                            values= {
                                'vehicle_id': line.vehicle_id.id,
                                'date_assign': xdate,
                                'available': False,
                            }
                            temp = False
                        elif temp:
                            values={
                                'vehicle_id': line.vehicle_id.id,
                                'date_assign': xdate,
                                'available': True,
                            }
                    t.create(values)
                    xdate = xdate + timedelta(days=1)
            else:
                while xdate <= fin:
                    values={
                        'vehicle_id': item.id,
                        'date_assign': xdate,
                        'available': True,
                    }
                    t.create(values)
                    xdate = xdate + timedelta(days=1)

        self.lines_ids = self.env['fleet.wizard.available.lines'].search([])

    def generate_xls_report(self):

        self.env['fleet.wizard.available.lines'].search([]).unlink()

        self._get_lineas(self.date_from, self.date_to)
        dates_data = (self.date_to - self.date_from) + timedelta(days=1)

        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet('Disponibilidad de Vehículos en Viajes')
        fp = BytesIO()

        header_content_style = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170; align: horiz center;")
        sub_header_style = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170")
        sub_header_style_c = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz center; align: vertical center;")
        sub_header_style_r = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz right")
        sub_header_content_style = xlwt.easyxf("font: name Helvetica size 10 px, height 170;")
        line_content_style = xlwt.easyxf("font: name Helvetica, height 170;")

        row = 0
        col = 0
        ws1.row(row).height = 500
        ws1.write_merge(row,row, 2, (dates_data.days + 1), "Estadística de Disponibilidad de Vehículos en Viajes", header_content_style)
        xdate = self.date_now.strftime('%d/%m/%Y %I:%M:%S %p')
        xdate = datetime.strptime(xdate,'%d/%m/%Y %I:%M:%S %p') - timedelta(hours=4)
        ws1.write_merge(row,row, (dates_data.days + 2), (dates_data.days + 3), xdate.strftime('%d/%m/%Y %I:%M:%S %p'), header_content_style)
        row += 2

        #CABECERA DE LA TABLA
        ws1.write_merge(row,row, 2, (dates_data.days + 1), "Días desde " + self.date_from.strftime('%d/%m/%Y') + ' hasta ' + self.date_to.strftime('%d/%m/%Y') ,sub_header_style_c)
        row += 1

        col = 2
        days = 0
        while (dates_data.days - days) != 0:
            ws1.write(row,col, self.nueva_fecha(self.date_from.day + days, self.date_from.month, self.date_from.year).strftime('%a')[0].upper(),sub_header_style_c)
            days += 1
            col += 1

        col = 0
        row += 1

        ws1.write(row,col,"Vehículo",sub_header_style_c)
        ws1.col(col).width = int((len('Vehículo')+25)*256)
        ws1.write(row,col+1,"Placa",sub_header_style_c)
        ws1.col(col+1).width = int((len('Placa')+10)*256)
        
        col = 2
        days = 0
        while (dates_data.days - days) != 0:
            ws1.write(row,col, self.nueva_fecha(self.date_from.day + days, self.date_from.month, self.date_from.year).strftime('%d'),sub_header_style_c)
            ws1.col(col).width = 5 * 256
            days += 1
            col += 1

        ws1.write(row,col+0,"Total Días Disp.",sub_header_style_c)
        ws1.col(col+0).width = int((len('Total Días Disp.'))*256)
        ws1.write(row,col+1,"%",sub_header_style_c)
        ws1.col(col+1).width = int((len('%')+14)*256)

        col = 0

        xlwt.add_palette_colour("custom_colour", 0x21)
        wb1.set_colour_RGB(0x21, 0, 175, 0)
        center = xlwt.easyxf("align: horiz center; align: vertical center; borders: left thin, right thin, top thin, bottom thin;")
        right = xlwt.easyxf("align: horiz right; align: vertical center; borders: left thin, right thin, top thin, bottom thin;")
        disp = xlwt.easyxf("align: horiz center; align: vertical center; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour custom_colour; font: bold 1;")
        no_disp = xlwt.easyxf("align: horiz center; align: vertical center; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour red; font: bold 1;")

        #Totales
        total_mes = 0
        #Fin Totales

        for item in self.vehiculos():
            disponibilidad = 0
            col = 0
            row += 1
            # Vehicles
            ws1.write(row,col+0, item.display_name,center)
            # License Plate
            ws1.write(row,col+1, item.license_plate,center)

            col = 2
            for line in self.lines_ids:
                # Disponibility
                if line.vehicle_id.id == item.id:
                    if line.available:
                        ws1.write(row,col, '1',disp)
                        col += 1
                        disponibilidad += 1
                    else:
                        ws1.write(row,col, '0',no_disp)
                        col += 1

            # Disponibility Days
            ws1.write(row,col, disponibilidad,center)
            # %
            ws1.write(row,col+1, str(round((disponibilidad * 100) / dates_data.days, 2)) + '%',center)

            total_mes += disponibilidad

        row += 1
        ws1.write(row,col, total_mes,center)
        ws1.write(row,col+1, str(round((total_mes * 100) / (dates_data.days * len(self.vehiculos())), 2)) + '%',center)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({
            'state': 'get',
            'report': out,
            'name': 'Disponibilidad de Vehículos en Viajes '+ fecha +'.xls'
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.wizard.available',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }