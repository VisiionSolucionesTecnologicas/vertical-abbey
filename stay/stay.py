# -*- encoding: utf-8 -*-
##############################################################################
#
#    Stay module for Odoo
#    Copyright (C) 2014 Artisanat Monastique de Provence
#                       (http://www.barroux.org)
#    @author: Alexis de Lattre <alexis.delattre@akretion.com>
#    @author: Brother Bernard <informatique@barroux.org>
#    @author: Brother Irénée
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning


class StayStay(models.Model):
    _name = 'stay.stay'
    _description = 'Guest Stay'
    _order = 'arrival_date desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Stay Number', readonly=True, default='/', copy='/')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'stay.stay'))
    partner_id = fields.Many2one(
        'res.partner', string='Guest',
        help="If guest is anonymous, leave this field empty.")
    partner_name = fields.Char(
        'Guest Name', required=True, track_visibility='onchange')
    guest_qty = fields.Integer(
        string='Guest Quantity', default=1, track_visibility='onchange')
    arrival_date = fields.Date(
        string='Arrival Date', required=True, track_visibility='onchange')
    arrival_time = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
        ], string='Arrival Time', required=True, track_visibility='onchange')
    departure_date = fields.Date(
        string='Departure Date', required=True, track_visibility='onchange')
    departure_time = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
        ], string='Departure Time', required=True, track_visibility='onchange')
    room_id = fields.Many2one(
        'stay.room', string='Room', track_visibility='onchange')
    line_ids = fields.One2many(
        'stay.line', 'stay_id', string='Stay Lines')

    @api.model
    def create(self, vals=None):
        if vals is None:
            vals = {}
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('stay.stay')
        return super(StayStay, self).create(vals)

    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = self.env['ir.sequence'].next_by_code('stay.stay')
        return super(StayStay, self).copy(default)

    @api.one
    @api.constrains('departure_date', 'arrival_date')
    def _check_stay_date(self):
        if self.arrival_date >= self.departure_date:
            raise Warning(
                _('Arrival date (%s) must be earlier than departure date (%s)')
                % (self.arrival_date, self.departure_date))

    _sql_constraints = [(
        'name_company_uniq', 'unique(name, company_id)',
        'A stay with this number already exists for this company.')]

    @api.onchange('partner_id')
    def _partner_id_change(self):
        if self.partner_id:
            self.partner_name = self.partner_id.name_get()[0][1]


class StayRefectory(models.Model):
    _name = 'stay.refectory'
    _description = 'Refectory'

    code = fields.Char(string='Code', size=10)
    name = fields.Char(string='Name', required=True)
    capacity = fields.Integer(string='Capacity')
    active = fields.Boolean(default=True)

    _sql_constraints = [(
        'code_uniq', 'unique(code)',
        'A refectory with this code already exists.')]

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.code:
                name = u'[%s] %s' % (record.code, name)
            res.append((record.id, name))
        return res

    @api.model
    def name_search(
            self, name='', args=None, operator='ilike', limit=80):
        if name:
            refs = self.search(
                [('code', '=', name)] + args, limit=limit)
            if refs:
                return refs.name_get()
        return super(StayRefectory, self).name_search(
            name=name, args=args, operator=operator, limit=limit)


class StayRoom(models.Model):
    _name = 'stay.room'
    _description = 'Room'

    code = fields.Char(string='Code', size=10, copy=False)
    name = fields.Char(string='Name', required=True, copy=False)
    bed_qty = fields.Integer(string='Number of beds', default='1')
    active = fields.Boolean(default=True)

    _sql_constraints = [(
        'code_uniq', 'unique(code)',
        'A room with this code already exists.')]

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.code:
                name = u'[%s] %s' % (record.code, name)
            res.append((record.id, name))
        return res

    @api.model
    def name_search(
            self, name='', args=None, operator='ilike', limit=80):
        if name:
            rooms = self.search(
                [('code', '=', name)] + args, limit=limit)
            if rooms:
                return rooms.name_get()
        return super(StayRoom, self).name_search(
            name=name, args=args, operator=operator, limit=limit)


class StayLine(models.Model):
    _name = 'stay.line'
    _description = 'Stay Journal'
    _rec_name = 'partner_name'
    _order = 'date desc'

    @api.model
    def _default_refectory(self):
        company_id = self.env['res.company']._company_default_get(
            'stay.stay')
        company = self.env['res.company'].browse(company_id)
        return company.default_refectory_id

    stay_id = fields.Many2one('stay.stay', string='Stay')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self:
        self.env['res.company']._company_default_get('stay.line'))
    date = fields.Date(
        string='Date', required=True, default=fields.Date.context_today)
    lunch_qty = fields.Integer(string='Lunches')
    dinner_qty = fields.Integer(string='Dinners')
    bed_night_qty = fields.Integer(string='Bed Nights')
    partner_id = fields.Many2one(
        'res.partner', string='Guest',
        help="If guest is anonymous, leave this field empty.")
    partner_name = fields.Char('Guest Name', required=True)
    refectory_id = fields.Many2one(
        'stay.refectory', string='Refectory', default=_default_refectory)
    room_id = fields.Many2one('stay.room', string='Room')

    @api.one
    @api.constrains(
        'refectory_id', 'lunch_qty', 'dinner_qty', 'date', 'room_id')
    def _check_room_refectory(self):
        if (self.lunch_qty or self.dinner_qty) and not self.refectory_id:
            raise Warning(
                _("Missing refectory for guest '%s' on %s.")
                % (self.partner_name, self.date))
        if self.room_id and self.bed_night_qty:
            same_room_same_day_line = self.search([
                ('date', '=', self.date),
                ('room_id', '=', self.room_id.id),
                ('bed_night_qty', '!=', False)])
            guests_in_room_qty = 0
            for same_room in same_room_same_day_line:
                guests_in_room_qty += same_room.bed_night_qty
            if guests_in_room_qty > self.room_id.bed_qty:
                raise Warning(
                    _("The room '%s' is booked or all beds of the "
                        "room are booked")
                    % self.room_id.name)

    _sql_constraints = [
        ('lunch_qty_positive', 'CHECK (lunch_qty >= 0)',
            'The number of lunches must be positive or null'),
        ('dinner_qty_positive', 'CHECK (dinner_qty >= 0)',
            'The number of dinners must be positive or null'),
        ('bed_night_qty_positive', 'CHECK (bed_night_qty >= 0)',
            'The number of bed nights must be positive or null'),
    ]

    @api.onchange('partner_id')
    def _partner_id_change(self):
        if self.partner_id:
            self.partner_name = self.partner_id.name_get()[0][1]
