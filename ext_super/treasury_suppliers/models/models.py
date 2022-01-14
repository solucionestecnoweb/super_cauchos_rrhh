import json
from datetime import datetime, timedelta
import base64
from io import StringIO
from odoo import api, fields, models, _
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning
import time
from base64 import encodestring

class Suppliers(models.Model):
    _inherit ='account.payment'

    def send_email_recipt(self):
        company = self.env.user.company_id
        if self.partner_id.email:
            template = self.env.ref('treasury_suppliers.email_template_oasis_send_email', False)
            attachment_ids = []
            attach = {}

            result_pdf, type = self.env['ir.actions.report']._get_report_from_name('account_move_extend_fields_reports.account_payment_extend').render_qweb_pdf(self.id)
            attach['name'] = 'Recibo de Pago.pdf' 
            attach['type'] = 'binary'
            attach['datas'] = encodestring(result_pdf)
           # attach['datas_fname'] = 'Recibo de Pago.pdf' 
            attach['res_model'] = 'mail.compose.message'
            attachment_id = self.env['ir.attachment'].create(attach)
            attachment_ids.append(attachment_id.id)

            mail = template.send_mail(self.id, force_send=True,email_values={'attachment_ids': attachment_ids}) #envia mail
            if mail:
                self.message_post(body=_("Enviado email al Cliente: %s"%self.partner_id.name))
                self.state_dte_partner = 'sent'
                print('Correo Enviado a '+ str(self.partner_id.email))

    @api.onchange('partner_type', 'partner_id')
    def onchange_facturas(self):
        if self.partner_type == 'customer':
            res = {'domain':{'invoice_ids':[('type', '=', 'out_invoice'), ('invoice_payment_state', '=', 'not_paid'), ('state', '=', 'posted'), ('partner_id', '=', self.partner_id.id)]}}
            return res
        else:
            res = {'domain':{'invoice_ids':[('type', '=', 'in_invoice'), ('invoice_payment_state', '=', 'not_paid'), ('state', '=', 'posted'), ('partner_id', '=', self.partner_id.id)]}}
            return res

class InvoicesDisplayName(models.Model):
    _inherit ='account.move'

    def name_get(self):
        result = []
        for record in self:
            if record.type == 'in_invoice':
                # Only goes in when invoice is suppliers
                result.append((record.id, record.invoice_number_pro))
            elif record.type == 'out_invoice':
                # Only goes in when invoice is customer
                result.append((record.id, record.invoice_number_cli))
            else:
                result.append((record.id, record.name))
        return result