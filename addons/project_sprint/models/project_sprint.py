from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProjectSprint(models.Model):
    _name = 'project.sprint'
    _description = 'Project Sprint'
    _order = 'date_start desc'

    name = fields.Char(string='Name', required=True)
    team_id = fields.Many2one(
        'project.team',
        string='Team',
        required=True,
        ondelete='restrict',
    )
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    goal = fields.Text(string='Sprint Goal')
    task_ids = fields.One2many(
        'project.task',
        'sprint_id',
        string='Tasks',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
    )

    task_count = fields.Integer(
        string='Task Count',
        compute='_compute_metrics',
        store=True,
    )
    points_total = fields.Integer(
        string='Total Points',
        compute='_compute_metrics',
        store=True,
    )
    points_done = fields.Integer(
        string='Done Points',
        compute='_compute_metrics',
        store=True,
    )
    progress = fields.Float(
        string='Progress',
        compute='_compute_metrics',
        store=True,
    )

    committed_points = fields.Integer(string='Committed Points', readonly=True)
    delivered_points = fields.Integer(string='Delivered Points', readonly=True)

    member_ids = fields.Many2many(
        'res.users',
        string='Sprint Members',
        compute='_compute_members',
    )
    borrowed_member_ids = fields.Many2many(
        'res.users',
        string='Borrowed Members',
        compute='_compute_members',
    )

    carried_over_task_ids = fields.Many2many(
        'project.task',
        string='Carried Over Tasks',
        compute='_compute_carried_over_task_ids',
    )

    @api.depends('task_ids.story_points', 'task_ids.state')
    def _compute_metrics(self):
        for sprint in self:
            tasks = sprint.task_ids.filtered(lambda t: t.state != '1_canceled')
            done_tasks = tasks.filtered(lambda t: t.state == '1_done')
            sprint.task_count = len(tasks)
            sprint.points_total = sum(tasks.mapped('story_points'))
            sprint.points_done = sum(done_tasks.mapped('story_points'))
            if sprint.points_total:
                sprint.progress = sprint.points_done / sprint.points_total * 100
            else:
                sprint.progress = 0.0

    @api.depends('task_ids.user_ids', 'team_id.member_ids')
    def _compute_members(self):
        for sprint in self:
            members = sprint.task_ids.user_ids._origin
            sprint.member_ids = members
            sprint.borrowed_member_ids = members - sprint.team_id.member_ids

    @api.depends('task_ids')
    def _compute_carried_over_task_ids(self):
        for sprint in self:
            sprint.carried_over_task_ids = self.env['project.task'].search([
                ('sprint_history_ids', 'in', sprint._origin.id),
                ('sprint_id', '!=', sprint._origin.id),
            ])

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for sprint in self:
            if sprint.date_end < sprint.date_start:
                raise ValidationError(_("The end date must be after the start date."))

    @api.constrains('date_start', 'date_end', 'team_id', 'state')
    def _check_overlap(self):
        for sprint in self:
            if sprint.state == 'cancelled':
                continue
            domain = [
                ('team_id', '=', sprint.team_id.id),
                ('id', '!=', sprint.id),
                ('state', '!=', 'cancelled'),
                ('date_start', '<=', sprint.date_end),
                ('date_end', '>=', sprint.date_start),
            ]
            if self.search_count(domain):
                raise ValidationError(_("This sprint overlaps with another sprint of the same team."))

    @api.constrains('team_id', 'state')
    def _check_single_active(self):
        for sprint in self:
            if sprint.state == 'active':
                domain = [
                    ('id', '!=', sprint.id),
                    ('team_id', '=', sprint.team_id.id),
                    ('state', '=', 'active')
                ]
                if self.search_count(domain):
                    raise ValidationError(_("This team already has an active sprint"))

    def action_start(self):
        for sprint in self:
            sprint.write({
                'state': 'active',
                'committed_points': sprint.points_total,
            })

    def action_done(self):
        self.ensure_one()
        open_tasks = self.task_ids.filtered(lambda t: not t.is_closed)
        if not open_tasks:
            self.write({'state': 'done', 'delivered_points': self.points_done})
            return True

        next_sprint = self.search([
            ('team_id', '=', self.team_id.id),
            ('state', '=', 'draft'),
            ('date_start', '>=', self.date_end),
        ], order='date_start', limit=1)

        if next_sprint:
            destination = 'next_sprint'
        else:
            destination = 'backlog'

        return {
            'type': 'ir.actions.act_window',
            'name': _('Close Sprint'),
            'res_model': 'project.sprint.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sprint_id': self.id,
                'default_next_sprint_id': next_sprint.id,
                'default_destination': destination,
            },
        }

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_create_next_sprint(self):
        self.ensure_one()
        count = self.search_count([('team_id', '=', self.team_id.id)])
        duration = self.date_end - self.date_start
        start = self.date_end + timedelta(days=1)
        next_sprint = self.create({
            'team_id': self.team_id.id,
            'name': _("%(team)s - Sprint %(number)s", team=self.team_id.name, number=count + 1),
            'date_start': start,
            'date_end': start + duration,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.sprint',
            'res_id': next_sprint.id,
            'view_mode': 'form',
            'target': 'current',
        }