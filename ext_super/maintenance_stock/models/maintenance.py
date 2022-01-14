# -*- coding: utf-8

from odoo import models, fields, api, _
from collections import defaultdict
from datetime import datetime, timedelta
from odoo.tools.misc import formatLang, get_lang
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import AccessError, UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    @api.model
    def _default_warehouse_id(self):
        company = self.env.company.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids

    license_plate = fields.Char(related='vehicle_id.license_plate', store=True, string="Placa")
    odometer_unit = fields.Char(string='Odometer Unit')
    odometer = fields.Float(string='Kilometraje')
    work_order = fields.Boolean(string='Orden de Trabajo')
    technician_user_id = fields.Many2one(string='Tecnico')
    equipment_id = fields.Many2one(string='Equipo')

    type_equipment = fields.Selection([('flota de vehículos', 'Flota de Vehículos') ,('maquinas y herramientas', 'Maquinas y Herramientas')],
                     string='Tipo de equipamiento', default='flota de vehículos')
    number_petition = fields.Char(string='N° petición')
    preventive_maintenance = fields.Float(string='Ultimo mantenimento preventivo')
    report_succes = fields.Text(string='Reporte Trabajo Realizado')
    description_fault = fields.Text(string='Descripcion de fallas')
    note = fields.Text(string='Reporte Trabajo Realizado')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')
    commitment_date = fields.Datetime('Delivery Date', copy=False, readonly=True,
                                      help="This is the delivery date promised to the customer. "
                                           "If set, the delivery maintenance will be scheduled based on "
                                           "this date rather than product lead times.")

    driver_id = fields.Many2one('res.partner', related='vehicle_id.driver_id', store=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehiculo')
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group', copy=False)
    maintenance_line_ids = fields.One2many('maintenance.line.request', 'maintenance_id')
    picking_ids = fields.One2many('stock.picking', 'maintenance_id', string='Transfers')
    mt_odometer_unit = fields.Selection([
        ('kilometers', 'km'),
        ], 'Odometer Unit', default='kilometers', help='Unit of the odometer ')
    warehouse_id = fields.Many2one('stock.warehouse', string='Bodega',
                                   required=True, default=_default_warehouse_id, check_company=True)
    picking_policy = fields.Selection([('direct', 'As soon as possible'), ('one', 'When all products are ready')],
                                      string='Shipping Policy', required=True, default='direct',
                                      help="If you deliver all products at once, the delivery "
                                           "order will be scheduled based on the greatest "
                                           "product lead time. Otherwise, it will be based on the shortest.")

    @api.onchange('vehicle_id')
    def _onchange_fleet_odometer(self):
        if self.vehicle_id:
            FleetVehicalOdometer = self.env['fleet.vehicle.odometer']
            vehicle_odometer = FleetVehicalOdometer.search([('vehicle_id', '=', self.vehicle_id.id)], limit=1, order='value desc')
            if vehicle_odometer:
                self.odometer = vehicle_odometer.value
                self.odometer_unit = vehicle_odometer.unit

    @api.model
    def create(self, vals):
        new_id = super(MaintenanceRequest, self).create(vals)
        seq = self.env['ir.sequence'].get('maintenance.petition')
        new_id.number_petition = seq
        if 'warehouse_id' not in vals and 'company_id' in vals and vals.get('company_id') != self.env.company.id:
            vals['warehouse_id'] = self.env['stock.warehouse'].search([('company_id', '=', vals.get('company_id'))], limit=1).id
        return new_id

    @api.depends('picking_ids')
    def _compute_picking_ids(self):
        for maintenance in self:
            maintenance.delivery_count = len(maintenance.picking_ids)

    def action_view_delivery(self):
        '''
            This function returns an action that display existing delivery orders
            of given sales order ids. It can either be a in a list or in a form
            view, if there is only one delivery order to show.
        '''
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        # Prepare the context.
        picking_id = pickings.filtered(lambda l: l.picking_type_id.code == 'outgoing')
        if picking_id:
            picking_id = picking_id[0]
        else:
            picking_id = pickings[0]
        action['context'] = dict(
            self._context, default_partner_id=self.driver_id.id or self.urser_id.partner_id.id,
            default_picking_type_id=picking_id.picking_type_id.id,
            default_origin=self.number_petition, default_group_id=picking_id.group_id.id
        )
        return action

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            warehouse_id = self.env['ir.default'].get_model_defaults('maintenance.request').get('warehouse_id')
            self.warehouse_id = warehouse_id or self.env['stock.warehouse'].search([
                ('company_id', '=', self.company_id.id)], limit=1)

    def _log_decrease_ordered_quantity(self, documents, cancel=False):

        def _render_note_exception_quantity_so(rendering_context):
            order_exceptions, visited_moves = rendering_context
            visited_moves = list(visited_moves)
            visited_moves = self.env[visited_moves[0]._name].concat(*visited_moves)
            maintenance_line_ids_line_ids = self.env['maintenance.line.request'].browse([maintenance_line.id for m in order_exceptions.values() for maintenance_line in m[0]])
            sale_order_ids = maintenance_line_ids_line_ids.mapped('order_id')
            impacted_pickings = visited_moves.filtered(lambda m: m.state not in ('done', 'cancel')).mapped('picking_id')
            values = {
                'sale_order_ids': sale_order_ids,
                'order_exceptions': order_exceptions.values(),
                'impacted_pickings': impacted_pickings,
                'cancel': cancel
            }
            return self.env.ref('sale_stock.exception_on_so').render(values=values)

        self.env['stock.picking']._log_activity(_render_note_exception_quantity_so, documents)


class MaintenanceLineRequest(models.Model):
    _name = "maintenance.line.request"
    _description = 'Lineas de manteniminetos'
    _order = "date desc, id"

    sequence = fields.Integer(string='Sequence')
    name = fields.Char(string='Description')
    date = fields.Date(related='maintenance_id.request_date', store=True, readonly=True, index=True, copy=False,
                       group_operator='min')
    product_qty = fields.Float(string='Cantidad',required=True, default=1.0)
    qty_delivered_method = fields.Selection([('stock_move_maintenance', 'Stock Moves maintenance')],
                                            compute='_compute_qty_delivered_method')
    maintenance_id = fields.Many2one('maintenance.request')
    company_id = fields.Many2one(related='maintenance_id.company_id', string='Company', store=True, readonly=True, index=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                                     domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    product_id = fields.Many2one('product.product', string='product')
    route_id = fields.Many2one('stock.location.route', string='Route', domain=[('maintenance_selectable', '=', True)],
                                ondelete='restrict', check_company=True)
    move_ids = fields.One2many('stock.move', 'maintenance_line_id', string='Stock Moves')
    warehouse_id = fields.Many2one('stock.warehouse', compute='_compute_qty_at_date')
    product_type = fields.Selection(related='product_id.type')
    scheduled_date = fields.Datetime(compute='_compute_qty_at_date')
    free_qty_today = fields.Float(compute='_compute_qty_at_date')
    virtual_available_at_date = fields.Float(compute='_compute_qty_at_date')
    qty_available_today = fields.Float(compute='_compute_qty_at_date')
    display_qty_widget = fields.Boolean(compute='_compute_qty_to_deliver')
    qty_to_deliver = fields.Float(compute='_compute_qty_to_deliver')
    state = fields.Selection([('process', 'Procesado'), ('cancel', 'Cancelado')], default='process')
    is_mto = fields.Boolean(compute='_compute_is_mto')
    customer_lead = fields.Float(
        'Lead Time', required=True, default=0.0,
        help="Number of days between the order confirmation and the shipping of the products to the customer")

    @api.model
    def _prepare_add_missing_fields(self, values):
        """ Deduce missing required fields from the onchange """
        res = {}
        onchange_fields = ['name', 'product_qty', 'product_uom_id']
        if values.get('warehouse_id') and values.get('product_id') and any(f not in values for f in onchange_fields):
            line = self.new(values)
            line.product_id_change()
            for field in onchange_fields:
                if field not in values:
                    res[field] = line._fields[field].convert_to_write(line[field], line)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(MaintenanceLineRequest, self).create(vals_list)
        lines.filtered(lambda line: line.state == 'process')._action_launch_stock_rule()
        return lines

    def write(self, values):
        if 'product_uom_qty' in values:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            self.filtered(
                lambda r: r.state == 'process' and float_compare(
                    r.product_uom_qty, values['product_uom_qty'], precision_digits=precision) != 0)._update_line_quantity(values)
        previous_product_uom_qty = {line.id: line.product_uom_qty for line in self}
        self._action_launch_stock_rule(previous_product_uom_qty)
        protected_fields = self._get_protected_fields()
        if 'cancel' in self.mapped('state') and any(f in values.keys() for f in protected_fields):
            protected_fields_modified = list(set(protected_fields) & set(values.keys()))
            fields = self.env['ir.model.fields'].search([
                ('name', 'in', protected_fields_modified), ('model', '=', self._name)
            ])
            raise UserError(
                _('It is forbidden to modify the following fields in the line maintenance blocked:\n%s')
                % '\n'.join(fields.mapped('field_description'))
            )

    @api.depends('product_id', 'product_qty',  'product_uom_id')
    def _compute_qty_to_deliver(self):
        """Compute the visibility of the inventory widget."""
        for line in self:
            line.qty_to_deliver = line.product_qty #- line.qty_delivered
            if line.product_type == 'product' and line.product_uom_id and line.qty_to_deliver > 0:
                line.display_qty_widget = True
            else:
                line.display_qty_widget = False

    @api.depends(
        'product_id',
        'customer_lead',
        'product_qty',
        'product_uom_id',
        'maintenance_id.warehouse_id',
        'maintenance_id.commitment_date'
    )
    def _compute_qty_at_date(self):
        """ Compute the quantity forecasted of product at delivery date. There are
        two cases:
         1. The quotation has a commitment_date, we take it as delivery date
         2. The quotation hasn't commitment_date, we compute the estimated delivery
            date based on lead time"""
        qty_processed_per_product = defaultdict(lambda: 0)
        grouped_lines = defaultdict(lambda: self.env['maintenance.line.request'])
        # We first loop over the SO lines to group them by warehouse and schedule
        # date in order to batch the read of the quantities computed field.
        for line in self:
            if not (line.product_id and line.display_qty_widget):
                continue
            line.warehouse_id = line.maintenance_id.warehouse_id

            if line.maintenance_id.commitment_date:
                date = line.maintenance_id.commitment_date
            else:
                date = line._expected_date()
            grouped_lines[(line.warehouse_id.id, date)] |= line

        treated = self.browse()
        for (warehouse, scheduled_date), lines in grouped_lines.items():
            product_qties = lines.mapped('product_id').with_context(to_date=scheduled_date,
                                                                    warehouse=warehouse).read([
                'qty_available',
                'free_qty',
                'virtual_available',
            ])
            qties_per_product = {
                product['id']: (product['qty_available'], product['free_qty'], product['virtual_available'])
                for product in product_qties
            }
            for line in lines:
                line.scheduled_date = scheduled_date
                qty_available_today, free_qty_today, virtual_available_at_date =\
                    qties_per_product[line.product_id.id]
                line.qty_available_today = qty_available_today - qty_processed_per_product[line.product_id.id]
                line.free_qty_today = free_qty_today - qty_processed_per_product[line.product_id.id]
                line.virtual_available_at_date = virtual_available_at_date - qty_processed_per_product[
                    line.product_id.id]
                if line.product_uom_id and line.product_id.uom_id and line.product_uom_id != line.product_id.uom_id:
                    line.qty_available_today = line.product_id.uom_id._compute_quantity(
                        line.qty_available_today, line.product_uom)
                    line.free_qty_today = line.product_id.uom_id._compute_quantity(
                        line.free_qty_today, line.product_uom)
                    line.virtual_available_at_date = line.product_id.uom_id._compute_quantity(
                        line.virtual_available_at_date, line.product_uom)
                qty_processed_per_product[line.product_id.id] += line.product_qty
            treated |= lines
        remaining = (self - treated)
        remaining.virtual_available_at_date = False
        remaining.scheduled_date = False
        remaining.free_qty_today = False
        remaining.qty_available_today = False
        remaining.warehouse_id = False

    @api.depends('product_id')
    def _compute_qty_delivered_method(self):
        """ Stock module compute delivered qty for product [('type', 'in', ['consu', 'product'])]
            For line maintenance coming from expense, no picking should be generate: we don't manage stock for
            thoses lines, even if the product is a storable.
        """
        for line in self:
            if not line.is_expense and line.product_id.type in ['consu', 'product']:
                line.qty_delivered_method = 'stock_move_maintenance'

    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_delivered(self):
        for line in self:  # TODO: maybe one day, this should be done in SQL for performance sake
            if line.qty_delivered_method == 'stock_move_maintenance':
                qty = 0.0
                outgoing_moves, incoming_moves = line._get_outgoing_incoming_moves()
                for move in outgoing_moves:
                    if move.state != 'done':
                        continue
                    qty += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
                for move in incoming_moves:
                    if move.state != 'done':
                        continue
                    qty -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
                line.qty_delivered = qty

    @api.depends('product_id', 'route_id', 'maintenance_id.warehouse_id', 'product_id.route_ids')
    def _compute_is_mto(self):
        self.is_mto = False
        for line in self:
            if not line.display_qty_widget:
                continue
            product = line.product_id
            product_routes = line.route_id or (product.route_ids + product.categ_id.total_route_ids)

            # Check MTO
            mto_route = line.maintenance_id.warehouse_id.mto_pull_id.route_id
            if not mto_route:
                try:
                    mto_route = self.env['stock.warehouse']._find_global_route('stock.route_warehouse0_mto', _('Make To Maintenance'))
                except UserError:
                    # if route MTO not found in ir_model_data, we treat the product as in MTS
                    pass

            if mto_route and mto_route in product_routes:
                line.is_mto = True
            else:
                line.is_mto = False

    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return ''
        vals = {}
        if not self.product_uom_id or (self.product_id.uom_id.id != self.product_uom_id.id):
            vals['product_uom_id'] = self.product_id.uom_id.id
            vals['product_qty'] = self.product_qty or 1.0
        product = self.product_id.with_context(
            lang=get_lang(self.env, self.maintenance_id.driver_id.lang or self.maintenance_id.user_id.partner_id.lang).code,
            partner=self.maintenance_id.driver_id or self.maintenance_id.user_id.partner_id,
            quantity=vals.get('product_qty') or self.product_qty,
            date=self.maintenance_id.request_date,
            uom=self.product_uom_id.id
        )
        format_product = "[{0}] {1}".format(self.product_id.default_code, self.product_id.name)
        self.name = format_product

        vals.update(name=self.get_sale_order_line_multiline_description_sale(product))

        title = False
        message = False
        result = {}
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s") % product.name
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.maintenance_line_warn == 'block':
                self.product_id = False
        return result

    @api.onchange('product_uom_id', 'product_qty')
    def product_uom_change(self):
        if not self.product_uom_id or not self.product_id:
            return ''
        if self.maintenance_id.driver_id or self.maintenance_id.user_id.partner_id.id:
            product = self.product_id.with_context(
                lang=self.maintenance_id.driver_id.lang or self.maintenance_id.user_id.partner_id.lang,
                partner=self.maintenance_id.driver_id or self.maintenance_id.urser_id.partner_id,
                quantity=self.product_qty,
                date=self.maintenance_id.request_date,
                uom=self.product_uom_id.id,
            )

    @api.onchange('product_qty')
    def _onchange_product_uom_qty(self):
        # When modifying a one2many, _origin doesn't guarantee that its values will be the ones
        # in database. Hence, we need to explicitly read them from there.
        if self._origin:
            product_uom_qty_origin = self._origin.read(["product_qty"])[0]["product_qty"]
        else:
            product_uom_qty_origin = 0

        if self.state == 'sale' and self.product_id.type in ['product', 'consu'] and self.product_qty < product_uom_qty_origin:
            warning_mess = {
                'title': _('Ordered quantity decreased!'),
                'message': _(
                    'The quantity ordered is decreasing! Be sure to manually update the maintenance order if necessary.'),
            }
            return {'warning': warning_mess}
        return {}


    def get_sale_order_line_multiline_description_sale(self, product):
        """ Compute a default multiline description for this sales order line.

        In most cases the product description is enough but sometimes we need to append information that only
        exists on the sale order line itself.
        e.g:
        - custom attributes and attributes that don't create variants, both introduced by the "product configurator"
        - in event_sale we need to know specifically the sales order line as well as the product to generate the name:
          the product is not sufficient because we also need to know the event_id and the event_ticket_id (both which belong to the sale order line).
        """
        return product.get_product_multiline_description_sale()

    def _get_protected_fields(self):
        return ['product_id', 'name', 'product_uom_id', 'product_qty']

    def _prepare_procurement_values(self, group_id=False):
        values = {}
        self.ensure_one()
        values.update({
            'group_id': group_id,
            'maintenance_line_id': self.id,
            'date_planned': self.maintenance_id.request_date,
            'route_ids': self.route_id,
            'warehouse_id': self.maintenance_id.warehouse_id or False,
            'partner_id': self.maintenance_id.driver_id.id or self.maintenance_id.user_id.partner_id.id,
            'company_id': self.maintenance_id.company_id,
        })
        return values

    def _get_qty_procurement(self, previous_product_uom_qty=False):
        self.ensure_one()
        qty = 0.0
        outgoing_moves, incoming_moves = self._get_outgoing_incoming_moves()
        for move in outgoing_moves:
            qty += move.product_uom_id._compute_quantity(move.product_uom_qty, self.product_uom_id, rounding_method='HALF-UP')
        for move in incoming_moves:
            qty -= move.product_uom_id._compute_quantity(move.product_uom_qty, self.product_uom_id, rounding_method='HALF-UP')
        return qty

    def _get_outgoing_incoming_moves(self):
        outgoing_moves = self.env['stock.move']
        incoming_moves = self.env['stock.move']

        for move in self.move_ids.filtered(lambda r: r.state != 'cancel' and not r.scrapped and self.product_id == r.product_id):
            if move.location_dest_id.usage == "customer":
                if not move.origin_returned_move_id or (move.origin_returned_move_id and move.to_refund):
                    outgoing_moves |= move
            elif move.location_dest_id.usage != "customer" and move.to_refund:
                incoming_moves |= move
        return outgoing_moves, incoming_moves

    def _get_procurement_group(self):
        return self.maintenance_id.procurement_group_id

    def _prepare_procurement_group_vals(self):
        return {
            'name': self.maintenance_id.name,
            'move_type': self.maintenance_id.picking_policy,
            'maintenance_id': self.maintenance_id.id,
            'partner_id': self.maintenance_id.driver_id.id or self.maintenance_id.user_id.partner_id.id,
        }

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        for line in self:
            if line.state != 'process' or not line.product_id.type in ('consu', 'product'):
                continue
            qty = line._get_qty_procurement(previous_product_uom_qty)
            if float_compare(qty, line.product_qty, precision_digits=precision) >= 0:
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.maintenance_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.maintenance_id.drive_id:
                    updated_vals.update({'partner_id': line.maintenance_id.drive_id.id})
                if group_id.move_type != line.maintenance_id.picking_policy:
                    updated_vals.update({'move_type': line.maintenance_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            values = line._prepare_procurement_values(group_id=group_id)
            product_qty = line.product_qty - qty

            line_uom = line.product_uom_id
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
            procurements.append(self.env['procurement.group'].Procurement(
                line.product_id, product_qty, procurement_uom, line.maintenance_id.user_id.partner_id.property_stock_customer,
                line.name, line.maintenance_id.name, line.maintenance_id.company_id, values))

        if procurements:
            self.env['procurement.group'].run(procurements)
        return True

    def _expected_date(self):
        self.ensure_one()
        order_date = fields.Datetime.from_string(self.maintenance_id.request_date if self.maintenance_id.stage_id == 1 or self.maintenance_id.stage_id == 4 else fields.Datetime.now())
        return order_date + timedelta(days=self.customer_lead or 0.0)






