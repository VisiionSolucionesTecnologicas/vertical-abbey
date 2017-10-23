# -*- coding: utf-8 -*-
# © 2014-2017 Barroux Abbey (www.barroux.org)
# © 2014-2017 Akretion France (www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MassJournalValidate(models.TransientModel):
    _name = 'mass.journal.validate'
    _description = "Validate Masses Journal"

    @api.model
    def _get_default_journal_date(self):
        lines = self.env['mass.line'].search(
            [('state', '=', 'draft')], limit=1, order='date asc')
        if lines:
            default_str = lines[0].date
        else:
            default_str = fields.Date.context_today(self)
        return default_str

    journal_date = fields.Date(
        'Journal Date', required=True, default=_get_default_journal_date)

    @api.model
    def _prepare_mass_validation_move(self, company, date, lines):
        movelines = []
        stock_aml = {}  # key = account_id, value = amount
        income_aml = {}
        # key = (account_id, analytic_account_id) value = amount
        income_account_id = company.mass_validation_account_id.id
        for line in lines:
            stock_account_id = line.request_id.stock_account_id.id or False
            analytic_account_id = \
                line.request_id.analytic_account_id.id or False

            if stock_account_id:
                if stock_account_id in stock_aml:
                    stock_aml[stock_account_id] += line.unit_offering
                else:
                    stock_aml[stock_account_id] = line.unit_offering

                if (income_account_id, analytic_account_id) in income_aml:
                    income_aml[(income_account_id, analytic_account_id)] +=\
                        line.unit_offering
                else:
                    income_aml[(income_account_id, analytic_account_id)] =\
                        line.unit_offering

        name = _('Masses celebrated on %s') % date
        for stock_account_id, stock_amount in stock_aml.iteritems():
            movelines.append((0, 0, {
                'name': name,
                'credit': 0,
                'debit': stock_amount,
                'account_id': stock_account_id,
                }))

        # counter-part
        for (income_account_id, analytic_account_id), income_amount in\
                income_aml.iteritems():

            movelines.append(
                (0, 0, {
                    'debit': 0,
                    'credit': income_amount,
                    'name': name,
                    'account_id': income_account_id,
                    'analytic_account_id': analytic_account_id,
                    }))

        vals = {
            'journal_id': company.mass_validation_journal_id.id,
            'date': date,
            'period_id': self.env['account.period'].find(dt=date).id,
            'ref': _('Masses'),
            'line_id': movelines,
            }
        return vals

    def validate_journal(self):
        self.ensure_one()
        date = self.journal_date
        company = self.env.user.company_id
        # Search draft mass lines on the date of the wizard
        lines = self.env['mass.line'].search(
            [('date', '=', date), ('company_id', '=', company.id)])
        move_id = False
        if company.mass_validation_account_id:
            # Loop on result to compute the total amount
            if not company.mass_validation_journal_id:
                raise UserError(_(
                    "Missing Mass Validation Journal on company '%s'.")
                    % company.name)
            # Create account move
            move_vals = self._prepare_mass_validation_move(
                company, date, lines)
            move = self.env['account.move'].create(move_vals)
            move_id = move.id

        # Update mass lines
        lines.write({'state': 'done', 'move_id': move_id})

        action = self.env['ir.actions.act_window'].for_xml_id(
            'mass', 'mass_line_action')
        action.update({
            'domain': [('id', 'in', lines.ids)],
            })
        return action
