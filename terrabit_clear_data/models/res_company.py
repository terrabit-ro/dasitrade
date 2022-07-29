from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def unlink(self):
        if self.env["ir.module.module"].search([("name", "=", "stock"), ("state", "=", "installed")]):
            warehouses = self.env["stock.warehouse"].sudo().search([("company_id", "in", self.ids)])
            rules = self.env["stock.rule"].sudo().search([("warehouse_id", "in", warehouses.ids)])
            rules.unlink()
            warehouses.unlink()
        users = self.env["res.users"].sudo().with_context(active_test=False).search([("company_id", "in", self.ids)])
        users.write({"company_ids": [(4, self.env.user.company_id.id, False)]})
        users.write({"company_id": self.env.user.company_id.id})
        if self.env["ir.module.module"].search([("name", "=", "website"), ("state", "=", "installed")]):
            website = self.env["website"].sudo().search([("company_id", "in", self.ids)])
            website.unlink()
        if self.env["ir.module.module"].search([("name", "=", "account"), ("state", "=", "installed")]):
            accounts = (
                self.env["account.account"]
                .sudo()
                .with_context(active_test=False)
                .search([("company_id", "in", self.ids)])
            )

            values = ["account.account,%s" % (account_id,) for account_id in accounts.ids]
            partner_prop_acc = (
                self.env["ir.property"]
                .sudo()
                .with_context(active_test=False)
                .search([("value_reference", "in", values)])
            )
            if partner_prop_acc:
                partner_prop_acc.unlink()
            accounts.unlink()
        return super(ResCompany, self).unlink()
