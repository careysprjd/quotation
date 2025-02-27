from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import logging
import math

_logger = logging.getLogger(__name__)

# reusable selection options
TERM_OPTIONS = [
    ('1', "0 (nol)"),
    ('2', "½ (setengah)"),
    ('3', "1 (satu)"),
    ('4', "1½ (satu setengah)"),
    ('5', "2 (dua)"),
    ('6', "2½ (dua setengah)"),
    ('7', "3 (tiga)"),
    ('8', "3½ (tiga setengah)"),
    ('9', "4 (empat)"),
    ('10', "4½ (empat setengah)"),
    ('11', "5 (lima)"),
    ('12', "5½ (lima setengah)"),
    ('13', "6 (enam)"),
    ('14', "7 (tujuh)"),
    ('15', "8 (delapan)"),
    ('16', "9 (sembilan)"),
    ('17', "10 (sepuluh)"),
    ('18', "11 (sebelas)"),
    ('19', "12 (dua belas)"),
    ('20', "15 (lima belas)"),
    ('21', "18 (delapan belas)"),
    ('22', "21 (dua puluh satu)"),
    ('23', "24 (dua puluh empat)"),
    ('24', "30 (tiga puluh)"),
    ('25', "36 (tiga puluh enam)")
]
class UolaQuotation(models.Model):
    _name = 'uola.base.sale.quotation'
    _description = 'Uola Sales Quotation'

    # def action_preview_quotation(self):
    #     _logger.info("Preview button clicked")
    #     report = self.env.ref('uola_sale_quotation.uola_report_sales_quot_preview')
    #     return report.report_action(self)
    
    # def action_download_quotation(self):
    #     _logger.info("Download button clicked")
    #     report = self.env.ref('uola_sale_quotation.uola_report_sales_quot_with_alt')
    #     return report.report_action(self)
    
    # def action_download_quotation_noalt(self):
    #     _logger.info("Download button without alt unit clicked")
    #     report = self.env.ref('uola_sale_quotation.uola_report_sales_quot_without_alt')
    #     return report.report_action(self)

    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    
    # Quotation Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('quoted', 'Quoted'),
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('cancel', 'Cancelled'),
    ], string="Status", default="draft", readonly=True, index=True)

    # Customer Field
    partner_id = fields.Many2one('res.partner', string="Customer", required=True) # Autocomplete search

    # Relation Field
    project_id = fields.Many2one('project.project', string="Project", required=True)  # Autocomplete search
    quo_city_id = fields.Many2one('res.city', string="Project Location", required=True) # Autocomplete search
    brand_id = fields.Char(string="Brand", required=True)  # Autocomplete search (later)

    # Hubungkan ke res.users
    salesman_id = fields.Many2one('res.users', string="Salesman")
    salesinfo_id = fields.Many2one('res.users', string="Sales Info")

    # Simpan Initial User ID tetapi tetap diperbarui jika salesman_id/salesinfo_id berubah
    salesman_initial = fields.Char(string="Salesman Initial", compute="_compute_initials", store=True)
    salesinfo_initial = fields.Char(string="Sales Info Initial", compute="_compute_initials", store=True)

    # Quotation Line Relation Detail
    quotation_main_unit_ids = fields.One2many('uola.base.sale.quotation.main.line', 'quotation_line_main_id', string="Quotation Main Units")  # Main unit relation
    quotation_alt_unit_ids = fields.One2many('uola.base.sale.quotation.alt.line', 'quotation_line_alt_id', string="Quotation Alternative Units")  # Alternative unit relation
    quotation_payment_unit_ids = fields.One2many('uola.base.sale.quotation.payment.unit', 'quotation_term_unit_id', string="Payment Units")  # unit payment
    quotation_payment_inst_ids = fields.One2many('uola.base.sale.quotation.payment.installation', 'quotation_term_inst_id', string="Payment Units")  # install payment
    quotation_schedule_term_ids = fields.One2many('uola.base.sale.quotation.term.schedule', 'quotation_term_schedule_id', string="Schedule")  # Schedule
    quotation_warranty_term_ids = fields.One2many('uola.base.sale.quotation.term.warranty', 'quotation_term_warranty_id', string="Warranty")  # Warranty
    quotation_validity_term_ids = fields.One2many('uola.base.sale.quotation.term.validity', 'quotation_term_validity_id', string="Validity")  # Validity

    # Core quotation fields
    number = fields.Char(string="Quotation Number", required=True) # Manual input (Automatic Later)
    visnumber = fields.Char(string="VIS Number Ref", required=True)  # Manual input
    base_quotation_date = fields.Date(string="Date", required=True)  # Manual input

    # Margin and floating factor
    margin = fields.Float(string="Margin", required=True, default=30)  # Manual input
    floatingfactor = fields.Float(string="Floating Factor", required=True, default=4)  # Automatic invisible

    # Exchange rates
    today_rate_cny = fields.Float(string="CNY Rate Today", digits=(16, 0), readonly=True)  # Automatic
    today_rate_usd = fields.Float(string="USD Rate Today", digits=(16, 0), readonly=True)  # Automatic
    sales_rate_cny = fields.Float(string="CNY Rate Sales", digits=(16, 0), required=True)  # Sales can edit
    sales_rate_usd = fields.Float(string="USD Rate Sales", digits=(16, 0), required=True)  # Sales can edit
    lock_rate_cny = fields.Float(string="CNY Rate Lock", digits=(16, 0), readonly=True)  # Manual lock by button
    lock_rate_usd = fields.Float(string="USD Rate Lock", digits=(16, 0), readonly=True)  # Manual lock by button

    is_locked = fields.Boolean(string="Rates Locked", default=False) #Lock Rate Control

    # Incentive fields
    sales_incentive_main = fields.Float(string="Sales Incentive Main Unit", digits=(16, 0), compute='_compute_sales_incentive')  # Automatic
    sales_incentive_alt = fields.Float(string="Sales Incentive Alt Unit", digits=(16, 0), compute='_compute_sales_incentive')  # Automatic
    agent_incentive_percentage = fields.Float(string="Agent Incentive Percentage", default=0)  # Manual input
    agent_incentive = fields.Float(string="Agent Incentive", digits=(16, 0), compute='_compute_agent_incentive')  # Automatic

    # Project Budget fields
    quo_total_overhead = fields.Float(string='Overhead Budget', digits=(16, 0), compute='_compute_overhead_budget')  # Automatic
    quo_budget_permission = fields.Float(string='Permission Budget', digits=(16, 0), default=0)  # Manual input
    quo_budget_onsite = fields.Float(string='On-site Budget', digits=(16, 0), default=0)  # Manual input
    quo_budget_engineer = fields.Float(string='Engineer Budget', digits=(16, 0), default=0)  # Manual input
    quo_budget_adv = fields.Float(string='Advertisement Budget', digits=(16, 0), default=0)  # Manual input
    quo_budget_others = fields.Float(string='Others Budget', digits=(16, 0), default=0)  # Manual input
    remarks_permission = fields.Char(string='Permission Remarks')  # Manual input
    remarks_onsite = fields.Char(string='On-site Remarks')  # Manual input
    remarks_engineer = fields.Char(string='Engineer Remarks')  # Manual input
    remarks_adv = fields.Char(string='Advertisement Remarks')  # Manual input
    remarks_others = fields.Char(string='Others Remarks')  # Manual input

    # Total rawprice fields
    total_rawprice_unit_main = fields.Float(string="Total Unit (Main)", digits=(16, 0), compute='_compute_totalrawprice_unit_main')  # Automatic

    # Total rawprice fields
    total_qty_main = fields.Float(string="Qty Unit (Main)", digits=(16, 0), compute='_compute_total_qty_main')  # Automatic

    #Total Price for Unit & Install before Tax
    subtotal_price_unit_main = fields.Float(string="Subtotal Unit Price", digits=(16, 0), compute='_compute_totalprice_unit_bt')  # Automatic
    subtotal_price_inst_main = fields.Float(string="Subtotal Instal Price", digits=(16, 0), compute='_compute_totalprice_inst_bt')  # Automatic

    #Tax 11% - 2025
    uola_quo_tax_unit = fields.Float(string="Tax Units", digits=(16, 0), compute='_compute_uola_tax')  # Automatic
    uola_quo_tax_inst = fields.Float(string="Tax Instal", digits=(16, 0), compute='_compute_uola_tax')  # Automatic

    #Total
    uola_quo_total_unit = fields.Float(string="Total Units Quotation", digits=(16, 0), compute='_compute_uola_total')  # Automatic
    uola_quo_total_inst = fields.Float(string="Total Instal Quotation", digits=(16, 0), compute='_compute_uola_total')  # Automatic

    @api.depends('salesman_id', 'salesinfo_id')
    def _compute_initials(self):
        for record in self:
            record.salesman_initial = record.salesman_id.initial_user_id if record.salesman_id and record.salesman_id.initial_user_id else ' '
            record.salesinfo_initial = record.salesinfo_id.initial_user_id if record.salesinfo_id and record.salesinfo_id.initial_user_id else ' '

    @api.model
    def default_get(self, fields):
        """
        Override default_get to prepopulate payment terms when creating a new quotation.
        """
        res = super(UolaQuotation, self).default_get(fields)

        # Default data for Payment Unit
        payment_unit_defaults = [
            (0, 0, {'term_category_id': 1, 'percentage': 30}),
            (0, 0, {'term_category_id': 2, 'percentage': 65}),
            (0, 0, {'term_category_id': 3, 'percentage': 5}),
        ]
        res['quotation_payment_unit_ids'] = payment_unit_defaults

        # Default data for Payment Installation
        payment_install_defaults = [
            (0, 0, {'term_category_id': 1, 'percentage': 30}),
            (0, 0, {'term_category_id': 3, 'percentage': 65}),
            (0, 0, {'term_category_id': 5, 'percentage': 5}),
        ]
        res['quotation_payment_inst_ids'] = payment_install_defaults

        # Default data for Schedule
        schedule_default = [
            (0, 0, {'term_production': '7', 'term_delivery': '3', 'term_instalandtc': '4'}),
        ]
        res['quotation_schedule_term_ids'] = schedule_default

        # Default data for Warranty
        warranty_default = [
            (0, 0, {'term_unitwarranty_bast': '19', 'term_unitwarranty_shipment': '21', 'term_free_maintenance': '7'}),
        ]
        res['quotation_warranty_term_ids'] = warranty_default

        # Default data for Validity
        validity_default = [
            (0, 0, {'term_validityperiod': '2'}),
        ]
        res['quotation_validity_term_ids'] = validity_default

        return res
    
    # Validasi Payment Units dan Payment Installations
    @api.constrains('quotation_payment_unit_ids', 'quotation_payment_inst_ids')
    def _check_payment_percentage(self):
        for record in self:
            total_unit_percentage = sum(unit.percentage for unit in record.quotation_payment_unit_ids)
            total_installation_percentage = sum(install.percentage for install in record.quotation_payment_inst_ids)

            if total_unit_percentage != 100:
                raise ValidationError(
                    f"Total Payment Unit Percentage must be 100%. Current: {total_unit_percentage}%"
                )
            if total_unit_percentage != 100:
                raise ValidationError(
                    f"Total Payment Installation Percentage must be 100%. Current: {total_installation_percentage}%"
                )
    
    @api.constrains('quotation_payment_unit_ids', 'quotation_payment_inst_ids')
    def _onchange_payment_percentage(self):
        total_unit_percentage = sum(unit.percentage for unit in self.quotation_payment_unit_ids)
        total_installation_percentage = sum(install.percentage for install in self.quotation_payment_inst_ids)

        if total_unit_percentage > 100:
            return {'warning': {'title': "Warning", 'message': "Total Payment Unit Percentage exceeds 100%."}}

        if total_installation_percentage > 100:
            return {'warning': {'title': "Warning", 'message': "Total Payment Installation Percentage exceeds 100%."}}
         
    # Prevent setting margin below allowed levels
    @api.onchange('margin')
    def _onchange_margin(self):
        """
        Prevents setting margin below the allowed level for sales and managers.
        """
        user = self.env.user
        group_sales = self.env.ref('sales_team.group_sale_salesman')
        group_manager = self.env.ref('sales_team.group_sale_manager')

        if user.has_group('sales_team.group_sale_salesman') and self.margin < 5.0:
            self.margin = 5.0
            return {'warning': {'title': "Margin too low!", 'message': "Sales margin cannot be below 5.00%."}}

        if user.has_group('sales_team.group_sale_manager') and self.margin < 0.0:
            self.margin = 0.0
            return {'warning': {'title': "Margin too low!", 'message': "Manager margin cannot be below 0.00%."}}

    @api.constrains('margin')
    def _check_margin(self):
        """
        Ensures that margin is not saved below the allowed level for sales and managers.
        """
        for record in self:
            user = self.env.user
            group_sales = self.env.ref('sales_team.group_sale_salesman')
            group_manager = self.env.ref('sales_team.group_sale_manager')

            if user.has_group('sales_team.group_sale_salesman') and self.margin < 5.0:
                raise ValidationError("Sales margin must be at least 5.00%.")
            if user.has_group('sales_team.group_sale_manager') and record.margin < 0.0:
                raise ValidationError("Manager margin must be at least 0.00%.")
    
    @api.constrains('margin', 'sales_rate_usd', 'sales_rate_cny')
    def _validate_margin_and_rates(self):
        for record in self:
            if record.margin < 0 or record.margin > 100:
                raise ValidationError("Margin must be between 0 and 100%.")
            if record.sales_rate_usd < 0 or record.sales_rate_cny < 0:
                raise ValidationError("Sales rates cannot be negative.")

    # Update Today Rate on create or update
    @api.onchange('project_id', 'is_locked')
    def _onchange_project_id(self):
        """
        Update today rates when the project_id is selected or changed.
        """
        if self.project_id and not self.is_locked:
            bca_kurs_model = self.env['uola.bca.kurs']
            usd_rate = bca_kurs_model.search([('currency', '=', 'USD')], order='date desc', limit=1)
            cny_rate = bca_kurs_model.search([('currency', '=', 'CNY')], order='date desc', limit=1)

            self.today_rate_usd = usd_rate.tt_sell if usd_rate else 0
            self.today_rate_cny = cny_rate.tt_sell if cny_rate else 0

            self.sales_rate_usd = usd_rate.tt_sell if usd_rate else 0
            self.sales_rate_cny = cny_rate.tt_sell if cny_rate else 0

    @api.constrains('sales_rate_usd', 'sales_rate_cny')
    def _check_sales_rate(self):
        """
        Ensure sales rates are not lower than today's rates.
        """
        for record in self:
            if record.sales_rate_usd < record.today_rate_usd:
                raise ValidationError("USD Sales Rate cannot be lower than Today's Rate.")
            if record.sales_rate_cny < record.today_rate_cny:
                raise ValidationError("CNY Sales Rate cannot be lower than Today's Rate.")

    @api.depends('is_locked')
    def _compute_rates(self):
        """
        Update today rates when `is_locked` changes.
        """
        for record in self:
            if not record.is_locked:
                bca_kurs_model = self.env['uola.bca.kurs']
                usd_rate = bca_kurs_model.search([('currency', '=', 'USD')], order='date desc', limit=1)
                cny_rate = bca_kurs_model.search([('currency', '=', 'CNY')], order='date desc', limit=1)

                record.today_rate_usd = usd_rate.tt_sell if usd_rate else 0
                record.today_rate_cny = cny_rate.tt_sell if cny_rate else 0
                record.sales_rate_usd = usd_rate.tt_sell if usd_rate else 0
                record.sales_rate_cny = cny_rate.tt_sell if cny_rate else 0
                
    def action_lock_rates(self):
        """
        Lock rates to prevent further changes.
        """
        for record in self:
            # Pastikan today_rate tetap tidak berubah
            if not record.today_rate_usd or not record.today_rate_cny:
                bca_kurs_model = self.env['uola.bca.kurs']
                usd_rate = bca_kurs_model.search([('currency', '=', 'USD')], order='date desc', limit=1)
                cny_rate = bca_kurs_model.search([('currency', '=', 'CNY')], order='date desc', limit=1)

                record.today_rate_usd = usd_rate.tt_sell if usd_rate else record.today_rate_usd
                record.today_rate_cny = cny_rate.tt_sell if cny_rate else record.today_rate_cny

            # Tetapkan lock rates berdasarkan sales rates
            record.lock_rate_usd = record.sales_rate_usd
            record.lock_rate_cny = record.sales_rate_cny
            record.is_locked = True

    def action_unlock_rates(self):
        """
        Unlock rates for editing (admin only).
        """
        for record in self:
            record.is_locked = False
            record.lock_rate_usd = 0
            record.lock_rate_cny = 0
            record._compute_rates()
            _logger.info(f"Updated rates: USD {record.today_rate_usd}, CNY {record.today_rate_cny}")

    # Compute overhead budget
    @api.depends('quo_budget_permission', 'quo_budget_onsite', 'quo_budget_engineer', 'quo_budget_adv', 'quo_budget_others')
    def _compute_overhead_budget(self):
        """
        Computes the total overhead budget by summing all budget categories.
        """
        for record in self:
            record.quo_total_overhead = (
                record.quo_budget_permission
                + record.quo_budget_onsite
                + record.quo_budget_engineer
                + record.quo_budget_adv
                + record.quo_budget_others
            )

    # Compute sales incentive Main Unit
    @api.depends('margin', 'quotation_main_unit_ids', 'quotation_alt_unit_ids')
    def _compute_sales_incentive(self):
        """
        Compute sales incentives for both main and alternative units.
        """
        for record in self:
            total_main = sum(line.buql_subtotal_unitprice for line in record.quotation_main_unit_ids)
            total_alt = sum(line.buql_subtotal_unitprice for line in record.quotation_alt_unit_ids)

            record.sales_incentive_main = total_main * (record.margin / 1000)
            record.sales_incentive_alt = total_alt * (record.margin / 1000)

    # Compute agent incentive
    @api.depends('agent_incentive_percentage', 'quotation_main_unit_ids')
    def _compute_agent_incentive(self):
        """
        Computes the agent incentive as:
        Agent Incentive = Agent Incentive Percentage * Sum of (Raw Price Unit + Raw Price Component) for all Main Units
        """
        for record in self:
            total_base_price = sum(line.buql_subtotal_unitprice for line in record.quotation_main_unit_ids)
            record.agent_incentive = (record.agent_incentive_percentage / 100) * total_base_price

    # Compute total rawprice for main units
    @api.depends('quotation_main_unit_ids.buql_rawprice_total', 'quotation_main_unit_ids.buql_qty')
    def _compute_totalrawprice_unit_main(self):
        """
        Computes the total rawprice of all main units in the quotation.
        """
        for record in self:
            record.total_rawprice_unit_main = sum(line.buql_rawprice_total for line in record.quotation_main_unit_ids)

    # Compute subtotal price for unit before tax
    @api.depends('quotation_main_unit_ids.buql_subtotal_unitprice')
    def _compute_totalprice_unit_bt(self):
        """
        Computes subtotal price of all units in the quotation.
        """
        for record in self:
            record.subtotal_price_unit_main = sum(line.buql_subtotal_unitprice for line in record.quotation_main_unit_ids)

    # Compute subtotal price for installation before tax
    @api.depends('quotation_main_unit_ids.buql_subtotal_instalprice')
    def _compute_totalprice_inst_bt(self):
        """
        Computes subtotal price of all installs in the quotation.
        """
        for record in self:
            record.subtotal_price_inst_main = sum(line.buql_subtotal_instalprice for line in record.quotation_main_unit_ids)

    # Tax Compute 11% - 2025
    @api.depends('subtotal_price_unit_main', 'subtotal_price_inst_main')
    def _compute_uola_tax(self):
        """
        Tax Computing.
        """
        for record in self:
            tax = 11 #percentage
            tax_compute = tax/100
            record.uola_quo_tax_unit = record.subtotal_price_unit_main*tax_compute
            record.uola_quo_tax_inst = record.subtotal_price_inst_main*tax_compute
    
    # Total Qty Main
    @api.depends('quotation_main_unit_ids.buql_qty')
    def _compute_total_qty_main(self):
        """
        Tax Computing.
        """
        for record in self:
            record.total_qty_main = sum(line.buql_qty for line in record.quotation_main_unit_ids)

    # Total Price Quotation
    @api.depends('subtotal_price_unit_main', 'subtotal_price_inst_main', 'uola_quo_tax_unit', 'uola_quo_tax_inst')
    def _compute_uola_total(self):
        """
        Total Quotation Price Computing.
        """
        for record in self:
            record.uola_quo_total_unit = record.subtotal_price_unit_main + record.uola_quo_tax_unit
            record.uola_quo_total_inst = record.subtotal_price_inst_main + record.uola_quo_tax_inst

    def action_set_quoted(self):
        """ Ubah status ke 'quoted' """
        self.write({'status': 'quoted'})

    def action_set_won(self):
        """ Ubah status ke 'won' """
        self.write({'status': 'won'})

    def action_set_lost(self):
        """ Ubah status ke 'lost' """
        self.write({'status': 'lost'})

    def action_set_cancel(self):
        """ Ubah status ke 'cancel' """
        self.write({'status': 'cancel'})

    def action_set_quoted(self):
        if self.status != 'draft':
            raise ValidationError("You can only mark as Quoted if the status is Draft.")
        self.write({'status': 'quoted'})

class UolaQuotationMainLine(models.Model):
    _name = 'uola.base.sale.quotation.main.line'
    _description = 'Uola Sales Quotation Main Unit'
    _rec_name = 'buql_unitcode'

    # Relation fields
    quotation_line_main_id = fields.Many2one('uola.base.sale.quotation', string="Quotation Reference", required=True, ondelete='cascade')
    alt_unit_ids = fields.One2many('uola.base.sale.quotation.alt.line', 'main_unit_id', string="Alternative Units")

    # Fields
    #   Unit
    #       Unit Price Component
    buql_unitcode = fields.Char(string="Unit Code", required=True)  # Manual input
    buql_desc = fields.Char(string="Unit Description", required=True)  # Manual input
    buql_rawprice = fields.Float(string="Raw Price", digits=(16, 0), required=True) # Manual input
    buql_qty = fields.Float(string="Quantity", digits=(16, 0), required=True)  # Manual input
    buql_additionalprice = fields.Float(string="Additional Price", digits=(16, 0), default=0)  # Manual input
    #       Unit Calculation Component
    buql_rawprice_tocny = fields.Float(string="Raw Price CNY", digits=(16, 0), compute='_compute_rawprice_tocny', store=True)  # Automatic
    buql_rawprice_total = fields.Float(string="Raw Price Total", digits=(16, 0), compute='_compute_rawprice_total', store=True) # Automatic
    buql_oh_allocation = fields.Float(string="Overhead Allocation", digits=(16, 0), compute='_compute_oh_allocation', store=True)  # Automatic
    buql_unitprice = fields.Float(string="Unit Price", digits=(16, 0) , compute='_compute_unit_price', store=True)  # Automatic
    buql_subtotal_unitprice = fields.Float(string="Subtotal Unit Price", digits=(16, 0), compute='_compute_subtotalprice_unit', store=True)  # Automatic
    #   Installation
    #       Installation Component
    buql_installation_price = fields.Float(string="Installation Price (IDR)", digits=(16, 0), required=True)  # Manual input
    #       Installation Calculation Component
    buql_subtotal_instalprice = fields.Float(string="Subtotal Installation Price", digits=(16, 0), compute='_compute_subtotalprice_instal', store=True)  # Automatic

    # Compute rawprice IDR to CNY for base data
    @api.depends('buql_rawprice', 'buql_qty')
    def _compute_rawprice_tocny(self):
        for record in self:
            if record.quotation_line_main_id and record.quotation_line_main_id.today_rate_cny > 0:
                record.buql_rawprice_tocny = record.buql_rawprice / record.quotation_line_main_id.today_rate_cny
            else:
                record.buql_rawprice_tocny = 0.0

    # Compute total rawprice follow lock rate CNY
    @api.depends('buql_rawprice_tocny', 'buql_qty')
    def _compute_rawprice_total(self):
        for record in self:
            if record.quotation_line_main_id:
                rate_cny = record.quotation_line_main_id.lock_rate_cny if record.quotation_line_main_id.lock_rate_cny > 0 else record.quotation_line_main_id.today_rate_cny
                rate_floating = rate_cny*1.04 #Floating Factor 4 percent
                if rate_cny > 0 and record.buql_rawprice_tocny > 0:
                    record.buql_rawprice_total = (record.buql_rawprice_tocny * rate_floating) * record.buql_qty
                else:
                    record.buql_rawprice_total = 0.0

    # Compute overhead allocation
    @api.depends('quotation_line_main_id.quotation_main_unit_ids.buql_rawprice_total', 'quotation_line_main_id.quotation_main_unit_ids.buql_qty', 'quotation_line_main_id.quo_total_overhead', 'quotation_line_main_id.total_rawprice_unit_main')
    def _compute_oh_allocation(self):
        for record in self:
            total_rawprice = record.quotation_line_main_id.total_rawprice_unit_main
            total_overhead = record.quotation_line_main_id.quo_total_overhead

            if total_rawprice > 0 and record.buql_rawprice_total > 0:
                record.buql_oh_allocation = total_overhead * (record.buql_rawprice_total / total_rawprice)
            else:
                record.buql_oh_allocation = 0.0

    def write(self, vals):
        result = super(UolaQuotationMainLine, self).write(vals)

        if 'buql_rawprice' in vals or 'buql_qty' in vals:
            related_lines = self.mapped('quotation_line_main_id.quotation_main_unit_ids')
            related_lines._compute_oh_allocation()
            related_lines._compute_unit_price()

        return result

    # Compute unit price for main lines
    @api.depends('buql_qty', 'buql_rawprice_total', 'buql_oh_allocation', 'buql_additionalprice', 'quotation_line_main_id.margin', 'quotation_line_main_id.agent_incentive_percentage')
    def _compute_unit_price(self):
        """
        Computes the total price of each main unit, including adjustment, overhead allocation,
        sales incentive, and agent incentive, rounded up to the nearest thousand.
        """
        for record in self:
            if record.quotation_line_main_id.lock_rate_cny and record.buql_qty > 0:
                # Base Price
                base_price = (record.buql_rawprice_total + record.buql_oh_allocation) / record.buql_qty
                # Sales Incentive
                sales_inc = record.quotation_line_main_id.margin * 0.1
                # Unit Price
                denominator = 100 - record.quotation_line_main_id.margin - sales_inc - record.quotation_line_main_id.agent_incentive_percentage
                if denominator > 0:
                    unit_price = (base_price + record.buql_additionalprice) / (denominator/100)
                else:
                    unit_price = 0.0
                # Round Up
                record.buql_unitprice = math.ceil(unit_price / 1000) * 1000
            else:
                record.buql_unitprice = 0

    # Compute subtotal unit price
    @api.depends('buql_unitprice', 'buql_qty')
    def _compute_subtotalprice_unit(self):
        for record in self:
            record.buql_subtotal_unitprice = record.buql_unitprice * (record.buql_qty if record.buql_qty > 0 else 0)

    # Compute subtotal installation price
    @api.depends('buql_installation_price', 'buql_qty')
    def _compute_subtotalprice_instal(self):
        for record in self:
            record.buql_subtotal_instalprice = record.buql_installation_price * (record.buql_qty if record.buql_qty > 0 else 0)

class UolaQuotationAltLine(models.Model):
    _name = 'uola.base.sale.quotation.alt.line'
    _description = 'Uola Sales Quotation Alternative Unit'
    _rec_name = 'buql_unitcode'

    # Relation fields
    quotation_line_alt_id = fields.Many2one('uola.base.sale.quotation', string="Quotation Reference", required=True, ondelete='cascade')
    main_unit_id = fields.Many2one('uola.base.sale.quotation.main.line', string="Main Unit", domain="[('quotation_line_main_id', '=', parent.id)]", ondelete='cascade')

    # Fields
    #   Unit Price Component
    buql_unitcode = fields.Char(string="Unit Code", required=True)  # Manual input
    buql_desc = fields.Char(string="Unit Description", required=True)  # Manual input
    buql_rawprice = fields.Float(string="Raw Price", digits=(16, 0), required=True)  # Manual input
    buql_qty = fields.Float(string="Quantity", digits=(16, 0), required=True)  # Manual input
    buql_additionalprice = fields.Float(string="Additional Price (IDR)", digits=(16, 0), default=0)  # Manual input

    # Unit Calculation Component
    buql_rawprice_tocny = fields.Float(string="Raw Price CNY", digits=(16, 0), compute='_compute_rawprice_alt_tocny', store=True)  # Automatic
    buql_rawprice_total = fields.Float(string="Raw Price Total", digits=(16, 0), compute='_compute_rawprice_alt_total', store=True)  # Automatic
    buql_oh_allocation = fields.Float(string="Overhead Allocation", digits=(16, 0), compute='_compute_alt_oh_allocation', store=True)  # Automatic
    buql_unitprice = fields.Float(string="Unit Price", compute='_compute_alt_unit_price', digits=(16, 0), store=True)  # Automatic
    buql_subtotal_unitprice = fields.Float(string="Subtotal Unit Price", digits=(16, 0), compute='_compute_subtotalprice_alt_unit', store=True)  # Automatic

    # Installation Component
    buql_installation_price = fields.Float(string="Installation Price (IDR)", digits=(16, 0), required=True)  # Manual input
    buql_subtotal_instalprice = fields.Float(string="Subtotal Installation Price", digits=(16, 0), compute='_compute_subtotalprice_alt_instal', store=True)  # Automatic

    # Validasi quotation_line_alt_id
    @api.onchange('quotation_line_alt_id')
    def _onchange_quotation_line_alt_id(self):
        if self.quotation_line_alt_id:
            _logger.info(f"Domain applied to main_unit_id: {self.quotation_line_alt_id.id}")
            return {
                'domain': {
                    'main_unit_id': [('quotation_line_main_id', '=', self.quotation_line_alt_id.id)]
                }
            }

    # Compute rawprice IDR to CNY for base data
    @api.depends('buql_rawprice', 'buql_qty')
    def _compute_rawprice_alt_tocny(self):
        for record in self:
            if record.quotation_line_alt_id and record.quotation_line_alt_id.today_rate_cny > 0:
                record.buql_rawprice_tocny = record.buql_rawprice / record.quotation_line_alt_id.today_rate_cny
            else:
                record.buql_rawprice_tocny = 0.0

    # Compute total rawprice follow lock rate CNY
    @api.depends('buql_rawprice_tocny', 'buql_qty')
    def _compute_rawprice_alt_total(self):
        for record in self:
            if record.quotation_line_alt_id:
                rate_cny = record.quotation_line_alt_id.lock_rate_cny if record.quotation_line_alt_id.lock_rate_cny > 0 else record.quotation_line_alt_id.today_rate_cny
                rate_floating = rate_cny*1.04 #Floating Factor 4 percent
                if rate_cny > 0 and record.buql_rawprice_tocny > 0:
                    record.buql_rawprice_total = (record.buql_rawprice_tocny * rate_floating) * record.buql_qty
                else:
                    record.buql_rawprice_total = 0.0

    # Compute overhead allocation mengikuti konsep sebelumnya
    @api.depends('main_unit_id.buql_rawprice_total', 'buql_rawprice_total', 'buql_qty', 'quotation_line_alt_id.quo_total_overhead', 'quotation_line_alt_id.total_rawprice_unit_main')
    def _compute_alt_oh_allocation(self):
        """
        Menghitung alokasi overhead untuk unit alternatif berdasarkan aturan sebelumnya:
        - OH unit alternatif dihitung berdasarkan perbandingan rawprice terhadap total rawprice unit utama.
        - Jika tidak ada Main Unit yang terkait, maka OH alternatif diberikan 0.
        """
        for record in self:
            if record.main_unit_id and record.quotation_line_alt_id.total_rawprice_unit_main:
                total_oh = record.quotation_line_alt_id.quo_total_overhead
                total_rawprice_main = record.quotation_line_alt_id.total_rawprice_unit_main

                # Rawprice yang disesuaikan
                adjusted_rawprice = (
                    total_rawprice_main
                    - record.main_unit_id.buql_rawprice_total
                    + record.buql_rawprice_total
                )

                # OH untuk unit utama
                oh_main = record.main_unit_id.buql_oh_allocation

                # OH untuk unit alternatif berdasarkan rawprice yang disesuaikan
                if adjusted_rawprice > 0 and record.buql_qty > 0 and record.buql_rawprice_total > 0:
                    oh_alt = total_oh * (record.buql_rawprice_total / adjusted_rawprice)
                    # Pilih OH yang lebih besar
                    record.buql_oh_allocation = max(oh_main, oh_alt)
                else:
                    record.buql_oh_allocation = 0.0
            else:
                record.buql_oh_allocation = 0.0

    # Compute unit price for alternative units
    @api.depends('buql_qty', 'buql_rawprice_total', 'buql_oh_allocation', 'buql_additionalprice', 'quotation_line_alt_id.margin', 'quotation_line_alt_id.agent_incentive_percentage')
    def _compute_alt_unit_price(self):
        for record in self:
            if record.quotation_line_alt_id.lock_rate_cny and record.buql_qty > 0:
                base_price = (record.buql_rawprice_total + record.buql_oh_allocation) / record.buql_qty
                sales_inc = record.quotation_line_alt_id.margin * 0.1
                denominator = 100 - record.quotation_line_alt_id.margin - sales_inc - record.quotation_line_alt_id.agent_incentive_percentage
                if denominator > 0:
                    unit_price = (base_price + record.buql_additionalprice) / (denominator / 100)
                else:
                    unit_price = 0.0
                record.buql_unitprice = math.ceil(unit_price / 1000) * 1000
            else:
                record.buql_unitprice = 0

    # Compute subtotal unit price
    @api.depends('buql_unitprice', 'buql_qty')
    def _compute_subtotalprice_alt_unit(self):
        for record in self:
            record.buql_subtotal_unitprice = record.buql_unitprice * (record.buql_qty if record.buql_qty > 0 else 0)

    # Compute subtotal installation price
    @api.depends('buql_installation_price', 'buql_qty')
    def _compute_subtotalprice_alt_instal(self):
        for record in self:
            record.buql_subtotal_instalprice = record.buql_installation_price * (record.buql_qty if record.buql_qty > 0 else 0)

#Payment Category
class UolaQuotationPaymentCategory(models.Model):
    _name = 'uola.base.sale.quotation.payment.category'
    _description = 'Payment Category'
    _rec_name = 'name'

    name = fields.Char(string='Payment Category Name', required=True)
    description = fields.Char(string='Payment Category Description')

#Terms Payment For Unit
class UolaQuotationTermPaymentUnit(models.Model):
    _name = 'uola.base.sale.quotation.payment.unit'
    _description = 'Terms Payment - Unit'

    quotation_term_unit_id = fields.Many2one('uola.base.sale.quotation', string="Quotation Reference", required=True, ondelete='cascade')
    term_category_id = fields.Many2one('uola.base.sale.quotation.payment.category', string="Payment Category", required=True, ondelete='cascade')
    percentage = fields.Integer(string="Percentage", required=True)

    @api.constrains('term_payment_unit_lines')
    def _check_unit_term_payment_percentage(self):
        """
        Validasi agar total persentase term payment untuk Unit harus 100%
        """
        for record in self:
            total_percentage = sum(line.percentage for line in record.term_payment_unit_lines)
            if total_percentage != 100:
                raise ValidationError(
                    f"Total persentase Term Payment untuk Unit harus 100%. Saat ini: {total_percentage}%"
                )

#Terms Payment For Installation
class UolaQuotationTermPaymentInstallation(models.Model):
    _name = 'uola.base.sale.quotation.payment.installation'
    _description = 'Terms Payment - Installation'

    quotation_term_inst_id = fields.Many2one('uola.base.sale.quotation', string="Quotation Reference", required=True, ondelete='cascade')
    term_category_id = fields.Many2one('uola.base.sale.quotation.payment.category', string="Payment Category", required=True, ondelete='cascade')
    percentage = fields.Integer(string="Percentage", required=True)

    @api.constrains('term_payment_installation_lines')
    def _check_installation_term_payment_percentage(self):
        """
        Validasi agar total persentase term payment untuk Instalasi harus 100%
        """
        for record in self:
            total_percentage = sum(line.percentage for line in record.term_payment_installation_lines)
            if total_percentage != 100:
                raise ValidationError(
                    f"Total persentase Term Payment untuk Instalasi harus 100%. Saat ini: {total_percentage}%"
                )

#Terms For Time Schedule (Jadwal Pelaksanaan)
class UolaQuotationTermSchedule(models.Model):
    _name = 'uola.base.sale.quotation.term.schedule'
    _description = 'Terms - Schedule'

    quotation_term_schedule_id = fields.Many2one('uola.base.sale.quotation', string="Quotation Reference", required=True, ondelete='cascade')
    term_production = fields.Selection(TERM_OPTIONS, string="Production", default='7')
    term_delivery = fields.Selection(TERM_OPTIONS, string="Delivery", default='3')
    term_instalandtc = fields.Selection(TERM_OPTIONS, string="Instal & T/C", default='4')

#Terms For Warranty & Free Maintenance (Garansi dan Perawatan Berkala Gratis)
class UolaQuotationTermGuarantee(models.Model):
    _name = 'uola.base.sale.quotation.term.warranty'
    _description = 'Terms - Warranty'

    quotation_term_warranty_id = fields.Many2one('uola.base.sale.quotation', string="Quotation Reference", required=True, ondelete='cascade')
    term_unitwarranty_bast = fields.Selection(TERM_OPTIONS, string="Unit Warranty After BAST I", default='19')
    term_unitwarranty_shipment = fields.Selection(TERM_OPTIONS, string="Unit Warranty After Shipment", default='21')
    term_free_maintenance = fields.Selection(TERM_OPTIONS, string="Free Maintenance", default='7')

#Terms For Offer Validity Period (Masa Berlaku Penawaran)
class UolaQuotationTermValidityPeriod(models.Model):
    _name = 'uola.base.sale.quotation.term.validity'
    _description = 'Terms - Quotation Validity Periode'

    # reusable selection options
    TERM_VALID = [
        ('1', "½ (setengah)"),
        ('2', "1 (satu)"),
    ]

    quotation_term_validity_id = fields.Many2one('uola.base.sale.quotation', string="Quotation Reference", required=True, ondelete='cascade')
    term_validityperiod = fields.Selection(TERM_VALID, string="Quotation Validity Period", default='2')

class UolaSaleQuotationReport(models.AbstractModel):
    _name = 'report.uola_sale_quotation.uola_report_sales_quot_template'
    _description = 'Uola Sale Quotation Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['uola.base.sale.quotation'].browse(docids)
        company = self.env.company  # Mengambil data perusahaan aktif
        return {
            'doc_ids': docids,
            'doc_model': 'uola.base.sale.quotation',
            'docs': docs,
            'company': company,  # Pastikan company dimasukkan dalam konteks
        }