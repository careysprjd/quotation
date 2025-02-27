from odoo import api, fields, models

class UolaInvoice(models.Model):
    _name = 'uola.invoice'
    _description = 'Uola Sales Invoice'
    
    uola_invoice_id = fields.Char(string='Invoice ID')
    uola_invoice_number = fields.Char(string='Invoice No.', default='New')
    uola_invoice_date = fields.Char(string='Invoice Date')
    company_id = fields.Many2one('res.partner', string="Company")
    partner_id = fields.Many2one('project.project', string="Project")
    uola_invoice_po_number = fields.Char(string='PO. No.')
    uola_invoice_do_number = fields.Char(string='DO. No.')
    uola_invoice_telp = fields.Char(string='Telp/Fax')
    uola_invoice_payment_terms = fields.Char('Due Date')
    uola_invoice_currency = fields.Char(string='Currency')
    uola_invoice_item_description = fields.Char(string='Item Description')
    uola_invoice_qty = fields.Char(string='Qty')
    uola_invoice_unit_price = fields.Char(string='Unit Price')
    uola_invoice_amount = fields.Char(string='Amount')
    uola_invoice_bank_account = fields.Char(string='Bank Account')
    uola_invoice_say = fields.Char(string='Say')
    uola_invoice_discount = fields.Char(string='Discount')
    uola_invoice_payment = fields.Char(string='Payment')
    uola_invoice_freight = fields.Char(string='Freight')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # untuk membuat angka berurutan cth (S0001)
            if not vals.get('uola_invoice_number') or vals['uola_invoice_number'] == 'New':
                vals['uola_invoice_number'] = self.env['ir.sequence'].next_by_code('uola.invoice')
        return super().create(vals_list)