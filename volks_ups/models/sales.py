from odoo import api, fields, models
from odoo.addons.account.models import exceptions
from odoo.addons.base.models.ir_model import IrModel
from odoo.exceptions import UserError, ValidationError


class ManageSales(models.Model):
    _name = 'manage.sales'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Sales Record'
    
    sale_quo_id = fields.Char(string='Quotation ID', required=True, tracking=True)
    sale_quo_date= fields.Char(string='Tanggal Penawaran', tracking=True)
    sale_quo_number = fields.Char(string='Nomor Penawaran', tracking=True)
    sale_quo_ref = fields.Char(string= 'Referensi dari Prinsipal', tracking=True)
    sale_quo_contact_id = fields.Char(string= 'Ref table contact', tracking=True)
    sale_quo_brand_id = fields.Char(string= 'Ref table brand', tracking=True)
    sale_quo_project_id = fields.Char(string= 'Ref table project', tracking=True)
    sale_quo_sales_id = fields.Char(string= 'Ref table user', tracking=True)
    sale_quo_location_id = fields.Char(string= 'Ref table city/regency', tracking=True)
    sale_quo_margin = fields.Integer(string= 'Margin Penawaran')
    sale_quo_kurs = fields.Integer(string='Exchange Rate')
    sale_salesincentive = fields.Integer(string='Sales Incentive')
    sale_agentincentive = fields.Integer(string='Agent Incentive')
    sale_quo_oh_permission = fields.Integer(string='Permission')
    sale_quo_oh_onsite = fields.Integer(string='Onsite Expense')
    sale_quo_oh_engineer = fields.Integer(string='Engineer Expense')
    sale_quo_oh_advance = fields.Integer(string='Advance Expense')
    sale_quo_oh_others = fields.Integer(string='Others Expense')
    sale_quo_installation = fields.Integer(string='Installation Unit Expense')
    sale_quo_remarks = fields.Text(string='Remarks')
    subtotal = fields.Float(string='Subtotal (Tanpa Pajak)', compute='_compute_subtotal', store=True)
    tax_11_percent = fields.Integer(string='Pajak 11%', compute='_compute_tax_11_percent', store=True)
    total_with_tax = fields.Float(string='Total Dengan Pajak', compute='_compute_total_with_tax',store=True)
    state = fields.Selection([
                    ('draft', 'Quoted'), ('done', 'Done'), ('cancel', 'Cancel')
                            ], default='draft', tracking=True)
    
    def write(self, values):
        for order in self:
            if order.state == 'done':
                raise UserError("You cannot edit a quotation that is already completed.")
        return super(ManageSales, self).write(values)
    
    def unlink(self):
        for order in self:
            if order.state == 'done':
                raise UserError("You cannot delete a quotation that is already completed.")
        return super(ManageSales, self).unlink()
    
    def write(self, values):
        for order in self:
            if order.state == 'cancel':
                raise UserError("You cannot edit a quotation that is already cancelling.")
        return super(ManageSales, self).write(values)
    
    def unlink(self):
        for order in self:
            if order.state == 'cancel':
                raise UserError("You cannot delete a quotation that is already completed.")
        return super(ManageSales, self).unlink()
   
    def action_done(self):
        for rec in self:
            rec.state = 'done'
            
    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            
    def _compute_access_url(self):
        super()._compute_access_url()
        for order in self:
            order.access_url = f'/my/orders/{order.id}'
    
    @api.depends('sale_quo_installation', 'sale_quo_margin')
    def _compute_subtotal(self):
        for record in self:
            # Menghitung subtotal (total tanpa pajak)
            record.subtotal = record.sale_quo_margin * record.sale_quo_installation

    @api.depends('subtotal')
    def _compute_tax_11_percent(self):
        for record in self:
            # Menghitung pajak 11% dari subtotal
            record.tax_11_percent = record.subtotal * 0.11  # 11% pajak

    @api.depends('subtotal', 'tax_11_percent')
    def _compute_total_with_tax(self):
        for record in self:
            # Menghitung total akhir dengan pajak 11%
            record.total_with_tax = record.subtotal + record.tax_11_percent