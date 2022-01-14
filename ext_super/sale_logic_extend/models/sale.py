from odoo import api, fields, models


class SaleOrderLogicExtend(models.Model):
    _inherit = 'sale.order'

    seller_id = fields.Many2one(comodel_name='res.partner', string='Seller Name')
    date_start = fields.Date(string='Date Start')
    date_end = fields.Date(string='Date End')
    estimated_date = fields.Date(string='Estimated Delivery Date')

    @api.onchange('partner_id')
    def onchange_seller_id(self):
        if self.partner_id.assigned_seller_id.id:
            self.seller_id = self.partner_id.assigned_seller_id.id
            self.user_id = self.partner_id.assigned_seller_id.user_id.id
            self.team_id = self.partner_id.assigned_seller_id.team_id.id
        else:
            self.seller_id = False
            self.user_id = False
            self.team_id = False
