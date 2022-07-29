import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class DataClear(models.TransientModel):
    _name = "ir.data.clear"
    _description = "Data clear"

    ok = fields.Boolean("Sunt sigur ca vreau sa sterg datele!")
    bom = fields.Boolean("Sterge LDM")

    all_prod = fields.Boolean(string="Sterge toate produsele")
    pf = fields.Boolean(string="Sterge produse finite")
    sf = fields.Boolean(string="Sterge semifabricate")

    all_part = fields.Boolean(string="Stergere parteneri")

    doc_stock = fields.Boolean(string="Sterge documente stoc", default=True)
    doc_sale = fields.Boolean(string="Sterge documente vanzare", default=True)
    doc_purchase = fields.Boolean(string="Sterge documente achizitie", default=True)
    doc_invoice = fields.Boolean(string="Sterge facturi", default=True)
    doc_account = fields.Boolean(string="Sterge documente contabile", default=True)
    doc_proiecte = fields.Boolean(string="Sterge proiecte", default=True)

    load_demo = fields.Boolean("Load data data")
    reset_website = fields.Boolean("Reset website")

    def do_reset_website(self):
        sql = """
            delete from ir_ui_view
            WHERE type = 'qweb' and website_id is not null and arch_updated is null ;


             update ir_ui_view
             set arch_updated = false;

        """
        # pylint: disable=E8103
        self.env.cr.execute(sql)

    def do_clear(self):
        # de adaugat un obiect de autorizare

        if not self.ok:
            return
        _logger.warning("======= Stergere Date =======")
        sql = ""

        if self.doc_stock:
            self.del_stock_step1()

        if self.doc_sale:
            self.del_sale()

        if self.doc_invoice:
            self.del_invoice()

        if self.doc_account:
            self.del_account_extrase()

        if self.doc_purchase:
            self.del_purchase()

        if self.doc_sale:
            if self.env["ir.module.module"].search([("name", "=", "stock_landed_costs"), ("state", "=", "installed")]):
                sql += "delete from stock_landed_cost;"

            if self.env["ir.module.module"].search(
                [("name", "=", "website_sale_wishlist"), ("state", "=", "installed")]
            ):
                sql += "delete from product_wishlist;"

        if self.doc_account:
            self.del_account_nc()

        product_mod = self.env["ir.module.module"].search([("name", "=", "product"), ("state", "=", "installed")])

        if self.env["ir.module.module"].search([("name", "=", "queue_job"), ("state", "=", "installed")]):
            sql += "delete from queue_job;"

        if self.env["ir.module.module"].search([("name", "=", "deltatech_queue_job"), ("state", "=", "installed")]):
            sql += "delete from queue_job;"

        # if self.doc_purchase or self.doc_stock:
        #
        #     if product_mod:
        #         sql += """
        #             delete from product_price_history;
        #         """

        if self.doc_stock:
            if self.env["ir.module.module"].search([("name", "=", "stock"), ("state", "=", "installed")]):
                sql += """
                    delete from stock_change_product_qty;
                   -- delete from stock_inventory;
                """

            if self.env["ir.module.module"].search([("name", "=", "deltatech_stock_inventory"), ("state", "=", "installed")]):
                sql += """
                   delete from stock_inventory;
                """

        if self.doc_proiecte:
            if self.env["ir.module.module"].search([("name", "=", "project"), ("state", "=", "installed")]):
                sql += """
                    delete from project_task;
                    delete from project_project;
                """

            if self.env["ir.module.module"].search([("name", "=", "hr_timesheet"), ("state", "=", "installed")]):
                sql += """
                    delete from account_analytic_line;
                """

        if self.doc_invoice:
            if self.env["ir.module.module"].search([("name", "=", "deltatech_service"), ("state", "=", "installed")]):
                sql += """
                    delete from service_consumption;
                """

            if self.env["ir.module.module"].search([("name", "=", "deltatech_expenses"), ("state", "=", "installed")]):
                sql += "delete from deltatech_expenses_deduction;"

        if self.doc_stock:
            mrp_mod = self.env["ir.module.module"].search([("name", "=", "mrp"), ("state", "=", "installed")])
            if mrp_mod:
                sql += """
                    delete from change_production_qty;
                    delete from mrp_workorder;
                    delete from mrp_production;
                    delete from mrp_workcenter_productivity;
                """

                if self.bom:
                    sql += "delete from mrp_bom;"

        if product_mod:
            if self.all_prod:
                sql = self.del_all_products()

            if self.pf:
                category = self.env.ref("product.product_category_finish", raise_if_not_found=False)
                if category:
                    sql += "delete from product_template where categ_id = %s ;" % category.id
            if self.sf:
                category = self.env.ref("product.product_category_half", raise_if_not_found=False)
                if category:
                    sql += "delete from product_template where categ_id = %s ;" % category.id

        if self.all_part:
            exclude = []
            companii = self.env["res.company"].with_context(active_test=False).search([])
            for comp in companii:
                exclude += [comp.partner_id.id]
            users = self.env["res.users"].with_context(active_test=False).search([])
            for user in users:
                exclude += [user.partner_id.id]
            # pylint: disable=E8103
            sql = "delete from res_partner where id not in %s ; " % str(tuple(exclude))

        if self.env["ir.module.module"].search([("name", "=", "deltatech_kds"), ("state", "=", "installed")]):
            sql += """
                delete from kitchen_order;
                delete from kitchen_order_line;
            """

        sql += """
            delete from mail_activity;
            delete from mail_mail;
            delete from mail_message;

        """
        # pylint: disable=E8103
        self.env.cr.execute(sql)

        if self.load_demo:
            action = self.env.ref("base.demo_force_install_action").read()[0]
        else:
            action = True

        return action

    def del_stock_step1(self):
        if self.env["ir.module.module"].search([("name", "=", "stock"), ("state", "=", "installed")]):
            sql = """
                delete from stock_move;
                delete from mail_followers where res_model = 'stock.move';
                delete from stock_move_line;

                delete from stock_quant;
                delete from stock_production_lot;
                delete from stock_package_level;
                delete from stock_quant_package;


                delete from stock_picking;
                delete from mail_followers where res_model = 'stock.picking';
                delete from procurement_group;
                delete from stock_valuation_layer;
            """
            _logger.info(" Stergere Stocuri ")
            self.env.cr.execute(sql)
            # pylint: disable=E8102
            self.env.cr.commit()

    def del_sale(self):

        if self.env["ir.module.module"].search([("name", "=", "sale"), ("state", "=", "installed")]):
            _logger.info(" Stergere vanzari ")
            sql = """
                 delete from payment_transaction;
                 delete from sale_order;
                 delete from mail_followers where res_model = 'sale.order';
            """
            self.env.cr.execute(sql)
            # pylint: disable=E8102
            self.env.cr.commit()

        if self.env["ir.module.module"].search([("name", "=", "sale_management"), ("state", "=", "installed")]):
            sql = """
                delete from sale_order_template;
                delete from sale_order_template_line;
                delete from sale_order_template_option;
            """
            self.env.cr.execute(sql)

        pos_mod = self.env["ir.module.module"].search([("name", "=", "point_of_sale"), ("state", "=", "installed")])
        if pos_mod:
            sql = """
            delete from pos_payment;
            delete from pos_order;
            delete from pos_make_payment;
            delete from pos_session;
            delete from account_cashbox_line;
            """
            self.env.cr.execute(sql)

    def del_invoice(self):

        if self.env["ir.module.module"].search([("name", "=", "account"), ("state", "=", "installed")]):
            sql = """
                -- delete from account_analytic_tag_account_invoice_line_rel;
                delete from account_partial_reconcile;
               -- delete from account_invoice_line;
               -- delete from account_invoice;
                delete from mail_followers where res_model = 'account.invoice';
            """
            _logger.info(" Stergere documente : facturi  ")
            self.env.cr.execute(sql)
            # pylint: disable=E8102
            self.env.cr.commit()

        if self.env["ir.module.module"].search([("name", "=", "account_voucher"), ("state", "=", "installed")]):
            sql = """
            delete from account_voucher;
            delete from mail_followers where res_model = 'account.voucher';
            """
            self.env.cr.execute(sql)
            # pylint: disable=E8102
            self.env.cr.commit()

    def del_account_extrase(self):

        if self.env["ir.module.module"].search([("name", "=", "account"), ("state", "=", "installed")]):
            sql = """
                delete from account_bank_statement_line;
                delete from account_bank_statement;
               -- delete from account_bank_statement_import;  nu mai este in 14.0
            """
            _logger.info(" Stergere etrase ")
            self.env.cr.execute(sql)

    def del_account_nc(self):

        if self.env["ir.module.module"].search([("name", "=", "account"), ("state", "=", "installed")]):
            sql = """
                     -- update account_invoice set move_id = null ;
                     delete from account_move;
                     delete from account_payment;
                 """
            _logger.info(" Stergere note contabile ")
            self.env.cr.execute(sql)

    def del_purchase(self):

        if self.env["ir.module.module"].search([("name", "=", "purchase"), ("state", "=", "installed")]):
            sql = """
            delete from purchase_order;
            delete from mail_followers where res_model = 'purchase.order';
            """
            _logger.info(" Stergere achizitii ")
            self.env.cr.execute(sql)

    def del_all_products(self):

        sql = """

        delete from product_template where type <> 'service';
        delete from mail_followers where res_model = 'product.template';

        """
        _logger.info(" Stergere produse ")
        self.env.cr.execute(sql)

        return sql
