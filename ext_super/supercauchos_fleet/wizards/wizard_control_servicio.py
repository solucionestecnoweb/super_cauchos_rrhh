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

_logger = logging.getLogger(__name__)

class FlotaControlServicioLineas(models.TransientModel):
    _name = "fleet.wizard.services.lines"

    type_vehicle = fields.Selection(string='Tipo de Transporte', selection=[('propio', 'propio'), ('externo', 'Externo')], default="propio")
    driver_id = fields.Many2one('res.partner', string='Conductor')
    travel_qty = fields.Integer(string='Cantidad de Viajes')
    filler = fields.Float(string='Filler')
    km_traveled = fields.Float(string='KM Recorrido')
    days_street = fields.Integer(string='Días en la calle')

class FlotaControlServicio(models.TransientModel):
    _name = "fleet.wizard.services"

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_now = fields.Datetime(string='Date Now', default=lambda *a:datetime.now())

    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=50)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.user.company_id.id)

    lines_ids = fields.Many2many('fleet.wizard.services.lines',string='Lineas')

    def print_ordenes(self):
        self.env['fleet.wizard.services.lines'].search([]).unlink()
        self._get_lineas()
        return {'type': 'ir.actions.report','report_name': 'supercauchos_fleet.flota_control_servicio','report_type':"qweb-pdf"}


    #VEHICULOS
    def vehiculos_p(self):
        values = []
        temp_id = 0
        busqueda = self.env['fleet.wizard.services.lines'].search([
            ('type_vehicle', '=', 'propio')
        ])
        for item in busqueda.sorted(key=lambda driver: driver.driver_id.id):
            busqueda2 = self.env['fleet.wizard.services.lines'].search([
                ('type_vehicle', '=', 'propio'),
                ('driver_id', '=', item.driver_id.id),
            ])
            vehicle_type = ''
            driver = ''
            travels = 0
            fillers = 0
            traveled_km = 0.0
            days = 0
            temp_value = []
            for line in busqueda2:
                driver = line.driver_id.name
                travels = travels + line.travel_qty
                fillers = fillers + line.filler
                traveled_km = traveled_km + line.km_traveled
                days = days + line.days_street
            if temp_id != item.driver_id.id:
                temp_value = [driver, travels, fillers, traveled_km, days]
                values.append(temp_value)
                temp_id = item.driver_id.id
        return values

    def vehiculos_e(self):
        values = []
        temp_id = 0
        busqueda = self.env['fleet.wizard.services.lines'].search([
            ('type_vehicle', '=', 'externo')
        ])
        for item in busqueda.sorted(key=lambda driver: driver.driver_id.id):
            busqueda2 = self.env['fleet.wizard.services.lines'].search([
                ('type_vehicle', '=', 'externo'),
                ('driver_id', '=', item.driver_id.id),
            ])
            vehicle_type = ''
            driver = ''
            travels = 0
            fillers = 0
            traveled_km = 0.0
            days = 0
            temp_value = []
            for line in busqueda2:
                driver = line.driver_id.name
                travels = travels + line.travel_qty
                fillers = fillers + line.filler
                traveled_km = traveled_km + line.km_traveled
                days = days + line.days_street
            if temp_id != item.driver_id.id:
                temp_value = [driver, travels, fillers, traveled_km, days]
                values.append(temp_value)
                temp_id = item.driver_id.id
        return values

    #LINEAS
    def _get_lineas(self):
        t = self.env['fleet.wizard.services.lines']
        ###Busqueda de asignaciones
        busqueda = self.env['fleet.vehicle.log.assignment.control'].search([
            ('status', 'in', ('confirmed','done')),
            ('date_ini', '>=', self.date_from),
            ('date_end', '<=', self.date_to)
        ])
        ###Iteración de todas las asignaciones
        for item in busqueda.sorted(key=lambda driver: driver.driver_id.id):
            dias = item.date_end - item.date_ini
            street_days = dias.days + 1
            filler = 0
            odometer = 0
            for line in item.stock_picking_ids:
                l = line.move_ids_without_package
                if len(l) > 1:
                    for lines in l:
                        filler = filler + (lines.product_id.filler * lines.product_uom_qty)
                else:
                    filler = filler + (l.product_id.filler * l.product_uom_qty)
            find_odometer = item.env['fleet.vehicle.odometer'].search([
                ('date', '>=', item.date_ini),
                ('date', '<=', item.date_end),
                ('vehicle_id', '=', item.vehicle_id.id),
                ('driver_id', '=', item.driver_id.id)
            ])
            for lines in find_odometer:
                odometer = odometer + lines.value
            values = {
            'type_vehicle': item.vehicle_id.type_vehicle,
            'driver_id': item.driver_id.id,
            'travel_qty': 1,
            'filler': filler,
            'km_traveled': odometer,
            'days_street': street_days,
            }
            t.create(values)
        self.lines_ids = t.search([])

    def generate_xls_report(self):

        self.env['fleet.wizard.services.lines'].search([]).unlink()
        self._get_lineas()

        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet('Control de Servicios de Conductores')
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
        ws1.write_merge(row,row, 2, 3, "Control de Servicios de Conductores", header_content_style)
        xdate = self.date_now.strftime('%d/%m/%Y %I:%M:%S %p')
        xdate = datetime.strptime(xdate,'%d/%m/%Y %I:%M:%S %p') - timedelta(hours=4)
        ws1.write_merge(row,row, 4, 5, xdate.strftime('%d/%m/%Y %I:%M:%S %p'), header_content_style)
        row += 2

        #CABECERA DE LA TABLA 
        ws1.write(row,col+0,"Tipo Transporte",sub_header_style_c)
        ws1.col(col+0).width = int((len('Tipo Transporte')+15)*256)
        ws1.write(row,col+1,"Conductor",sub_header_style_c)
        ws1.col(col+1).width = int((len('Conductor')+15)*256)
        ws1.write(row,col+2,"Cant Viaje",sub_header_style_c)
        ws1.col(col+2).width = int((len('Cant Viaje')+8)*256)
        ws1.write(row,col+3,"Filler",sub_header_style_c)
        ws1.col(col+3).width = int((len('Filler')+12)*256)
        ws1.write(row,col+4,"KM Recorrido",sub_header_style_c)
        ws1.col(col+4).width = int((len('KM Recorrido')+35)*256)
        ws1.write(row,col+5,"Total Días Calle",sub_header_style_c)
        ws1.col(col+5).width = int(len('Total Días Calle')*256)

        center = xlwt.easyxf("align: horiz center; align: vertical center; borders: left thin, right thin, top thin, bottom thin;")
        right = xlwt.easyxf("align: horiz right; align: vertical center; borders: left thin, right thin, top thin, bottom thin;")

        #Totales
        viajes_p = 0
        filler_p = 0
        km_p = 0
        dias_p = 0
        ##############
        viajes_e = 0
        filler_e = 0
        km_e = 0
        dias_e = 0
        #Fin Totales

        temp = True
        rows_len = len(self.vehiculos_p())
        for item in self.vehiculos_p():
            row += 1
            if temp:
                ws1.write_merge(row,row + (rows_len - 1), 0, 0, 'PROPIO',sub_header_style_c)
                temp = False
            # Driver
            ws1.write(row,col+1, item[0],center)
            # Travel Qty
            ws1.write(row,col+2, item[1],center)
            # Filler
            ws1.write(row,col+3, round(item[2], 3),center)
            # KM Traveled
            ws1.write(row,col+4, item[3],center)
            # Total Street Days
            ws1.write(row,col+5,item[4],center)

            viajes_p += item[1]
            filler_p += item[2]
            km_p += item[3]
            dias_p += item[4]

        row += 1
        ws1.write_merge(row,row, 0, 1, 'Total Propio',sub_header_style_c)
        ws1.write(row,col+2, viajes_p, center)
        ws1.write(row,col+3, round(filler_p, 3), center)
        ws1.write(row,col+4, km_p, center)
        ws1.write(row,col+5, dias_p, center)

        temp = True
        rows_len = len(self.vehiculos_e())
        for line in self.vehiculos_e():
            row += 1
            if temp:
                ws1.write_merge(row,row + (rows_len - 1), 0, 0, 'EXTERNO',sub_header_style_c)
                temp = False
            # Driver
            ws1.write(row,col+1, line[0],center)
            # Travel Qty
            ws1.write(row,col+2, line[1],center)
            # Filler
            ws1.write(row,col+3, round(line[2], 3),center)
            # KM Traveled
            ws1.write(row,col+4, line[3],center)
            # Total Street Days
            ws1.write(row,col+5,line[4],center)

            viajes_e += line[1]
            filler_e += line[2]
            km_e += line[3]
            dias_e += line[4]

        row += 1
        ws1.write_merge(row,row, 0, 1, 'Total Externo',sub_header_style_c)
        ws1.write(row,col+2, viajes_e, center)
        ws1.write(row,col+3, round(filler_e, 3), center)
        ws1.write(row,col+4, km_e, center)
        ws1.write(row,col+5, dias_e, center)

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name':'Control de Servicios de Conductor '+ fecha+'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.wizard.services',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
        