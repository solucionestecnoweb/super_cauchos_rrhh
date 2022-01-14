from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import base64
from odoo.exceptions import UserError, ValidationError, Warning, except_orm
from odoo.tools.float_utils import float_round

class PurchasePayOrder(models.Model):
    _name = 'purchase.pay.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Request Number', default='/')

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Requesting User', default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))
    request_date = fields.Date(string='Request Date', default=fields.Date.today())
    cancel_date = fields.Date(string='Cancel Date')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.user.company_id)
    payment_reference = fields.Selection(string='Payment Reference', selection=[('invoice', 'Invoice'), ('purchase_order', 'Purchase Order')], default='invoice')
    invoice_id = fields.Many2one(comodel_name='account.move', string='Invoice')
    order_id = fields.Many2one(comodel_name='purchase.order', string='Purchase Order')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
    rate = fields.Float(string='Tasa', default=lambda x: x.env['res.currency.rate'].search([('name', '<=', fields.Date.today()), ('currency_id', '=', 2)], limit=1).sell_rate)

    pay_order_lines_ids = fields.One2many(comodel_name='purchase.pay.order.lines', inverse_name='pay_order_id', string='Requisition Lines')
    amount_total = fields.Float(string='Amount Total', compute='_compute_amount_total')
    current_debt = fields.Float(string='Deuda Restante', compute='_compute_current_debt')
    
    total_debt_invoice = fields.Monetary(string='Total Debt', store=True, related='invoice_id.amount_total')
    currency_invoice = fields.Many2one(comodel_name='res.currency', string='Currency', related='invoice_id.currency_id')    
    total_debt_order = fields.Monetary(string='Total Debt', store=True, related='order_id.amount_total')
    currency_order = fields.Many2one(comodel_name='res.currency', string='Currency', related='order_id.currency_id')
    
    state = fields.Selection([ ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled')], default='draft')
    
    def _compute_amount_total(self):
        for item in self:
            amount = 0
            for line in item.pay_order_lines_ids:
                if item.currency_id.id == 3:
                    if item.currency_id.id == item.invoice_id.currency_id.id or item.currency_id.id == item.order_id.currency_id.id:
                        amount += line.amount
                    else:
                        amount += line.amount / item.rate
                else:
                    if item.currency_id.id == item.invoice_id.currency_id.id or item.currency_id.id == item.order_id.currency_id.id:
                        amount += line.amount
                    else:
                        amount += line.amount * item.rate
            item.amount_total = amount

    def _compute_current_debt(self):
        for item in self:
            if item.total_debt_invoice:
                item.current_debt = item.total_debt_invoice - item.amount_total
            else:
                item.current_debt = item.total_debt_order - item.amount_total

    @api.onchange('payment_reference')
    def _clean_reference(self):
        self.invoice_id = False
        self.order_id = False

    @api.constrains('amount_total', 'pay_order_lines_ids')
    def _constrains_amount_total(self):
        for item in self:
            if item.payment_reference == 'invoice':
                if item.amount_total > item.invoice_id.amount_total:
                    raise Warning(_('The total amount does not match the invoice'))
            elif item.payment_reference == 'purchase_order':
                if item.amount_total > item.order_id.amount_total:
                    raise Warning(_('The total amount does not match the purchase order'))

    @api.constrains('state')
    def _compute_name(self):
        if self.name == '/':
            self.name = self.env['ir.sequence'].next_by_code('purchase.pay.orders.sequence')
    
    def reset_draft(self):
        for item in self:
            item.state = 'draft'

    def action_confirmed(self):
        for item in self:
            item.state = 'confirmed'
    
    def action_done(self):
        for item in self:
            for line in item.pay_order_lines_ids:
                if not line.pay_date:
                    item.pay_order_lines_ids.pay_date = fields.Date.today()
            item.state = 'done'
    
    def action_cancel(self):
        for item in self:
            item.state = 'cancel'

class PurchasePayOrderLines(models.Model):
    _name = 'purchase.pay.order.lines'

    amount = fields.Float(string='Amount')
    pay_date = fields.Date(string='Pay Date')
    pay_order_id = fields.Many2one(comodel_name='purchase.pay.order', string='Pay Order')
    currency_id = fields.Many2one('res.currency', related='pay_order_id.currency_id')
